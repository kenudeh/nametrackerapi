from django.shortcuts import get_object_or_404
from rest_framework.views import APIView, exception_handler
from rest_framework import generics, viewsets, permissions, status, filters as drf_filters
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from django_filters.rest_framework import DjangoFilterBackend

# for agggregating values into an array in tags
from django.contrib.postgres.aggregates import ArrayAgg

# Error handling response
from rest_framework.exceptions import ValidationError, APIException
from django.db import IntegrityError

# Caching imports
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.core.cache import cache
from django.views.decorators.vary import vary_on_cookie 


# Search imports
from django.contrib.postgres.search import SearchVector, SearchQuery, SearchRank, SearchHeadline
from django.db.models import Q
from django.db.models import Subquery


# Filter imports
from django_filters.rest_framework import DjangoFilterBackend

# Imports from local Files
from .serializers import *
from .models import *
from .filters import ToolFilter, RequestFilter
from .pagination import ToolPagination, UserProfilePagination, FavoritePagination, ReviewPagination, RequestPagination, ToolSuggestionPagination
from .throttles import PostRequestThrottle, ToolSuggestionThrottle, ComparisonThrotttle
from .permissions import IsManagerOrReadOnly

# Imports for function-based views
from rest_framework.decorators import api_view, permission_classes


#Import for email notifications
from django.core.mail import send_mail

#Import for logging errors
import logging
logger = logging.getLogger(__name__)


from django.utils.cache import get_cache_key
from urllib.parse import urlencode
import hashlib



#*************************TOOL CREATION, VIEWING, AND UPDATE *************

class ToolSearchError(APIException):
    status_code = 400
    default_detail = 'An error occurred during search. Please try different keywords.'
    default_code = 'search_error'

# Endpoint for handling POST and GET requests to create or view tools
class ToolListCreateView(generics.ListCreateAPIView):
    queryset = Tool.objects.all()
    serializer_class = ToolSerializer
    permission_classes = [IsManagerOrReadOnly]
    
    # Remove drf_filters.SearchFilter since we're doing custom search
    filter_backends = [DjangoFilterBackend, drf_filters.OrderingFilter]
    filterset_class = ToolFilter
    pagination_class = ToolPagination
    ordering_fields = ["tool_name", "created_at", "updated_at", "is_featured"]
    ordering = ["-created_at"]
    
    # Restricting actions other than SAFE METHODS to admins
    def get_permissions(self):
        if self.request.method in ['POST', 'PUT', 'PATCH', 'DELETE']:
            return [permissions.IsAdminUser()]
        return [permissions.AllowAny()]
    

    def get_queryset(self):
        # Base queryset with optimized relations
        queryset = super().get_queryset().prefetch_related(
            "tags", "languages", "target_users"
        ).select_related("category")
            
        search_query = self.request.query_params.get("q")
        if not search_query:
            return queryset.distinct()

        try:
            fields = [
                ("tool_name", "A"),
                ("description", "B"), 
                ("tags__name", "C"),
                ("category__name", "C"),
                ("languages__name", "D"),
                ("target_users__name", "D")
            ]

            combined_vector = None
            search_conditions = Q()

            for field, weight in fields:
                vector = SearchVector(field, weight=weight, config="english")
                combined_vector = vector if combined_vector is None else combined_vector + vector
                search_conditions |= Q(**{f"{field}__icontains": search_query})

            # Get ranked Tool IDs using subquery
            ranked_ids = queryset.filter(search_conditions).annotate(
                rank=SearchRank(combined_vector, SearchQuery(search_query, config="english"))
            ).order_by("-rank").values_list("id", flat=True).distinct()

            # Final queryset: clean fetch by ID with prefetches, no redundant annotations
            return queryset.filter(id__in=Subquery(ranked_ids)).order_by("-created_at")

        except Exception as e:
            print(f"Search error: {str(e)}")
            raise ToolSearchError()



    # Modified caching that accounts for search parameters
    def _generate_cache_key(self, request):
        """Generate a safe cache key that works with Memcached"""
        # Create a base key
        base_key = "tools_list"
        
        # Include the query parameters (sorted for consistency)
        params = urlencode(sorted(request.GET.items()))
        
        # Create a hash of the full path and params
        path_hash = hashlib.md5(f"{request.path}?{params}".encode()).hexdigest()
        
        return f"{base_key}_{path_hash}"

    @method_decorator(cache_page(60 * 60 * 24))
    def list(self, request, *args, **kwargs):
        """Override to use our custom cache key"""
        # Manually set cache key before calling super
        request._cache_key_custom = self._generate_cache_key(request)
        return super().list(request, *args, **kwargs)


    def dispatch(self, request, *args, **kwargs):
        """Override to use our custom cache key"""
        if request.method == 'GET' and hasattr(self, '_generate_cache_key'):
            request._cache_key_custom = self._generate_cache_key(request)
        return super().dispatch(request, *args, **kwargs)

    # Error handling
    def handle_exception(self, exc):
        """
        Custom error handling to return more user-friendly error messages.
        """
        if isinstance(exc, ValidationError):
            return Response({"error": str(exc)}, status=400)
        return super().handle_exception(exc)


# Endpoint for handling PATCH and GET requests to update or view a specific tool
class SingleToolViewAndUpdate(generics.RetrieveUpdateAPIView):
    queryset = Tool.objects.all()
    serializer_class = ToolSerializer
    permission_classes = [IsManagerOrReadOnly]
    lookup_field = 'slug'  # Changed from default 'pk' to 'slug' for SEO and human readbility benefits
    

    # Restrict PUT and PATCH to admins; allow GET for anyone
    def get_permissions(self):
        if self.request.method in ['PUT', 'PATCH', 'POST']:  # Only restrict PUT and PATCH
            return [permissions.IsAdminUser()]
        return [permissions.AllowAny()]  # Allow anyone to view (GET)

    # Cache GET requests for 60 minutes
    @method_decorator(cache_page(60 * 60 * 24)) # Cache for 24 hours
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    # Custom error handling
    def handle_exception(self, exc):
        if isinstance(exc, ValidationError):
            return Response({"error": str(exc)}, status=400)
        return super().handle_exception(exc)
    
    


#*******************TOOL SUGGESTION VIEWS********************

"""Separate endpoint JUST for form category and pricing dropdown options"""
class ToolOptionsView(APIView):
    permission_classes = [IsManagerOrReadOnly]

    @method_decorator(cache_page(60 * 60 * 24)) # Cache for 24 hours
    def get(self, request):
        return Response({
            'categories' : list(Category.objects.values('id', 'name', 'display_name')),
            'pricing' : list(PricingModel.objects.values('id', 'type'))
        })
        

"""Separate endpoint for returning featured tools"""
class FeaturedToolsView(APIView):
    permission_classes = [IsManagerOrReadOnly]

    @method_decorator(cache_page(60 * 60 * 24)) # Cache for 24 hours
    def get(self, request):
        featured_tools = Tool.objects.filter(is_featured=True).select_related('category', 'pricing').prefetch_related('tags')
        serializer = FeaturedToolsSerializer(featured_tools, many=True)
        
        return Response({
            'featured' : serializer.data
        })


class ToolSuggestionViewSet(viewsets.ModelViewSet):
    """Viewset for handling tool submissions."""
    serializer_class = ToolSuggestionSerializer
    permission_classes = [permissions.AllowAny] 
    throttle_classes = [ToolSuggestionThrottle]
    pagination_class = ToolSuggestionPagination
    
    def get_queryset(self):
        """Retrieve submissions - simplified for public access"""
        queryset = ToolSuggestion.objects.all()\
            .select_related('category', 'pricing')\
            .prefetch_related('tags')\
            .order_by('-created_at')  # Consistent sorting

        # Public vs admin filtering
        if not self.request.user.is_staff:
            # Public users only see approved tools
            queryset = queryset.filter(status='approved')
        else:
            # Admin-specific filters
            status_filter = self.request.query_params.get('status', '').lower()
            if status_filter in ['pending', 'approved', 'rejected']:
                queryset = queryset.filter(status=status_filter)

            # Date range filtering (uses created_at index)
            start_date = self.request.query_params.get('start_date')
            end_date = self.request.query_params.get('end_date')
            if start_date:
                queryset = queryset.filter(created_at__date__gte=start_date)
            if end_date:
                queryset = queryset.filter(created_at__date__lte=end_date)

        return queryset
        
    
    def perform_create(self, serializer):
        # 1. Image validation (unchanged, required)
        image = self.request.FILES.get("image")
        if not image:
            raise serializers.ValidationError({"image": "Image file is required"})

        # 2. Feature extraction with safety net (updated)
        features = []
        
        # Case 1: Check for multi-part form array first (modern browsers)
        if 'features[]' in self.request.POST:
            features = self.request.POST.getlist('features[]')
        # Case 2: Check for single JSON string (legacy/API submissions)
        elif 'features' in self.request.POST:
            features_raw = self.request.POST['features']
            try:
                features = json.loads(features_raw) if features_raw.startswith('[') else [features_raw]
            except json.JSONDecodeError:
                features = [features_raw]
        # Case 3: Fallback for DRF's parsed data
        elif hasattr(self.request, 'data'):
            features = self.request.data.getlist('features', [])

        # 3. Normalize features (existing logic)
        features = [str(f).strip() for f in features if str(f).strip()]

        # 4. Save with all data (unchanged)
        tool = serializer.save(
            image=image,
            features=features,
            status='pending'
        )

        # 5. User association (unchanged, important for auth)
        if self.request.user.is_authenticated:
            user_profile = UserProfile.objects.get(user=self.request.user)
            tool.submitted_by = user_profile
            tool.save()  
            
               
            
    def create(self, request, *args, **kwargs):
        # Debug: Print incoming data
        # print("\n=== Raw request data ===")
        # print(request.data)
        # print("Content-Type:", request.content_type)
        
        # Pre-validate tool_name uniqueness
        tool_name = request.data.get('tool_name', '')
        if ToolSuggestion.objects.filter(tool_name__iexact=tool_name).exists():
            print(f"! Tool name conflict: {tool_name}")
            return Response(
                {"tool_name": "A tool with this name already exists."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Initialize serializer
        serializer = self.get_serializer(data=request.data)
        
        # Debug: Print serializer initial data
        # print("\n=== Serializer initial data ===")
        # print(serializer.initial_data)
        
        # Validate
        if not serializer.is_valid():
            print("\n!!! Validation errors !!!")
            print(serializer.errors)
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Debug: Print validated data
        # print("\n=== Validated data ===")
        # print(serializer.validated_data)
        
        # Proceed with creation
        try:
            instance = serializer.save()
            print(f"\n✓ Successfully created: {instance}")
            return Response(
                serializer.data,
                status=status.HTTP_201_CREATED
            )
        except Exception as e:
            print("\n!!! Creation failed !!!")
            print(str(e))
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )




# Custom permission class
# class IsOwnerOrStaff(permissions.BasePermission):
#     """Custom permission to allow only the owner or staff to access an object."""
#     def has_object_permission(self, request, view, obj):
#         return request.user.is_staff or obj.submitted_by == request.user


# class ToolSuggestionViewSet(viewsets.ModelViewSet):
#     """Viewset for handling tool submissions."""
#     serializer_class = ToolSuggestionSerializer
#     permission_classes = [permissions.AllowAny]
#     throttle_classes = [ToolSuggestionThrottle]
#     pagination_class = ToolSuggestionPagination
    
#     def get_queryset(self):
#         """Retrieve submissions based on user role"""
#         queryset = ToolSuggestion.objects.all().order_by('-created_at')
        
#         # Restriciting the list to a user's submission alone
#         if not self.request.user.is_staff:
#             user_profile = UserProfile.objects.get(user=self.request.user)
#             queryset = queryset.filter(submitted_by=user_profile)
            
#         # Filtering by status
#         status_filter = self.request.query_params.get('status', '').lower()
#         if status_filter in ['pending', 'approved', 'rejected']:
#             queryset = queryset.filter(status=status_filter)
        
#         # Filtering by submission date
#         start_date = self.request.query_params.get('start_date')
#         end_date = self.request.query_params.get('end_date')
#         if start_date:
#             queryset = queryset.filter(created_at__gte=start_date)  
#         if end_date:
#             queryset = queryset.filter(created_at__lte=end_date)
                
#         return queryset
    
    
#     def perform_create(self, serializer):
#         """Associate submission with the logged-in user and handle tags.."""
#         user_profile = UserProfile.objects.get(user=self.request.user)  # Ensure it's a UserProfile instance
#         tags = self.request.data.get('tags', [])
        
#         # Normalize and validate tags
#         normalized_tags = [tag.lower().strip() for tag in tags]
        
#         # Save the tool suggestion
#         tool_suggestion = serializer.save(submitted_by=user_profile, status='pending')
        
#         # Add tags to the tool suggestion
#         for tag_name in normalized_tags:
#             tag, created = Tag.objects.get_or_create(name=tag_name)
#             tool_suggestion.tags.add(tag)



#     def create(self, request, *args, **kwargs):
#         logger.info(f"Incoming data: {request.data}")
#         try:
#             return super().create(request, *args, **kwargs)
#         except Exception as e:
#             logger.error(f"Validation error: {e}")
#             raise


#     def get_permissions(self):
#         """Apply specific permissions for detail view."""
#         if self.action in ['retrieve']:
#             self.permission_classes = [IsOwnerOrStaff]
#         return super().get_permissions()
     
            
# These methods will allow approval and rejection outside the Django admin panel

    # @action(detail=True, methods=['post'], permission_classes=[permissions.IsAdminUser])
    # def approve(self, request, pk=None):
    #     """Approve a tool and move it to the Tool table"""
    #     tool_suggestion = get_object_or_404(ToolSuggestion, pk=pk)
    #     Tool.objects.create(
    #         name=tool_suggestion.tool_name,
    #         description=tool_suggestion.description,
    #         website=tool_suggestion.website,
    #         category=tool_suggestion.category,
    #         pricing=tool_suggestion.pricing,
    #     )
    #     tool_suggestion.status = 'approved'
    #     tool_suggestion.save()
    #     return Response({'detail': 'Tool approved and addedd to directory.'}, status=status.HTTP_200_OK)
    
    
    # @action(detail=True, methods=['post'], permission_classes=[permissions.IsAdminUser])
    # def reject(self, request, pk=None):
    #     tool_suggestion = get_object_or_404(ToolSuggestion, pk=pk)
    #     tool_suggestion.status = 'rejected'
    #     tool_suggestion.save()
    #     return Response({'detail': 'Tool submission rejected.'}, status=status.HTTP_200_OK)
    


# ****************** UPDATE TOOL VIEW *****************
class UpdateToolView(APIView):
    # Throttle to 2 tool updates per day per IP
    throttle_classes = [PostRequestThrottle]
    
    def post(self, request):
        # Validate incoming data
        serializer = UpdateToolSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {
                    "status": "error",
                    "message": "Invalid input",
                    "errors": serializer.errors,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Save the data
        try:
            serializer.save()
            return Response(
                {
                    "status": "success",
                    "message": "Request submitted successfully",
                    "data": serializer.data,
                },
                status=status.HTTP_201_CREATED,
            )
            
        except Exception as e:
            # Logging the error for debugging with Django's logging framework
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to save data: {str(e)}")

            return Response(
                {
                    "status": "error",
                    "message": "Failed to save data",
                    "errors": str(e),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


    
#**************************USER PROFILE VIEW ************
# class UserProfileView(APIView):
#     permission_classes = [IsAuthenticated] # Only authenticated users can access
#     pagination_class = UserProfilePagination # Use custom pagination defined for UserProfile
    
#     @method_decorator(cache_page(60 * 5)) # Cache response for 5 minutes
#     @method_decorator(vary_on_cookie) # Vary cache based on user session
#     def get(self, request, *args, **kwargs):
#         try:
#             user = request.user  # Get the authenticated user

#             # Check if the user is an admin
#             if user.is_staff or user.is_superuser:
#                 # Admin can view all users' data
#                 user_profiles = UserProfile.objects.all().prefetch_related(
#                     'submissions',  # Prefetch submissions
#                     'my_favorites__tool'  # Prefetch favorites and related tools
#                 )
#                 serializer = UserProfileSerializer(user_profiles, many=True)
#             else:
#                 # Regular user can only view their own data
#                 user_profile = UserProfile.objects.prefetch_related(
#                     'submissions',  # Prefetch submissions
#                     'my_favorites__tool'  # Prefetch favorites and related tools
#                 ).get(id=user.id)

#                 # Filter favorites to include only approved tools
#                 approved_favorites = user_profile.my_favorites.filter(tool__status='approved')
#                 user_profile.my_favorites.set(approved_favorites)  # Update the queryset

#                 serializer = UserProfileSerializer(user_profile)

#             # Paginate the results
#             paginator = self.pagination_class()
#             paginated_data = paginator.paginate_queryset(serializer.data, request)
#             return paginator.get_paginated_response(paginated_data)

#         except UserProfile.DoesNotExist:
#             return Response(
#                 {"error": "User profile not found."},
#                 status=status.HTTP_404_NOT_FOUND
#             )
#         except Exception as e:
#             return Response(
#                 {"error": str(e)},
#                 status=status.HTTP_500_INTERNAL_SERVER_ERROR
#             )



#****************************FAVORITES VIEWS********************
# class FavoritesViewSet(viewsets.ModelViewSet):
#     """
#     Handles adding and listing favorite tools for an authenticated user.
#     Users can:
#     - View their favorite tools (GET request)
#     - Add a tool to their favorites (POST request)
#     - Remove a favorite (DELETE request)
#     """
#     serializer_class = FavoriteSerializer
#     permission_classes = [permissions.IsAuthenticated]
#     pagination_class = FavoritePagination  # Enables pagination for this viewset
#     ordering = ['-created_at']  # Orders favorites by newest first
    
#     # method used in handling GET requests
#     def get_queryset(self):
#         """
#         Retrieve only the authenticated user's favorite tools.
#         Uses caching to reduce database queries for repeated requests.
#         """
#         user = self.request.user
#         cache_key = f'user_{user.id}_favorites' # Unique cache key for each user
#         favorites = cache.get(cache_key)
        
#         if favorites is None:
#             favorites = Favorite.objects.filter(user=user).select_related('tool')
#             cache.set(cache_key, favorites, timeout=60 * 5) # Cache for 5 minutes
        
#         return favorites
    
#     def perform_create(self, serializer):
#         """
#         Handles adding a tool to favorites.
#         Prevents users from adding the same tool multiple times.
#         """
#         user = self.request.user
#         tool = serializer.validated_data.get('tool')
        
#         # Check if the tool is already in the user's favorites
#         if Favorite.objects.filter(user=user, tool=tool).exists():
#             return Response({
#                 "error": "You have already added this tool to your favorites."
#             }, status=status.HTTP_400_BAD_REQUEST)
            
#         try: 
#             serializer.save(user=user)
#             cache.delete(f'user_{user.id}_favorites')  # Clear cache after adding
#         except IntegrityError:
#             return Response({"error": "An error occurred while saving your favorite."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

#     def destroy(self, request, *args, **kwargs):
#         instance = self.get_object()
#         if instance.user != request.user:
#             return Response({"error": "You can only remove your own favorites."}, status=status.HTTP_403_FORBIDDEN)
        
#         cache.delete(f'user_{request.user.id}_favorites')  # Clear cache after deletion
#         return Response(status=status.HTTP_204_NO_CONTENT)
    
    
    
#****************************REVIEW VIEW***********************
# class ReviewViewSet(viewsets.ModelViewSet):
#     queryset = Review.objects.all()
#     serializer_class = ReviewSerializer
#     permission_classes = [permissions.IsAuthenticated]
#     pagination_class = ReviewPagination

#     def get_queryset(self):
#         # Filter reviews for a specific tool and only return approved reviews
#         tool_id = self.kwargs.get("tool_id")
#         tool = get_object_or_404(Tool, id=tool_id)
#         return Review.objects.filter(tool=tool, is_approved=True).order_by("-created_at")

#     def perform_create(self, serializer):
#         # Attach the review to the current user and the specified tool
#         tool_id = self.kwargs.get("tool_id")
#         tool = get_object_or_404(Tool, id=tool_id)
#         serializer.save(user=self.request.user.userprofile, tool=tool, is_approved=False)

#     def get_serializer_context(self):
#         # Pass the tool and request to the serializer context
#         context = super().get_serializer_context()
#         tool_id = self.kwargs.get("tool_id")
#         context["tool"] = get_object_or_404(Tool, id=tool_id)
#         return context
    
    
#****************************TOOL COMPARISON FEATURE******************************************
class ToolComparisonView(APIView):
    permission_classes = [IsManagerOrReadOnly]
    throttle_classes = [ComparisonThrotttle]
    
    """
    API view to compare two tools based on their slugs.
    """
    @method_decorator(cache_page(60 * 60 * 24))
    def get(self, request, *args, **kwargs):
        """
        Handles GET requests for comparing tools.
        """
        # Step 1: Get the slugs of the two tools from query parameters
        tool1_slug = request.query_params.get('tool1')
        tool2_slug = request.query_params.get('tool2')
        
        # Step 2: Fetch the tools from the database
        tool1 = get_object_or_404(
            Tool.objects.prefetch_related('languages', 'target_users'),
            slug=tool1_slug
        )
        tool2 = get_object_or_404(
            Tool.objects.prefetch_related('languages', 'target_users'),
            slug=tool2_slug
        )
        
        # Step 3: Validate that the tools belong to the same category
        if tool1.category != tool2.category:
            raise ValidationError("You can only compare tools from the same category.")
        
        # Step 4: Validate that the tools are not the same
        if tool1 == tool2:
            raise ValidationError("You cannot compare a tool with itself.")
        
        # Step 5: Calculate common features (using the ArrayField directly)
        tool1_features = set(tool1.features or [])
        tool2_features = set(tool2.features or [])
        common_features = list(tool1_features & tool2_features)
        
        # Step 6: Prepare the data for the response
        comparison_data = {
            'tool1': tool1,
            'tool2': tool2,
            'common_features': common_features,
        }
        
        # Step 7: Serialize the data and return the response
        serializer = ToolComparisonSerializer(comparison_data)
        return Response(serializer.data, status=status.HTTP_200_OK)
        
        
        
#****************************FUNCTION BASED VIEWS********************
# CATEGORY VIEWS
@cache_page(60 * 60 * 24)
@api_view(['GET'])
def CategoryListView(request):
    """
    Handle GET request to retrieve all categories.
    """
    try:
        categories = Category.objects.all()
        serializer = CategorySerializer(categories, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    

# PRICING VIEW
@cache_page(60 * 60 * 24)
@api_view(['GET'])
def PricingTypeView(request):
    """
    Handle GET request to retrieve all categories.
    """
    try:
        pricing = PricingModel.objects.all()
        serializer = PricingSerializer(pricing, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
        
# Newsletter View
class NewsletterView(APIView):
    throttle_classes = [AnonRateThrottle]
    
    def post(self, request):
        serializer = NewsLetterSerializer(data = request.data)
        if not serializer.is_valid():
            
             # Check if the error is due to duplicate email
            if 'email' in serializer.errors and 'unique' in str(serializer.errors['email']):
                return Response(
                    {
                        "status": "error",
                        "message": "You're already subscribed!",
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            return Response(
                {
                    "status": "error",
                    "message": "Invalid input",
                    "errors": serializer.errors,
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # save the email
        try:
            newsletter = serializer.save()
            return Response(
                {
                    "status": "success",
                    "message": "Subscription successful",
                    "data": serializer.data,
                },
                status=status.HTTP_201_CREATED,
            )
            
        except Exception as e:
            # Log the error for debugging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to save email: {str(e)}")

            return Response(
                {
                    "status": "error",
                    "message": "Failed to save email",
                    "errors": str(e),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        
        
        
        
# Support Message Request View
class SupportView(APIView):
    # Throttle to 2 requests per day per IP
    throttle_classes = [AnonRateThrottle]
    

    def post(self, request):
        # Validate incoming data
        serializer = SupportSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {
                    "status": "error",
                    "message": "Invalid input",
                    "errors": serializer.errors,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Save the data
        try:
            support_request = serializer.save()

            # Notify admin via email
            # self._notify_admin(support_request)

            return Response(
                {
                    "status": "success",
                    "message": "Support request submitted successfully",
                    "data": serializer.data,
                },
                status=status.HTTP_201_CREATED,
            )
        except Exception as e:
            # Log the error for debugging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to process support request: {str(e)}")

            return Response(
                {
                    "status": "error",
                    "message": "Failed to process support request",
                    "errors": str(e),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


# Method to send admin emails. To be activated when we purchase an email hosting plan. NOTE: Uncomment the _notify_admin call in the post method above.

    # def _notify_admin(self, support_request):
    #     """
    #     Sends an email notification to the admin about the new support request.
    #     """
    #     subject = f"New Support Request: {support_request.subject}"
    #     message = (
    #         f"A new support request has been submitted:\n\n"
    #         f"Subject: {support_request.subject}\n"
    #         f"Email: {support_request.email}\n"
    #         f"Message: {support_request.message}\n\n"
    #         f"Submitted at: {support_request.created_at}"
    #     )
    #     send_mail(
    #         subject,
    #         message,
    #         settings.DEFAULT_FROM_EMAIL,  # From email (configured in settings.py)
    #         [settings.ADMIN_EMAIL],  # Admin email (configured in settings.py)
    #         fail_silently=False,
    #     )