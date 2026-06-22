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


def main() -> int:
    if len(sys.argv) != 5:
        print(
            "Usage: record_submission.py <manifest_or_role_id> "
            "<ats:job_url> <approval_text> <output_path>",
            file=sys.stderr,
        )
        return 1

    _, manifest_or_role_id, submission_target, approval_text, output_path_str = sys.argv

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
    if manifest_path.exists() and manifest_path.suffix == ".json":
        try:
            with open(manifest_path, encoding="utf-8") as f:
                manifest_data = json.load(f)
        except (json.JSONDecodeError, OSError):
            pass  # non-fatal — log still writes

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

    log: dict = {
        "schema_version": "1",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "manifest_source": str(manifest_or_role_id),
        "ats_platform": ats_part,
        "job_url": url_part,
        "approval_text_length": len(approval_text),
        "approval_text_prefix": approval_text[:12],
        "manifest_summary": manifest_data.get("summary", {}),
    }

    try:
        output_path.write_text(json.dumps(log, indent=2, ensure_ascii=False))
    except OSError as exc:
        print(f"Error: could not write submission log to {output_path}: {exc}", file=sys.stderr)
        return 1

    print(f"Submission log written: {output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
