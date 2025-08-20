import requests
import logging
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type
from django.conf import settings

logger = logging.getLogger(__name__)


# RapidAPI Bulk Domain Availability Service
# This class encapsulates the provider's API logic
# Uses POST requests with JSON payloads for bulk checks
class RapidAPIBulkDomainAPI:
    """
    Handles communication with the RapidAPI bulk domain availability service.
    """

    RAPIDAPI_URL = settings.RAPIDAPI_URL
    RAPIDAPI_HOST = settings.RAPIDAPI_HOST
    

    def __init__(self):
        # Store API key securely via Django settings
        self.api_key = settings.RAPIDAPI_KEY

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(5),
           retry=retry_if_exception_type(requests.RequestException))
    def check_bulk_domain_availability(self, domain_names):
        """
        Checks availability of multiple domains in one API call.

        Args:
            domain_names (list[str]): List of domains to check.

        Returns:
            dict: Mapping of domain names -> 'available' | 'taken' | 'unknown'
        """

        # Construct the request headers for authentication
        headers = {
            "x-rapidapi-key": self.api_key,
            "x-rapidapi-host": self.RAPIDAPI_HOST,
            "Content-Type": "application/json",
        }

        # Body must be JSON with a list of domains
        payload = {"domains": domain_names}

        try:
            # Make POST request to RapidAPI endpoint
            response = requests.post(
                self.RAPIDAPI_URL,
                json=payload,
                headers=headers,
                timeout=20
            )
            response.raise_for_status()  # Raise if HTTP error
            data = response.json()       # Parse response JSON

            results = data.get("results", [])
            availability_map = {}

            # Normalize results into your unified format
            for result in results:
                domain = result.get("domain")
                is_available = result.get("available")

                if is_available is True:
                    availability_map[domain] = "available"
                elif is_available is False:
                    availability_map[domain] = "taken"
                else:
                    availability_map[domain] = "unknown"

            logger.info(f"[RapidAPIBulkDomainAPI] Checked {len(domain_names)} domains successfully.")
            return availability_map

        except requests.RequestException as e:
            logger.error(f"[RapidAPIBulkDomainAPI] Bulk availability check failed: {e}")
            # If the request fails entirely, mark all domains as unknown
            return {domain: "unknown" for domain in domain_names}
