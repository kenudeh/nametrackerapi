import os
import jwt
import requests
from jwt import PyJWKClient
from django.conf import settings
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from .models import AppUser  # import my local model

class ClerkJWTAuthentication(BaseAuthentication):
    def authenticate(self, request):
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return None

        token = auth.split("Bearer ")[1]
        try:
            # Load and cache public keys for verification
            jwks_client = PyJWKClient(settings.CLERK_JWKS_URL)
            key = jwks_client.get_signing_key_from_jwt(token).key

            # Decode the Clerk-issued JWT
            payload = jwt.decode(
                token,
                key=key,
                algorithms=["RS256"],
                issuer=settings.CLERK_ISSUER,
                audience=settings.CLERK_AUDIENCE,
            )
        except Exception as e:
            raise AuthenticationFailed(f"Invalid token: {str(e)}")

        # Synchronize with local AppUser model
        clerk_id = payload.get("sub")
        email = payload.get("email")
        full_name = payload.get("name", "")

        # Fetch or create the user:
        user, _ = AppUser.objects.update_or_create(
            clerk_id=clerk_id,
            defaults={"email": email, "full_name": full_name}
        )

        # Auto-derive and store first/last names
        user.split_full_name()

        return (user, None)
