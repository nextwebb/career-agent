"""validation.py — Schema validation for profile.json and role configs.

Validates required fields and data types without external dependencies.
Provides actionable error messages for debugging.
"""

from typing import Any, Dict, List, Optional, Tuple


class ValidationError(Exception):
    """Raised when validation fails."""
    pass


def validate_profile(data: dict, strict: bool = False) -> Tuple[bool, List[str]]:
    """
    Validate profile.json structure.

    Args:
        data: The profile data dictionary
        strict: If True, warn about unknown fields (default: False)

    Returns:
        Tuple of (is_valid, error_messages)
    """
    errors = []

    # Required top-level fields
    required_fields = ["name", "email", "links", "experience", "education", "skills"]
    for field in required_fields:
        if field not in data:
            errors.append(f"Missing required field: '{field}'")

    # Validate name structure
    if "name" in data:
        if not isinstance(data["name"], dict):
            errors.append("'name' must be a dictionary")
        else:
            name = data["name"]
            if "first" not in name:
                errors.append("'name.first' is required")
            if "last" not in name:
                errors.append("'name.last' is required")

    # Validate email
    if "email" in data:
        if not isinstance(data["email"], str) or "@" not in data["email"]:
            errors.append("'email' must be a valid email address")

    # Validate links
    if "links" in data:
        if not isinstance(data["links"], dict):
            errors.append("'links' must be a dictionary")
        else:
            for key, value in data["links"].items():
                if value and not isinstance(value, str):
                    errors.append(f"'links.{key}' must be a string")

    # Validate experience
    if "experience" in data:
        if not isinstance(data["experience"], list):
            errors.append("'experience' must be a list")
        else:
            for i, exp in enumerate(data["experience"]):
                if not isinstance(exp, dict):
                    errors.append(f"'experience[{i}]' must be a dictionary")
                    continue

                # Check required experience fields
                if "id" not in exp:
                    errors.append(f"'experience[{i}].id' is required")
                if "title" not in exp:
                    errors.append(f"'experience[{i}].title' is required")
                if "company" not in exp:
                    errors.append(f"'experience[{i}].company' is required")
                if "bullets" not in exp:
                    errors.append(f"'experience[{i}].bullets' is required")

    # Validate education
    if "education" in data:
        if not isinstance(data["education"], list):
            errors.append("'education' must be a list")

    # Validate skills
    if "skills" in data:
        if not isinstance(data["skills"], list):
            errors.append("'skills' must be a list")
        else:
            for i, skill in enumerate(data["skills"]):
                if not isinstance(skill, dict):
                    errors.append(f"'skills[{i}]' must be a dictionary")
                    continue
                if "label" not in skill:
                    errors.append(f"'skills[{i}].label' is required")
                if "items" not in skill:
                    errors.append(f"'skills[{i}].items' is required")

    # Validate variants if present
    if "variants" in data:
        if not isinstance(data["variants"], dict):
            errors.append("'variants' must be a dictionary")
        else:
            valid_variants = {"A", "B", "C"}
            for variant_key in data["variants"].keys():
                if variant_key not in valid_variants:
                    errors.append(
                        f"Unknown variant '{variant_key}'. Valid variants: A, B, C"
                    )

    # Validate impact_statements if present
    if "impact_statements" in data:
        if not isinstance(data["impact_statements"], dict):
            errors.append("'impact_statements' must be a dictionary")
        else:
            for key, statement in data["impact_statements"].items():
                if not isinstance(statement, dict):
                    errors.append(f"'impact_statements.{key}' must be a dictionary")
                    continue
                if "title" not in statement:
                    errors.append(f"'impact_statements.{key}.title' is required")
                if "body" not in statement:
                    errors.append(f"'impact_statements.{key}.body' is required")

    return len(errors) == 0, errors


def validate_role_config(data: dict, strict: bool = False) -> Tuple[bool, List[str]]:
    """
    Validate role config JSON structure.

    Args:
        data: The role config data dictionary
        strict: If True, warn about unknown fields (default: False)

    Returns:
        Tuple of (is_valid, error_messages)
    """
    errors = []

    # Required fields
    required_fields = [
        "role_id",
        "company",
        "title",
        "url",
        "ats_platform",
        "variant",
        "output_prefix",
    ]

    for field in required_fields:
        if field not in data:
            errors.append(f"Missing required field: '{field}'")

    # Validate variant
    if "variant" in data:
        valid_variants = {"A", "B", "C"}
        if data["variant"] not in valid_variants:
            errors.append(
                f"Invalid variant '{data['variant']}'. Must be one of: A, B, C"
            )

    # Validate ATS platform
    if "ats_platform" in data:
        valid_platforms = {"greenhouse", "lever", "workable"}
        platform = data["ats_platform"].lower()
        if platform not in valid_platforms:
            errors.append(
                f"Unknown ATS platform '{data['ats_platform']}'. "
                f"Supported platforms: {', '.join(sorted(valid_platforms))}"
            )

    # Validate URL format
    if "url" in data:
        url = data["url"]
        if not isinstance(url, str):
            errors.append("'url' must be a string")
        elif not url.startswith(("http://", "https://")):
            errors.append("'url' must start with http:// or https://")

    # Validate output_prefix
    if "output_prefix" in data:
        prefix = data["output_prefix"]
        if not isinstance(prefix, str):
            errors.append("'output_prefix' must be a string")
        elif not prefix:
            errors.append("'output_prefix' cannot be empty")

    # Validate custom_answers if present
    if "custom_answers" in data:
        if not isinstance(data["custom_answers"], dict):
            errors.append("'custom_answers' must be a dictionary")

    # Validate cover_letter if present
    if "cover_letter" in data:
        if not isinstance(data["cover_letter"], dict):
            errors.append("'cover_letter' must be a dictionary")
        else:
            cl = data["cover_letter"]
            if "paragraphs" in cl and not isinstance(cl["paragraphs"], list):
                errors.append("'cover_letter.paragraphs' must be a list")

    # Validate experience_overrides if present
    if "experience_overrides" in data:
        if not isinstance(data["experience_overrides"], dict):
            errors.append("'experience_overrides' must be a dictionary")

    return len(errors) == 0, errors


def validate_and_report(
    data: dict,
    validator_func: callable,
    config_type: str,
    filepath: str = None
) -> None:
    """
    Validate data and raise ValidationError with formatted message if invalid.

    Args:
        data: The data to validate
        validator_func: The validation function (validate_profile or validate_role_config)
        config_type: Type of config for error message (e.g., "profile", "role config")
        filepath: Optional file path for error message context

    Raises:
        ValidationError: If validation fails
    """
    is_valid, errors = validator_func(data)

    if not is_valid:
        file_context = f" in {filepath}" if filepath else ""
        error_msg = f"Invalid {config_type}{file_context}:\n"
        for i, err in enumerate(errors, 1):
            error_msg += f"  {i}. {err}\n"

        error_msg += f"\nRefer to {config_type.replace(' ', '_')}.example.json for the correct schema."
        raise ValidationError(error_msg)
