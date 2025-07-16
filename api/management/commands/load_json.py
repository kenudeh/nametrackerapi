import json
from django.core.management.base import BaseCommand, CommandError
from django.utils.dateparse import parse_date
from api.management.validators import validate_domain_data  # Custom validator function
from api.models import Name, NameTag, NameCategory, UseCase, DomainListOptions, RegStatusOptions
import traceback 



# Example CLI usage:python manage.py load_json appname/data(a folder in app)/date.json(the exact json file) --drop_date=2025-07-01(a flag) --domain_list=marketplace(another flag)


class Command(BaseCommand):
    help = 'Loads domain data from an AI-generated JSON file into the database.'

    def add_arguments(self, parser):
        """
        Defines command-line arguments this loader accepts:
        
        1. Positional: 
            - json_file: Required path to the JSON file to load.
        
        2. Required Option: 
            - --drop_date: Manually specified drop date for this batch (in YYYY-MM-DD format).
        
        3. Optional Option:
            - --domain_list: Allows overriding the domain_list applied to this batch. 
                             Defaults to 'pending_delete'. Validated against the Enum.
        """
        parser.add_argument(
            'json_file', 
            type=str, 
            help='Path to the JSON file containing domain data.'
        )
        parser.add_argument(
            '--drop_date', 
            type=str, 
            required=True,
            help='Required: Drop date for this batch in YYYY-MM-DD format.'
        )
        parser.add_argument(
            '--domain_list',
            type=str,
            choices=[choice[0] for choice in DomainListOptions.choices],  # Enforced against Enum choices
            default=DomainListOptions.PENDING_DELETE,  # Default is 'pending_delete'
            help=(
                "Optional: Specify domain_list to assign all loaded domains to. "
                "Options: 'all_list', 'pending_delete', 'deleted', 'marketplace'. "
                "Defaults to 'pending_delete'."
            )
        )

    def handle(self, *args, **options):
        json_file_path = options['json_file']
        drop_date_str = options['drop_date']
        domain_list = options['domain_list']  # Already validated by argparse choices

        # --- Validate and parse drop_date argument ---
        if not drop_date_str:
            raise CommandError("Error: --drop_date argument is required.")
        
        try:
            drop_date = parse_date(drop_date_str)
            if not drop_date:
                raise ValueError("Invalid drop_date format. Use YYYY-MM-DD.")
        except Exception as e:
            raise CommandError(f"Error parsing drop_date: {e}")

        # --- Determine 'status' based on the provided 'domain_list' ---
        # Note: domain_list is guaranteed valid because of 'choices' in add_arguments
        if domain_list == DomainListOptions.PENDING_DELETE:
            status = RegStatusOptions.PENDING
        elif domain_list == DomainListOptions.MARKETPLACE:
            status = RegStatusOptions.AVAILABLE
        elif domain_list in [DomainListOptions.ALL_LIST, DomainListOptions.DELETED]:
            status = RegStatusOptions.PENDING  # Default assumption (can be adjusted if needed)
        else:
            # Safety net: Should never reach here because of argparse validation
            raise CommandError(f"Unexpected domain_list value encountered: {domain_list}")

        try:
            # --- Load and parse JSON data file ---
            with open(json_file_path, 'r') as file:
                data = json.load(file)

            # --- Validate the JSON structure before processing any records ---
            validate_domain_data(data)  # Custom validator ensures structure correctness
            self.stdout.write(self.style.SUCCESS('JSON validation passed. Proceeding to load data...'))

            records_processed = 0  # Counter for logging how many records are processed

            # --- Process each domain record in the JSON file ---
            for item in data:
                # --- Handle category (ForeignKey to NameCategory) ---
                category_data = item.get('category', {})
                if not category_data or 'name' not in category_data:
                    raise CommandError(f"Missing 'category' or 'name' key in item: {item}")
                
                # Fetch or create the corresponding NameCategory object
                category_obj, _ = NameCategory.objects.get_or_create(name=category_data['name'])

                # --- Create or update the Name instance ---
                # Notes:
                #   - 'drop_date' and 'domain_list' come from CLI arguments, not JSON.
                #   - 'status' is determined dynamically based on 'domain_list'.
                #   - Fields like 'extension', 'drop_time', 'length', 'syllables' are auto-calculated in model.
                #   - Signals handle competition, difficulty, and suggested_usecase computations.

                name_obj, _ = Name.objects.update_or_create(
                    domain_name=item['domain_name'],  # Unique key to match existing records
                    defaults={
                        'drop_date': drop_date,          # Provided by CLI
                        'domain_list': domain_list,      # From CLI, overrides model default
                        'status': status,                # Derived earlier based on domain_list
                        'category': category_obj,        # From JSON (required key)
                        'score': item.get('score', None),  # From JSON (required key)
                        # Model will handle calculated and signal fields
                    }
                )

                # --- Handle tags (ManyToMany to NameTag) ---
                name_obj.tag.clear()  # Remove all existing tags to prevent duplication
                for tag_name in item.get('tags', []):  # 'tags' expected to be a list in JSON
                    tag_obj, _ = NameTag.objects.get_or_create(name=tag_name)
                    name_obj.tag.add(tag_obj)  # Associate the tag with the Name object

                # --- Handle use cases (OneToMany to UseCase) ---
                UseCase.objects.filter(domain_name=name_obj).delete()  # Remove old UseCases linked to this Name
                for use_case_data in item.get('use_cases', []):  # 'use_cases' expected to be a list in JSON
                    UseCase.objects.create(
                        domain_name=name_obj,  # FK to Name
                        **use_case_data        # Assumes each dict has correct UseCase model fields
                    )

                # --- Increment record processed count ---
                records_processed += 1

                # --- Log successful processing of this domain ---
                self.stdout.write(self.style.SUCCESS(f"Processed domain: {item['domain_name']}"))

            # --- After processing all records, log total processed domains ---
            self.stdout.write(self.style.SUCCESS(f'Total domains processed: {records_processed}'))
            self.stdout.write(self.style.SUCCESS('All domain data loaded successfully.'))

        except Exception as e:
            traceback.print_exc()  # To see full error, if any
            raise CommandError(f"Error loading JSON file: {e}")
