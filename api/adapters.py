from allauth.account.adapter import DefaultAccountAdapter
from django.http import JsonResponse
from allauth.account.utils import send_email_confirmation


# This custom adapter disables auto-login, to manually send the confirmation email, stop auto-login, and reject unconfirmed users login attempt

class MyAccountAdapter(DefaultAccountAdapter):
    def is_open_for_signup(self, request):
        return True

    def save_user(self, request, user, form, commit=True):
        user = super().save_user(request, user, form, commit=False)
        user.is_active = False  # prevent login before email confirmation
        if commit:
            user.save()
        # Send confirmation email
        send_email_confirmation(request, user)

        return user

    def is_auto_login_after_signup(self, request, user):
        return False  # stops auto-login after signup

    def respond_user_inactive(self, request, user):
        # Return a clean JSON error instead of redirecting
        return JsonResponse(
            {"detail": "Email confirmation required before login."},
            status=403
        )
