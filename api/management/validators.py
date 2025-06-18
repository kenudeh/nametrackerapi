"""
This module provides JSON validation for the AI-generated domain data
before inserting into the database. It ensures that every domain record
and its nested use cases meet the required structure, types, and business rules.

Usage:
    from .validators import validate_domain_data
    validate_domain_data(data)  # Raises ValueError if invalid
"""

def validate_domain_data(data):
    """
    Validates a list of domain items for required fields, types, and business rules.

    Args:
        data (list): List of domain dicts loaded from JSON.

    Raises:
        ValueError: If validation fails due to missing fields, wrong types, or invalid structure.

    Returns:
        True if validation passes.
    """
    if not isinstance(data, list):
        raise ValueError("Top-level JSON data must be a list of domain records.")

    # These are the *only* fields required directly from JSON per domain
    required_name_fields = ['domain_name', 'category', 'tags', 'use_cases']

    # Required fields inside each use_case entry
    required_use_case_fields = [
        'case_title', 'description', 'difficulty', 'competition',
        'target_market', 'revenue_potential', 'order'
    ]

    for index, item in enumerate(data):
        if not isinstance(item, dict):
            raise ValueError(f"Domain item at index {index} must be a dictionary.")

        # Check that all required fields are present in each domain
        for field in required_name_fields:
            if field not in item:
                raise ValueError(f"Missing field '{field}' in domain item at index {index}.")

        # Field type checks
        if not isinstance(item['domain_name'], str):
            raise ValueError(f"'domain_name' must be a string at index {index}.")

        if not isinstance(item['tags'], list):
            raise ValueError(f"'tags' must be a list at index {index}.")

        if not isinstance(item['use_cases'], list):
            raise ValueError(f"'use_cases' must be a list at index {index}.")

        if len(item['use_cases']) > 3:
            raise ValueError(f"'use_cases' cannot contain more than 3 items (found {len(item['use_cases'])}) at index {index}.")

        # Validate 'category' field structure
        category = item['category']
        if not isinstance(category, dict) or 'name' not in category:
            raise ValueError(f"'category' must be a dict containing a 'name' key at index {index}.")

        # Validate each UseCase entry
        for uc_index, uc in enumerate(item['use_cases']):
            if not isinstance(uc, dict):
                raise ValueError(f"Use case at index {uc_index} in domain {index} must be a dictionary.")

            for uc_field in required_use_case_fields:
                if uc_field not in uc:
                    raise ValueError(f"Missing field '{uc_field}' in use_case {uc_index} at domain index {index}.")

            # Example type check for 'order'
            if not isinstance(uc['order'], int):
                raise ValueError(f"'order' in use_case {uc_index} at domain index {index} must be an integer.")

    return True  # All records passed validation
