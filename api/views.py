from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.throttling import UserRateThrottle
from .throttles import PostRequestThrottle
from .authentication import ClerkJWTAuthentication
from django.shortcuts import get_object_or_404
from .models import Name, NewsLetter, PublicInquiry, SavedName, AcquiredName
from .serializers import NameSerializer, AppUserSerializer, SavedNameLightSerializer, AcquiredNameSerializer, NewsletterSerializer, PublicInquirySerializer
from .permissions import IsManagerOrReadOnly
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from rest_framework.pagination import LimitOffsetPagination
from django.utils.dateparse import parse_date
from django.db.models import Q

from rest_framework import filters, generics, status # Filters import can be more explicitly done and avoid using filters. prefix by switching to "from rest_framework.filters import OrderingFilter, SearchFilter"
from django_filters.rest_framework import DjangoFilterBackend


#Imports for google login view
# from django.core.cache import cache
# from django.shortcuts import redirect
# from urllib.parse import urlencode
# from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
# from dj_rest_auth.registration.views import SocialLoginView
# # For csrf view
# from django.views.decorators.csrf import ensure_csrf_cookie
# from django.http import JsonResponse

import logging


logger = logging.getLogger(__name__)




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
# Name views
#====================================
class NameListAPIView(generics.ListAPIView):
    queryset = Name.objects.all()
    serializer_class = NameSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter, filters.SearchFilter]
    filterset_fields = ['category__name', 'extension', 'is_top_rated', 'is_idea_of_the_day']
    ordering_fields = ['score', 'length', 'created_at']
    search_fields = ['domain_name', 'tag__name', 'category__name']

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request  # Needed to compute saved status
        return context



class NameDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        name = get_object_or_404(Name, pk=pk)
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



# View for toggling a SavedName instance for the current user and given domain ID.
class ToggleSavedNameView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, name_id):
        name = get_object_or_404(Name, id=name_id)
        user = request.user

        saved_obj = SavedName.objects.filter(user=user, name=name).first()

        if saved_obj:
            saved_obj.delete()
            return Response({'saved': False}, status=status.HTTP_200_OK)
        else:
            SavedName.objects.create(user=user, name=name)
            return Response({'saved': True}, status=status.HTTP_201_CREATED)


#===============================================================================
# Shared Mixin for views needing Pagination and Optonal filtering by date range
#===============================================================================
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
        'name__suggested_usecase', 'name__category', 'name__tag'
    ]


    def get(self, request):
        saved_qs = SavedName.objects.filter(user=request.user).select_related("name")
        saved_qs = self.filter_by_date_range(saved_qs, request)
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
    search_fields = ['name__domain_name', 'name__competition', 'name__difficulty', 'name__suggested_usecase', 'name__category', 'name__tag']



    def get(self, request):
        acquired_qs = AcquiredName.objects.filter(user=request.user).select_related("name")
        acquired_qs = self.filter_by_date_range(acquired_qs, request)
        return self.paginate(acquired_qs, request, AcquiredNameSerializer)






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

