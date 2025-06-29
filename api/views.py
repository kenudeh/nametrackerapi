from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from .models import Name
from .serializers import NameSerializer

#Imports for google login view
from django.core.cache import cache
from django.shortcuts import redirect
from urllib.parse import urlencode
from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from dj_rest_auth.registration.views import SocialLoginView
import logging

logger = logging.getLogger(__name__)


# Google login/signup view
class GoogleLogin(SocialLoginView):
    """
    Handles Google OAuth2 login/signup with:
    - Rate limiting
    - Process differentiation (login vs signup)
    - Secure error forwarding
    """
    adapter_class = GoogleOAuth2Adapter

    def post(self, request, *args, **kwargs):
        # 1. Rate Limiting (5 attempts/hour per IP)
        ip = request.META.get('REMOTE_ADDR', '')
        rate_key = f"google_auth_rate:{ip}"
        attempts = cache.get(rate_key, 0)
        
        if attempts >= 5:
            logger.warning(f"Rate limit exceeded for IP: {ip}")
            return self._build_error_response(
                request,
                "Too many attempts. Try again later.",
                status=429
            )
        
        try:
            # 2. Process the social login
            cache.set(rate_key, attempts + 1, timeout=3600)
            response = super().post(request, *args, **kwargs)
            
            # 3. Verify new users (if process=signup)
            if request.GET.get('process') == 'signup':
                self._verify_new_user(request.user)
            
            return response

        except Exception as e:
            logger.error(f"Google auth failed: {str(e)}", exc_info=True)
            return self._build_error_response(request, str(e))

    def _build_error_response(self, request, error_msg, status=400):
        """Standardized error response formatting"""
        process = request.GET.get('process', 'login')
        redirect_uri = request.GET.get('redirect_uri', '/')
        
        # Forward errors securely without exposing details
        safe_error = "Authentication failed" if status != 429 else error_msg
        error_url = f"{redirect_uri}?error={urlencode({'message': safe_error})}&process={process}"
        
        return redirect(error_url, status=status)

    def _verify_new_user(self, user):
        """Additional checks for signup flows"""
        if not user.email_verified:
            logger.info(f"New unverified user: {user.email}")
            # Add post-signup actions here if needed
           

class NameListAPIView(APIView):
    def get(self, request):
        names = Name.objects.all()
        serializer = NameSerializer(names, many=True)
        return Response(serializer.data)

class NameDetailAPIView(APIView):
    def get(self, request, pk):
        name = get_object_or_404(Name, pk=pk)
        serializer = NameSerializer(name)
        return Response(serializer.data)

class NameCreateAPIView(APIView):
    def post(self, request):
        serializer = NameSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class NameUpdateAPIView(APIView):
    def patch(self, request, pk):
        name = get_object_or_404(Name, pk=pk)
        serializer = NameSerializer(name, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class NameDeleteAPIView(APIView):
    def delete(self, request, pk):
        name = get_object_or_404(Name, pk=pk)
        name.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)