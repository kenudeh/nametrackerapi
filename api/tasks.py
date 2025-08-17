from celery import shared_task, chain
from celery.exceptions import Retry

from django.utils import timezone
from datetime import timedelta
from django.db.models import Q
from django.db import transaction

from .models import Name, ArchivedName, IdeaOfTheDay, UseCase, UploadedFile
from .handlers.services import DynadotAPI

from pathlib import Path
# from django.conf import settings
import subprocess
# from datetime import date
import logging

from django.db import transaction
from django.db.models import F
from django.utils import timezone
from itertools import islice

from django.core.cache import cache



logger = logging.getLogger('api.domain_tasks')

logger = logging.getLogger(__name__)


# Constants for availability checking time per extension (in hours)
EXTENSION_CHECK_DELAYS = {
    '.com': 2,
    '.co': 2,
    '.io': 6,
    '.ai': 12,
}

BATCH_SIZE = 50  # Upper limit per Dynadot batch
BULK_CHUNK = 50


# --- Archive old domains with lock ---
@shared_task(bind=True, time_limit=3600, ignore_result=True)
def archive_old_domains_task(self):
    """
    Bulk archives domains older than 90 days with improved:
    - Memory efficiency via chunking
    - Transaction safety
    - Batch operations
    - Error handling
    """
    lock_key = "archive_old_domains_lock"
    try:
        with cache.lock(lock_key, timeout=4000):  # ~1h + buffer
            ARCHIVAL_AGE_DAYS = 90
            BATCH_SIZE = 500

            cutoff = timezone.now() - timedelta(days=ARCHIVAL_AGE_DAYS)
            qs = Name.objects.filter(drop_date__lt=cutoff.date()).order_by('id')

            try:
                with transaction.atomic():
                    # Single-pass batch processing
                    for ids in batch(qs.values_list('id', flat=True), BATCH_SIZE):
                        batch_domains = Name.objects.filter(id__in=ids)
                        ArchivedName.objects.bulk_create(
                            [ArchivedName(**{
                                f.name: getattr(d, f.name)
                                for f in ArchivedName._meta.fields
                                if hasattr(d, f.name)
                            }) for d in batch_domains]
                        )
                        batch_domains.delete()
                        logger.info(f"Archived batch {ids[0]}-{ids[-1]}")
            except Exception as e:
                logger.exception("Archival failed at batch")
                raise self.retry(exc=e, countdown=300)
    except Exception as e:
        logger.error(f"Failed to acquire lock for archive_old_domains_task: {str(e)}")
        raise self.retry(exc=e, countdown=300)

        
# @shared_task
# def archive_old_domains_task(ignore_result=True, time_limit=1800):
#     """
#     Bulk archives domains older than 90 days with improved:
#     - Memory efficiency via chunking
#     - Transaction safety
#     - Batch operations
#     - Error handling
#     """
#     ARCHIVAL_AGE_DAYS = 90
#     ARCHIVE_BATCH_SIZE = 500  # Optimal for most DBs

#     now = timezone.now()
#     cutoff_date = (now - timedelta(days=ARCHIVAL_AGE_DAYS)).date()

#     try:
#         with transaction.atomic():
#             # Get queryset iterator for memory efficiency
#             old_domains = Name.objects.filter(
#                 drop_date__lt=cutoff_date
#             ).iterator(chunk_size=ARCHIVE_BATCH_SIZE)

#             archived_count = 0
#             current_batch = []

#             for domain in old_domains:
#                 current_batch.append(
#                     ArchivedName(
#                         domain=domain.domain,
#                         extension=domain.extension,
#                         drop_date=domain.drop_date,
#                         drop_time=domain.drop_time,
#                         domain_list=domain.domain_list,
#                         status=domain.status,
#                         last_checked=domain.last_checked,
#                         created_at=domain.created_at
#                     )
#                 )
#                 archived_count += 1

#                 # Process in batches
#                 if len(current_batch) >= ARCHIVE_BATCH_SIZE:
#                     ArchivedName.objects.bulk_create(current_batch)
#                     Name.objects.filter(
#                         id__in=[d.id for d in current_batch]
#                     ).delete()
#                     current_batch = []

#             # Process final partial batch
#             if current_batch:
#                 ArchivedName.objects.bulk_create(current_batch)
#                 Name.objects.filter(
#                     id__in=[d.id for d in current_batch]
#                 ).delete()

#             logger.info(
#                 "Successfully archived %d domains older than %s",
#                 archived_count,
#                 cutoff_date
#             )
#             return archived_count

#     except Exception as e:
#         logger.error(
#             "Archival failed for domains older than %s: %s",
#             cutoff_date,
#             str(e)
#         )
#         raise self.retry(exc=e)




# --- Pending to deleted transition (daily lock) ---
@shared_task(bind=True, time_limit=1200, ignore_result=True)
def transition_pending_to_deleted_task(self):
    """
    Transition domains from pending_delete to deleted status when their drop_time has passed.
    
    Processing Rules:
    1. Only move Names where domain_list='pending_delete' and drop_time <= now
    2. Set status='unverified' for all moved names
    3. For moved names with is_top_rated=True, set top_rated_date = drop_date
    4. Update IdeaOfTheDay with:
       - deleted_idea: Highest scoring domain from the entire batch being moved
       - pending_delete_idea: Highest scoring remaining pending_delete domain for today
    
    Implementation Notes:
    - Uses nested functions for task-specific helpers to avoid namespace pollution
    - Maintains chunked updates for memory efficiency
    - Single atomic transaction ensures data consistency
    """
    lock_key = f"pending_transition_lock_{timezone.now().date()}"

    if not cache.add(lock_key, "locked", timeout=3600):
        logger.warning("Task already running for today")
        return

    try:
        now = timezone.now()
        today = now.date()
        logger.info("Starting pending->deleted transition at %s", now)

        def process_bulk_transitions(ready_ids_iter):
            """Handle the bulk updates in memory-efficient chunks."""
            chunk = list(islice(ready_ids_iter, 0, BULK_CHUNK))
            while chunk:
                Name.objects.filter(id__in=chunk).update(
                    domain_list='deleted',
                    status='unverified'
                )
                Name.objects.filter(id__in=chunk, is_top_rated=True).update(
                    top_rated_date=F('drop_date')
                )
                chunk = list(islice(ready_ids_iter, 0, BULK_CHUNK))

        def get_top_pending_idea():
            """Get the highest-scoring pending idea for the day."""
            return (
                Name.objects
                .filter(domain_list='pending_delete', drop_date=today)
                .exclude(score__isnull=True)
                .order_by('-score')
                .first()
            )

        def update_ideas(top_deleted, top_pending):
            """Authoritative update of both idea fields."""
            idea_obj, _ = IdeaOfTheDay.objects.get_or_create(date=today)
            update_needed = False

            if top_deleted and idea_obj.deleted_idea != top_deleted:
                idea_obj.deleted_idea = top_deleted
                update_needed = True
                logger.debug("Set deleted_idea for %s to %s", today, top_deleted.domain)

            if top_pending and idea_obj.pending_delete_idea != top_pending:
                idea_obj.pending_delete_idea = top_pending
                update_needed = True
                logger.debug("Set pending_idea for %s to %s", today, top_pending.domain)

            if update_needed:
                idea_obj.save()

        ready_qs = (
            Name.objects
            .filter(domain_list='pending_delete', drop_time__lte=now)
            .order_by('-score')
            .only('id', 'score', 'domain', 'is_top_rated', 'drop_date')
        )

        ready_count = ready_qs.count()
        if ready_count == 0:
            if top_pending := get_top_pending_idea():
                idea_obj, _ = IdeaOfTheDay.objects.get_or_create(date=today)
                idea_obj.pending_delete_idea = top_pending
                idea_obj.save()
                logger.info("Updated pending idea for %s: %s", today, top_pending.domain)
            return

        all_ready_ids = ready_qs.values_list('id', flat=True)
        top_deleted = ready_qs.first()
        top_pending = get_top_pending_idea()

        with transaction.atomic():
            process_bulk_transitions(all_ready_ids)
            update_ideas(top_deleted, top_pending)

        logger.info(
            "Transitioned %d domains (top: %s) at %s",
            ready_count,
            top_deleted.domain if top_deleted else "none",
            now
        )
    finally:
        cache.delete(lock_key) # Release lock






# Helper function for availability check tasks
def get_eligible_check_domains():
    """Centralized query for domains ready for availability checks"""
    now = timezone.now()
    return Name.objects.filter(
        domain_list='deleted',
        status='unverified',
    ).annotate(
        check_time=F('drop_time') + timedelta(
            hours=EXTENSION_CHECK_DELAYS.get(F('extension'), 0)
        )
    ).filter(
        check_time__lte=now
    )




@shared_task(bind=True, ignore_result=True, time_limit=900)
def check_domain_availability_subtask(self, domain_ids):
    """
    Subtask: Checks availability of pre-qualified domains.
    
    Requirements:
    - Only processes domains that are:
      * In 'deleted' list
      * With 'unverified' status
      * Past their extension-specific check time
    - Updates status to available/taken/unverified
    - Handles API failures gracefully
    """
    now = timezone.now()
    dynadot_api = DynadotAPI()
    
    # Double-check eligibility (defensive programming)
    domains = get_eligible_check_domains().filter(id__in=domain_ids)
    if not domains.exists():
        logger.debug(f"Skipping batch - no eligible domains in {domain_ids}")
        return

    domain_names = [d.domain for d in domains]
    try:
        availability_map = dynadot_api.check_bulk_domain_availability(domain_names)
    except Exception as e:
        logger.error(f"API failed for batch {domain_ids}: {str(e)}")
        raise self.retry(exc=e)

    updates = []
    for domain in domains:
        availability = availability_map.get(domain.domain, 'unknown')
        new_status = (
            'available' if availability == 'available' else
            'taken' if availability == 'taken' else
            'unverified'
        )
        updates.append((domain.id, new_status, now))

    # Bulk update in a single operation
    Name.objects.bulk_update(
        [Name(id=id, status=status, last_checked=last_checked) 
        for id, status, last_checked in updates
        ],
        fields=['status', 'last_checked']
    )

    # Detailed logging
    counts = {
        'available': sum(1 for _, status, _ in updates if status == 'available'),
        'taken': sum(1 for _, status, _ in updates if status == 'taken'),
        'unknown': sum(1 for _, status, _ in updates if status == 'unverified')
    }
    logger.info(
        "Processed %d domains (A:%d/T:%d/U:%d)", 
        len(updates), counts['available'], counts['taken'], counts['unknown']
    )




@shared_task(bind=True, ignore_result=True, time_limit=900)
def trigger_bulk_availability_check_task(self):
    """
    Parent task: Orchestrates availability checks for eligible domains.
    
    Workflow:
    1. Finds all domains meeting check criteria:
       - In 'deleted' list
       - With 'unverified' status
       - Past their extension-specific check time (drop_time + EXTENSION_CHECK_DELAYS)
    2. Splits them into batches (respecting Dynadot's API limits)
    3. Creates a chain of subtasks for processing
    """
    lock_key = "dynadot_api_lock"
    lock_timeout = 1800

    try:
        # Attempt to acquire lock
        with cache.lock(lock_key, timeout=lock_timeout):
            # Main task logic 
            eligible_domains = get_eligible_check_domains()
            eligible_count = eligible_domains.count()

            if eligible_count == 0:
                logger.info("No domains currently eligible for availability checks")
                return

            # Get just IDs for efficient batching
            domain_ids = eligible_domains.values_list('id', flat=True)
            logger.info(
                "Preparing %d domains for checking (extensions: %s)",
                eligible_count,
                ", ".join(eligible_domains.values_list('extension', flat=True).distinct())
            )

            # Create batches respecting BATCH_SIZE constant
            batches = [list(islice(domain_ids, i, i + BATCH_SIZE))
                for i in range(0, eligible_count, BATCH_SIZE)]

            # Build subtask chain
            chain(
                check_domain_availability_subtask.s(batch)
                for batch in batches
            ).apply_async()

            logger.info(
                "Dispatched %d batches (%d domains total) for availability checking",
                len(batches),
                eligible_count
            )
 
    except Exception as e:
        logger.error(f"Failed to acquire lock or execute task: {str(e)}")
        raise self.retry(exc=e, countdown=300)





@shared_task(bind=True, ignore_result=True, time_limit=900)
def second_check_task(self):
    """
    Periodic recheck of domains in 'available' or 'unverified' status.
    Applies extension-specific check intervals and handles all states properly.
    """
    lock_key = "dynadot_second_check_lock"
    lock_timeout = 1800

    try:
        with cache.lock(lock_key, timeout=lock_timeout):
            now = timezone.now()
            dynadot_api = DynadotAPI()

            domains = Name.objects.filter(
                domain_list='deleted',
                status__in=['available', 'unverified'],
            ).annotate(
                # Dynamic check intervals based on extension
                min_check_hours=Greatest(
                    Value(12),
                    Value(EXTENSION_CHECK_DELAYS.get(F('extension'), 12)),
                    output_field=IntegerField()
                ),
                next_check_time=F('last_checked') + timedelta(
                    hours=F('min_check_hours')
                )
            ).filter(
                next_check_time__lte=now
            )

            if not domains.exists():
                logger.debug("No domains currently due for recheck")
                return

            domain_names = [d.domain for d in domains]
            try:
                availability_map = dynadot_api.check_bulk_domain_availability(domain_names)
            except Exception as e:
                logger.error(f"Recheck API failed: {str(e)}")
                raise self.retry(exc=e)

            updates = []
            for domain in domains:
                availability = availability_map.get(domain.domain, 'unknown')
                new_status = 'taken' if availability == 'taken' else domain.status
                updates.append((domain.id, new_status, now))

            Name.objects.bulk_update(
                [Name(id=id, status=status, last_checked=last_checked)
                 for id, status, last_checked in updates],
                fields=['status', 'last_checked']
            )

            # Detailed status reporting
            status_counts = {
                'previously_available': domains.filter(status='available').count(),
                'previously_unverified': domains.filter(status='unverified').count(),
                'now_taken': sum(1 for _, status, _ in updates if status == 'taken'),
                'still_available': sum(1 for _, status, _ in updates if status == 'available'),
                'still_unverified': sum(1 for _, status, _ in updates if status == 'unverified')
            }

            logger.info(
                "Recheck completed. Previous: A:%(previously_available)d/U:%(previously_unverified)d. "
                "Now: T:%(now_taken)d/A:%(still_available)d/U:%(still_unverified)d",
                status_counts
            )
    except Exception as e:
        logger.error(f"Failed to acquire lock or execute second check task: {str(e)}")
        raise self.retry(exc=e, countdown=300)





@shared_task(bind=True)
def daily_maintenance_task(self):
    lock_id = "daily_maintenance_lock"
    try:
        with cache.lock(lock_id, timeout=3600):
            chain(
                archive_old_domains_task.si(),
                # other future tasks
            ).apply_async()
    except Exception as e:
        logger.error(f"Daily maintenance failed: {str(e)}")
        raise self.retry(exc=e, countdown=300)

# Old master task
# @shared_task
# def full_domain_availability_task():
#     """
#     Master workflow now with improved scheduling and error handling.
#     """
#     from celery import chain, group

#     # Main sequential workflow
#     workflow = chain(
#         archive_old_domains_task.si(),
#         transition_pending_to_deleted_task.si(),
#         trigger_bulk_availability_check_task.si()
#     )

#     # Parallelize the periodic checks
#     periodic_checks = group(
#         second_check_task.si(),
#         # Could add other maintenance tasks here
#     )

#     # Execute workflow then periodic checks
#     (workflow | periodic_checks).apply_async()

#     logger.info("Initiated full domain availability pipeline")



# Auto-Loader Task
@shared_task(bind=True, ignore_result=True, time_limit=300)
def process_pending_files(self):
    """Automated periodic processing"""
    from .utils import process_file
    for record in UploadedFile.objects.filter(processed=False):
        try:
            process_file(record)
            record.processing_method = 'celery'
            record.save()
        except Exception as e:
            logger.error(f"Auto-process failed {record.filename}: {str(e)}")

# @shared_task
# def process_pending_files():
#     """Process files not marked as processed"""
#     unprocessed_files = UploadedFile.objects.filter(processed=False)
    
#     for record in unprocessed_files:
#         file_path = Path(settings.UPLOAD_DIR) / record.filename
        
#         try:
#             with transaction.atomic():
#                 # Use call_command instead of subprocess
#                 call_command(
#                     "load_json",
#                     str(file_path),
#                     "--drop_date", date.today().isoformat(),
#                     "--domain_list", "pending_delete"
#                 )
                
#                 record.processed = True
#                 record.processed_at = timezone.now()
#                 record.processing_method = 'celery'
#                 record.save()
                
#                 logger.info(f"Processed {record.filename}")
                
#         except Exception as e:
#             logger.error(f"Failed processing {record.filename}: {str(e)}")


# @shared_task
# def process_pending_files():
#     """
#     Check for unprocessed JSON files and call the loader command.
#     """
 
#     today = date.today().isoformat()
#     volume_path = Path(settings.UPLOAD_DIR)

#     for file in volume_path.glob("*.json"):
#         if not UploadedFile.objects.filter(filename=file.name, processed=True).exists():
#             # Run the loader
#             cmd = [
#                 "python", "manage.py", "load_json",
#                 str(file),
#                 "--drop_date", today,
#                 "--domain_list", "pending_delete"
#             ]
#             logger.info(f"Running loader for file: {file.name}")
#             subprocess.call(cmd)

#             # Mark as processed
#             UploadedFile.objects.update_or_create(
#                 filename=file.name,
#                 defaults={'processed': True}
#             )
#             logger.info(f"Marked {file.name} as processed.")
