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
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

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


class LeverCooldownError(PreApplyError):
    """Raised when a Lever submission would violate the per-company cooldown."""


# ---------------------------------------------------------------------------
# Lever per-company cooldown policy
# ---------------------------------------------------------------------------

# ASSUMPTION (NOT confirmed Lever policy): Lever's per-company cooldown is ~30 days.
# Inferred purely from observed date arithmetic on one block event
# (applied 2026-06-18, resubmit blocked 2026-06-26, human-noted retry window 2026-07-18).
# No verbatim Lever error text or policy doc confirms this number. Change in one place if real policy is observed.
LEVER_COOLDOWN_DAYS = 30

# Lever hosts that carry the company slug as the first path segment.
_LEVER_HOSTS = ("jobs.lever.co", "jobs.eu.lever.co")

# Tracker statuses that mean an application was NEVER actually submitted.
# Lever retains any sent application, so we bias toward blocking: everything
# past "draft" is treated as a real submission. A false block is recoverable
# via --override-ats-policy; a false ALLOW causes a double-submit Lever penalty.
_NOT_SUBMITTED_STATUSES = frozenset({"draft"})


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


def check_lever_cooldown(
    job_url: str,
    tracker_path: Path,
    cooldown_days: int = LEVER_COOLDOWN_DAYS,
    override_ats_policy: bool = False,
) -> None:
    """
    FAIL if a prior application to the same Lever company was submitted within
    the inferred per-company cooldown window.

    Lever-only and URL-driven. The company is identified by the slug in the
    submission URL (jobs.lever.co/<slug>/...), NOT by any `ats` field in the
    tracker (that field is not yet populated — see #139). If job_url is not a
    Lever URL, this gate is a no-op.

    Scans the tracker for prior entries whose `url` is a Lever URL with the SAME
    slug and whose status indicates the application was actually submitted at
    least once (anything past "draft"). If the most recent such submission is
    within `cooldown_days` of today, raise LeverCooldownError.

    Bias toward blocking: Lever retains any sent application, so a false block
    (recoverable via --override-ats-policy) is preferred over a false allow
    (which causes a double-submit penalty). A matching entry with no usable
    submission date is therefore blocked, citing the unknown date — but a
    never-submitted draft never blocks.

    When override_ats_policy is True, a would-be block is downgraded to a
    stderr WARNING and the gate passes.
    """
    slug = _lever_slug(job_url)
    if slug is None:
        return  # not a Lever URL — gate does not apply

    if not tracker_path.exists():
        return  # no history, safe to proceed

    with open(tracker_path, encoding="utf-8") as f:
        entries: list[dict[str, Any]] = json.load(f)

    today = date.today()

    # Collect matching prior submissions: same slug + a status past "draft".
    # Each candidate is (parsed_date_or_None, role_id, raw_date_str).
    candidates: list[tuple[date | None, str, str]] = []
    for entry in entries:
        entry_url = entry.get("url", "")
        if not entry_url:
            continue  # url-empty entries are invisible to the slug match (accepted trade-off)
        if _lever_slug(entry_url) != slug:
            continue
        status = entry.get("status", "")
        if status in _NOT_SUBMITTED_STATUSES:
            continue  # never submitted — do not block on a draft
        role_id = entry.get("role_id", "unknown")
        raw_date = _submission_date_str(entry)
        candidates.append((_parse_date(raw_date), role_id, raw_date))

    if not candidates:
        return  # no prior same-slug submission

    # If any matching entry has an unusable date, be conservative and block on it.
    undated = [c for c in candidates if c[0] is None]
    if undated:
        _, role_id, raw_date = undated[0]
        msg = (
            f"Lever enforces one application per company. A prior application to "
            f"'{slug}' ({role_id}) was submitted on an unknown/unparseable date "
            f"('{raw_date}'), so it cannot be cleared of the inferred {cooldown_days}-day "
            f"cooldown (ASSUMPTION — not confirmed Lever policy). "
            f"Re-run with --override-ats-policy to bypass."
        )
        _raise_or_warn(msg, override_ats_policy)
        return

    # Block on the most recent prior submission if it is within the window.
    most_recent_date, role_id, raw_date = max(candidates, key=lambda c: c[0])  # type: ignore[arg-type,return-value]
    days_elapsed = (today - most_recent_date).days  # type: ignore[operator]
    if days_elapsed < cooldown_days:
        msg = (
            f"Lever enforces one application per company. A prior application to "
            f"'{slug}' ({role_id}) was submitted on {raw_date} ({days_elapsed} day(s) "
            f"ago), within the inferred {cooldown_days}-day cooldown "
            f"(ASSUMPTION — not confirmed Lever policy). "
            f"Re-run with --override-ats-policy to bypass."
        )
        _raise_or_warn(msg, override_ats_policy)
        return

    # Most recent prior submission is older than the window — the inferred reopen.


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
    override_ats_policy: bool = False,
) -> None:
    """
    Run all pre-apply gates in sequence. Raises PreApplyError on first failure.

    Gates run in this order (fail-fast):
    1. Duplicate check — catches already-applied roles
    2. Artifacts exist — catches missing or corrupt PDFs
    3. Lever cooldown — blocks same-company Lever resubmit within the inferred
       30-day cooldown window (no-op for non-Lever URLs; --override-ats-policy bypasses)
    4. Platform supported — blocks autonomous mode on unverified ATS (HITL: warning only)

    All gates must pass before browser automation starts.
    """
    check_duplicate(job_url, tracker_path)
    check_artifacts_exist(output_prefix, generated_dir)
    check_lever_cooldown(job_url, tracker_path, override_ats_policy=override_ats_policy)

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


def _lever_slug(url: str) -> str | None:
    """
    Extract the Lever company slug from a submission URL, or None if not Lever.

    The slug is the first path segment after a Lever host
    (jobs.lever.co or jobs.eu.lever.co), e.g.:
        https://jobs.lever.co/acme/<uuid>            -> "acme"
        https://jobs.lever.co/acme/<uuid>/apply      -> "acme"
        https://jobs.lever.co/acme/<uuid>/?utm=x#frag -> "acme"
        https://jobs.eu.lever.co/acme/<uuid>         -> "acme"

    Query strings, fragments, trailing slashes, and a trailing "/apply"
    segment are all ignored. Returns None for any non-Lever host or a Lever
    URL with no slug segment.
    """
    if not url:
        return None
    parsed = urlparse(url.strip())
    host = parsed.netloc.lower()
    # Drop any userinfo/port that may be present.
    if "@" in host:
        host = host.rsplit("@", 1)[1]
    if ":" in host:
        host = host.split(":", 1)[0]
    if host not in _LEVER_HOSTS:
        return None
    segments = [seg for seg in parsed.path.split("/") if seg]
    if not segments:
        return None
    return segments[0]


def _submission_date_str(entry: dict[str, Any]) -> str:
    """
    Return the best-available submission date string for a tracker entry.

    Prefers `applied` (the true submission date), then falls back to
    `last_update`, then `added`. ASSUMPTION: when `applied` is null but the
    entry has a submitted status (e.g. a withdrawn entry with applied=null),
    `last_update`/`added` is a usable proxy for "when this was acted on" —
    good enough to place it inside or outside the cooldown window. Returns ""
    when no date field is usable (caller treats that as a conservative block).
    """
    for field in ("applied", "last_update", "added"):
        value = entry.get(field)
        if value:
            return str(value)
    return ""


def _parse_date(raw: str) -> date | None:
    """Parse an ISO date (YYYY-MM-DD) string; return None if missing/malformed."""
    if not raw:
        return None
    try:
        return datetime.strptime(raw.strip(), "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def _raise_or_warn(message: str, override_ats_policy: bool) -> None:
    """Raise LeverCooldownError, or downgrade to a stderr WARNING when overridden."""
    if override_ats_policy:
        print(
            f"WARNING: ATS-policy gate bypassed via --override-ats-policy. {message}",
            file=sys.stderr,
        )
        return
    raise LeverCooldownError(message)
