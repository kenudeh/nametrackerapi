import json
from django.core.management.base import BaseCommand, CommandError
from django.utils.dateparse import parse_date
import traceback 


from api.management.validators import validate_domain_data  # Custom validator function
from api.models import Name, UseCaseTag, UseCaseCategory, UseCase, IdeaOfTheDay, DomainListOptions, RegStatusOptions

import logging
logger = logging.getLogger(__name__)


# Example CLI usage:python manage.py load_json appname/data(a folder in app)/date.json(the exact json file) --drop_date=2025-07-01(a flag) --domain_list=pending_delete | marketplace(another flag)


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
                             Can be any of pending_delete, delted, or marketplac, but it defaults to 'pending_delete'. Validated against the Enum.
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

        # --- Map domain_list to status ---
        if domain_list == DomainListOptions.PENDING_DELETE:
            status = RegStatusOptions.PENDING
        elif domain_list == DomainListOptions.MARKETPLACE:
            status = RegStatusOptions.AVAILABLE
        elif domain_list in [DomainListOptions.ALL_LIST, DomainListOptions.DELETED]:
            status = RegStatusOptions.PENDING
        else:
            raise CommandError(f"Unexpected domain_list value encountered: {domain_list}")

        try:
            # --- Load and parse JSON file ---
            # with open(json_file_path, 'r', encoding='utf-8') as file:
            #     data = json.load(file)
            try:
                with open(json_file_path, 'r', encoding='utf-8') as file:
                    try:
                        data = json.load(file)
                    except json.JSONDecodeError as e:
                        logger.error(f"Invalid JSON format in {json_file_path}: {e}")
                        raise CommandError(f"JSON decode error: {e}")
            except FileNotFoundError:
                logger.error(f"File not found: {json_file_path}")
                raise CommandError(f"File not found: {json_file_path}")

            # --- Validate top-level structure ---
            if not isinstance(data, list):
                raise CommandError("Top-level JSON must be a list of domains.")

            # --- Preload allowed category names from DB ---
            allowed_categories = set(
                UseCaseCategory.objects.values_list('name', flat=True)
            )

            # To track domains and their scores
            top_scoring_domains = [] 
            records_processed = 0  # Count successful inserts

            # --- Process each domain entry ---
            for index, item in enumerate(data):
                domain_name = item.get('domain_name')

                # PER-ITEM VALIDATION: block bad domains BEFORE saving anything
                try:
                    validate_domain_data([item])  # Validator expects a list, but we're passing domains one by one for scalability purposes.
                except ValueError as e:
                    # self.stdout.write(self.style.ERROR(
                    #     f"Skipped '{domain_name}' due to validation error: {e}"
                    # ))
                    logger.error(f"Skipped '{domain_name}' due to validation error: {e}")
                    continue  #Block this domain from being saved

                # --- Check if domain already exists in DB ---
                if Name.objects.filter(domain_name=domain_name).exists():
                    # self.stdout.write(self.style.WARNING(
                    #     f"Skipped '{domain_name}': already exists in DB."
                    # ))
                    logger.warning(f"Skipped '{domain_name}': already exists in DB.")
                    continue

                # --- Extract all category names used in this domain's use cases ---
                use_case_categories = [
                    uc['category']['name']
                    for uc in item.get('use_cases', [])
                    if 'category' in uc and 'name' in uc['category']
                ]

                # --- Ensure all categories used exist in DB ---
                invalid_categories = [
                    name for name in use_case_categories if name not in allowed_categories
                ]
                if invalid_categories:
                    # self.stdout.write(self.style.WARNING(
                    #     f"Skipped '{domain_name}': unknown categories used: {', '.join(invalid_categories)}"
                    # ))
                    logger.warning(f"Skipped '{domain_name}': unknown categories used: {', '.join(invalid_categories)}")
                    continue

                # --- Create the Name entry ---
                name_obj = Name.objects.create(
                    domain_name=domain_name,
                    drop_date=drop_date,
                    domain_list=domain_list,
                    status=status,
                    score=item.get('score', None)
                )

                # --- Collect and assign unique tags across all use cases ---
                all_tag_names = set()
                for uc in item['use_cases']:
                    all_tag_names.update(
                        tag_dict['name']
                        for tag_dict in uc.get('tag', [])
                        if isinstance(tag_dict, dict) and 'name' in tag_dict
                    )

                # --- Create UseCase entries, including tags and categories ---
                for uc in item['use_cases']:
                    uc_category = UseCaseCategory.objects.get(name=uc['category']['name'])

                    # Create the use case instance
                    use_case_obj = UseCase.objects.create(
                        domain_name=name_obj,
                        case_title=uc['case_title'],
                        description=uc['description'],
                        difficulty=uc['difficulty'],
                        competition=uc['competition'],
                        target_market=uc['target_market'],
                        revenue_potential=uc['revenue_potential'],
                        order=uc['order'],
                        category=uc_category,
                    )

                    # Assign tags to this individual use case
                    for tag_dict in uc.get('tag', []):
                        tag_name = tag_dict.get('name')
                        if tag_name:
                            tag_obj, _ = UseCaseTag.objects.get_or_create(name=tag_name)
                            use_case_obj.tag.add(tag_obj)


                 # --- Log success for this domain ---
                # self.stdout.write(self.style.SUCCESS(f"Processed: {domain_name}"))
                logger.info(f"Processed: {domain_name}")

                # --- Track top scoring domains (for idea assignment later)
                if domain_list == DomainListOptions.PENDING_DELETE and item.get('score') is not None:
                    top_scoring_domains.append({
                        'domain_obj': name_obj,
                        'score': item.get('score'),
                    })


                records_processed += 1

            # --- Assign IdeaOfTheDay for 'pending_delete' domains if applicable ---
            if domain_list == DomainListOptions.PENDING_DELETE and top_scoring_domains:
                # Sort by score (descending), pick the top one (or more with same score)
                top_scoring_domains.sort(key=lambda x: x['score'], reverse=True)
                top_score = top_scoring_domains[0]['score']

                # Filter domains with the same top score
                tied_top_domains = [
                    d['domain_obj'] for d in top_scoring_domains if d['score'] == top_score
                ]

                # Pick the first one deterministically (if tie)
                selected_domain = tied_top_domains[0]

                # Get its top use case (order=1)
                top_use_case = selected_domain.use_cases.filter(order=1).first()

                if top_use_case:
                    # Check if an IdeaOfTheDay already exists for this date and list to avoid duplicates
                    existing = IdeaOfTheDay.objects.filter(
                        drop_date=drop_date,
                        domain_list=DomainListOptions.PENDING_DELETE
                    ).exists()

                    if not existing:
                        IdeaOfTheDay.objects.create(
                            use_case=top_use_case,
                            drop_date=drop_date,
                            domain_list=DomainListOptions.PENDING_DELETE
                        )
                        # self.stdout.write(self.style.SUCCESS(
                        #     f"IdeaOfTheDay created for drop_date {drop_date} from domain '{selected_domain.domain_name}'"
                        # ))
                        logger.info(f"IdeaOfTheDay created for drop_date {drop_date} from domain '{selected_domain.domain_name}'")
                    else:
                        # self.stdout.write(self.style.WARNING(
                        #     f"Skipped IdeaOfTheDay creation: already exists for {drop_date} and pending_delete."
                        # ))
                        logger.warning(f"Skipped IdeaOfTheDay creation: already exists for {drop_date} and pending_delete.")
                else:
                    # self.stdout.write(self.style.WARNING(
                    #     f"Skipped IdeaOfTheDay creation: no top use case (order=1) found for domain '{selected_domain.domain_name}'."
                    # ))
                    logger.warning( f"Skipped IdeaOfTheDay creation: no top use case (order=1) found for domain '{selected_domain.domain_name}'.")







            # --- Final success message ---
            # self.stdout.write(self.style.SUCCESS(f'Total domains processed: {records_processed}'))
            logger.info(f'Total domains processed: {records_processed}')
            # self.stdout.write(self.style.SUCCESS('All domain data loaded successfully.'))

        except Exception as e:
            logger.exception(f"Error loading JSON file: {e}")
            raise CommandError(f"Error loading JSON file: {e}")

