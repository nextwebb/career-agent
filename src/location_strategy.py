"""location_strategy.py — configurable, context-aware location resolver.

Pure module. Resolves what value each artifact (CV, cover letter, ATS field,
availability banner, relocation statement) should render for its location
context, based on candidate-owned facts, presentations, and per-role strategy.

Contexts and strategy values are documented in profile.example.json and
roles.example/example_role.json.

Backward compatibility: when neither profile-level defaults nor role-level
strategy configure a context, `resolve_location` falls back to the legacy
top-level `profile["location"]` for the three artifact contexts that used to
read it (cv_contact, cover_letter_contact, ats_location). This preserves
byte-identical output for profiles that predate the new schema.
"""

from __future__ import annotations

from typing import Any

DEFAULT_REMOTE_LABEL = "Remote"

# Contexts backed by the legacy profile["location"] value. Other contexts
# (availability_banner, relocation_statement) have no legacy default; if the
# user does not configure a strategy for them, they render nothing.
_LEGACY_LOCATION_CONTEXTS = frozenset({"cv_contact", "cover_letter_contact", "ats_location"})

_ROLE_SPECIFIC_FIELDS = {
    "availability_banner": "availability_banner",
    "relocation_statement": "relocation_statement",
}


def _get_dict(container: Any, key: str) -> dict[str, Any]:
    value = container.get(key) if isinstance(container, dict) else None
    return value if isinstance(value, dict) else {}


def _clean(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _apply_strategy(
    strategy: str,
    profile: dict[str, Any],
    role_config: dict[str, Any],
    context: str,
) -> str | None:
    """Return the rendered value for a resolved (non-inherit) strategy."""

    if strategy == "hide":
        return None

    if strategy == "remote_label":
        presentations = _get_dict(profile, "location_presentations")
        return _clean(presentations.get("remote_label")) or DEFAULT_REMOTE_LABEL

    if strategy == "current_residence":
        facts = _get_dict(profile, "location_facts")
        return _clean(facts.get("current_residence")) or _clean(profile.get("location"))

    if strategy == "country_only":
        facts = _get_dict(profile, "location_facts")
        return _clean(facts.get("country_of_residence"))

    if strategy == "role_location":
        return _clean(role_config.get("location"))

    if strategy.startswith("custom:"):
        key = strategy[len("custom:") :]
        presentations = _get_dict(profile, "location_presentations")
        custom = presentations.get("custom")
        if isinstance(custom, dict):
            return _clean(custom.get(key))
        return None

    if strategy == "generated_role_specific":
        field = _ROLE_SPECIFIC_FIELDS.get(context)
        if field is None:
            return None
        return _clean(role_config.get(field))

    # Unknown strategy — treat as no value rather than crashing.
    return None


def resolve_location(
    profile: dict[str, Any],
    role_config: dict[str, Any],
    context: str,
) -> str | None:
    """Return the rendered value for one location context, or None to hide.

    Precedence (highest wins):
      1. role_config["location_strategy"][context]
      2. profile["location_strategy_defaults"][context]
      3. legacy profile["location"] for cv_contact / cover_letter_contact /
         ats_location when no strategy is configured
      4. None (context has no default; caller must skip rendering)

    The `inherit` strategy value falls through to the next-lower precedence
    level. Unknown strategies return None.
    """

    role_strategy = _get_dict(role_config, "location_strategy").get(context)
    profile_default = _get_dict(profile, "location_strategy_defaults").get(context)

    role_value = _clean(role_strategy)
    if role_value and role_value != "inherit":
        return _apply_strategy(role_value, profile, role_config, context)

    profile_value = _clean(profile_default)
    if profile_value and profile_value != "inherit":
        return _apply_strategy(profile_value, profile, role_config, context)

    if context in _LEGACY_LOCATION_CONTEXTS:
        return _clean(profile.get("location"))

    return None


def _strategy_value(container: Any, key: str, context: str) -> str | None:
    block = _get_dict(container, key)
    return _clean(block.get(context))


def _effective_strategy(
    profile: dict[str, Any],
    role_config: dict[str, Any],
    context: str,
) -> str | None:
    """Return the strategy that actually applies after inherit fall-through.

    Used by the warning collector to decide whether a configured story
    exists; distinct from `resolve_location`, which returns the rendered
    value rather than the strategy name.
    """

    role_value = _strategy_value(role_config, "location_strategy", context)
    if role_value and role_value != "inherit":
        return role_value
    profile_value = _strategy_value(profile, "location_strategy_defaults", context)
    if profile_value and profile_value != "inherit":
        return profile_value
    return None


def collect_location_warnings(
    profile: dict[str, Any],
    role_config: dict[str, Any],
) -> list[str]:
    """Return warning strings for suspicious contradictions.

    v1 warnings (conservative):
      1. cv_contact resolved to remote_label but role_config["location"]
         names a specific city
      2. Any strategy is `generated_role_specific` but the corresponding
         role field is missing
      3. Any strategy references `custom:X` but the presentation is not
         defined
      4. Legacy profile["location"] and
         profile["location_facts"]["current_residence"] disagree
    """

    warnings: list[str] = []
    presentations = _get_dict(profile, "location_presentations")
    custom = presentations.get("custom") if isinstance(presentations, dict) else None
    custom_dict = custom if isinstance(custom, dict) else {}

    cv_strategy = _effective_strategy(profile, role_config, "cv_contact")
    role_location = _clean(role_config.get("location"))
    if cv_strategy == "remote_label" and role_location and _names_specific_city(role_location):
        warnings.append(
            f"cv_contact renders remote_label but role location names a specific city "
            f"({role_location}); confirm this is intentional."
        )

    for context in (
        "cv_contact",
        "cover_letter_contact",
        "ats_location",
        "availability_banner",
        "relocation_statement",
    ):
        strategy = _effective_strategy(profile, role_config, context)
        if strategy is None:
            continue
        if strategy == "generated_role_specific":
            field = _ROLE_SPECIFIC_FIELDS.get(context)
            if field is None or not _clean(role_config.get(field)):
                warnings.append(
                    f"{context} strategy is generated_role_specific but role_config.{field} "
                    f"is missing."
                )
        elif strategy.startswith("custom:"):
            key = strategy[len("custom:") :]
            if not _clean(custom_dict.get(key)):
                warnings.append(
                    f"{context} strategy references custom:{key} but "
                    f"profile.location_presentations.custom.{key} is not defined."
                )

    legacy = _clean(profile.get("location"))
    facts = _get_dict(profile, "location_facts")
    residence = _clean(facts.get("current_residence"))
    if legacy and residence and legacy != residence:
        warnings.append(
            f"profile.location ({legacy}) and profile.location_facts.current_residence "
            f"({residence}) disagree; the new field wins for current_residence strategies."
        )

    return warnings


# Explicit restriction/eligibility markers used by pre_apply_checks are
# orthogonal; here we only need a lightweight signal that a role location
# names a specific place rather than a purely-remote posting. Anything that
# is not clearly a remote-only phrase counts.
_REMOTE_ONLY_TOKENS = ("remote", "anywhere", "global")


def _names_specific_city(location: str) -> bool:
    """True when a role location string looks like a specific place.

    Heuristic: a location is treated as "specific" when it contains any
    alphabetic content that is not one of the pure-remote tokens. This is
    conservative — the goal is warning surface, not eligibility gating.
    """

    lowered = location.strip().lower()
    if not lowered:
        return False
    # A location like "Remote" or "Anywhere" alone is not specific.
    stripped = lowered
    for token in _REMOTE_ONLY_TOKENS:
        stripped = stripped.replace(token, "")
    stripped = stripped.strip(" -,/()")
    return bool(stripped)
