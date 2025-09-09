import json
from django.core.management.base import BaseCommand
from api.models import TargetMarket

class Command(BaseCommand):
    help = "Load Target Markets from the master JSON file."

    def handle(self, *args, **kwargs):
        json_file = "api/fixtures/target_markets.json"
        
        try:
            with open(json_file) as f:
                target_markets = json.load(f)
                count = 0
                for tm_data in target_markets:
                    name = tm_data["name"]
                    obj, created = TargetMarket.objects.get_or_create(name=name)
                    if created:
                        count += 1
                self.stdout.write(self.style.SUCCESS(f"Loaded/Verified {len(target_markets)} target markets. {count} new ones were created."))
                
        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f"JSON file not found at: {json_file}"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"An error occurred: {str(e)}"))