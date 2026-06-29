"""
test_record_submission.py — Behavior contracts for the pre-submit audit log.

Focus: the audit log written by record_submission.py carries both
`ats_platform` and `variant`, sourced from the role config for consistency
with the tracker entry (issue #139).

The script reads its inputs from argv and resolves roles/<role_id>.json under
the current working directory, so each test runs in a chdir'd temp workspace.

Run: pytest tests/test_record_submission.py -v
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Allow imports from src/ without installation
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import record_submission  # noqa: E402


def _run(monkeypatch, workspace: Path, role_id: str, output_rel: str) -> dict:
    monkeypatch.chdir(workspace)
    out_path = workspace / output_rel
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "record_submission.py",
            role_id,
            "lever:https://jobs.lever.co/acme/abc/apply",
            "yolo-pre-authorized:abcd",
            str(out_path),
        ],
    )
    rc = record_submission.main()
    assert rc == 0
    return json.loads(out_path.read_text())


def _write_role(workspace: Path, role_id: str, **fields) -> None:
    (workspace / "roles").mkdir(exist_ok=True)
    cfg = {"role_id": role_id, "company": "Acme"}
    cfg.update(fields)
    (workspace / "roles" / f"{role_id}.json").write_text(json.dumps(cfg))


def test_audit_log_includes_ats_platform_and_variant(tmp_path, monkeypatch):
    _write_role(tmp_path, "acme_eng", ats_platform="lever", variant="C")

    log = _run(monkeypatch, tmp_path, "acme_eng", "audits/log.json")

    assert log["ats_platform"] == "lever"
    assert log["variant"] == "C"


def test_audit_log_variant_is_null_when_absent(tmp_path, monkeypatch):
    _write_role(tmp_path, "acme_eng")  # no variant

    log = _run(monkeypatch, tmp_path, "acme_eng", "audits/log.json")

    assert "variant" in log
    assert log["variant"] is None


def test_audit_log_falls_back_to_target_ats_when_no_role_config(tmp_path, monkeypatch):
    """No roles/<id>.json: ats_platform falls back to the parsed submission target."""
    log = _run(monkeypatch, tmp_path, "missing_role", "audits/log.json")

    assert log["ats_platform"] == "lever"  # from submission_target
    assert log["variant"] is None
