import requests
import logging
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type
from django.conf import settings

logger = logging.getLogger(__name__)


# Dynadot API Logic
# This file handles Dynadot's availability check via its API
# via a class-based structure for reuse, clarity, and testability.
class DynadotAPI:
    """
    Handles communication with the Dynadot API for domain availability checks (bulk supported).
    """

    BASE_URL = "https://api.dynadot.com/api3.json"

    def __init__(self):
        self.api_key = settings.DYNADOT_API_KEY
        self.secret = settings.DYNADOT_API_SECRET  # Reserved if needed later

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(5),
           retry=retry_if_exception_type(requests.RequestException))
    def check_bulk_domain_availability(self, domain_names):
        """
        Checks the availability of multiple domains in one API call.

        Args:
            domain_names (list of str): Domains to check.

        Returns:
            dict: Mapping of domain names to 'available', 'taken', or 'unknown'.
        """
        params = {
            'key': self.api_key,
            'command': 'search',
            'domain': ','.join(domain_names),  # Comma-separated domains for bulk check
        }

        try:
            response = requests.get(self.BASE_URL, params=params, timeout=20)
            response.raise_for_status()
            data = response.json()

            results = data.get("SearchResult", [])
            availability_map = {}

            for result in results:
                domain = result.get("domain")
                is_available = result.get("available")

                if is_available is True:
                    availability_map[domain] = 'available'
                elif is_available is False:
                    availability_map[domain] = 'taken'
                else:
                    availability_map[domain] = 'unknown'

            logger.info(f"[DynadotAPI] Checked {len(domain_names)} domains successfully.")
            return availability_map

        except requests.RequestException as e:
            logger.error(f"[DynadotAPI] Bulk availability check failed: {e}")
            # Mark all as unknown if the request failed
            return {domain: 'unknown' for domain in domain_names}