"""
test_tracker.py — Behavior contracts for the tracker write path (Step F).

Focus: propagation of `ats_platform` and `variant` from the role config into
the tracker entry created at submission time (issue #139), plus backward
compatibility for entries written before those fields existed.

These tests exercise the public `tracker.add()` / `tracker.update_status()`
interface against a temp workspace, patching the module-level path constants
so no real workspace files are touched.

Run: pytest tests/test_tracker.py -v
"""

from __future__ import annotations

import json
import sys
from datetime import date, timedelta
from pathlib import Path

import pytest

# Allow imports from src/ without installation
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import tracker  # noqa: E402

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A temp workspace with a roles/ dir, wired into tracker's path globals."""
    roles_dir = tmp_path / "roles"
    roles_dir.mkdir()
    tracker_path = tmp_path / "tracker.json"
    monkeypatch.setattr(tracker, "WORKSPACE_DIR", tmp_path)
    monkeypatch.setattr(tracker, "TRACKER_PATH", tracker_path)
    monkeypatch.setattr(tracker, "ROLES_DIR", roles_dir)
    return tmp_path


def _write_role(workspace: Path, role_id: str, **fields) -> None:
    cfg = {"role_id": role_id, "company": "Acme", "title": "Engineer", "url": "https://x/y"}
    cfg.update(fields)
    (workspace / "roles" / f"{role_id}.json").write_text(json.dumps(cfg))


def _entry(workspace: Path, role_id: str) -> dict:
    entries = json.loads((workspace / "tracker.json").read_text())
    return next(e for e in entries if e["role_id"] == role_id)


# ---------------------------------------------------------------------------
# Field propagation
# ---------------------------------------------------------------------------


class TestAtsPlatformAndVariantPropagation:
    def test_entry_carries_ats_platform_and_variant_from_role_config(self, workspace: Path):
        """A role config with both fields produces an entry with those exact values."""
        _write_role(workspace, "stripe_backend", ats_platform="lever", variant="C")

        tracker.add("stripe_backend")

        entry = _entry(workspace, "stripe_backend")
        assert entry["ats_platform"] == "lever"
        assert entry["variant"] == "C"

    def test_missing_fields_are_written_as_null_not_absent(self, workspace: Path):
        """A role config lacking the fields still yields present, null-valued fields."""
        _write_role(workspace, "acme_eng")  # no ats_platform / variant

        tracker.add("acme_eng")

        entry = _entry(workspace, "acme_eng")
        assert "ats_platform" in entry
        assert "variant" in entry
        assert entry["ats_platform"] is None
        assert entry["variant"] is None

    def test_unknown_ats_platform_is_preserved_verbatim(self, workspace: Path):
        """`unknown` is a real config value, not a synonym for null."""
        _write_role(workspace, "bit_capital", ats_platform="unknown", variant="B")

        tracker.add("bit_capital")

        entry = _entry(workspace, "bit_capital")
        assert entry["ats_platform"] == "unknown"
        assert entry["variant"] == "B"


# ---------------------------------------------------------------------------
# Backward compatibility
# ---------------------------------------------------------------------------


class TestBackwardCompatibility:
    def test_unrelated_operation_does_not_backfill_legacy_entry(self, workspace: Path):
        """An existing entry without the fields is not mutated by --note/--update."""
        legacy = {
            "role_id": "legacy_role",
            "company": "Old Co",
            "title": "Engineer",
            "url": "https://old/role",
            "status": "applied",
            "added": "2026-01-01",
            "applied": "2026-01-01",
            "last_update": "2026-01-01",
            "notes": [],
        }
        (workspace / "tracker.json").write_text(json.dumps([legacy]))

        tracker.add_note("legacy_role", "Recruiter called")
        tracker.update_status("legacy_role", "interview")

        entry = _entry(workspace, "legacy_role")
        # Fields were never present and must not be introduced by unrelated ops.
        assert "ats_platform" not in entry
        assert "variant" not in entry


# ---------------------------------------------------------------------------
# Refresh at submission transition
# ---------------------------------------------------------------------------


class TestSubmissionTransitionRefresh:
    def test_legacy_draft_gains_fields_when_marked_applied(self, workspace: Path):
        """A pre-#139 draft with no fields gets them from the role config on apply."""
        legacy_draft = {
            "role_id": "legacy_role",
            "company": "Old Co",
            "title": "Engineer",
            "url": "https://old/role",
            "status": "draft",
            "added": "2026-01-01",
            "applied": None,
            "last_update": "2026-01-01",
            "notes": [],
        }
        (workspace / "tracker.json").write_text(json.dumps([legacy_draft]))
        _write_role(workspace, "legacy_role", ats_platform="lever", variant="B")

        tracker.update_status("legacy_role", "applied")

        entry = _entry(workspace, "legacy_role")
        assert entry["status"] == "applied"
        assert entry["ats_platform"] == "lever"
        assert entry["variant"] == "B"

    def test_edited_role_config_overrides_stale_add_time_metadata(self, workspace: Path):
        """If roles/<id>.json is edited after --add, the submission row reflects the NEW values."""
        _write_role(workspace, "moved_role", ats_platform="greenhouse", variant="A")
        tracker.add("moved_role")

        # Role JSON edited before applying: ATS re-detected, CV variant changed.
        _write_role(workspace, "moved_role", ats_platform="lever", variant="B")

        tracker.update_status("moved_role", "autonomous_submitted")

        entry = _entry(workspace, "moved_role")
        assert entry["ats_platform"] == "lever"  # not stale greenhouse
        assert entry["variant"] == "B"  # not stale A

    def test_missing_role_file_does_not_crash_or_null_existing_fields(self, workspace: Path):
        """No roles/<id>.json at transition time: no crash, existing values preserved."""
        existing = {
            "role_id": "orphan_role",
            "company": "Acme",
            "title": "Engineer",
            "url": "https://x/y",
            "ats_platform": "workable",
            "variant": "C",
            "status": "draft",
            "added": "2026-01-01",
            "applied": None,
            "last_update": "2026-01-01",
            "notes": [],
        }
        (workspace / "tracker.json").write_text(json.dumps([existing]))
        # Note: no roles/orphan_role.json written.

        tracker.update_status("orphan_role", "applied")  # must not raise

        entry = _entry(workspace, "orphan_role")
        assert entry["status"] == "applied"
        assert entry["ats_platform"] == "workable"  # unchanged, not nulled
        assert entry["variant"] == "C"

    def test_role_config_missing_one_field_does_not_null_existing_value(self, workspace: Path):
        """A role config that lost a field must not clobber a previously-set tracker value."""
        existing = {
            "role_id": "partial_role",
            "company": "Acme",
            "title": "Engineer",
            "url": "https://x/y",
            "ats_platform": "lever",
            "variant": "B",
            "status": "draft",
            "added": "2026-01-01",
            "applied": None,
            "last_update": "2026-01-01",
            "notes": [],
        }
        (workspace / "tracker.json").write_text(json.dumps([existing]))
        # Role config now only carries ats_platform; variant dropped.
        _write_role(workspace, "partial_role", ats_platform="greenhouse")

        tracker.update_status("partial_role", "applied")

        entry = _entry(workspace, "partial_role")
        assert entry["ats_platform"] == "greenhouse"  # refreshed
        assert entry["variant"] == "B"  # preserved, not nulled

    def test_non_submission_status_does_not_refresh(self, workspace: Path):
        """Transitioning to rejected/interview must not re-capture role-config metadata."""
        _write_role(workspace, "rej_role", ats_platform="greenhouse", variant="A")
        tracker.add("rej_role")
        # Role JSON edited after add; a non-submission transition must NOT pick it up.
        _write_role(workspace, "rej_role", ats_platform="lever", variant="B")

        tracker.update_status("rej_role", "rejected")

        entry = _entry(workspace, "rej_role")
        # Value stays as captured at add() time — the submission event owns the value.
        assert entry["ats_platform"] == "greenhouse"
        assert entry["variant"] == "A"


# ---------------------------------------------------------------------------
# Ghost detection
# ---------------------------------------------------------------------------


def _make_entry(role_id: str, status: str, last_update: date, **kwargs) -> dict:
    """Build a minimal tracker entry dict."""
    return {
        "role_id": role_id,
        "company": "Acme",
        "title": "Engineer",
        "url": "https://x/y",
        "status": status,
        "added": str(last_update),
        "applied": str(last_update) if status != "draft" else None,
        "last_update": str(last_update),
        "notes": [],
        **kwargs,
    }


class TestGhostDetection:
    def test_applied_8_days_ago_appears_in_ghost_filter_and_has_annotation(
        self, workspace: Path, capsys: pytest.CaptureFixture
    ):
        """Applied entry with last_update 8 days ago shows in --ghost and has the annotation."""
        stale_date = date.today() - timedelta(days=8)
        entries = [_make_entry("old_apply", "applied", stale_date)]
        (workspace / "tracker.json").write_text(json.dumps(entries))

        tracker.list_entries(ghost_only=True)

        captured = capsys.readouterr()
        assert "old_apply" in captured.out
        assert "⚠ ghost risk (8d)" in captured.out

    def test_applied_3_days_ago_does_not_appear_in_ghost_filter(
        self, workspace: Path, capsys: pytest.CaptureFixture
    ):
        """Applied entry with last_update 3 days ago is below threshold, excluded from --ghost."""
        recent_date = date.today() - timedelta(days=3)
        entries = [_make_entry("new_apply", "applied", recent_date)]
        (workspace / "tracker.json").write_text(json.dumps(entries))

        tracker.list_entries(ghost_only=True)

        captured = capsys.readouterr()
        # No entries shown — the "No applications tracked" message should NOT appear
        # (entries exist), but the role should not be printed.
        assert "new_apply" not in captured.out
        assert "⚠ ghost risk" not in captured.out

    def test_rejected_30_days_ago_does_not_appear_in_ghost_filter(
        self, workspace: Path, capsys: pytest.CaptureFixture
    ):
        """Rejected entry, even very stale, is excluded from --ghost (applied-only check)."""
        old_date = date.today() - timedelta(days=30)
        entries = [_make_entry("old_rejection", "rejected", old_date)]
        (workspace / "tracker.json").write_text(json.dumps(entries))

        tracker.list_entries(ghost_only=True)

        captured = capsys.readouterr()
        assert "old_rejection" not in captured.out
        assert "⚠ ghost risk" not in captured.out

    def test_list_without_ghost_shows_all_entries_including_ghost_risk(
        self, workspace: Path, capsys: pytest.CaptureFixture
    ):
        """--list without --ghost shows all entries, ghost-risk ones get the annotation."""
        stale_date = date.today() - timedelta(days=10)
        recent_date = date.today() - timedelta(days=2)
        entries = [
            _make_entry("stale_apply", "applied", stale_date),
            _make_entry("fresh_apply", "applied", recent_date),
        ]
        (workspace / "tracker.json").write_text(json.dumps(entries))

        tracker.list_entries()

        captured = capsys.readouterr()
        assert "stale_apply" in captured.out
        assert "fresh_apply" in captured.out
        assert "⚠ ghost risk (10d)" in captured.out
        # The fresh entry must NOT have a ghost annotation
        lines = captured.out.splitlines()
        for line in lines:
            if "fresh_apply" in line:
                assert "⚠ ghost risk" not in line
