import json
from django.core.management.base import BaseCommand
from django.utils.text import slugify
from api.models import UseCaseCategory

class Command(BaseCommand):
    help = "Load categories from JSON and auto-generate slugs"
    #usage: python manage.py load_categories

    def handle(self, *args, **kwargs):
        # Path to your JSON file (adjust if needed)
        json_file = "api/fixtures/categories.json"
        
        try:
            with open(json_file) as f:
                categories = json.load(f)
                for cat in categories:
                    name = cat["name"]
                    slug = slugify(name)  # Auto-generate slug
                    
                    # Create or update category
                    UseCaseCategory.objects.update_or_create(
                        name=name,
                        defaults={"slug": slug}
                    )
                self.stdout.write(self.style.SUCCESS(f"Loaded {len(categories)} categories!"))
                
        except FileNotFoundError:
            self.stdout.write(self.style.ERROR("JSON file not found!"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error: {str(e)}"))