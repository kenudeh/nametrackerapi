# nametrackerapi/postmark_backend.py

"""
Custom Email Backend to send all Django emails using Postmark API (not SMTP).
This replaces the default SMTP backend.

Keeps Allauth and dj-rest-auth functionality (like signup confirmation, password reset).
"""

from django.core.mail.backends.base import BaseEmailBackend
from postmarker.core import PostmarkClient
from django.conf import settings

class EmailBackend(BaseEmailBackend):
    """
    Custom Email Backend for Django to send emails via Postmark API.
    """

    def send_messages(self, email_messages):
        """
        Sends all EmailMessage instances via Postmark API.

        Args:
            email_messages (list): A list of Django EmailMessage instances.
        
        Returns:
            int: The number of successfully sent messages.
        """
        if not email_messages:
            return 0  # No emails to send

        # Initialize the Postmark API client
        client = PostmarkClient(server_token=settings.POSTMARK_API_TOKEN)
        sent_count = 0

        # Loop through each email message Django tries to send
        for message in email_messages:
            try:
                # Send the email using Postmark's API
                client.emails.send(
                    From=message.from_email,
                    To=', '.join(message.to),  # Recipients list converted to comma-separated string
                    Subject=message.subject,
                    HtmlBody=message.body,  # Sends HTML body (or plain text if preferred)
                    # TextBody=message.body, # Use this instead if you want plain text emails
                )
                sent_count += 1  # Increment success counter
            except Exception as e:
                if not self.fail_silently:
                    raise e  # Re-raise exception unless fail_silently=True

        return sent_count  # Return how many were successfully sent
