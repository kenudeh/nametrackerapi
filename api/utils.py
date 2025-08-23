from pathlib import Path
from django.core.management import call_command
from django.db import transaction
from django.conf import settings
from datetime import date
from django.utils import timezone



def process_file(file_record):
    """Shared processing logic"""
    file_path = Path(settings.UPLOAD_DIR) / file_record.filename
    with transaction.atomic():
        call_command(
            "load_json",
            str(file_path),
            "--drop_date", str(file_record.drop_date),
            "--domain_list", file_record.domain_list
        )
        file_record.processed = True
        file_record.processed_at = timezone.now()
        file_record.save()