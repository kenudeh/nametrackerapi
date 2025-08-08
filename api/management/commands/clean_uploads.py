from django.core.management.base import BaseCommand
from yourapp.models import UploadedFile
from django.conf import settings
from pathlib import Path
import os

class Command(BaseCommand):
    help = 'Cleans orphaned files in upload directory'

    def handle(self, *args, **options):
        existing_files = set(UploadedFile.objects.values_list('filename', flat=True))
        upload_dir = Path(settings.UPLOAD_DIR)
        
        for file_path in upload_dir.iterdir():
            if file_path.is_file() and file_path.name not in existing_files:
                try:
                    file_path.unlink()
                    self.stdout.write(f"Deleted orphaned: {file_path.name}")
                except OSError as e:
                    self.stderr.write(f"Error deleting {file_path.name}: {e}")