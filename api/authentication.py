import jwt
from jwt import PyJWKClient
from django.conf import settings
from django.core.cache import caches
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from .models import AppUser
import logging

from django.utils.dateparse import parse_datetime
import requests

logger = logging.getLogger(__name__)


class ClerkJWTAuthentication(BaseAuthentication):
    """
    Production-ready JWT Authentication for Clerk with:
    - JWKS-based secure token validation
    - Optional Redis caching support
    - Graceful user synchronization
    """

    def __init__(self):
        # Initialize JWKS client with caching
        self.jwks_client = PyJWKClient(
            settings.CLERK_JWKS_URL,
            cache_keys=True,
            lifespan=3600,  # Cache keys for 1 hour
            timeout=10
        )
        # Use Django's default cache (can be Redis or LocMem)
        self.cache = caches['default']


    def authenticate(self, request):
        """
        Main entry point for DRF authentication.
        Extracts and verifies the JWT from the Authorization header.
        Returns (user, None) on success, raises AuthenticationFailed otherwise.
        """
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return None  # Let other authentication classes try

        token = auth_header.split(" ")[1].strip()

        try:
            # if settings.debug:
            #     # Decode without verification for debugging purposes
            #     unverified = jwt.decode(token, options={"verify_signature": False})
            #     logger.debug(f"Token claims (unverified): {unverified}")

            # Get the signing key from Clerk
            signing_key = self.jwks_client.get_signing_key_from_jwt(token).key

            # Build decoding arguments dynamically based on settings
            decode_kwargs = {
                "key": signing_key,
                "algorithms": ["RS256"],
                "issuer": settings.CLERK_ISSUER,
                "options": {
                    "verify_exp": True,
                    "verify_iss": True,
                    "verify_aud": False,  # Default to False
                },
                "leeway": 10 
            }

            # Only verify audience if explicitly configured
            if settings.CLERK_AUDIENCE:
                decode_kwargs["audience"] = settings.CLERK_AUDIENCE
                decode_kwargs["options"]["verify_aud"] = True

            # Decode and validate token
            payload = jwt.decode(token, **decode_kwargs)

            # Sync and return user
            user = self.get_user(payload)
            return (user, None)

        except Exception as e:
            logger.error(f"Auth failed: {str(e)}")
            raise AuthenticationFailed("Invalid token")



    def get_user(self, payload):
        """
        Extracts user data from a validated token payload and syncs with database.
        This method is expected by DRF internals and wraps _get_or_create_user().
        """
        clerk_id = payload['sub']
        email = payload.get('email', f"{clerk_id}@temp.clerk")
        full_name = payload.get('name', '')

        return self._get_or_create_user(clerk_id, email, full_name)




    
    def _get_or_create_user(self, clerk_id, email, full_name):
        """
        Thread-safe user sync. Uses cache locking if supported.
        """
        cache_key = f"user_sync_{clerk_id}"

        def sync_user():
            user, created = AppUser.objects.get_or_create(
                clerk_id=clerk_id,
                defaults={'email': email, 'full_name': full_name}
            )

            update_fields = []

            if user.email != email:
                user.email = email
                update_fields.append('email')

            if user.full_name != full_name:
                user.full_name = full_name
                update_fields.append('full_name')

            # ✅ Fetch true created_at from Clerk if user was newly created
            if created:
                try:
                    response = requests.get(
                        f"{settings.CLERK_API_BASE_URL}/users/{clerk_id}",
                        headers={"Authorization": f"Bearer {settings.CLERK_SECRET_KEY}"}
                    )
                    logger.debug(f"Clerk Management API status: {response.status_code}")
                    response.raise_for_status()
                    data = response.json()

                    created_raw = data.get("created_at")
                    logger.debug(f"Clerk created_at raw: {created_raw}")

                    true_created = parse_datetime(created_raw)
                    if true_created:
                        user.created_at = true_created
                        update_fields.append("created_at")
                    else:
                        logger.warning("Failed to parse Clerk created_at")

                except Exception as e:
                    logger.warning(f"Could not fetch true created_at from Clerk: {str(e)}")

            # Save updates and split name
            if update_fields:
                user.save(update_fields=update_fields)

            if not user.first_name or not user.last_name:
                user.split_full_name()

            return user

        try:
            if hasattr(self.cache, "lock"):
                with self.cache.lock(cache_key, timeout=5):
                    return sync_user()
            else:
                return sync_user()
        except Exception as e:
            logger.error(f"User sync failed: {str(e)}")
            raise AuthenticationFailed("User synchronization error")

    # def _get_or_create_user(self, clerk_id, email, full_name):
    #     """
    #     Thread-safe user sync with cache lock to avoid race conditions.
    #     Creates or updates AppUser instance based on Clerk ID.
    #     """
    #     cache_key = f"user_sync_{clerk_id}"

    #     try:
    #         # Prevent concurrent writes using cache lock (requires Redis or compatible backend)
    #         with self.cache.lock(cache_key, timeout=5):
    #             user, created = AppUser.objects.get_or_create(
    #                 clerk_id=clerk_id,
    #                 defaults={'email': email, 'full_name': full_name}
    #             )

    #             # Update user fields if necessary
    #             update_fields = []

    #             if user.email != email:
    #                 user.email = email
    #                 update_fields.append('email')

    #             if user.full_name != full_name:
    #                 user.full_name = full_name
    #                 update_fields.append('full_name')

    #             if update_fields:
    #                 user.save(update_fields=update_fields)
    #                 user.split_full_name()

    #             return user

    #     except Exception as e:
    #         logger.error(f"User sync failed: {str(e)}")
    #         raise AuthenticationFailed("User synchronization error")
