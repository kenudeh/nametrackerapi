
from allauth.account.models import EmailConfirmationHMAC
from rest_framework.permissions import AllowAny
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response
from django.shortcuts import redirect
from rest_framework import status
import os
import logging

logger = logging.getLogger(__name__)

class CustomConfirmEmailView(GenericAPIView):
    permission_classes = [AllowAny]
    """
    Custom email confirmation view that:
    - Confirms user via token key.
    - Avoids template rendering errors.
    - Redirects user to React frontend after confirmation.
    """


    def get(self, request, key, *args, **kwargs):
        logger.info("Attempting email confirmation with key: %s", key)
        confirmation = EmailConfirmationHMAC.from_key(key)

        if confirmation:
            confirmation.confirm(request)
            user = confirmation.get_user()
            user.is_active = True
            user.save()
            logger.info("Email confirmed and user activated: %s", user.email)


            frontend_redirect_url = os.getenv(
                'FRONTEND_CONFIRM_REDIRECT', 
                'https://www.aitracker.io/email-confirmed'
            )
            return redirect(frontend_redirect_url)
        else:
            logger.warning("Invalid or expired confirmation link attempted: %s", key)
            return Response(
                {'detail': 'Invalid or expired confirmation link.'},
                status=status.HTTP_400_BAD_REQUEST
            )
