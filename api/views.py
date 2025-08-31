from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.throttling import UserRateThrottle
from .throttles import PostRequestThrottle
from .authentication import ClerkJWTAuthentication
from .management.validators import validate_domain_data
from django.shortcuts import get_object_or_404
from .models import Name, NewsLetter, PublicInquiry, SavedName, AcquiredName, UploadedFile, IdeaOfTheDay, UseCase
from .serializers import NameSerializer, AppUserSerializer, SavedNameLightSerializer, AcquiredNameSerializer, UseCaseSerializer, IdeaOfTheDayListSerializer, IdeaOfTheDaySerializer, NewsletterSerializer, PublicInquirySerializer, UseCaseListSerializer, UseCaseDetailSerializer, DashboardNameSerializer, NameSearchSerializer, UseCaseSearchSerializer
from .permissions import IsManagerOrReadOnly
from .pagination import StandardResultsSetPagination, IdeaPageNumberPagination
from .filters import UseCaseFilter
from django.contrib.postgres.search import SearchVector, SearchQuery, SearchRank


# Cache import
from django.core.cache import cache

from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from rest_framework.pagination import LimitOffsetPagination
from django.utils.dateparse import parse_date
from django.db.models import Q

from rest_framework import filters, generics, status # Filters import can be more explicitly done and avoid using filters. prefix by switching to "from rest_framework.filters import OrderingFilter, SearchFilter"
from django_filters.rest_framework import DjangoFilterBackend

# Alias import for filters
from rest_framework import filters as drf_filters
 
from rest_framework.request import Request

from datetime import timedelta
from django.utils.timezone import now

# Admin-file loader view imports
from django.contrib.admin.views.decorators import staff_member_required
from django.core.files.storage import FileSystemStorage
from django.shortcuts import render
from django.http import HttpResponse
from django.core.management import call_command
import os
from pathlib import Path
from django.conf import settings
from django.utils.text import get_valid_filename 

from django.db import transaction

#Imports for google login view
# from django.core.cache import cache
# from django.shortcuts import redirect
# from urllib.parse import urlencode
# from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
# from dj_rest_auth.registration.views import SocialLoginView
# # For csrf view
# from django.views.decorators.csrf import ensure_csrf_cookie

from django.http import JsonResponse
import json
from django.utils import timezone
from datetime import datetime

from celery import current_app

import logging


logger = logging.getLogger(__name__)


#=================================== 
# Admin file loader page view
#====================================
@staff_member_required  # Restrict access to staff users
def upload_file(request):
    """
    Handle file uploads:
    - Enforces JSON-only uploads via extension and MIME type checks.
    - Parses JSON and validates with validate_domain_data() BEFORE saving.
    - Persists the file and a DB record if validation passes.
    - Returns 202 to indicate the file is queued/awaiting processing (processing currently disabled).
    """

    # Only proceed if it's a POST and a file under the key "file" is present.
    # The walrus operator assigns the file to 'uploaded_file' while checking existence.
    if request.method == "POST" and (uploaded_file := request.FILES.get("file")):

        # Extract additional params sent with the form.
        # 'drop_date' is required for my downstream logic; 'domain_list' is optional with a default.
        raw_drop_date = request.POST.get("drop_date")
        domain_list = request.POST.get("domain_list", "pending_delete")

        # ----------------------------
        # Basic request-level validation
        # ----------------------------

        # 'drop_date' must be provided and parsable into a valid date.
        if not raw_drop_date:
            return HttpResponse("Drop date is required", status=400)

        try:
            # Normalize into a date object; enforce YYYY-MM-DD for consistency.
            drop_date = datetime.strptime(raw_drop_date, "%Y-%m-%d").date()
        except ValueError:
            return HttpResponse("Drop date must be in YYYY-MM-DD format", status=400)

        # Enforce a maximum upload size using my settings.
        # 'uploaded_file.size' is the size of the uploaded content in bytes.
        if uploaded_file.size > settings.MAX_UPLOAD_SIZE:
            return HttpResponse(
                f"File exceeds maximum size of {settings.MAX_UPLOAD_SIZE}Mb",
                status=413
            )

        # ---------------------------------------
        # Enforce JSON-only uploads (extension + MIME)
        # ---------------------------------------

        # Normalize filename to lowercase and ensure it ends with '.json'.
        # This blocks obviously-wrong extensions early (e.g., .csv, .zip).
        if not uploaded_file.name.lower().endswith(".json"):
            return HttpResponse("Only JSON files (.json) are allowed.", status=415)

        # Checking MIME type when provided by the client.
        # Some clients may omit or misreport it; we still parse JSON below to be certain.
        allowed_mime_types = {
            "application/json",
            "text/json",
            "application/x-json",
        }
        # If a content_type exists and isn't one of the allowed types, reject as unsupported.
        if uploaded_file.content_type and uploaded_file.content_type not in allowed_mime_types:
            return HttpResponse(
                "Unsupported file type; expected application/json.",
                status=415
            )

        # ---------------------------------------
        # Parse JSON and validate BEFORE persisting
        # ---------------------------------------

        try:
            # IMPORTANT: Reading the file pointer consumes the stream.
            # We'll rewind the pointer before saving (executed in uploaded_file.seek(0) below).
            data = json.load(uploaded_file)
        except json.JSONDecodeError as e:
            # Malformed JSON -> client error
            return HttpResponse(f"Invalid JSON format: {str(e)}", status=400)

        # Optional: Assert the top-level structure is a list, matching my validator's expectations.
        # (My validator iterates with enumerate(data), but this makes the error clearer.)
        if not isinstance(data, list):
            return HttpResponse(
                "Top-level JSON must be a list of domain items.",
                status=400
            )

        try:
            # Reusing existing centralized validation logic
            # This enforces structure for domain_name/use_cases and all nested fields.
            validate_domain_data(data)
        except ValueError as e:
            # Validation failure -> client error with specific message from the validator
            return HttpResponse(f"Invalid domain data: {str(e)}", status=400)

        # ---------------------------------------
        # Prepare to persist the (now-validated) file
        # ---------------------------------------

        # Sanitize the filename to remove unsafe characters for filesystem storage.
        filename = get_valid_filename(uploaded_file.name)

        # Construct the final file path inside the configured upload directory.
        file_path = Path(settings.UPLOAD_DIR) / filename

        # After reading JSON, the file pointer is at EOF; resetting to the beginning so storage can read it again.
        uploaded_file.seek(0)

        # ---------------------------------------
        # Atomic DB transaction for metadata writes
        # ---------------------------------------
        # Filesystem operations are not part of the DB transaction and won't roll back automatically.
        # This block ensures:
        #   - We check for duplicates before saving.
        #   - We create the DB metadata only if the save succeeds.
        try:
            with transaction.atomic():
                # Defensive duplicate checks:
                # 1) Does a file with this name already exist on disk?
                # 2) Does a DB record already exist with this filename?
                if file_path.exists() or UploadedFile.objects.filter(filename=filename).exists():
                    return HttpResponse("File already exists", status=409)

                # Save the uploaded file to disk inside UPLOAD_DIR.
                fs = FileSystemStorage(location=str(settings.UPLOAD_DIR))
                fs.save(filename, uploaded_file)

                # Creating a DB record marking this file as not yet processed.
                # Add new fields: processed_at (null initially) and processing_method (manual for uploads).
                UploadedFile.objects.create(
                    filename=filename,
                    processed=False,
                    drop_date=drop_date,
                    domain_list=domain_list
                )

        except Exception as e:
            # Any unexpected issues while saving the file or writing the DB record -> server error.
            return HttpResponse(f"File save failed: {str(e)}", status=500)

        # ------------------------------------------------------------
        # Optional: Immediate processing (INTENTIONALLY DISABLED)
        # ------------------------------------------------------------
        # try:
        #     call_command(
        #         "load_json",
        #         str(file_path),
        #         drop_date=drop_date,
        #         domain_list=domain_list
        #     )
        #     return HttpResponse("File processed successfully")
        #
        # except Exception as e:
        #     # Cleanup if processing fails:
        #     # 1) Remove the file from disk (ignore errors).
        #     if file_path.exists():
        #         try:
        #             os.unlink(file_path)
        #         except OSError:
        #             pass
        #     # 2) Remove the DB record to avoid dangling metadata.
        #     UploadedFile.objects.filter(filename=filename).delete()
        #     return HttpResponse(f"Processing failed: {str(e)}", status=500)

        # ------------------------------------------------------------
        # Current behavior: don't process immediately; just acknowledge.
        # ------------------------------------------------------------
        return HttpResponse("File uploaded successfully - awaiting processing", status=202)

    # If it's not a POST or no file was included, render the upload form template.
    return render(request, "upload.html")



#=================================== 
# Health check 
#====================================
def health_check(request):
    # Default values
    django_status = "ok"
    celery_status = "inactive"
    redis_status = "down"
    worker_count = 0

    # Django DB check
    try:
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
    except Exception:
        django_status = "unhealthy"

    # Redis check
    try:
        from django.core.cache import caches
        caches['default'].get("test_key", version=1)
        redis_status = "up"
    except Exception:
        redis_status = "down"

    # Celery check
    try:
        workers = current_app.control.inspect(timeout=1.0).active()
        if workers:
            celery_status = "active"
            worker_count = len(workers)
    except Exception:
        pass

    status_code = 200 if all([
        django_status == "ok",
        celery_status == "active",
        redis_status == "up"
    ]) else 503

    return JsonResponse({
        "django": django_status,
        "celery": celery_status,
        "redis": redis_status,
        "workers": worker_count,
        "timestamp": timezone.now().isoformat()
    }, status=status_code)
    
# def health_check(request):
#     # Default values
#     django_status = "ok"
#     celery_status = "inactive"
#     worker_count = 0

#     try:
#         # Try to inspect Celery workers
#         workers = current_app.control.inspect(timeout=1.0).active()
#         if workers:
#             celery_status = "active"
#             worker_count = len(workers)
#     except Exception:
#         # Celery is not running or unreachable
#         celery_status = "inactive"

#     return JsonResponse({
#         "django": django_status,
#         "celery": celery_status,
#         "workers": worker_count,
#         "timestamp": timezone.now().isoformat()
#     })




#=================================== 
# User profile
#====================================
class UserProfileView(APIView):
    authentication_classes = [ClerkJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user  # Clerk-authenticated AppUser instance
        username = getattr(user, 'username', None)  # Safe fallback
        serializer = AppUserSerializer(user)
        logger.debug(f"Serialized user data: {serializer.data}")
        return Response(serializer.data)

    # def patch(self, request):
    #     user = request.user  # Your AppUser instance
    #     data = request.data

    #     update_payload = {}

    #     if "first_name" in data:
    #         update_payload["first_name"] = data["first_name"]
    #     if "last_name" in data:
    #         update_payload["last_name"] = data["last_name"]
    #     if "email" in data:
    #         update_payload["email_address"] = data["email"]

    #     try:
    #         response = requests.patch(
    #             f"{settings.CLERK_API_BASE_URL}/users/{user.clerk_id}",
    #             json=update_payload,
    #             headers={
    #                 "Authorization": f"Bearer {settings.CLERK_SECRET_KEY}",
    #                 "Content-Type": "application/json"
    #             },
    #             timeout=5
    #         )
    #         response.raise_for_status()

    #         # Optionally update your local AppUser model too
    #         if "first_name" in data:
    #             user.first_name = data["first_name"]
    #         if "last_name" in data:
    #             user.last_name = data["last_name"]
    #         if "email" in data:
    #             user.email = data["email"]
    #         user.save()

    #         return Response({"detail": "Profile updated"}, status=status.HTTP_200_OK)

    #     except requests.RequestException as e:
    #         return Response(
    #             {"error": "Failed to update profile", "details": str(e)},
    #             status=status.HTTP_400_BAD_REQUEST
    #         )


#===================================
# Name list view
#====================================
class NameListAPIView(generics.ListAPIView):
    """
    Full tabular endpoint for names with extensive filters, search, and ordering.
    - Pagination: StandardResultsSetPagination (10 per page by default)
    - Filters: extension, is_top_rated, is_idea_of_the_day, drop_date, domain_list, status, score, length
    - Ordering: score, length, created_at (use '?ordering=-score' etc.)
    - Search: by 'domain_name' (use '?search=foo')
    """
    queryset = (
        Name.objects.all()
        .select_related('suggested_usecase')
        .prefetch_related(
            'use_cases__tag',
            'use_cases__category',
            'suggested_usecase__tag',
            'suggested_usecase__category',
        )
    )
    serializer_class = NameSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter, filters.SearchFilter]
    filterset_fields = [
        'extension',
        'is_top_rated',
        'is_idea_of_the_day',
        'drop_date',
        'domain_list',
        'status',
        'score',
        'length',
    ]    
    ordering_fields = ['score', 'length', 'created_at']
    search_fields = ['domain_name',] #removed 'tag__name', 'category__name'

    def get_serializer_context(self):
        # Keeping request in context
        context = super().get_serializer_context()
        context['request'] = self.request  # Needed to compute saved status
        return context





class NameDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, slug):
        name = get_object_or_404(Name, domain_name=slug)
        serializer = NameSerializer(name, context={'request': request})
        return Response(serializer.data)




class NameCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = NameSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class NameUpdateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        name = get_object_or_404(Name, pk=pk)
        serializer = NameSerializer(name, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class NameDeleteAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk):
        name = get_object_or_404(Name, pk=pk)
        name.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)



# View for toggling a SavedName instance for the current user and given domain slug
class ToggleSavedNameView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, slug):  # Keep parameter named 'slug' for URL consistency
        name = get_object_or_404(Name, domain_name=slug)  # Lookup by domain_name but using slug parameter
        user = request.user

        saved_obj = SavedName.objects.filter(user=user, name=name).first()

        if saved_obj:
            saved_obj.delete()
            return Response({'saved': False}, status=status.HTTP_200_OK)
        else:
            SavedName.objects.create(user=user, name=name)
            return Response({'saved': True}, status=status.HTTP_201_CREATED)




            
#===============================================================================
# TopRatedNames View
#===============================================================================
class TopRatedNamesAPIView(generics.GenericAPIView):
    """
    Dashboard endpoint that returns two groups: 'today' and 'yesterday' top-rated names.
    Features:
      - ?last_n=<int> : limit per day (defaults to 12; hard cap applied to prevent abuse)
      - ?domain_list=<value> : optional filter by list type (e.g., 'gold', 'silver' etc.)
    Behavior:
      - Uses timezone-aware "today" per server TZ. If you want request/user-TZ based,
        we can adjust once you specify the TZ source.
      - Deterministic ordering by: score DESC, created_at DESC, domain_name ASC
    Response shape:
    {
      "today": [... TopRatedNamesAPIView ...],
      "yesterday": [... TopRatedNamesAPIView ...]
    }
    """
    permission_classes = [IsAuthenticated]
    serializer_class = DashboardNameSerializer

    # Sensible defaults/caps to guard the DB
    DEFAULT_LAST_N = 12
    MAX_LAST_N = 100

    def get(self, request, *args, **kwargs):
        # 1) Parse & validate query params
        last_n_raw = request.query_params.get('last_n', None)
        domain_list = request.query_params.get('domain_list', None)

        if last_n_raw is None:
            last_n = self.DEFAULT_LAST_N
        else:
            try:
                last_n = int(last_n_raw)
            except (TypeError, ValueError):
                return Response(
                    {"detail": "Invalid 'last_n' — must be an integer."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            if last_n <= 0:
                return Response(
                    {"detail": "'last_n' must be a positive integer."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            if last_n > self.MAX_LAST_N:
                last_n = self.MAX_LAST_N  # clamp instead of erroring

        # 2) Resolve dates (timezone-aware, date part only)
        today = now().date()
        yesterday = today - timedelta(days=1)

        # 3) Base queryset: top-rated only, with deterministic ordering
        base_qs = (
            Name.objects
            .filter(is_top_rated=True)
            .order_by('-score', '-created_at', 'domain_name')
            .select_related('suggested_usecase')  # cheap join; harmless for dashboard payload
        )

        # Optional filter by domain_list if provided
        if domain_list:
            base_qs = base_qs.filter(domain_list=domain_list)

        # 4) Split per date and limit to last_n items each
        today_qs = base_qs.filter(drop_date=today)[:last_n]
        yesterday_qs = base_qs.filter(drop_date=yesterday)[:last_n]

        # 5) Serialize with the lean dashboard serializer
        today_data = DashboardNameSerializer(today_qs, many=True).data
        yesterday_data = DashboardNameSerializer(yesterday_qs, many=True).data

        return Response({"today": today_data, "yesterday": yesterday_data}, status=status.HTTP_200_OK)




            
#======================================================
# Daily Drop Names View
#=======================================================

class DailyDropAPIView(generics.GenericAPIView):
    """
    Dashboard endpoint for 'daily drop list', returning both 'today' and 'yesterday'.
    - By default EXCLUDES top-rated names to avoid duplication with Top Rated tile.
    - Query params:
        - ?last_n=<int>           -> number of items to return per day (default 50; clamped)
        - ?domain_list=<value>    -> optional domain_list filter
        - ?include_top_rated=true -> include top-rated names (defaults to False)
        - ?include_counts=true    -> include counts (useful for debugging empty responses)
    - Ordering: score DESC, created_at DESC, domain_name ASC (deterministic).
    """
    permission_classes = [IsAuthenticated]
    serializer_class = DashboardNameSerializer

    DEFAULT_LAST_N = 50
    MAX_LAST_N = 500

    def _parse_bool(self, raw, default=False):
        """Normalize common truthy strings to True; else False."""
        if raw is None:
            return default
        return str(raw).lower() in ("1", "true", "yes", "y", "t")

    def get(self, request, *args, **kwargs):
        # ----------------------------
        # 1) Parse and validate params
        # ----------------------------
        # last_n (limit per day)
        last_n_raw = request.query_params.get('last_n')
        if last_n_raw is None:
            last_n = self.DEFAULT_LAST_N
        else:
            try:
                last_n = int(last_n_raw)
            except (TypeError, ValueError):
                return Response({"detail": "Invalid 'last_n' — must be an integer."},
                                status=status.HTTP_400_BAD_REQUEST)
            if last_n <= 0:
                return Response({"detail": "'last_n' must be a positive integer."},
                                status=status.HTTP_400_BAD_REQUEST)
            if last_n > self.MAX_LAST_N:
                last_n = self.MAX_LAST_N  # clamp

        domain_list = request.query_params.get('domain_list')
        include_top_rated = self._parse_bool(request.query_params.get('include_top_rated'), default=False)
        include_counts = self._parse_bool(request.query_params.get('include_counts'), default=False)

        # ----------------------------
        # 2) Resolve UTC dates (matches frontend T00:00:00Z approach)
        # ----------------------------
        today = now().date()
        yesterday = today - timedelta(days=1)

        # Helper that builds the per-day queryset (applies domain_list and top-rated toggle)
        def build_queryset_for_date(target_date):
            qs = Name.objects.filter(drop_date=target_date)
            # Apply optional domain_list filter
            if domain_list:
                qs = qs.filter(domain_list=domain_list)
            # By default exclude top-rated to avoid duplication across dashboard sections
            if not include_top_rated:
                qs = qs.exclude(is_top_rated=True)
            # Deterministic ordering & select_related for small payloads
            qs = qs.order_by('-score', '-created_at', 'domain_name').select_related('suggested_usecase')
            return qs

        # ----------------------------
        # 3) Fetch & slice (apply last_n)
        # ----------------------------
        today_qs = build_queryset_for_date(today)[:last_n]
        yesterday_qs = build_queryset_for_date(yesterday)[:last_n]

        # 4) Serialize
        today_data = DashboardNameSerializer(today_qs, many=True).data
        yesterday_data = DashboardNameSerializer(yesterday_qs, many=True).data

        # 5) Build response
        response_payload = {
            "today": today_data,
            "yesterday": yesterday_data,
        }

        return Response(response_payload, status=status.HTTP_200_OK)




#===================================
# Name Search View
#====================================

class NameSearchView(APIView):
    """
    Search for domain names using case-insensitive containment search.
    - Uses icontains with B-tree index for efficient pattern matching
    - Returns an empty result set if no search term is provided
    - Ensures exact substring matches only
    """

    def get(self, request):
        query = request.GET.get("q", "").strip()

        # If no query is provided, return empty results immediately
        if not query:
            return Response({"results": []})

        # Use icontains for case-insensitive substring matching
        qs = (
            Name.objects
            .filter(domain_name__icontains=query)
            .order_by('domain_name')  # Order alphabetically, you can adjust this
        )

        # Apply pagination
        paginator = StandardResultsSetPagination()
        page = paginator.paginate_queryset(qs, request, view=self)

        # Serialize and return results
        return paginator.get_paginated_response(NameSearchSerializer(page, many=True).data)

        

#===================================
# Use Case Search View
#====================================
class UseCaseSearchView(APIView):
    """
    Search across use cases using PostgreSQL full-text search.
    - Fields: case_title (high weight), description (medium weight),
              category name (lower weight), tags (lower weight).
    - Uses SearchRank to sort results by relevance.
    - Returns an empty result set if no search term is provided.
    """

    def get(self, request):
        query = request.GET.get("q", "").strip()

        # If no query is provided, return empty results immediately
        if not query:
            return Response({"results": []})

        # Weighted search vector for relevance ranking
        search_vector = (
            SearchVector("case_title", weight="A") +
            SearchVector("description", weight="B") +
            SearchVector("category__name", weight="C") +
            SearchVector("tag__name", weight="C")
        )
        search_query = SearchQuery(query)

        # Annotate queryset with rank and filter relevant matches
        qs = (
            UseCase.objects.annotate(rank=SearchRank(search_vector, search_query))
                           .filter(rank__gt=0)        # Exclude non-matching rows
                           .order_by("-rank")         # Highest rank first
                           .distinct()                # Prevent duplicates (joins on category/tags)
        )

        # Apply pagination
        paginator = StandardResultsSetPagination()
        page = paginator.paginate_queryset(qs, request, view=self)

        # Serialize and return results
        return paginator.get_paginated_response(UseCaseSearchSerializer(page, many=True).data)



#=======================================================
# Shared Mixin for views needing Pagination and Optonal filtering by date range
#=======================================================
class DateRangePaginationMixin:
    """
    Reusable mixin for views that need:
    - Pagination
    - Optional filtering by start_date and end_date query params
    """
    def filter_by_date_range(self, queryset, request):
        start_date_param = request.query_params.get('start_date')
        end_date_param = request.query_params.get('end_date')

        if start_date_param:
            start_date = parse_date(start_date_param)
            if start_date:
                queryset = queryset.filter(created_at__date__gte=start_date)

        if end_date_param:
            end_date = parse_date(end_date_param)
            if end_date:
                queryset = queryset.filter(created_at__date__lte=end_date)

        return queryset

    def paginate(self, queryset, request, serializer_class):
        paginator = LimitOffsetPagination()
        paginated_qs = paginator.paginate_queryset(queryset, request)
        return paginator.get_paginated_response(serializer_class(paginated_qs, many=True).data)



#===================================
# SavedNames views
#====================================
class SavedNameListView(APIView, DateRangePaginationMixin):
    authentication_classes = [ClerkJWTAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = SavedNameLightSerializer

    # Search and filtering setup
    filter_backends = [filters.OrderingFilter, filters.SearchFilter, DjangoFilterBackend]
    filterset_fields = ['name__domain_name', 'name__domain_list', 'name__status', 'name__created_at']
    ordering_fields = ['name__domain_name', 'name__domain_list', 'name__status', 'name__created_at']
    ordering = ['-name__created_at', 'name__domain_name']
    search_fields = [
        'name__domain_name', 'name__competition', 'name__difficulty',
        'name__suggested_usecase' # removed 'name__category', 'name__tag'
    ]


    def get(self, request):
        saved_qs = SavedName.objects.filter(user=request.user).select_related("name")
        saved_qs = self.filter_by_date_range(saved_qs, request)
        # return paginated data via the limit-offset pagination define in the mixin
        return self.paginate(saved_qs, request, self.serializer_class)


#===================================
# AcquiredNames views
#====================================
class AcquiredNameView(APIView, DateRangePaginationMixin):
    authentication_classes = [ClerkJWTAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = AcquiredNameSerializer
    queryset = AcquiredName.objects.all()

    # Enable filter and search backend for better UX
    filter_backends = [filters.OrderingFilter, filters.SearchFilter, DjangoFilterBackend]
    # Allow filtering by these fields
    filterset_fields = ['domain_name', 'domain_list', 'status', 'created_at']  # 'name' maps to 'domain'
    # Allow ordering by query string (like ?ordering=domain_name, etc)
    ordering_fields = ['domain_name', 'domain_list', 'status', 'created_at']
    ordering = ['-created_at', 'domain_name']  # Default ordering
    search_fields = ['name__domain_name', 'name__competition', 'name__difficulty', 'name__suggested_usecase'] #removed 'name__category', 'name__tag'



    def get(self, request):
        acquired_qs = AcquiredName.objects.filter(user=request.user).select_related("name")
        acquired_qs = self.filter_by_date_range(acquired_qs, request)
        return self.paginate(acquired_qs, request, AcquiredNameSerializer)




#===================================
# Ideas
#====================================

FEATURED_COUNT = 8
FEATURED_CACHE_KEY = "featured_usecases"
FEATURED_TTL = 60 * 60 * 24               # 24 hours


class UseCaseListView(generics.ListAPIView):
    serializer_class = UseCaseListSerializer
    pagination_class = IdeaPageNumberPagination

    filter_backends = [
        DjangoFilterBackend,
        drf_filters.SearchFilter,
        drf_filters.OrderingFilter,
    ]
    filterset_class = UseCaseFilter
    search_fields = ["case_title", "category__name", "tag__name"]
    ordering_fields = ["created_at", "case_title", "order"]
    ordering = ["-created_at", "order"]

    def get_queryset(self):
        return (
            UseCase.objects
            .select_related("domain_name", "category")
            .prefetch_related("tag")
            .all()
            .distinct()
        )

    def list(self, request: Request, *args, **kwargs):
        """
        Supports:
          - Filtering via UseCaseFilter
          - Search on case_title/category/tag
          - Ordering (?ordering=created_at, -created_at, case_title, order)
          - Pagination
          - last_n (?last_n=10 → last 10 by created_at)
          - Featured (?featured=true → 8 random cached items)
        """
        featured = request.query_params.get("featured")
        if featured and featured.lower() in ("1", "true", "yes"):
            payload = cache.get(FEATURED_CACHE_KEY)
            if payload is None:
                base_qs = self.get_queryset()
                featured_qs = base_qs.order_by("?")[:FEATURED_COUNT]
                serializer = self.get_serializer(featured_qs, many=True)
                payload = serializer.data
                cache.set(FEATURED_CACHE_KEY, payload, FEATURED_TTL)
            return Response(payload)

        queryset = self.filter_queryset(self.get_queryset())

        # last_n shortcut (handled here instead of FilterSet)
        last_n = request.query_params.get("last_n")
        if last_n:
            try:
                n = max(0, int(last_n))
            except ValueError:
                n = 0
            if n > 0:
                queryset = queryset.order_by("-created_at")[:n]
                serializer = self.get_serializer(queryset, many=True)
                return Response(serializer.data)

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)




#===================================
# Use case detail view
#====================================
class UseCaseDetailView(generics.RetrieveAPIView):
    queryset = (
        UseCase.objects
        .select_related("domain_name", "category")
        .prefetch_related("tag")
        .all()
    )
    serializer_class = UseCaseDetailSerializer
    lookup_field = "slug"

    



#===================================
# Idea of the day
#====================================
class IdeaOfTheDayView(APIView):
    """
    Return today's idea-of-the-day entries:
    - pending_delete = today's entry
    - deleted = yesterday's entry (since that's when it was pending_delete)
    """

    def get(self, request):
        # Parse ?date=YYYY-MM-DD if provided, else use today
        date_str = request.query_params.get("date")
        if date_str:
            try:
                drop_date = timezone.datetime.strptime(date_str, "%Y-%m-%d").date()
            except ValueError:
                return Response({"error": "Invalid date format. Use YYYY-MM-DD"}, status=400)
        else:
            drop_date = timezone.now().date()

        # Yesterday's date
        yesterday = drop_date - timezone.timedelta(days=1)

        # Fetch today's pending_delete
        today_obj = (
            IdeaOfTheDay.objects
            .filter(drop_date=drop_date, domain_list="deleting_today") # Use deleting_today for prod
            .select_related("use_case")
            .first()
        )

        # Fetch yesterday's deleted
        yesterday_obj = (
            IdeaOfTheDay.objects
            .filter(drop_date=yesterday, domain_list="pending_delete") # Use deleted for prod
            .select_related("use_case")
            .first()
        )

        pending_delete_data = IdeaOfTheDaySerializer(today_obj).data if today_obj else None
        deleted_data = IdeaOfTheDaySerializer(yesterday_obj).data if yesterday_obj else None

        return Response({
            "date": drop_date,
            "pending_delete": pending_delete_data,
            "deleted": deleted_data,
        })




#===================================
# IdeaOfTheDay List View
#====================================
class IdeaOfTheDayListView(generics.ListAPIView):
    """
    Paginated, filterable list of all IdeaOfTheDay entries.
    Useful for history, analytics, browsing.
    """
    queryset = IdeaOfTheDay.objects.select_related("use_case").order_by("-drop_date")
    serializer_class = IdeaOfTheDayListSerializer
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["drop_date", "domain_list"]  # will be extended with category, etc.
    ordering_fields = ["drop_date"]


    


#===================================
# Idea Center
#====================================


#===================================
# Newsletter views
#====================================
@method_decorator(csrf_exempt, name='dispatch')
class NewsletterView(APIView):
    permission_classes = [IsManagerOrReadOnly]
    throttle_classes = [PostRequestThrottle]
    authentication_classes = [] 


    def post(self, request):
        serializer = NewsletterSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "Successfully subscribed."}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def get(self, request):
        newsletters = NewsLetter.objects.all()
        serializer = NewsletterSerializer(newsletters, many=True)
        return Response(serializer.data)




#===================================
# Public Inquiry views
#====================================
@method_decorator(csrf_exempt, name='dispatch')
class PublicInquiryView(APIView):
    permission_classes = [IsManagerOrReadOnly]
    throttle_classes = [PostRequestThrottle]
    authentication_classes = [] 


    def post(self, request):
        serializer = PublicInquirySerializer(data=request.data)
        if serializer.is_valid():
            ip_address = (
                request.META.get("HTTP_X_FORWARDED_FOR", "").split(",")[0]
                or request.META.get("REMOTE_ADDR")
            )
            serializer.save(ip_address=ip_address)

            return Response({
                "message": "Inquiry received. We'll get back to you shortly."
            }, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


    def get(self, request):
        inquiries = PublicInquiry.objects.all().order_by('-created_at')
        serializer = PublicInquirySerializer(inquiries, many=True)
        return Response(serializer.data)




# ============================================
# Authetication view logics - now handled by Clerk 
# ============================================

# # Google login/signup view
# class GoogleLogin(SocialLoginView):
#     """
#     Handles Google OAuth2 login/signup with:
#     - Rate limiting
#     - Process differentiation (login vs signup)
#     - Secure error forwarding
#     """
#     adapter_class = GoogleOAuth2Adapter

#     def post(self, request, *args, **kwargs):
#         # 1. Rate Limiting (5 attempts/hour per IP)
#         ip = request.META.get('REMOTE_ADDR', '')
#         rate_key = f"google_auth_rate:{ip}"
#         attempts = cache.get(rate_key, 0)
        
#         if attempts >= 5:
#             logger.warning(f"Rate limit exceeded for IP: {ip}")
#             return self._build_error_response(
#                 request,
#                 "Too many attempts. Try again later.",
#                 status=429
#             )
        
#         try:
#             # 2. Process the social login
#             cache.set(rate_key, attempts + 1, timeout=3600)
#             response = super().post(request, *args, **kwargs)
            
#             # 3. Verify new users (if process=signup)
#             if request.GET.get('process') == 'signup':
#                 self._verify_new_user(request.user)
            
#             return response

#         except Exception as e:
#             logger.error(f"Google auth failed: {str(e)}", exc_info=True)
#             return self._build_error_response(request, str(e))

#     def _build_error_response(self, request, error_msg, status=400):
#         """Standardized error response formatting"""
#         process = request.GET.get('process', 'login')
#         redirect_uri = request.GET.get('redirect_uri', '/')
        
#         # Forward errors securely without exposing details
#         safe_error = "Authentication failed" if status != 429 else error_msg
#         error_url = f"{redirect_uri}?error={urlencode({'message': safe_error})}&process={process}"
        
#         return redirect(error_url, status=status)

#     def _verify_new_user(self, user):
#         """Additional checks for signup flows"""
#         if not user.email_verified:
#             logger.info(f"New unverified user: {user.email}")
#             # Add post-signup actions here if needed
           

# #CSRF 
# @ensure_csrf_cookie
# def get_csrf_token(request):
#     return JsonResponse({"message": "CSRF cookie set"})








# @staff_member_required
# def upload_file(request):
#     if request.method == "POST" and (uploaded_file := request.FILES.get("file")):
#         drop_date = request.POST.get("drop_date")
#         domain_list = request.POST.get("domain_list", "pending_delete")

#         # Validate inputs
#         if not drop_date:
#             return HttpResponse("Drop date is required", status=400)
#         if uploaded_file.size > settings.MAX_UPLOAD_SIZE:
#             return HttpResponse(f"File exceeds maximum size of {settings.MAX_UPLOAD_SIZE} bytes", 
#                               status=413)

#         # Prepare file
#         filename = get_valid_filename(uploaded_file.name)
#         file_path = Path(settings.UPLOAD_DIR) / filename

#         # Atomic transaction block
#         try:
#             with transaction.atomic():
#                 # Check for existing records
#                 if file_path.exists() or UploadedFile.objects.filter(filename=filename).exists():
#                     return HttpResponse("File already exists", status=409)
                
#                 # Save file and create record
#                 fs = FileSystemStorage(location=str(settings.UPLOAD_DIR))
#                 fs.save(filename, uploaded_file)
#                 UploadedFile.objects.create(
#                     filename=filename,
#                     processed=False  # Explicitly mark as unprocessed
#                 )

#         except Exception as e:
#             return HttpResponse(f"File save failed: {str(e)}", status=500)

#         # # Process file with cleanup on failure
#         # try:
#         #     call_command(
#         #         "load_json",
#         #         str(file_path),
#         #         drop_date=drop_date,
#         #         domain_list=domain_list
#         #     )
#         #     return HttpResponse("File processed successfully")
        
#         # except Exception as e:
#         #     # Cleanup if processing fails
#         #     if file_path.exists():
#         #         try:
#         #             os.unlink(file_path)
#         #         except OSError:
#         #             pass
#         #     UploadedFile.objects.filter(filename=filename).delete()
#         #     return HttpResponse(f"Processing failed: {str(e)}", status=500)

#         # DON'T process immediately - just return success
#         return HttpResponse("File uploaded successfully - awaiting processing", status=202)

#     return render(request, "upload.html")

