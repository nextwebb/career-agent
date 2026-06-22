"""
test_yolo.py — Tests for yolo mode authorization model and gate battery.

Tests cover:
  - Authorization key derivation and verification
  - is_yolo_enabled returns False on missing/disabled/wrong-key profiles
  - Individual gates raise the right error codes
  - run_yolo_gates fail-fast order

What we do NOT test:
  - jobqa subprocess integration (requires jobqa installed; mocked instead)
  - Browser automation steps (covered by integration tests)

Run: pytest tests/test_yolo.py -v
"""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from yolo import (
    JobQAGateError,
    YoloGateError,
    check_company_not_excluded,
    check_cover_letter_present,
    check_cover_letter_specificity,
    check_daily_cap,
    check_tier_permitted,
    derive_authorization_key,
    is_yolo_enabled,
    run_yolo_gates,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

EMAIL = "jane@example.com"


def _make_profile(
    enabled: bool = True,
    key: str | None = None,
    permitted_tiers: list[str] | None = None,
    excluded_companies: list[str] | None = None,
    daily_cap: int = 10,
) -> dict:
    real_key = derive_authorization_key(EMAIL)
    return {
        "email": EMAIL,
        "name": {"first": "Jane", "last": "Doe"},
        "yolo_mode": {
            "enabled": enabled,
            "authorization_key": key if key is not None else real_key,
            "permitted_tiers": permitted_tiers or ["volume"],
            "excluded_companies": excluded_companies or [],
            "daily_cap": daily_cap,
        },
    }


def _make_role(
    tier: str = "volume",
    company: str = "Acme Corp",
    cover_letter_paragraphs: list[str] | None = None,
) -> dict:
    if cover_letter_paragraphs is None:
        cover_letter_paragraphs = [
            f"I am excited to apply to {company}.",
            "My experience in backend engineering spans 7 years.",
            "I am confident I can contribute significantly.",
        ]
    return {
        "role_id": "test_role",
        "company": company,
        "title": "Senior Engineer",
        "url": "https://jobs.example.com/123",
        "ats_platform": "lever",
        "variant": "A",
        "output_prefix": "Test_SeniorEngineer",
        "application_tier": tier,
        "cover_letter": {"paragraphs": cover_letter_paragraphs},
    }


@pytest.fixture
def empty_tracker(tmp_path: Path) -> Path:
    t = tmp_path / "tracker.json"
    t.write_text("[]")
    return t


@pytest.fixture
def tracker_with_cap_reached(tmp_path: Path) -> Path:
    t = tmp_path / "tracker.json"
    entries = [
        {
            "role_id": f"role_{i}",
            "status": "autonomous_submitted",
            "last_update": str(date.today()),
        }
        for i in range(3)
    ]
    t.write_text(json.dumps(entries))
    return t


# ---------------------------------------------------------------------------
# Authorization model
# ---------------------------------------------------------------------------


class TestAuthorizationKey:
    def test_derive_key_is_deterministic(self):
        k1 = derive_authorization_key(EMAIL)
        k2 = derive_authorization_key(EMAIL)
        assert k1 == k2

    def test_derive_key_is_32_chars(self):
        key = derive_authorization_key(EMAIL)
        assert len(key) == 32

    def test_derive_key_differs_for_different_emails(self):
        k1 = derive_authorization_key("alice@example.com")
        k2 = derive_authorization_key("bob@example.com")
        assert k1 != k2

    def test_is_yolo_enabled_true_when_key_matches(self):
        profile = _make_profile(enabled=True)
        assert is_yolo_enabled(profile) is True

    def test_is_yolo_enabled_false_when_disabled(self):
        profile = _make_profile(enabled=False)
        assert is_yolo_enabled(profile) is False

    def test_is_yolo_enabled_false_when_key_wrong(self):
        profile = _make_profile(key="wrong-key-" + "x" * 22)
        assert is_yolo_enabled(profile) is False

    def test_is_yolo_enabled_false_when_yolo_mode_absent(self):
        profile = {"email": EMAIL, "name": {"first": "Jane", "last": "Doe"}}
        assert is_yolo_enabled(profile) is False

    def test_is_yolo_enabled_false_when_key_is_empty_string(self):
        profile = _make_profile(key="")
        assert is_yolo_enabled(profile) is False


# ---------------------------------------------------------------------------
# Tier gate
# ---------------------------------------------------------------------------


class TestTierGate:
    def test_permits_volume_tier(self):
        role = _make_role(tier="volume")
        check_tier_permitted(role, ["volume"])  # must not raise

    def test_blocks_selective_when_only_volume_permitted(self):
        role = _make_role(tier="selective")
        with pytest.raises(YoloGateError) as exc:
            check_tier_permitted(role, ["volume"])
        assert exc.value.code == "TIER_NOT_PERMITTED"

    def test_permits_selective_when_in_list(self):
        role = _make_role(tier="selective")
        check_tier_permitted(role, ["volume", "selective"])  # must not raise

    def test_defaults_to_selective_when_tier_absent(self):
        role = {**_make_role(), "application_tier": None}
        role.pop("application_tier", None)
        with pytest.raises(YoloGateError) as exc:
            check_tier_permitted(role, ["volume"])
        assert exc.value.code == "TIER_NOT_PERMITTED"


# ---------------------------------------------------------------------------
# Company exclusion gate
# ---------------------------------------------------------------------------


class TestCompanyExclusionGate:
    def test_permits_non_excluded_company(self):
        role = _make_role(company="Acme Corp")
        check_company_not_excluded(role, ["Evil Corp"])  # must not raise

    def test_blocks_excluded_company(self):
        role = _make_role(company="Evil Corp")
        with pytest.raises(YoloGateError) as exc:
            check_company_not_excluded(role, ["Evil Corp"])
        assert exc.value.code == "COMPANY_EXCLUDED"

    def test_exclusion_is_case_insensitive(self):
        role = _make_role(company="Evil Corp")
        with pytest.raises(YoloGateError):
            check_company_not_excluded(role, ["evil corp"])

    def test_empty_excluded_list_permits_all(self):
        role = _make_role(company="Any Company")
        check_company_not_excluded(role, [])  # must not raise


# ---------------------------------------------------------------------------
# Daily cap gate
# ---------------------------------------------------------------------------


class TestDailyCap:
    def test_allows_when_under_cap(self, empty_tracker: Path):
        check_daily_cap(empty_tracker, daily_cap=5)  # must not raise

    def test_blocks_when_cap_reached(self, tracker_with_cap_reached: Path):
        with pytest.raises(YoloGateError) as exc:
            check_daily_cap(tracker_with_cap_reached, daily_cap=3)
        assert exc.value.code == "DAILY_CAP_REACHED"

    def test_allows_when_no_tracker_file(self, tmp_path: Path):
        check_daily_cap(tmp_path / "tracker.json", daily_cap=1)  # must not raise

    def test_does_not_count_manual_applied_status(self, tmp_path: Path):
        t = tmp_path / "tracker.json"
        t.write_text(
            json.dumps([{"role_id": "x", "status": "applied", "last_update": str(date.today())}])
        )
        check_daily_cap(t, daily_cap=1)  # must not raise — "applied" is not autonomous


# ---------------------------------------------------------------------------
# Cover letter gates
# ---------------------------------------------------------------------------


class TestCoverLetterGates:
    def test_permits_non_empty_cover_letter(self):
        role = _make_role()
        check_cover_letter_present(role)  # must not raise

    def test_blocks_when_no_paragraphs(self):
        role = {**_make_role(), "cover_letter": {"paragraphs": []}}
        with pytest.raises(YoloGateError) as exc:
            check_cover_letter_present(role)
        assert exc.value.code == "COVER_LETTER_REQUIRED"

    def test_blocks_when_cover_letter_absent(self):
        role = _make_role()
        role.pop("cover_letter", None)
        with pytest.raises(YoloGateError) as exc:
            check_cover_letter_present(role)
        assert exc.value.code == "COVER_LETTER_REQUIRED"

    def test_specificity_passes_when_company_named(self):
        role = _make_role(company="Acme Corp")
        check_cover_letter_specificity(role)  # must not raise

    def test_specificity_blocks_when_company_not_mentioned(self):
        role = _make_role(
            company="Acme Corp",
            cover_letter_paragraphs=[
                "I am excited to apply to this company.",
                "My experience is strong.",
            ],
        )
        with pytest.raises(YoloGateError) as exc:
            check_cover_letter_specificity(role)
        assert exc.value.code == "QUALITY_GATE_FAILED"

    def test_specificity_blocks_on_placeholder_text(self):
        role = _make_role(
            company="Acme Corp",
            cover_letter_paragraphs=[
                "Opening paragraph — specific hook to the company/role...",
                "Paragraph 2 — relevant experience, concrete evidence...",
            ],
        )
        with pytest.raises(YoloGateError) as exc:
            check_cover_letter_specificity(role)
        assert exc.value.code == "QUALITY_GATE_FAILED"


# ---------------------------------------------------------------------------
# Composite gate battery
# ---------------------------------------------------------------------------


class TestCompositeGateBattery:
    def test_all_gates_pass_for_clean_role(self, empty_tracker: Path, tmp_path: Path):
        """Happy path: no gate raises, returns empty warnings list."""
        profile = _make_profile(permitted_tiers=["selective"], daily_cap=10)
        role = _make_role(tier="selective", company="Acme Corp")
        workspace = tmp_path / "workspace"  # does not exist — jobqa gate skipped
        warnings = run_yolo_gates(profile, role, workspace, empty_tracker)
        assert warnings == []

    def test_tier_blocked_before_daily_cap(self, tracker_with_cap_reached: Path, tmp_path: Path):
        """Tier gate runs before daily cap — tier failure is reported first."""
        profile = _make_profile(permitted_tiers=["volume"], daily_cap=3)
        role = _make_role(tier="selective")
        workspace = tmp_path / "workspace"
        with pytest.raises(YoloGateError) as exc:
            run_yolo_gates(profile, role, workspace, tracker_with_cap_reached)
        assert exc.value.code == "TIER_NOT_PERMITTED"

    def test_daily_cap_blocked_after_tier_passes(
        self, tracker_with_cap_reached: Path, tmp_path: Path
    ):
        """Daily cap gate runs after tier gate passes."""
        profile = _make_profile(permitted_tiers=["volume"], daily_cap=3)
        role = _make_role(tier="volume")
        workspace = tmp_path / "workspace"
        with pytest.raises(YoloGateError) as exc:
            run_yolo_gates(profile, role, workspace, tracker_with_cap_reached)
        assert exc.value.code == "DAILY_CAP_REACHED"

    def test_jobqa_gate_skipped_when_workspace_does_not_exist(
        self, empty_tracker: Path, tmp_path: Path
    ):
        """If workspace_dir does not exist, jobqa gate is not attempted."""
        profile = _make_profile()
        role = _make_role(company="Acme Corp")
        workspace = tmp_path / "nonexistent_workspace"
        warnings = run_yolo_gates(profile, role, workspace, empty_tracker)
        assert warnings == []

    def test_jobqa_gate_skipped_when_workspace_exists_and_jobqa_missing(
        self, empty_tracker: Path, tmp_path: Path
    ):
        """If workspace exists but jobqa is not installed, run_yolo_gates must NOT
        raise — it should return a warnings list containing a skip message."""
        import shutil

        if shutil.which("jobqa"):
            pytest.skip("jobqa is installed — this test only applies when it is absent")

        profile = _make_profile()
        role = _make_role(company="Acme Corp")
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        warnings = run_yolo_gates(profile, role, workspace, empty_tracker)
        assert any("jobqa not in PATH" in w for w in warnings)


# ---------------------------------------------------------------------------
# jobqa PATH-check gate (issue #109 canary tests)
# ---------------------------------------------------------------------------


class TestJobqaPathCheck:
    def test_run_yolo_gates_skips_jobqa_when_not_installed(
        self, empty_tracker: Path, tmp_path: Path
    ):
        """When jobqa is not in PATH, run_yolo_gates must NOT raise; it should return
        a warnings list that contains a message about jobqa not being in PATH."""
        from unittest.mock import patch

        profile = _make_profile()
        role = _make_role(company="Acme Corp")
        workspace = tmp_path / "workspace"
        workspace.mkdir()

        with patch("shutil.which", return_value=None):
            warnings = run_yolo_gates(profile, role, workspace, empty_tracker)

        assert any("jobqa not in PATH" in w for w in warnings), (
            f"Expected a 'jobqa not in PATH' warning but got: {warnings}"
        )

    def test_run_yolo_gates_raises_when_jobqa_fails(
        self, empty_tracker: Path, tmp_path: Path
    ):
        """When jobqa is in PATH but run_jobqa_gate raises JobQAGateError,
        run_yolo_gates must re-raise that error."""
        from unittest.mock import patch

        profile = _make_profile()
        role = _make_role(company="Acme Corp")
        workspace = tmp_path / "workspace"
        workspace.mkdir()

        with (
            patch("shutil.which", return_value="/usr/bin/jobqa"),
            patch("yolo.run_jobqa_gate", side_effect=JobQAGateError("JOBQA_GATE_FAILED: qa failed")),
        ):
            with pytest.raises(JobQAGateError):
                run_yolo_gates(profile, role, workspace, empty_tracker)
