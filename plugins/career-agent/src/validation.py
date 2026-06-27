"""validation.py — Schema validation for profile.json and role configs.

Validates required fields and data types without external dependencies.
Provides actionable error messages for debugging.
"""

from collections.abc import Callable


class ValidationError(Exception):
    """Raised when validation fails."""

    pass


def validate_profile(data: dict, strict: bool = False) -> tuple[bool, list[str]]:
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
    if "email" in data and (not isinstance(data["email"], str) or "@" not in data["email"]):
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
    if "education" in data and not isinstance(data["education"], list):
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
            for variant_key in data["variants"]:
                if variant_key not in valid_variants:
                    errors.append(f"Unknown variant '{variant_key}'. Valid variants: A, B, C")

    # Validate yolo_mode if present
    if "yolo_mode" in data:
        yolo = data["yolo_mode"]
        if not isinstance(yolo, dict):
            errors.append("'yolo_mode' must be a dictionary")
        else:
            if "enabled" in yolo and not isinstance(yolo["enabled"], bool):
                errors.append("'yolo_mode.enabled' must be a boolean")
            if "authorization_key" in yolo and not isinstance(yolo["authorization_key"], str):
                errors.append("'yolo_mode.authorization_key' must be a string")
            if "permitted_tiers" in yolo:
                if not isinstance(yolo["permitted_tiers"], list):
                    errors.append("'yolo_mode.permitted_tiers' must be a list")
                else:
                    valid_tiers = {"volume", "selective", "priority"}
                    for tier in yolo["permitted_tiers"]:
                        if tier not in valid_tiers:
                            errors.append(
                                f"Unknown tier '{tier}' in yolo_mode.permitted_tiers. "
                                f"Valid: {', '.join(sorted(valid_tiers))}"
                            )
            if "excluded_companies" in yolo and not isinstance(yolo["excluded_companies"], list):
                errors.append("'yolo_mode.excluded_companies' must be a list")
            if "daily_cap" in yolo and (
                not isinstance(yolo["daily_cap"], int) or yolo["daily_cap"] < 1
            ):
                errors.append("'yolo_mode.daily_cap' must be a positive integer")

    # Validate additional_experience if present — inherited by role configs via
    # prepare_generation_config; a string would be iterated character-by-character
    # by cv_builder, producing a broken PDF section.
    if "additional_experience" in data:
        if not isinstance(data["additional_experience"], list):
            errors.append("'additional_experience' must be a list (use [] to suppress)")
        else:
            for i, line in enumerate(data["additional_experience"]):
                if not isinstance(line, str):
                    errors.append(f"'additional_experience[{i}]' must be a string")

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


def validate_role_config(data: dict, strict: bool = False) -> tuple[bool, list[str]]:
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
            errors.append(f"Invalid variant '{data['variant']}'. Must be one of: A, B, C")

    # Validate ATS platform
    # Note: "workable" (Workable.com) != "workday" (Workday HCM) — these are different platforms
    if "ats_platform" in data:
        if not isinstance(data["ats_platform"], str):
            errors.append("'ats_platform' must be a string")
        else:
            valid_platforms = {
                "greenhouse",
                "greenhouse_eu",
                "lever",
                "workable",
                "ashby",
                "teamtailor",
                "unknown",
            }
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

    # Validate application_tier if present
    if "application_tier" in data:
        valid_tiers = {"volume", "selective", "priority"}
        if data["application_tier"] not in valid_tiers:
            errors.append(
                f"Invalid 'application_tier' '{data['application_tier']}'. "
                f"Must be one of: {', '.join(sorted(valid_tiers))}"
            )

    # Validate sponsorship_available if present
    if "sponsorship_available" in data:
        valid_sponsorship = {"available", "unavailable", "unknown"}
        if data["sponsorship_available"] not in valid_sponsorship:
            errors.append(
                f"Invalid 'sponsorship_available' '{data['sponsorship_available']}'. "
                f"Must be one of: {', '.join(sorted(valid_sponsorship))}"
            )

    # Validate remote_status if present
    if "remote_status" in data:
        valid_remote = {"global", "regional", "onsite", "hybrid", "unknown"}
        if data["remote_status"] not in valid_remote:
            errors.append(
                f"Invalid 'remote_status' '{data['remote_status']}'. "
                f"Must be one of: {', '.join(sorted(valid_remote))}"
            )

    # Validate required_skills if present
    if "required_skills" in data:
        if not isinstance(data["required_skills"], list):
            errors.append("'required_skills' must be a list")
        else:
            for i, skill in enumerate(data["required_skills"]):
                if not isinstance(skill, str):
                    errors.append(f"'required_skills[{i}]' must be a string")

    # Validate custom_answers if present
    if "custom_answers" in data and not isinstance(data["custom_answers"], dict):
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
    if "experience_overrides" in data and not isinstance(data["experience_overrides"], dict):
        errors.append("'experience_overrides' must be a dictionary")

    # Validate openness if present — rendered verbatim into the CV banner,
    # so a non-string value (or `None`) would crash reportlab Paragraph.
    if "openness" in data and not isinstance(data["openness"], str):
        errors.append("'openness' must be a string")

    # Validate additional_experience if present — iterated as bullet lines by
    # cv_builder; a string would render character-by-character, a None would
    # raise on iteration if a future refactor drops the truthiness guard.
    if "additional_experience" in data:
        if not isinstance(data["additional_experience"], list):
            errors.append("'additional_experience' must be a list (use [] to suppress)")
        else:
            for i, line in enumerate(data["additional_experience"]):
                if not isinstance(line, str):
                    errors.append(f"'additional_experience[{i}]' must be a string")

    return len(errors) == 0, errors


def validate_and_report(
    data: dict,
    validator_func: Callable[[dict, bool], tuple[bool, list[str]]],
    config_type: str,
    filepath: str | None = None,
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
    is_valid, errors = validator_func(data, False)

    if not is_valid:
        file_context = f" in {filepath}" if filepath else ""
        error_msg = f"Invalid {config_type}{file_context}:\n"
        for i, err in enumerate(errors, 1):
            error_msg += f"  {i}. {err}\n"

        error_msg += (
            f"\nRefer to {config_type.replace(' ', '_')}.example.json for the correct schema."
        )
        raise ValidationError(error_msg)
