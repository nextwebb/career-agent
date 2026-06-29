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
