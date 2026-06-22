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
) -> None:
    """
    Run all pre-apply gates in sequence. Raises PreApplyError on first failure.

    Gates run in this order (fail-fast):
    1. Duplicate check — catches already-applied roles
    2. Artifacts exist — catches missing or corrupt PDFs
    3. Platform supported — blocks autonomous mode on unverified ATS (HITL: warning only)

    All gates must pass before browser automation starts.
    """
    check_duplicate(job_url, tracker_path)
    check_artifacts_exist(output_prefix, generated_dir)

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
