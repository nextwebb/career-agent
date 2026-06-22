"""
test_jobqa_workspace.py — Tests for the career-agent → job-application-quality workspace translator.

Tests cover:
  - generate_jobqa_workspace creates the expected files
  - ATS field mapping (workable→other, teamtailor→other, etc.)
  - Claims derivation from experience bullets
  - Missing required fields raise WorkspaceTranslationError
  - sponsorship_available / remote_status defaults

Run: pytest tests/test_jobqa_workspace.py -v
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from jobqa_workspace import (
    ATS_MAP,
    WorkspaceTranslationError,
    _build_candidate,
    _build_role_intake,
    _derive_claims,
    generate_jobqa_workspace,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

MINIMAL_PROFILE = {
    "name": {"first": "Jane", "last": "Doe"},
    "email": "jane@example.com",
    "phone": {"formatted": "+15551234567"},
    "location": "Berlin, Germany",
    "links": {
        "linkedin": "https://linkedin.com/in/janedoe",
        "github": "https://github.com/janedoe",
    },
    "experience": [
        {
            "id": "job_1",
            "title": "Senior Engineer",
            "company": "Acme Corp",
            "bullets": {
                "default": [
                    "Reduced API latency by 40% via async refactor",
                    "Led a team of 5 engineers",
                    "Improved CI pipeline throughput by 3x",
                ],
                "A": ["Built LLM evaluation harness covering 200+ test cases"],
            },
        }
    ],
    "education": [],
    "skills": [],
}

MINIMAL_ROLE = {
    "role_id": "acme_senior_eng_2026",
    "company": "Acme Corp",
    "title": "Senior Backend Engineer",
    "url": "https://jobs.lever.co/acme/abc123/apply",
    "ats_platform": "lever",
    "variant": "A",
    "output_prefix": "Jane_Doe_Acme_Senior_Backend",
}


def write_json(path: Path, data: dict) -> Path:
    path.write_text(json.dumps(data, indent=2))
    return path


# ---------------------------------------------------------------------------
# generate_jobqa_workspace integration
# ---------------------------------------------------------------------------


class TestGenerateJobqaWorkspace:
    def test_creates_candidate_and_role_json(self, tmp_path: Path):
        profile_path = write_json(tmp_path / "profile.json", MINIMAL_PROFILE)
        role_path = write_json(tmp_path / "role.json", MINIMAL_ROLE)
        workspace = tmp_path / "workspace"

        result = generate_jobqa_workspace(profile_path, role_path, workspace)

        assert result == workspace
        assert (workspace / "candidate.json").exists()
        assert (workspace / "role.json").exists()
        assert (workspace / "artifacts").is_dir()

    def test_candidate_json_has_required_fields(self, tmp_path: Path):
        profile_path = write_json(tmp_path / "profile.json", MINIMAL_PROFILE)
        role_path = write_json(tmp_path / "role.json", MINIMAL_ROLE)
        workspace = tmp_path / "workspace"
        generate_jobqa_workspace(profile_path, role_path, workspace)

        candidate = json.loads((workspace / "candidate.json").read_text())
        assert candidate["candidate_name"] == "Jane Doe"
        assert candidate["tenant_id"] == "jane@example.com"
        assert candidate["contact"]["email"] == "jane@example.com"
        assert candidate["contact"]["linkedin"] == "https://linkedin.com/in/janedoe"

    def test_role_json_has_required_fields(self, tmp_path: Path):
        profile_path = write_json(tmp_path / "profile.json", MINIMAL_PROFILE)
        role_path = write_json(tmp_path / "role.json", MINIMAL_ROLE)
        workspace = tmp_path / "workspace"
        generate_jobqa_workspace(profile_path, role_path, workspace)

        role = json.loads((workspace / "role.json").read_text())
        assert role["role_id"] == "acme_senior_eng_2026"
        assert role["company"] == "Acme Corp"
        assert role["ats"] == "lever"
        assert role["job_url"] == "https://jobs.lever.co/acme/abc123/apply"

    def test_artifacts_are_copied(self, tmp_path: Path):
        profile_path = write_json(tmp_path / "profile.json", MINIMAL_PROFILE)
        role_path = write_json(tmp_path / "role.json", MINIMAL_ROLE)

        cv = tmp_path / "Jane_Doe_Acme_CV.pdf"
        cv.write_bytes(b"%PDF-1.4\n" + b"x" * 600)

        workspace = tmp_path / "workspace"
        generate_jobqa_workspace(profile_path, role_path, workspace, artifacts=[cv])

        assert (workspace / "artifacts" / "Jane_Doe_Acme_CV.pdf").exists()

    def test_missing_artifacts_are_silently_skipped(self, tmp_path: Path):
        profile_path = write_json(tmp_path / "profile.json", MINIMAL_PROFILE)
        role_path = write_json(tmp_path / "role.json", MINIMAL_ROLE)
        workspace = tmp_path / "workspace"
        # should not raise for a non-existent artifact
        generate_jobqa_workspace(
            profile_path,
            role_path,
            workspace,
            artifacts=[tmp_path / "nonexistent.pdf"],
        )
        assert not list((workspace / "artifacts").iterdir())


# ---------------------------------------------------------------------------
# _build_candidate
# ---------------------------------------------------------------------------


class TestBuildCandidate:
    def test_concatenates_name(self):
        c = _build_candidate(MINIMAL_PROFILE)
        assert c["candidate_name"] == "Jane Doe"

    def test_raises_on_missing_name(self):
        profile = {**MINIMAL_PROFILE, "name": {}}
        with pytest.raises(WorkspaceTranslationError, match="profile.name"):
            _build_candidate(profile)

    def test_work_auth_defaults_require_sponsorship(self):
        profile = {**MINIMAL_PROFILE}
        profile.pop("eeo", None)
        c = _build_candidate(profile)
        assert c["work_authorization"]["requires_sponsorship_for_eu_uk_us"] is True

    def test_work_auth_uses_eeo_when_present(self):
        profile = {
            **MINIMAL_PROFILE,
            "eeo": {
                "requires_sponsorship_for_eu_uk_us": False,
                "contractor_globally": False,
                "current_right_to_work": ["EU"],
            },
        }
        c = _build_candidate(profile)
        assert c["work_authorization"]["requires_sponsorship_for_eu_uk_us"] is False
        assert c["work_authorization"]["current_right_to_work"] == ["EU"]

    def test_forbidden_claims_defaults_to_empty(self):
        c = _build_candidate(MINIMAL_PROFILE)
        assert c["forbidden_claims"] == []

    def test_forbidden_claims_uses_profile_field(self):
        profile = {**MINIMAL_PROFILE, "forbidden_claims": [{"claim_id": "x", "text": "foo"}]}
        c = _build_candidate(profile)
        assert len(c["forbidden_claims"]) == 1


# ---------------------------------------------------------------------------
# _derive_claims
# ---------------------------------------------------------------------------


class TestDeriveClaims:
    def test_extracts_measurable_bullets(self):
        experience = [
            {
                "id": "j1",
                "bullets": {
                    "default": [
                        "Reduced API latency by 40%",
                        "Led team meetings on Tuesdays",  # not measurable
                        "Saved $200K in cloud costs",
                    ]
                },
            }
        ]
        claims = _derive_claims(experience)
        texts = [c["text"] for c in claims]
        assert "Reduced API latency by 40%" in texts
        assert "Saved $200K in cloud costs" in texts
        assert "Led team meetings on Tuesdays" not in texts

    def test_all_claims_have_inferred_confidence(self):
        experience = MINIMAL_PROFILE["experience"]
        claims = _derive_claims(experience)
        assert all(c["confidence"] == "inferred" for c in claims)

    def test_deduplicates_across_variants(self):
        bullet = "Reduced latency by 50%"
        experience = [
            {
                "id": "j1",
                "bullets": {
                    "default": [bullet],
                    "A": [bullet],  # duplicate
                },
            }
        ]
        claims = _derive_claims(experience)
        texts = [c["text"] for c in claims]
        assert texts.count(bullet) == 1

    def test_empty_experience_returns_empty_claims(self):
        assert _derive_claims([]) == []


# ---------------------------------------------------------------------------
# _build_role_intake — ATS mapping
# ---------------------------------------------------------------------------


class TestBuildRoleIntake:
    @pytest.mark.parametrize(
        "ats_in, ats_out",
        [
            ("greenhouse", "greenhouse"),
            ("greenhouse_eu", "greenhouse"),
            ("lever", "lever"),
            ("ashby", "ashby"),
            ("workable", "other"),  # Workable.com != Workday HCM
            ("teamtailor", "other"),
            ("unknown", "other"),
            ("LEVER", "lever"),  # case-insensitive
        ],
    )
    def test_ats_mapping(self, ats_in: str, ats_out: str):
        role = {**MINIMAL_ROLE, "ats_platform": ats_in}
        intake = _build_role_intake(role)
        assert intake["ats"] == ats_out

    def test_sponsorship_defaults_to_unknown(self):
        role = {**MINIMAL_ROLE}
        role.pop("sponsorship_available", None)
        intake = _build_role_intake(role)
        assert intake["sponsorship"]["status"] == "unknown"

    def test_sponsorship_uses_explicit_field(self):
        role = {**MINIMAL_ROLE, "sponsorship_available": "available"}
        intake = _build_role_intake(role)
        assert intake["sponsorship"]["status"] == "available"

    def test_remote_status_defaults_to_unknown(self):
        role = {**MINIMAL_ROLE}
        role.pop("remote_status", None)
        intake = _build_role_intake(role)
        assert intake["remote"]["status"] == "unknown"

    def test_remote_status_uses_explicit_field(self):
        role = {**MINIMAL_ROLE, "remote_status": "global"}
        intake = _build_role_intake(role)
        assert intake["remote"]["status"] == "global"

    def test_required_skills_defaults_to_empty(self):
        role = {**MINIMAL_ROLE}
        role.pop("required_skills", None)
        intake = _build_role_intake(role)
        assert intake["required_skills"] == []

    def test_required_skills_passed_through(self):
        role = {**MINIMAL_ROLE, "required_skills": ["Python", "PostgreSQL"]}
        intake = _build_role_intake(role)
        assert intake["required_skills"] == ["Python", "PostgreSQL"]


# ---------------------------------------------------------------------------
# ATS_MAP completeness
# ---------------------------------------------------------------------------


class TestATSMap:
    def test_ats_map_covers_all_validation_platforms(self):
        """Every platform accepted by validation.py should have an ATS_MAP entry."""
        # This mirrors the valid_platforms set in validation.py.
        # If you add a platform to validation.py, add it here and to ATS_MAP too.
        required_in_map = {
            "greenhouse",
            "greenhouse_eu",
            "lever",
            "ashby",
            "workable",
            "teamtailor",
            "unknown",
        }
        for platform in required_in_map:
            assert (
                platform in ATS_MAP
            ), f"ATS_MAP missing platform '{platform}' — add a mapping entry"
