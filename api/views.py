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

