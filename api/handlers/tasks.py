from celery import shared_task, chain
from django.utils import timezone
from datetime import timedelta
from django.db.models import Q
from .models import Name, ArchivedName
from .services import DynadotAPI
import logging

logger = logging.getLogger(__name__)

# Constants for availability checking time per extension (in hours)
EXTENSION_CHECK_DELAYS = {
    '.com': 2,
    '.co': 2,
    '.io': 6,
    '.ai': 12,
}

BATCH_SIZE = 50  # Upper limit per Dynadot batch

@shared_task
def archive_old_domains_task():
    """
    Archives domains older than 90 days from 'Name' to 'ArchivedName'.
    """
    now = timezone.now()
    ninety_days_ago = now - timedelta(days=90)
    old_domains = Name.objects.filter(drop_date__lt=ninety_days_ago.date())

    for domain in old_domains:
        ArchivedName.objects.create(
            domain=domain.domain,
            extension=domain.extension,
            drop_date=domain.drop_date,
            drop_time=domain.drop_time,
            domain_list=domain.domain_list,
            status=domain.status,
            last_checked=domain.last_checked,
            created_at=domain.created_at
        )
        domain.delete()

    logger.info(f"Archived {old_domains.count()} old domains.")


@shared_task
def transition_pending_to_deleted_task():
    """
    Moves 'pending_delete' domains to 'deleted' if drop_date has arrived.
    Marks top-rated names with today's date.
    """
    now = timezone.now()
    pending_domains = Name.objects.filter(domain_list='pending_delete', drop_date__lte=now.date())

    for domain in pending_domains:
        domain.domain_list = 'deleted'
        domain.status = 'unverified'
        if domain.is_top_rated:
            domain.top_rated_date = now.date()  # Mark today's top-rated names
        domain.save()

    logger.info(f"Transitioned {pending_domains.count()} domains from pending_delete to deleted.")


@shared_task
def check_domain_availability_subtask(domain_ids):
    """
    Subtask: Checks availability of a batch of domains by IDs.
    """
    now = timezone.now()
    dynadot_api = DynadotAPI()
    domains = Name.objects.filter(id__in=domain_ids)

    domain_names = [d.domain for d in domains]
    availability_map = dynadot_api.check_bulk_domain_availability(domain_names)

    # Update domain statuses based on availability
    for domain in domains:
        availability = availability_map.get(domain.domain, 'unknown')

        if availability == 'available':
            domain.status = 'available'
        elif availability == 'taken':
            domain.status = 'taken'
        else:
            domain.status = 'unverified'  # Will retry in next cycle
        domain.last_checked = now

    Name.objects.bulk_update(domains, ['status', 'last_checked'])

    counts = {
        'available': sum(1 for d in domains if d.status == 'available'),
        'taken': sum(1 for d in domains if d.status == 'taken'),
        'unknown': sum(1 for d in domains if d.status == 'unverified')
    }
    logger.info(f"Processed batch: {len(domains)} domains. {counts}")


@shared_task
def trigger_bulk_availability_check_task():
    """
    Parent task: Splits 'deleted' domains into batches and triggers subtasks.
    """
    now = timezone.now()
    domains = Name.objects.filter(domain_list='deleted', status='unverified')

    domain_ids = list(domains.values_list('id', flat=True))

    # Split into batches
    batches = [domain_ids[i:i + BATCH_SIZE] for i in range(0, len(domain_ids), BATCH_SIZE)]

    logger.info(f"Scheduling {len(batches)} availability check subtasks.")

    # Chain subtasks for Celery to process
    subtasks = [check_domain_availability_subtask.s(batch) for batch in batches]
    chain(*subtasks)()


@shared_task
def second_check_task():
    """
    Checks 'available' domains after 12 hours to confirm they are still available.
    """
    now = timezone.now()
    dynadot_api = DynadotAPI()
    domains = Name.objects.filter(
        domain_list='deleted',
        status='available',
        last_checked__lte=now - timedelta(hours=12)
    )

    domain_names = [d.domain for d in domains]
    availability_map = dynadot_api.check_bulk_domain_availability(domain_names)

    for domain in domains:
        availability = availability_map.get(domain.domain, 'unknown')
        if availability == 'taken':
            domain.status = 'taken'  # Now taken; remove from 'available'
        domain.last_checked = now

    Name.objects.bulk_update(domains, ['status', 'last_checked'])
    logger.info(f"Performed 12-hour recheck on {len(domains)} domains.")


@shared_task
def full_domain_availability_task():
    """
    Master task that runs all required domain handling steps in order.
    """
    chain(
        archive_old_domains_task.s(),
        transition_pending_to_deleted_task.s(),
        trigger_bulk_availability_check_task.s(),
        second_check_task.s()
    )()