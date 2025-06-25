from allauth.account.models import EmailAddress
from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response
from django.shortcuts import redirect

class CustomConfirmEmailView(GenericAPIView):
    """
    Custom email confirmation view that:
    - Confirms user via token key.
    - Avoids template rendering errors.
    - Redirects user to React frontend after confirmation.
    """
    def get(self, request, key, *args, **kwargs):
        try:
            confirmation = (
                EmailAddress.objects
                .get(emailconfirmation__key=key)
                .emailconfirmation_set
                .get(key=key)
            )
            confirmation.confirm(request)
            # Using env variable to dynamically set confirmation URL
            frontend_url = os.getenv('FRONTEND_CONFIRM_REDIRECT', 'http://127.0.0.1:3000/email-confirmed')
            return redirect(frontend_url)
        except EmailAddress.DoesNotExist:
            return Response({'detail': 'Invalid or expired confirmation link.'}, status=status.HTTP_400_BAD_REQUEST)
