"""
audit.py — Per-submission audit sidecar writer for autonomous (yolo) mode.

Each autonomous submission writes a JSON sidecar to audits/<role_id>_<timestamp>.json.
This file is the authoritative post-mortem record for any submission and satisfies
the job-application-quality rubric's missing_submission_log hard-fail criterion.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SIDECAR_SCHEMA_VERSION = "1"


def write_sidecar(
    role_config: dict[str, Any],
    profile: dict[str, Any],
    outcome: str,
    gates_passed: list[str],
    gates_failed: list[str],
    attachments_verified: dict[str, bool],
    audits_dir: Path,
    *,
    confirmation_excerpt: str = "",
    matched_confirmation_pattern: str | None = None,
    jobqa_workspace_dir: str = "",
    jobqa_qa_status: str = "skipped",
    submission_log_path: str = "",
    screenshot_path: str | None = None,
) -> Path:
    """
    Write a per-submission audit sidecar to audits_dir.

    outcome: "confirmed" | "ambiguous" | "failed"
    Returns the path to the written sidecar file.
    """
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    role_id = role_config.get("role_id", "unknown")
    audits_dir.mkdir(parents=True, exist_ok=True)
    sidecar_path = audits_dir / f"{role_id}_{timestamp}_submission.json"

    email = profile.get("email", "")
    email_hash = hashlib.sha256(email.encode()).hexdigest()

    yolo = profile.get("yolo_mode", {})
    auth_key = yolo.get("authorization_key", "")
    key_prefix = auth_key[:4] if len(auth_key) >= 4 else auth_key

    sidecar: dict[str, Any] = {
        "schema_version": SIDECAR_SCHEMA_VERSION,
        "role_id": role_id,
        "company": role_config.get("company", ""),
        "job_title": role_config.get("title", ""),
        "timestamp_utc": timestamp,
        "ats_platform": role_config.get("ats_platform", "unknown"),
        "outcome": outcome,
        "confirmation_excerpt": confirmation_excerpt,
        "matched_confirmation_pattern": matched_confirmation_pattern,
        "gates_passed": gates_passed,
        "gates_failed": gates_failed,
        "attachments_verified": attachments_verified,
        "jobqa_workspace_dir": jobqa_workspace_dir,
        "jobqa_qa_status": jobqa_qa_status,
        "submission_log_path": submission_log_path,
        "screenshot_path": screenshot_path,
        "profile_email_hash": email_hash,
        "authorization_key_prefix": key_prefix,
    }

    sidecar_path.write_text(json.dumps(sidecar, indent=2, ensure_ascii=False))
    return sidecar_path
