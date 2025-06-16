
from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from .models import Name, ArchivedName
from .services import DynadotAPI

# Constants for availability checking time per extension (in hours)
EXTENSION_CHECK_DELAYS = {
    '.com': 2,
    '.co': 2,
    '.io': 6,
    '.ai': 12,
}

@shared_task
def check_domain_availability_task():
    """
    Celery task to:
    1. Move 'pending_delete' domains to 'deleted' list when their drop date arrives.
    2. Check availability for 'deleted' domains after extension-specific delays.
    3. Perform a secondary check (12 hours later) for domains still marked 'available'.
    4. Archive domains older than 90 days to ArchivedName model and remove them from the Name table.
    """
    now = timezone.now()
    dynadot_api = DynadotAPI()  # Initialize Dynadot API handler

    # 1. Archive domains older than 90 days
    ninety_days_ago = now - timedelta(days=90)
    old_domains = Name.objects.filter(
        drop_date__lt=ninety_days_ago.date()
    )

    for domain in old_domains:
        # Move to ArchivedName
        ArchivedName.objects.create(
            domain=domain.domain,
            extension=domain.extension,
            drop_date=domain.drop_date,
            drop_time=domain.drop_time,
            domain_list=domain.domain_list,
            status=domain.status,
            last_checked=domain.last_checked,
            created_at=domain.created_at
            # Add other fields if your models contain more
        )
        # Delete from Name table
        domain.delete()

    # 2. Transition 'pending_delete' domains to 'deleted' when drop_date arrives
    pending_domains = Name.objects.filter(domain_list='pending_delete', drop_date__lte=now.date())

    for domain in pending_domains:
        domain.domain_list = 'deleted'  # Move to deleted list
        domain.status = 'unverified'    # Needs availability check
        domain.save()

    # 3. Check availability for 'deleted' domains that are 'unverified'
    deleted_domains = Name.objects.filter(
        domain_list='deleted',
        status='unverified'
    )

    for domain in deleted_domains:
        extension = domain.extension.lower()
        delay_hours = EXTENSION_CHECK_DELAYS.get(extension)

        if delay_hours is None:
            # Unknown extension; skip
            continue

        # Calculate the earliest time when checking is allowed
        drop_datetime = timezone.make_aware(
            timezone.datetime.combine(domain.drop_date, domain.drop_time)
        )
        required_check_time = drop_datetime + timedelta(hours=delay_hours)

        if now >= required_check_time:
            # Perform API availability check via Dynadot
            availability = dynadot_api.check_domain_availability(domain.domain)

            if availability == 'available':
                domain.status = 'available'
            else:
                domain.status = 'taken'
            domain.last_checked = now  # Update the last checked time
            domain.save()

    # 4. Secondary check after 12 hours for domains still marked 'available'
    second_check_domains = Name.objects.filter(
        domain_list='deleted',
        status='available',
        last_checked__lte=now - timedelta(hours=12)
    )

    for domain in second_check_domains:
        availability = dynadot_api.check_domain_availability(domain.domain)

        if availability == 'available':
            # Still available; simply update check time
            domain.last_checked = now
        else:
            # Now taken; update status
            domain.status = 'taken'
        domain.save()

"""
NOTES:

- This task should be scheduled via Celery Beat to run periodically (e.g., every hour).
- Example CELERY_BEAT_SCHEDULE configuration (usually in settings.py or celery.py):
    CELERY_BEAT_SCHEDULE = {
        'check-domain-every-hour': {
            'task': 'your_app.tasks.check_domain_availability_task',
            'schedule': crontab(minute=0, hour='*'),
        },
    }
"""
