# CURRENTLY NOT IN USE. FRONTEND AND CLERK CONTROL USER"S SESSION LIFETIME


from django.conf import settings
from django.utils import timezone
from django.contrib.auth import logout
from django.http import JsonResponse
import datetime
import logging

logger = logging.getLogger(__name__)

class SessionTimeoutMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            if request.user.is_authenticated:
                last_activity = request.session.get('last_activity')
                
                if last_activity:
                    try:
                        last_activity = datetime.datetime.fromisoformat(last_activity)
                        current_time = timezone.now()
                        inactivity_period = current_time - last_activity
                        
                        # Check if user has been inactive for too long (30 minutes)
                        if inactivity_period > datetime.timedelta(minutes=30):
                            logger.info(
                                f"Session timeout for user {request.user.username}. "
                                f"Last activity: {last_activity.isoformat()}, "
                                f"Current time: {current_time.isoformat()}"
                            )
                            logout(request)
                            return JsonResponse({
                                'error': 'Session expired due to inactivity',
                                'code': 'SESSION_TIMEOUT'
                            }, status=440)
                    except (ValueError, TypeError) as e:
                        logger.error(f"Error parsing last activity timestamp: {e}")
                        # Reset the timestamp if there's an error
                        request.session['last_activity'] = timezone.now().isoformat()
                
                # Update last activity timestamp
                request.session['last_activity'] = timezone.now().isoformat()

        except Exception as e:
            logger.error(f"Unexpected error in SessionTimeoutMiddleware: {e}")
            # Continue processing the request even if there's an error
            pass

        response = self.get_response(request)
        return response