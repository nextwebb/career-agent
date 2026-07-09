#!/usr/bin/env python3
"""
record_submission.py — Write a pre-submit submission log for audit trail.

Called by the apply skill (yolo mode Step D) immediately before clicking Submit.
Satisfies the job-application-quality rubric hard-fails:
  missing_submission_log — a log file is written
  sends_without_approval — approval_text must be present and >= 8 chars

Usage:
    python src/record_submission.py \\
        <manifest_or_role_id> \\
        <ats_platform>:<job_url> \\
        <approval_text> \\
        <output_path>

Arguments:
    manifest_or_role_id  Path to a jobqa manifest JSON, or the role_id string
                         (used for identification in the log)
    submission_target    "<ats_platform>:<job_url>"
    approval_text        Pre-authorization token (must be >= 8 chars)
    output_path          Where to write the submission log JSON

Exit codes:
    0  Log written successfully
    1  approval_text too short, or output path not writable
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import tracker as tracker_module


def _extract_role_id(manifest_data: dict) -> str:
    """Pull the role_id out of a jobqa manifest.

    The manifest may expose role_id at the top level or nested under a
    "role" / "role_intake" object (the jobqa workspace role.json uses "role_id").
    Returns "" if no role_id is found.
    """
    if not isinstance(manifest_data, dict):
        return ""
    role_id = manifest_data.get("role_id")
    if isinstance(role_id, str) and role_id:
        return role_id
    for key in ("role", "role_intake"):
        nested = manifest_data.get(key)
        if isinstance(nested, dict):
            nested_id = nested.get("role_id")
            if isinstance(nested_id, str) and nested_id:
                return nested_id
    return ""


def _load_role_config(manifest_or_role_id: str, manifest_data: dict) -> dict:
    """
    Best-effort resolution of the role config for audit-log enrichment.

    The first CLI arg may be a manifest path or a bare role_id. We derive a
    role_id (from the manifest, or by treating the arg as the id) and look for
    roles/<role_id>.json under the current workspace. Never raises — a missing
    or unreadable config just yields {} so the audit log still writes.
    """
    role_id = _extract_role_id(manifest_data)
    if not role_id:
        candidate = Path(manifest_or_role_id)
        # A bare role_id arg has no .json suffix and is not an existing path.
        if candidate.suffix != ".json" and not candidate.exists():
            role_id = manifest_or_role_id
    if not role_id:
        return {}

    role_path = Path.cwd() / "roles" / f"{role_id}.json"
    if not role_path.exists():
        return {}
    try:
        with open(role_path, encoding="utf-8") as f:
            cfg = json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}
    return cfg if isinstance(cfg, dict) else {}


def main() -> int:
    if len(sys.argv) not in (5, 6):
        print(
            "Usage: record_submission.py <manifest_or_role_id> "
            "<ats:job_url> <approval_text> <output_path> [tracker_path]",
            file=sys.stderr,
        )
        return 1

    args = sys.argv[1:]
    manifest_or_role_id = args[0]
    submission_target = args[1]
    approval_text = args[2]
    output_path_str = args[3]
    tracker_path_str = args[4] if len(args) == 5 else None

    if len(approval_text) < 8:
        print(
            f"Error: approval_text must be >= 8 characters, got {len(approval_text)}",
            file=sys.stderr,
        )
        return 1

    output_path = Path(output_path_str)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Parse manifest if it's a file path; otherwise treat as role_id string
    manifest_data: dict = {}
    manifest_path = Path(manifest_or_role_id)
    parsed_from_manifest = False
    if manifest_path.exists() and manifest_path.suffix == ".json":
        try:
            with open(manifest_path, encoding="utf-8") as f:
                manifest_data = json.load(f)
            parsed_from_manifest = True
        except (json.JSONDecodeError, OSError):
            pass  # non-fatal — log still writes

    # Derive the REAL role_id so post-submit update_status(role_id, ...) can
    # transition the provisional submitted_unconfirmed row. When the first arg is
    # a manifest PATH, the role_id lives inside the manifest JSON (the jobqa
    # workspace stores it as "role_id", possibly nested under "role"/"role_intake");
    # using the path itself would orphan the provisional row forever (issue #135).
    if parsed_from_manifest:
        role_id = _extract_role_id(manifest_data) or str(manifest_or_role_id)
    else:
        role_id = str(manifest_or_role_id)

    # Resolve the role config so the audit log carries the same
    # ats_platform / variant fields the tracker entry gets (issue #139).
    # The first CLI arg is either a manifest path or a bare role_id; in both
    # cases we try to locate roles/<role_id>.json relative to the workspace.
    role_config = _load_role_config(manifest_or_role_id, manifest_data)

    # Parse submission_target "<ats_platform>:<job_url>"
    if ":" in submission_target:
        ats_part, _, url_part = submission_target.partition(":")
        # handle https:// — re-attach the protocol prefix
        if url_part.startswith("/"):
            url_part = ats_part + ":" + url_part
            ats_part = "unknown"
    else:
        ats_part = "unknown"
        url_part = submission_target

    # Prefer the role config's ats_platform for the analysis field; fall back
    # to the value parsed from the submission target. variant is role-config
    # only. Both are written unconditionally (None/JSON null when absent) so
    # the audit log stays queryable for outcome analysis (issue #139).
    ats_platform = role_config.get("ats_platform") if role_config.get("ats_platform") else ats_part
    variant = role_config.get("variant")

    log: dict = {
        "schema_version": "1",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "manifest_source": str(manifest_or_role_id),
        "ats_platform": ats_platform,
        "variant": variant,
        "job_url": url_part,
        "approval_text_length": len(approval_text),
        "approval_text_prefix": approval_text[:12],
        "manifest_summary": manifest_data.get("summary", {}),
    }

    # Write the fallible audit log FIRST. If this fails the apply flow aborts
    # before Submit, so we must NOT have written the provisional tracker row yet —
    # otherwise a never-submitted application would leave a submitted_unconfirmed
    # row that check_duplicate blocks on the next legitimate retry (false block).
    try:
        output_path.write_text(json.dumps(log, indent=2, ensure_ascii=False))
    except OSError as exc:
        print(f"Error: could not write submission log to {output_path}: {exc}", file=sys.stderr)
        return 1

    # Audit log is safely on disk. Now write the provisional tracker entry as the
    # LAST thing before returning success. record_submission.py runs before the
    # skill clicks Submit, so this still lands inside the crash window #135 guards:
    # a crash between Submit and the post-submit tracker update stays visible to
    # duplicate detection on the next run.
    if tracker_path_str is not None:
        tracker_module.mark_submitted_unconfirmed(
            role_id=role_id,
            job_url=url_part,
            company=role_config.get("company", ""),
            title=role_config.get("title", ""),
            ats_platform=ats_platform,
            variant=role_config.get("variant"),
            tracker_path=Path(tracker_path_str),
        )

    print(f"Submission log written: {output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
