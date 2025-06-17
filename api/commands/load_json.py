
import json
from django.core.management.base import BaseCommand, CommandError
from api.validators import validate_domain_data  
from api.models import Name, NameTag, NameCategory, UseCase

class Command(BaseCommand):
    help = 'Loads domain data from an AI-generated JSON file into the database.'

    def add_arguments(self, parser):
        parser.add_argument('json_file', type=str, help='Path to the JSON file.')

    def handle(self, *args, **options):
        json_file_path = options['json_file']

        try:
            with open(json_file_path, 'r') as file:
                data = json.load(file)

            # Validate JSON structure before processing
            validate_domain_data(data)

            self.stdout.write(self.style.SUCCESS('JSON validation passed. Loading data...'))

            # Proceed with loading after validation passes
            for item in data:
                category_data = {'name': item['category']}
                category_obj, _ = NameCategory.objects.get_or_create(**category_data)

                name_obj, _ = Name.objects.update_or_create(
                    domain_name=item['domain_name'],
                    defaults={
                        'extension': item['extension'],
                        'domain_list': item['domain_list'],
                        'status': item['status'],
                        'competition': item['competition'],
                        'difficulty': item['difficulty'],
                        'suggested_usecase': item['suggested_usecase'],
                        'is_top_rated': item['is_top_rated'],
                        'is_favorite': item['is_favorite'],
                        'drop_date': item['drop_date'],
                        'drop_time': item['drop_time'],
                        'category': category_obj
                    }
                )

                # Tags (ManyToMany)
                name_obj.tag.clear()
                for tag_name in item['tags']:
                    tag_obj, _ = NameTag.objects.get_or_create(name=tag_name)
                    name_obj.tag.add(tag_obj)

                # UseCases
                UseCase.objects.filter(domain_name=name_obj).delete()  # Clear existing
                for use_case_data in item['use_cases']:
                    UseCase.objects.create(
                        domain_name=name_obj,
                        **use_case_data
                    )

            self.stdout.write(self.style.SUCCESS('Domain data loaded successfully.'))

        except Exception as e:
            raise CommandError(f"Error loading JSON file: {e}")
