# myapp/views.py



from allauth.account.models import EmailAddress
from allauth.account.utils import send_email_confirmation
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

User = get_user_model()

@api_view(['POST'])
@permission_classes([AllowAny])
def resend_email_confirmation(request):
    """
    Endpoint to resend the email verification link.
    
    Expects JSON payload: { "email": "user@example.com" }

    Logic:
    - Checks if email is provided
    - Checks if user exists
    - Prevents resending to already verified emails
    - Triggers email confirmation flow (via django-allauth)

    Returns:
    - 200 OK if email is sent
    - 400/404 if there's an issue (e.g., invalid email or already verified)
    """
    email = request.data.get("email")

    # 1. Validate that an email is present
    if not email:
        return Response(
            {"detail": "Email is required."},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        # 2. Check if user exists with this email
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        # Do NOT leak whether email exists — could be a security/privacy risk
        return Response(
            {"detail": "If an account exists for this email, a confirmation email has been sent."},
            status=status.HTTP_200_OK
        )

    # 3. Check if the email is already verified
    email_address = EmailAddress.objects.filter(user=user, email=email).first()
    if email_address and email_address.verified:
        return Response(
            {"detail": "This email address has already been verified."},
            status=status.HTTP_400_BAD_REQUEST
        )

    # 4. Send email confirmation via django-allauth
    send_email_confirmation(request, user)

    return Response(
        {"detail": "Verification email resent. Please check your inbox."},
        status=status.HTTP_200_OK
    )
