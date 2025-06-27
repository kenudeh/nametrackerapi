from allauth.account.models import EmailConfirmation, EmailConfirmationHMAC
from rest_framework.permissions import AllowAny
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import redirect
import os
import logging

logger = logging.getLogger("api") 

class CustomConfirmEmailView(GenericAPIView):
    permission_classes = [AllowAny]

    def get(self, request, key, *args, **kwargs):
        logger.warning(f"Confirmation attempt with key: {key}")

        # Try both HMAC and DB-stored confirmation keys
        confirmation = EmailConfirmationHMAC.from_key(key)
        if confirmation is None:
            try:
                confirmation = EmailConfirmation.objects.get(key=key)
            except EmailConfirmation.DoesNotExist:
                confirmation = None

        if confirmation:
            confirmation.confirm(request)
            user = confirmation.email_address.user
            user.is_active = True
            user.save()

            redirect_url = os.getenv(
                'FRONTEND_CONFIRM_REDIRECT',
                'https://www.aitracker.io/email-confirmed'
            )
            return redirect(redirect_url)
        else:
            logger.warning(f"Invalid or expired confirmation link attempted: {key}")
            # NEW: Redirect to a user-friendly expired/invalid page
            error_redirect_url = os.getenv(
                'FRONTEND_CONFIRM_EXPIRED_REDIRECT',
                'https://www.aitracker.io/email-invalid-or-expired'
            )
            return redirect(error_redirect_url)
