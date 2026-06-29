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
import sys
from pathlib import Path
from typing import Any

# ASSUMPTION (policy choice, not platform-confirmed): block after this many prior
# same-company rejections. Default 2 per issue #138; not derived from any observed
# ATS rule. Configurable — change here or via the threshold parameter.
COMPANY_REPEAT_THRESHOLD = 2

# The exact tracker status that counts as a rejection. Mirrors the "rejected"
# constant in src/tracker.py STATUSES — kept as a named constant so the gate
# never silently drifts if the tracker vocabulary changes.
REJECTED_STATUS = "rejected"

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


class CompanyRepeatError(PreApplyError):
    """Raised when prior same-company rejections meet or exceed the threshold.

    Distinct from DuplicateApplicationError: that gate matches an exact role URL
    already in the tracker. This gate matches at the *company* level and only
    counts entries whose status is "rejected" — it targets the ATS pattern where
    per-email candidate history is retained across all roles at a company.
    """


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


def check_company_repeat(
    role_config: dict[str, Any],
    tracker_path: Path,
    threshold: int = COMPANY_REPEAT_THRESHOLD,
    allow_company_repeat: bool = False,
) -> None:
    """
    FAIL if the tracker holds >= `threshold` prior "rejected" entries for the
    same (normalised) company as this role.

    Why this exists: check_duplicate() matches on exact role URL. A different role
    at the same company has a different URL and passes that gate cleanly even when
    prior applications to the company were rejected. Lever and Greenhouse retain
    per-email candidate history at the company level, so re-applying after multiple
    rejections degrades the candidate record (and Lever can hard-block submission).

    Comparison is case-insensitive and uses conservative company normalisation
    (see _normalise_company). The dangerous direction here is a FALSE BLOCK from
    over-normalising two distinct companies into one name, so normalisation is
    deliberately minimal.

    Override: pass allow_company_repeat=True to downgrade the block to a logged
    stderr warning and proceed. This is a real function parameter — the apply skill
    re-invokes the checks with allow_company_repeat=True only on explicit user
    approval. It is NOT a CLI flag.
    """
    company_raw = (role_config or {}).get("company", "")
    company = _normalise_company(company_raw)
    if not company:
        return  # no company to compare against; nothing to gate

    if not tracker_path.exists():
        return  # no history, safe to proceed

    with open(tracker_path, encoding="utf-8") as f:
        entries: list[dict[str, Any]] = json.load(f)

    rejection_count = sum(
        1
        for entry in entries
        if entry.get("status") == REJECTED_STATUS
        and _normalise_company(entry.get("company", "")) == company
    )

    if rejection_count >= threshold:
        message = (
            f"Company-repeat gate: '{company_raw}' has {rejection_count} prior "
            f"rejected application(s) in the tracker (threshold {threshold}). "
            f"Re-applying after repeated rejections degrades your candidate record "
            f"and some ATS platforms (e.g. Lever) block it. To proceed intentionally, "
            f"the apply skill must re-run the pre-apply checks with "
            f"allow_company_repeat=True after explicit user approval."
        )
        if allow_company_repeat:
            print(f"WARNING (company-repeat override): {message}", file=sys.stderr)
            return
        raise CompanyRepeatError(message)


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
    role_config: dict[str, Any] | None = None,
    allow_company_repeat: bool = False,
) -> None:
    """
    Run all pre-apply gates in sequence. Raises PreApplyError on first failure.

    Gates run in this order (fail-fast):
    1. Duplicate check — catches already-applied roles (exact URL)
    2. Company-repeat check — blocks after N prior same-company rejections
    3. Artifacts exist — catches missing or corrupt PDFs
    4. Platform supported — blocks autonomous mode on unverified ATS (HITL: warning only)

    The company-repeat gate only runs when `role_config` is supplied (it needs the
    company name). Pass `allow_company_repeat=True` to downgrade that gate's block
    to a logged warning — the apply skill does this only on explicit user approval.

    All gates must pass before browser automation starts.
    """
    check_duplicate(job_url, tracker_path)
    if role_config is not None:
        check_company_repeat(
            role_config,
            tracker_path,
            allow_company_repeat=allow_company_repeat,
        )
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


# Common legal/entity suffixes stripped during company normalisation. Kept
# deliberately SHORT and unambiguous: each token here is a recognised corporate
# suffix, never a substantive part of a real company name. (Notably we do NOT
# strip bare "Co" — e.g. "BIT Capital" is fine, but stripping "Co" would maul
# names like "Tinkoff Co" vs "Tinkoff" inconsistently, and "Co" is too easily a
# real word fragment. Only the punctuated "Co." form is removed.)
_LEGAL_SUFFIXES = [
    "ltd.",
    "ltd",
    "inc.",
    "inc",
    "llc",
    "l.l.c.",
    "gmbh",
    "corp.",
    "corp",
    "co.",
    "plc",
    "ag",
    "s.a.",
    "b.v.",
]


def _normalise_company(name: str) -> str:
    """
    Normalise a company name for case-insensitive company-level comparison.

    Steps (intentionally conservative to avoid FALSE BLOCKS):
      1. lowercase + strip surrounding whitespace
      2. strip a single trailing legal suffix (Ltd, Inc, LLC, GmbH, Corp, Co.,
         PLC, AG, S.A., B.V. and punctuated variants), comma-separated or not
      3. strip trailing commas/periods/whitespace left behind

    We strip at most ONE trailing suffix and never touch interior words, so two
    genuinely different companies do not collapse onto the same normalised form.
    """
    s = name.strip().lower()
    if not s:
        return ""

    # Drop a trailing legal suffix that is separated by a comma and/or space,
    # e.g. "acme, llc" / "acme inc." / "acme ltd". Only one pass — conservative.
    for suffix in _LEGAL_SUFFIXES:
        # match: <name><optional comma><whitespace><suffix><optional trailing punct> at end
        pattern = r"[,\s]+" + re.escape(suffix) + r"\.?$"
        new = re.sub(pattern, "", s)
        if new != s:
            s = new
            break

    # Strip any trailing punctuation/whitespace left over.
    s = s.rstrip(" ,.")
    return s


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
