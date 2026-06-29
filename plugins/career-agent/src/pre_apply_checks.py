"""
pre_apply_checks.py — Blocking gates that run before any apply attempt.

These gates catch failure modes that are invisible to artifact quality checks:
duplicate applications, missing PDFs, unsupported ATS platforms, Lever
per-company cooldown violations, and unknown confirmation patterns. All gates
must pass before browser automation starts.

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
from datetime import date, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

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
# via the override_ats_policy=True parameter; a false ALLOW causes a
# double-submit Lever penalty.
_NOT_SUBMITTED_STATUSES = frozenset({"draft"})

# How to bypass the gate. NOTE: this is NOT a CLI flag — run_pre_apply_checks is
# invoked by the apply skill agent, not via argparse. The override is the
# override_ats_policy=True parameter, which the apply skill passes only with
# explicit user approval (see the apply skill's ATS-policy override step).
_OVERRIDE_HINT = (
    "To bypass (only with explicit user approval), re-run the pre-apply checks "
    "with override_ats_policy=True (see the apply skill's ATS-policy override step)."
)


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
            if status in ("failed", "autonomous_failed"):
                continue  # known failure — allow retry
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

    # Count distinct rejected APPLICATIONS, not rows. A corrupt/hand-edited tracker
    # can carry duplicate rows for the same application; counting rows would inflate
    # the total past the threshold and FALSE-BLOCK. Dedupe by a stable per-application
    # key — role_id if present, else url. Two genuinely different roles at the same
    # company have distinct keys and still count as 2 (the intended cross-role signal);
    # only literal duplicate rows collapse to 1. Rows with no usable key fall back to
    # their identity so they are not silently merged together.
    rejected_keys: set[Any] = set()
    for entry in entries:
        if entry.get("status") != REJECTED_STATUS:
            continue
        if _normalise_company(entry.get("company", "")) != company:
            continue
        key = entry.get("role_id") or entry.get("url") or id(entry)
        rejected_keys.add(key)

    rejection_count = len(rejected_keys)

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
    (recoverable via override_ats_policy=True) is preferred over a false allow
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
        status = str(entry.get("status", "")).strip().lower()
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
            f"{_OVERRIDE_HINT}"
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
            f"{_OVERRIDE_HINT}"
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
    role_config: dict[str, Any] | None = None,
    allow_company_repeat: bool = False,
) -> None:
    """
    Run all pre-apply gates in sequence. Raises PreApplyError on first failure.

    Gates run in this order (fail-fast):
    1. Duplicate check — catches already-applied roles (exact URL)
    2. Company-repeat check — blocks after N prior same-company rejections
    3. Lever cooldown — blocks same-company Lever resubmit within the inferred
       30-day cooldown window (no-op for non-Lever URLs; pass
       override_ats_policy=True to downgrade a block to a logged warning)
    4. Artifacts exist — catches missing or corrupt PDFs
    5. Platform supported — blocks autonomous mode on unverified ATS (HITL: warning only)

    The company-repeat gate only runs when `role_config` is supplied (it needs the
    company name). Pass `allow_company_repeat=True` to downgrade that gate's block
    to a logged warning — the apply skill does this only on explicit user approval.
    """
    check_duplicate(job_url, tracker_path)
    if role_config is not None:
        check_company_repeat(
            role_config,
            tracker_path,
            allow_company_repeat=allow_company_repeat,
        )
    check_lever_cooldown(job_url, tracker_path, override_ats_policy=override_ats_policy)
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


def _normalise_company(name: str | None) -> str:
    """
    Normalise a company name for case-insensitive company-level comparison.

    Steps (intentionally conservative to avoid FALSE BLOCKS):
      1. coerce None/missing to "" (an explicit "company": null in a role JSON or
         a tracker row would otherwise crash .strip() and abort the whole
         pre-apply run — a false block on a legitimate application)
      2. lowercase + strip surrounding whitespace
      3. strip a single trailing legal suffix (Ltd, Inc, LLC, GmbH, Corp, Co.,
         PLC, AG, S.A., B.V. and punctuated variants), comma-separated or not
      4. strip trailing commas/periods/whitespace left behind

    We strip at most ONE trailing suffix and never touch interior words, so two
    genuinely different companies do not collapse onto the same normalised form.
    """
    s = (name or "").strip().lower()
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


def _lever_slug(url: str) -> str | None:
    """
    Extract the Lever company slug from a submission URL, or None if not Lever.

    The slug is the first path segment after a Lever host
    (jobs.lever.co or jobs.eu.lever.co, plus any subdomain prefix such as
    www.), e.g.:
        https://jobs.lever.co/acme/<uuid>            -> "acme"
        https://jobs.lever.co/acme/<uuid>/apply      -> "acme"
        https://jobs.lever.co/acme/<uuid>/?utm=x#frag -> "acme"
        https://jobs.eu.lever.co/acme/<uuid>         -> "acme"
        https://www.jobs.lever.co/Acme/<uuid>        -> "acme"

    Query strings, fragments, trailing slashes, and a trailing "/apply"
    segment are all ignored. Host and slug are lowercased so casing never
    defeats a match. Returns None for any non-Lever host or a Lever URL with
    no slug segment.
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
    # Accept the Lever host exactly, or any subdomain prefix of it (e.g. a
    # leading "www."), so www.jobs.lever.co normalises to the same company.
    if not any(host == h or host.endswith("." + h) for h in _LEVER_HOSTS):
        return None
    segments = [seg for seg in parsed.path.split("/") if seg]
    if not segments:
        return None
    # Lowercase the slug: Lever slugs are case-insensitive company identifiers,
    # and historic tracker URLs preserve the original casing (e.g. "Fliff").
    # Both sides go through this function, so lowercasing here matches them.
    return segments[0].lower()


def _submission_date_str(entry: dict[str, Any]) -> str:
    """
    Return the best-available submission date string for a tracker entry.

    Prefers `applied` (the true submission date), then falls back to
    `last_update`. Both are >= the true submission date, so using them to
    decide whether the cooldown has elapsed biases toward blocking (safe).

    `added` is deliberately NOT in this chain: a draft can be added weeks
    before it is submitted, so `added` can be far older than the real
    submission and would wrongly CLEAR the cooldown (a false-allow →
    double-submit). When a submitted entry has neither `applied` nor
    `last_update`, this returns "" and the caller blocks it as undated.
    """
    for field in ("applied", "last_update"):
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
            f"WARNING: ATS-policy gate bypassed via override_ats_policy=True "
            f"(explicit user approval required). {message}",
            file=sys.stderr,
        )
        return
    raise LeverCooldownError(message)
