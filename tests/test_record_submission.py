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


def test_tracker_row_falls_back_to_target_ats_when_no_role_config(tmp_path, monkeypatch):
    """Tracker and audit metadata should agree when roles/<id>.json is absent."""
    output = tmp_path / "audits" / "log.json"
    tracker = tmp_path / "tracker.json"
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "record_submission.py",
            "missing_role",
            "lever:https://jobs.lever.co/acme/abc/apply",
            "yolo-pre-authorized:abcd",
            str(output),
            str(tracker),
        ],
    )

    rc = record_submission.main()

    assert rc == 0
    entry = json.loads(tracker.read_text())[0]
    assert entry["ats_platform"] == "lever"
    assert entry["variant"] is None


def test_existing_role_id_writes_metadata_to_provisional_tracker_row(tmp_path, monkeypatch):
    _write_role(
        tmp_path,
        "acme_eng",
        company="Acme Corp",
        title="Backend Engineer",
        url="https://jobs.lever.co/acme/abc/apply",
        ats_platform="lever",
        variant="C",
    )
    output = tmp_path / "audits" / "log.json"
    tracker = tmp_path / "tracker.json"
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "record_submission.py",
            "acme_eng",
            "lever:https://jobs.lever.co/acme/abc/apply",
            "yolo-pre-authorized:abcd",
            str(output),
            str(tracker),
        ],
    )

    rc = record_submission.main()

    assert rc == 0
    entry = json.loads(tracker.read_text())[0]
    assert entry["role_id"] == "acme_eng"
    assert entry["company"] == "Acme Corp"
    assert entry["title"] == "Backend Engineer"
    assert entry["url"] == "https://jobs.lever.co/acme/abc/apply"
    assert entry["ats_platform"] == "lever"
    assert entry["variant"] == "C"


def test_manifest_nested_role_id_resolves_role_config_for_tracker_row(tmp_path, monkeypatch):
    _write_role(
        tmp_path,
        "nested_role",
        company="Nested Co",
        title="Platform Engineer",
        ats_platform="greenhouse",
        variant="A",
    )
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"role": {"role_id": "nested_role"}, "summary": {}}))
    output = tmp_path / "audits" / "log.json"
    tracker = tmp_path / "tracker.json"
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "record_submission.py",
            str(manifest),
            "greenhouse:https://job-boards.greenhouse.io/nested/jobs/123",
            "yolo-pre-authorized:abcd",
            str(output),
            str(tracker),
        ],
    )

    rc = record_submission.main()

    assert rc == 0
    entry = json.loads(tracker.read_text())[0]
    assert entry["role_id"] == "nested_role"
    assert entry["company"] == "Nested Co"
    assert entry["title"] == "Platform Engineer"
    assert entry["ats_platform"] == "greenhouse"
    assert entry["variant"] == "A"
