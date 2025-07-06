import jwt
from jwt import PyJWKClient
from django.conf import settings
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from .models import AppUser


class ClerkJWTAuthentication(BaseAuthentication):
    """
    Custom authentication class that verifies Clerk-issued JWT tokens
    and syncs them with the local AppUser model.
    """

    def authenticate(self, request):
        # Getting the token from the Authorization header
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return None  # No token provided or wrong format

        token = auth.split("Bearer ")[1]

        try:
            # Fetching Clerk's public key and decode the JWT
            jwks_client = PyJWKClient(settings.CLERK_JWKS_URL)
            signing_key = jwks_client.get_signing_key_from_jwt(token).key

            payload = jwt.decode(
                token,
                key=signing_key,
                algorithms=["RS256"],
                issuer=settings.CLERK_ISSUER,
                audience=settings.CLERK_AUDIENCE,
            )
        except Exception as e:
            raise AuthenticationFailed(f"Invalid token: {str(e)}")

        # Extracting user data from Clerk token
        clerk_id = payload.get("sub")      # Clerk's unique user ID
        email = payload.get("email")
        full_name = payload.get("name", "")  # Clerk's full name claim

        if not clerk_id or not email:
            raise AuthenticationFailed("Missing required Clerk fields: 'sub' or 'email'")

        # Getting or create the AppUser locally
        user, created = AppUser.objects.get_or_create(clerk_id=clerk_id)

        # Checking if email or full_name has changed — update only if needed
        updated = False
        if user.email != email:
            user.email = email
            updated = True

        if user.full_name != full_name:
            user.full_name = full_name
            updated = True

        if updated:
            user.save(update_fields=["email", "full_name"])

            # If full_name changed, update first_name and last_name
            user.split_full_name()

        # Return the user as the authenticated principal
        return (user, None)
