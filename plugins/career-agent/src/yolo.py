"""
yolo.py — Authorization model and gate battery for autonomous (yolo) mode.

Yolo mode allows career-agent to complete and submit applications without
per-application human confirmation. It requires explicit pre-authorization
via a composite key stored in profile.json, and passes every application
through a deterministic gate battery before any Submit action.

Gate failures fall to HITL mode, not hard abort. Authorization key mismatch
always falls to HITL — never abort. All gate results are logged in the sidecar.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess  # nosec B404
from datetime import date
from pathlib import Path
from typing import Any, cast


class YoloAuthError(Exception):
    """Raised when yolo mode authorization fails — pipeline falls to HITL."""


class YoloGateError(Exception):
    """Raised when a pre-apply gate blocks autonomous submission."""

    def __init__(self, code: str, message: str = "") -> None:
        self.code = code
        super().__init__(f"{code}: {message}" if message else code)


class JobQAGateError(YoloGateError):
    """Raised when the jobqa gate fails or jobqa is not installed."""

    def __init__(self, message: str) -> None:
        super().__init__("JOBQA_GATE_FAILED", message)


# ---------------------------------------------------------------------------
# Authorization
# ---------------------------------------------------------------------------


def derive_authorization_key(email: str) -> str:
    """
    Derive the expected authorization key from the user's email.

    To generate your key:
      python -c "import hashlib; print(hashlib.sha256('career-agent-yolo:<email>'.encode()).hexdigest()[:32])"
    """
    return hashlib.sha256(f"career-agent-yolo:{email}".encode()).hexdigest()[:32]


def is_yolo_enabled(profile: dict[str, Any]) -> bool:
    """Return True only if yolo_mode is present, enabled, and the authorization key is valid."""
    yolo = profile.get("yolo_mode", {})
    if not yolo.get("enabled", False):
        return False
    stored_key = str(yolo.get("authorization_key", ""))
    expected = derive_authorization_key(str(profile.get("email", "")))
    return stored_key == expected


# ---------------------------------------------------------------------------
# Individual gates
# ---------------------------------------------------------------------------


def check_tier_permitted(role_config: dict[str, Any], permitted_tiers: list[str]) -> None:
    tier = role_config.get("application_tier", "selective")
    if tier not in permitted_tiers:
        raise YoloGateError(
            "TIER_NOT_PERMITTED",
            f"role tier '{tier}' not in permitted_tiers {permitted_tiers}",
        )


def check_company_not_excluded(role_config: dict[str, Any], excluded_companies: list[str]) -> None:
    company = role_config.get("company", "")
    excluded_lower = {c.lower() for c in excluded_companies}
    if company.lower() in excluded_lower:
        raise YoloGateError("COMPANY_EXCLUDED", company)


def check_daily_cap(tracker_path: Path, daily_cap: int) -> None:
    """Block if the number of autonomous submissions today already meets the cap."""
    if not tracker_path.exists():
        return
    with open(tracker_path, encoding="utf-8") as f:
        entries: list[dict[str, Any]] = json.load(f)
    today = str(date.today())
    autonomous_today = sum(
        1
        for e in entries
        if e.get("status") == "autonomous_submitted" and e.get("last_update", "") == today
    )
    if autonomous_today >= daily_cap:
        raise YoloGateError(
            "DAILY_CAP_REACHED",
            f"{autonomous_today} autonomous submissions today (cap: {daily_cap})",
        )


def check_cover_letter_present(role_config: dict[str, Any]) -> None:
    cl = role_config.get("cover_letter", {})
    paragraphs = cl.get("paragraphs", [])
    if not paragraphs or all(not str(p).strip() for p in paragraphs):
        raise YoloGateError(
            "COVER_LETTER_REQUIRED",
            "role config has no cover letter paragraphs",
        )


def check_cover_letter_specificity(role_config: dict[str, Any]) -> None:
    """Block on unedited template cover letters."""
    cl = role_config.get("cover_letter", {})
    paragraphs = cl.get("paragraphs", [])
    company = role_config.get("company", "")
    full_text = " ".join(str(p) for p in paragraphs).lower()

    # Must mention the company by name
    if company and company.lower() not in full_text:
        raise YoloGateError(
            "QUALITY_GATE_FAILED",
            f"cover letter does not mention company '{company}' by name",
        )

    # Must not be an unedited example template
    placeholder_markers = [
        "opening paragraph",
        "paragraph 2",
        "paragraph 3",
        "specific hook to the company",
        "concrete evidence",
        "fit with this specific jd",
        "availability, call to action",
    ]
    for marker in placeholder_markers:
        if marker in full_text:
            raise YoloGateError(
                "QUALITY_GATE_FAILED",
                f"cover letter contains placeholder text: '{marker}'",
            )


# ---------------------------------------------------------------------------
# jobqa integration (job-application-quality)
# ---------------------------------------------------------------------------


def run_jobqa_gate(workspace_dir: Path) -> dict[str, Any]:
    """
    Run jobqa on a workspace directory. Returns the parsed QA report.

    Raises JobQAGateError if jobqa exits non-zero, is not installed, or
    returns a "fail" QA status. Warnings pass through as part of the report.

    If jobqa is not in PATH, raises with a clear install message rather than
    blocking the pipeline on a missing optional dependency.
    """
    if not shutil.which("jobqa"):
        raise JobQAGateError(
            "jobqa not found in PATH — install job-application-quality: "
            "pip install git+https://github.com/nextwebb/job-application-quality.git"
        )

    result = subprocess.run(  # nosec B603 B607
        ["jobqa", "run", str(workspace_dir), "--format", "json"],
        capture_output=True,
        text=True,
        timeout=60,
    )

    if result.returncode != 0:
        try:
            err_data = json.loads(result.stdout)
            err_list = err_data.get("qa_report", {}).get("errors", [])
        except (json.JSONDecodeError, KeyError):
            err_list = []
        msg = "; ".join(str(e) for e in err_list) if err_list else (result.stderr or result.stdout)
        raise JobQAGateError(f"jobqa exited non-zero: {msg[:400]}")

    try:
        report = cast(dict[str, Any], json.loads(result.stdout))
    except json.JSONDecodeError as exc:
        raise JobQAGateError(f"jobqa returned non-JSON output: {result.stdout[:200]}") from exc

    qa = report.get("qa_report", {})
    if qa.get("status") == "fail":
        qa_errors = qa.get("errors", [])
        raise JobQAGateError(f"jobqa qa failed: {'; '.join(str(e) for e in qa_errors)}")

    return report


# ---------------------------------------------------------------------------
# Composite yolo gate battery
# ---------------------------------------------------------------------------


def run_yolo_gates(
    profile: dict[str, Any],
    role_config: dict[str, Any],
    workspace_dir: Path,
    tracker_path: Path,
) -> list[str]:
    """
    Run the full yolo pre-apply gate battery (gates 3–8 from SKILL.md).

    Gates 1–2 (duplicate check, artifact check) are handled by run_pre_apply_checks.
    Call that first with autonomous=True before calling this function.

    Returns a list of warning strings (non-blocking) from jobqa.
    Raises YoloGateError on first hard failure.
    All gate failures should fall to HITL mode, not hard abort.

    Gate order (fail-fast):
      3. Tier permitted
      4. Company not excluded
      5. Daily cap
      6. Cover letter present
      7. Cover letter specificity
      8. jobqa workspace gate (if workspace_dir exists and jobqa is installed)
    """
    yolo = profile.get("yolo_mode", {})
    permitted_tiers: list[str] = yolo.get("permitted_tiers", ["volume"])
    excluded_companies: list[str] = yolo.get("excluded_companies", [])
    daily_cap: int = int(yolo.get("daily_cap", 5))

    check_tier_permitted(role_config, permitted_tiers)
    check_company_not_excluded(role_config, excluded_companies)
    check_daily_cap(tracker_path, daily_cap)
    check_cover_letter_present(role_config)
    check_cover_letter_specificity(role_config)

    warnings: list[str] = []
    if workspace_dir.exists():
        if not shutil.which("jobqa"):
            warnings.append("jobqa not in PATH — workspace gate skipped")
        else:
            try:
                report = run_jobqa_gate(workspace_dir)
                qa = report.get("qa_report", {})
                warnings = [str(w) for w in qa.get("warnings", [])]
            except JobQAGateError:
                raise

    return warnings
