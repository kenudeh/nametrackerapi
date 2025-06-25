
from allauth.account.models import EmailConfirmationHMAC
from rest_framework.permissions import AllowAny
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response
from django.shortcuts import redirect
from rest_framework import status
import os

class CustomConfirmEmailView(GenericAPIView):
    permission_classes = [AllowAny]
    """
    Custom email confirmation view that:
    - Confirms user via token key.
    - Avoids template rendering errors.
    - Redirects user to React frontend after confirmation.
    """


    def get(self, request, key, *args, **kwargs):
        confirmation = EmailConfirmationHMAC.from_key(key)

        if confirmation:
            confirmation.confirm(request)
            frontend_redirect_url = os.getenv(
                'FRONTEND_CONFIRM_REDIRECT', 
                'http://127.0.0.1:3000/email-confirmed'
            )
            return redirect(frontend_redirect_url)
        else:
            return Response(
                {'detail': 'Invalid or expired confirmation link.'},
                status=status.HTTP_400_BAD_REQUEST
            )
