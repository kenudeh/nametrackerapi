import requests
from django.conf import settings

# Dynadot API Logic — Production Ready
# This file (services.py) handles Dynadot's availability check via its API
# via a class-based structure for reuse, clarity, and testability.


class DynadotAPI:
    """
    Handles communication with the Dynadot API to check domain availability.
    """

    BASE_URL = "https://api.dynadot.com/api3.json"

    def __init__(self):
        # Load API credentials from Django settings (read from .env via decouple or dotenv)
        self.api_key = settings.DYNADOT_API_KEY
        self.secret = settings.DYNADOT_API_SECRET  # Added in case secret is needed later

    def check_domain_availability(self, domain_name):
        """
        Checks the availability of a single domain name using Dynadot's API.

        Args:
            domain_name (str): The domain name to check (e.g., "example.com").

        Returns:
            str: 'available' if domain is free, 'taken' if already registered,
                 or 'unknown' if API call failed.
        """
        params = {
            'key': self.api_key,
            'command': 'search',   # Dynadot's availability check command
            'domain': domain_name,
            # 'secret': self.secret  # Only include if Dynadot requires secret in this request
        }

        try:
            response = requests.get(self.BASE_URL, params=params, timeout=10)
            response.raise_for_status()  # Raises an error for bad HTTP responses
            data = response.json()

            # Example expected Dynadot response structure — adjust if their API differs
            result = data.get("SearchResult", [{}])[0]
            is_available = result.get("available")

            if is_available is True:
                return 'available'
            elif is_available is False:
                return 'taken'
            else:
                return 'unknown'

        except requests.RequestException as e:
            # TODO: Replace print with proper logging in production
            print(f"[DynadotAPI] Error checking domain availability: {e}")
            return 'unknown'
