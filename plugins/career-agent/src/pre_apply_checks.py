"""
pre_apply_checks.py — Blocking gates that run before any apply attempt.

These gates catch failure modes that are invisible to artifact quality checks:
duplicate applications, missing PDFs, unsupported ATS platforms, and unknown
confirmation patterns. All gates must pass before browser automation starts.

Usage (from the apply skill or CLI):
    from pre_apply_checks import run_pre_apply_checks, PreApplyError

    try:
        run_pre_apply_checks(
            role_id="stripe_backend",
            job_url="https://jobs.lever.co/stripe/abc123/apply",
            ats_platform="lever",
            output_prefix="Peterson_Oaikhenah_Stripe_SeniorBackend_2026-06",
            generated_dir=Path("generated"),
            tracker_path=Path("tracker.json"),
        )
    except PreApplyError as e:
        print(f"Blocked: {e}")
        sys.exit(1)
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class PreApplyError(Exception):
    """Raised when a pre-apply gate blocks the application."""


class DuplicateApplicationError(PreApplyError):
    """Raised when the job URL already exists in the submission log."""


class MissingArtifactsError(PreApplyError):
    """Raised when required PDF artifacts are not present."""


class UnsupportedPlatformError(PreApplyError):
    """Raised when the ATS platform has no verified confirmation pattern."""


class LocationEligibilityError(PreApplyError):
    """Raised when the role's location/eligibility requirement does not match the profile."""


# ---------------------------------------------------------------------------
# Confirmation pattern registry
# ---------------------------------------------------------------------------

_REGISTRY_PATH = Path(__file__).parent / "ats_confirmation_patterns.json"


def load_confirmation_registry(registry_path: Path | None = None) -> dict[str, Any]:
    path = registry_path or _REGISTRY_PATH
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)  # type: ignore[no-any-return]


# ---------------------------------------------------------------------------
# Individual gates
# ---------------------------------------------------------------------------


def check_duplicate(job_url: str, tracker_path: Path) -> None:
    """
    FAIL if job_url already exists in the submission log.

    Regression target: BUX "You already applied" (2026-06-22).
    The ATS caught the duplicate; the pipeline never should have reached submit.

    Matches on normalised URL (strips trailing slash, lowercased scheme+host).
    """
    if not tracker_path.exists():
        return  # no history, safe to proceed

    with open(tracker_path, encoding="utf-8") as f:
        entries: list[dict[str, Any]] = json.load(f)

    normalised = _normalise_url(job_url)

    for entry in entries:
        entry_url = entry.get("url", "")
        if not entry_url:
            continue
        if _normalise_url(entry_url) == normalised:
            status = entry.get("status", "unknown")
            company = entry.get("company", "unknown")
            role_id = entry.get("role_id", "unknown")
            raise DuplicateApplicationError(
                f"Already tracked: {company} ({role_id}) with status '{status}'. " f"URL: {job_url}"
            )


def check_artifacts_exist(output_prefix: str, generated_dir: Path) -> None:
    """
    FAIL if the CV or cover letter PDF does not exist on disk.

    The apply skill must not start if artifacts are missing — it would
    upload nothing and the ATS would reject silently or not at all.
    """
    cv_path = generated_dir / f"{output_prefix}_CV.pdf"
    cl_path = generated_dir / f"{output_prefix}_CoverLetter.pdf"

    missing = []
    if not cv_path.exists():
        missing.append(str(cv_path))
    if not cl_path.exists():
        missing.append(str(cl_path))

    if missing:
        raise MissingArtifactsError(
            f"Required PDF(s) not found: {', '.join(missing)}. "
            f"Run: python src/generate_application.py --role <role_id>"
        )

    # Also fail on zero-byte files — a corrupt write looks like a file
    for path in [cv_path, cl_path]:
        if path.stat().st_size < 512:
            raise MissingArtifactsError(f"PDF appears corrupt (< 512 bytes): {path}")


def check_platform_supported(
    ats_platform: str,
    registry_path: Path | None = None,
) -> None:
    """
    FAIL if the ATS platform has no verified confirmation pattern.

    Autonomous mode cannot verify submission success on an unknown platform.
    The confirmation pattern registry is built empirically from real runs;
    a platform is added only after a successful HITL test confirms the pattern.

    In HITL mode, ats_platform="unknown" is allowed — the apply skill will hand
    off to the user for manual submission. This function has no concept of mode;
    the autonomous guard lives in run_pre_apply_checks.
    """
    if ats_platform in ("unknown", ""):
        # "unknown" is allowed in HITL mode (manual handoff).
        # run_pre_apply_checks raises before calling here when autonomous=True.
        return

    registry = load_confirmation_registry(registry_path)

    if ats_platform not in registry:
        raise UnsupportedPlatformError(
            f"ATS platform '{ats_platform}' has no verified confirmation pattern. "
            f"Known platforms: {', '.join(sorted(registry.keys()))}. "
            f"Add a confirmed entry to src/ats_confirmation_patterns.json before "
            f"enabling autonomous mode for this platform."
        )


# Country alias groups: each entry maps equivalent names/codes to one another so
# that an authorized "US" matches a restriction that says "United States" (and vice
# versa). Comparison is case-insensitive against the normalised tokens.
_COUNTRY_ALIASES: list[set[str]] = [
    {"us", "usa", "united states", "united states of america", "america"},
    {"uk", "united kingdom", "great britain", "britain", "gb"},
    {"uae", "united arab emirates"},
    {"eu", "european union", "eea", "european economic area"},
]


def _location_aliases(token: str) -> set[str]:
    """Return the set of equivalent names/codes for a country token (incl. itself)."""
    token = token.strip().lower()
    if not token:
        return set()
    for group in _COUNTRY_ALIASES:
        if token in group:
            return set(group)
    return {token}


# A role's `location` is a DISPLAY string by default. We only treat it as an
# eligibility restriction when it carries an explicit restriction marker — a clear,
# conservative signal that the location is gating eligibility rather than describing
# where the role sits. Bare locations ("Berlin", "Remote - United States") never gate.
_RESTRICTION_MARKER_PATTERNS = [
    r"\bonly\b",  # "United States only", "EU only"
    r"\bno sponsorship\b",
    r"\bmust be authori[sz]ed\b",
    r"\bmust have (?:the )?right to work\b",
    r"\bauthori[sz]ation required\b",
]
_RESTRICTION_MARKER_RE = re.compile("|".join(_RESTRICTION_MARKER_PATTERNS), re.IGNORECASE)


def _has_restriction_marker(text: str) -> bool:
    """True if a location string carries an explicit eligibility-restriction marker."""
    return bool(text and _RESTRICTION_MARKER_RE.search(text))


def _restriction_tokens(restriction: str) -> set[str]:
    """
    Tokenise a restriction string for whole-token country matching.

    Produces both single-word tokens (split on non-alphanumeric boundaries) and a
    set of multi-word substrings so multi-word country names like "united states"
    still match. Everything is lowercased.
    """
    words = [w for w in re.split(r"[^a-z0-9]+", restriction.lower()) if w]
    tokens: set[str] = set(words)
    # Add adjacent word pairs/triples so multi-word aliases match (e.g. "united states").
    for n in (2, 3):
        for i in range(len(words) - n + 1):
            tokens.add(" ".join(words[i : i + n]))
    return tokens


def check_location_eligibility(
    role_config: dict,
    profile: dict,
    force_location: bool = False,
) -> None:
    """
    FAIL if the role's eligibility restriction does not match the profile's
    authorized work countries.

    A restriction is selected from role_config when EITHER holds:
      (a) "right_to_work" is non-empty → it is always an eligibility restriction; OR
      (b) "location" carries an explicit RESTRICTION MARKER (e.g. the word "only" at
          a word boundary as in "United States only" / "EU only", or phrases like
          "no sponsorship", "must be authorized", "must have the right to work",
          "authorization required") → the location is treated as the restriction.

    A PLAIN display "location" with no marker ("Berlin", "Remote - United States",
    "Amsterdam, Netherlands", "Berlin HQ", ...) is NOT an eligibility restriction and
    does NOT gate — treating bare display locations as restrictions would false-block
    sponsorship-requiring profiles, since many such roles sponsor. We only enforce
    explicit restriction signals. (None of the current 30 role configs contain a
    marker, so this gate stays a safe no-op for them today, but it correctly fires on
    a future "X only" role and never false-blocks a plain display location.)

    Reads authorized countries from the profile's EEO work-authorization schema:
    profile["eeo"]["current_right_to_work"] (a list of country names/codes), with a
    fallback to profile["work_authorization"]["current_right_to_work"] for the shape
    built by src/jobqa_workspace.py:_build_candidate.

    Matching is done on whole, case-insensitive tokens (with a small alias map for
    common code/name pairs like US/USA/"United States"), so a substring like "us"
    in "Australia only" does NOT count as a match.

    If force_location is True, logs a warning and returns without raising.
    """
    if force_location:
        return  # explicit override — log warning in caller

    # Select the restriction. right_to_work is always an eligibility restriction;
    # "location" is display-only UNLESS it carries an explicit restriction marker.
    restriction = role_config.get("right_to_work", "")
    if not restriction:
        location = role_config.get("location", "")
        if _has_restriction_marker(location):
            restriction = location
    if not restriction:
        return  # no explicit restriction (no right_to_work, no location marker) — pass

    # Read authorized countries from the real profile schema (profile.eeo), falling
    # back to the jobqa-built work_authorization shape. Both use current_right_to_work.
    eeo = profile.get("eeo", {})
    authorized = eeo.get("current_right_to_work")
    if not authorized:
        work_auth = profile.get("work_authorization", {})
        authorized = work_auth.get("current_right_to_work", [])
    if not authorized:
        return  # no work-auth data in profile — skip (don't block on missing data)

    # Whole-token match: tokenise the restriction and compare against each
    # authorized country (and its aliases) by exact token equality.
    restriction_tokens = _restriction_tokens(restriction)
    for country in authorized:
        if _location_aliases(country) & restriction_tokens:
            return  # match found — allowed

    # No match
    raise LocationEligibilityError(
        f"Role location restriction '{restriction}' does not match profile "
        f"work-authorization: {authorized}. Use --force-location to override."
    )


def check_confirmation_pattern(
    ats_platform: str,
    final_url: str,
    page_text: str,
    registry_path: Path | None = None,
) -> str:
    """
    POST-SUBMIT: Classify the outcome after the form has been submitted.

    Returns one of: "confirmed", "ambiguous", "failed"

    "ambiguous" must halt the pipeline immediately — a retry risks double-submission.
    "failed" is a known failure pattern (e.g. "You already applied").
    "confirmed" means the ATS acknowledged receipt.

    This function is called by the apply skill after clicking Submit,
    with the actual final URL and visible page text as arguments.
    """
    if ats_platform in ("unknown", ""):
        # Cannot verify; treat as ambiguous — do not retry
        return "ambiguous"

    registry = load_confirmation_registry(registry_path)
    patterns = registry.get(ats_platform, {})

    # Check known failure patterns first
    failure_patterns = patterns.get("failure_text_contains", [])
    for pattern in failure_patterns:
        if pattern.lower() in page_text.lower():
            return "failed"

    # Check confirmation signals
    url_signal = patterns.get("url_contains", "")
    text_signals: list[str] = patterns.get("text_contains", [])

    url_match = url_signal and url_signal in final_url
    text_match = any(s.lower() in page_text.lower() for s in text_signals)

    if url_match or text_match:
        return "confirmed"

    return "ambiguous"


# ---------------------------------------------------------------------------
# Composite gate runner
# ---------------------------------------------------------------------------


def run_pre_apply_checks(
    role_id: str,
    job_url: str,
    ats_platform: str,
    output_prefix: str,
    generated_dir: Path,
    tracker_path: Path,
    registry_path: Path | None = None,
    autonomous: bool = False,
    role_config: dict | None = None,
    profile: dict | None = None,
    force_location: bool = False,
) -> None:
    """
    Run all pre-apply gates in sequence. Raises PreApplyError on first failure.

    Gates run in this order (fail-fast):
    1. Duplicate check — catches already-applied roles
    2. Artifacts exist — catches missing or corrupt PDFs
    3. Location eligibility — blocks roles with mismatched location/right-to-work
    4. Platform supported — blocks autonomous mode on unverified ATS (HITL: warning only)

    All gates must pass before browser automation starts.
    """
    check_duplicate(job_url, tracker_path)
    check_artifacts_exist(output_prefix, generated_dir)

    if role_config is not None and profile is not None:
        check_location_eligibility(role_config, profile, force_location=force_location)

    if autonomous:
        if ats_platform in ("unknown", ""):
            raise UnsupportedPlatformError(
                "Cannot run in autonomous mode: ats_platform is 'unknown'. "
                "Set a known ATS platform in the role config before enabling yolo_mode."
            )
        # In autonomous mode, unsupported platform is a hard block
        check_platform_supported(ats_platform, registry_path)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _normalise_url(url: str) -> str:
    """
    Normalise a URL for duplicate comparison.

    Strips trailing slashes and lowercases scheme + host.
    Preserves path case (some ATS URLs are case-sensitive in their job ID segment).
    """
    url = url.strip()
    # Lowercase scheme and host only
    if "://" in url:
        scheme, rest = url.split("://", 1)
        if "/" in rest:
            host, path = rest.split("/", 1)
            url = f"{scheme.lower()}://{host.lower()}/{path}"
        else:
            url = f"{scheme.lower()}://{rest.lower()}"
    return url.rstrip("/")
