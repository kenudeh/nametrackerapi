import jwt
from jwt import PyJWKClient
from django.conf import settings
from django.core.cache import caches
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from .models import AppUser
import logging

logger = logging.getLogger(__name__)

class ClerkJWTAuthentication(BaseAuthentication):
    """
    Production-ready JWT Authentication for Clerk with:
    - Secure token validation
    - Redis caching
    - Full user synchronization
    - Graceful degradation
    """

    def __init__(self):
        self.jwks_client = PyJWKClient(
            settings.CLERK_JWKS_URL,
            cache_keys=True,
            lifespan=3600,  # 1 hour cache
            timeout=10
        )
        self.cache = caches['default']  # Production-ready cache


    def authenticate(self, request):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return None

        token = auth_header.split(" ")[1].strip()
        
        try:
            payload = self._validate_token(token)
            
            # Clerk always includes 'sub' even if not in template
            clerk_id = payload['sub']  # No .get() needed - guaranteed to exist
            email = payload.get('email') or f"{clerk_id}@clerk_temp"  # Fallback
            full_name = payload.get('name', '')
            
            user = self._get_or_create_user(clerk_id, email, full_name)
            return (user, None)
            
        except Exception as e:
            logger.error(f"Auth failed: {str(e)}")
            raise AuthenticationFailed("Authentication failed")


    def _validate_token(self, token):
        try:
            signing_key = self.jwks_client.get_signing_key_from_jwt(token)
            payload = jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256"],
                issuer=settings.CLERK_ISSUER,
                audience=settings.CLERK_AUDIENCE if settings.CLERK_AUDIENCE else None,
                options={
                    "verify_exp": True,
                    "verify_iss": True,
                    "verify_aud": bool(settings.CLERK_AUDIENCE),
                }
            )
            
            # Additional claim validation
            if not payload.get('sub'):
                raise AuthenticationFailed("Missing user ID in token")
                
            return payload
            
        except jwt.ExpiredSignatureError:
            logger.warning("Expired token - frontend should refresh")
            raise AuthenticationFailed("Token expired - please refresh")
        except Exception as e:
            logger.error(f"Token validation failed: {str(e)}")
            raise AuthenticationFailed("Invalid authentication token")


    def _get_or_create_user(self, clerk_id, email, full_name):
        """Thread-safe user synchronization with cache locking"""
        cache_key = f"user_sync_{clerk_id}"
        
        try:
            # Cache lock prevents race conditions
            with self.cache.lock(cache_key, timeout=5):
                user, created = AppUser.objects.get_or_create(
                    clerk_id=clerk_id,
                    defaults={'email': email, 'full_name': full_name}
                )
                
                # Only update if changes detected
                update_fields = []
                if user.email != email:
                    user.email = email
                    update_fields.append('email')
                
                if user.full_name != full_name:
                    user.full_name = full_name
                    update_fields.append('full_name')
                
                if update_fields:
                    user.save(update_fields=update_fields)
                    user.split_full_name()
                    
                return user
                
        except Exception as e:
            logger.error(f"User sync failed: {str(e)}")
            raise AuthenticationFailed("User synchronization error")