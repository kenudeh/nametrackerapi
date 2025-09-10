import json
from django.core.management.base import BaseCommand
from api.models import TargetMarket

class Command(BaseCommand):
    help = "Finds and prints any TargetMarket entries in the DB that are not in the master JSON list."

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.SUCCESS("--- Running Discrepancy Check ---"))
        
        # --- Load the approved names from JSON file ---
        json_file_path = "api/fixtures/target_markets.json"
        try:
            with open(json_file_path, 'r') as f:
                approved_data = json.load(f)
            approved_names = {item['name'] for item in approved_data}
            self.stdout.write(f"  Loaded {len(approved_names)} approved names from the JSON file.")
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"  Error loading JSON file: {e}"))
            return

        # --- Get all names currently in the database ---
        db_names = set(TargetMarket.objects.values_list('name', flat=True))
        self.stdout.write(f"  Found {len(db_names)} names in the database.")

        # --- Find and print the difference ---
        extra_entries = db_names.difference(approved_names)

        if extra_entries:
            self.stdout.write(self.style.WARNING("\n--- DISCREPANCY FOUND ---"))
            self.stdout.write("The following entries exist in the database but not in the master JSON list:")
            for i, entry in enumerate(sorted(list(extra_entries)), 1):
                self.stdout.write(f"{i}. '{entry}'")
        else:
            self.stdout.write(self.style.SUCCESS("\n✅ No discrepancies found. The lists are identical."))

        self.stdout.write(self.style.SUCCESS("\n--- Discrepancy Check Complete ---"))