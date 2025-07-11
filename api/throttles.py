import hashlib
from rest_framework.throttling import UserRateThrottle


class PostRequestThrottle(UserRateThrottle):
    scope = 'post_request'

    def get_ident(self, request):
        if request.user.is_authenticated:
            # Authenticated users are throttled by their user ID
            return str(request.user.pk)

        # Fallback for anonymous users
        ip = (
            request.META.get("HTTP_X_FORWARDED_FOR") or 
            request.META.get("REMOTE_ADDR", "")
        ).split(",")[0].strip()

        ua = request.META.get("HTTP_USER_AGENT", "")

        if not ip and not ua:
            # Use static fallback to group unknown anonymous users
            return "anonymous-unknown"

        # Use a stable hash for consistent throttling
        ident_raw = f"{ip}:{ua}"
        ident_hash = hashlib.sha256(ident_raw.encode("utf-8")).hexdigest()

        return ident_hash

        #If I only want to throttle POST requests (and not GET, PUT, etc.)
        def allow_request(self, request, view):
            if request.method != 'POST':
                return True  # Do not throttle non-POST requests
            return super().allow_request(request, view)