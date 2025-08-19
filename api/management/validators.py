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
    Validates a list of domain name entries with associated use cases.

    Args:
        data (list): List of dictionaries, each representing a domain entry.

    Raises:
        ValueError: If required fields are missing or invalid.
    """

    required_name_fields = ['domain_name', 'use_cases']
    required_usecase_fields = [
        'case_title',
        'description',
        'difficulty',
        'competition',
        'category',
        'tag',
        'target_market',
        'revenue_potential',
        'order'
    ]

    for index, item in enumerate(data):
        # Check required top-level fields in Name
        for field in required_name_fields:
            if field not in item:
                raise ValueError(f"Missing field '{field}' in domain item at index {index}.")

        use_cases = item['use_cases']

        if not isinstance(use_cases, list) or len(use_cases) == 0:
            raise ValueError(f"'use_cases' must be a non-empty list in domain item at index {index}.")

        # Track seen orders to enforce uniqueness
        seen_orders = set()

        for uc_index, use_case in enumerate(use_cases):
            for field in required_usecase_fields:
                if field not in use_case:
                    raise ValueError(
                        f"Missing field '{field}' in use_case[{uc_index}] of domain item at index {index}."
                    )

            # Check category structure
            if not isinstance(use_case['category'], dict) or 'name' not in use_case['category']:
                raise ValueError(
                    f"Invalid or missing 'category.name' in use_case[{uc_index}] of domain item at index {index}."
                )

            # Check tag structure
            if not isinstance(use_case['tag'], list) or len(use_case['tag']) == 0:
                raise ValueError(
                    f"'tag' must be a non-empty list in use_case[{uc_index}] of domain item at index {index}."
                )

            for tag_item in use_case['tag']:
                if not isinstance(tag_item, dict) or 'name' not in tag_item:
                    raise ValueError(
                        f"Each tag in 'tag' must be a dict with a 'name' key in use_case[{uc_index}] of domain item at index {index}."
                    )

            # Check order is int and unique within this domain item
            order = use_case['order']
            if not isinstance(order, int):
                raise ValueError(
                    f"'order' must be an integer in use_case[{uc_index}] of domain item at index {index}."
                )

            if order in seen_orders:
                raise ValueError(
                    f"Duplicate 'order' value {order} in use_case[{uc_index}] of domain item at index {index}."
                )

            seen_orders.add(order)

        # Enforce that order numbers are sequential starting from 1
        expected_orders = set(range(1, len(use_cases) + 1))
        if seen_orders != expected_orders:
            raise ValueError(
                f"'order' values in domain item at index {index} must be unique and sequential starting from 1. Found: {sorted(seen_orders)}"
            )


