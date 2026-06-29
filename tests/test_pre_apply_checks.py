"""
test_pre_apply_checks.py — Integration tests for pre-apply gates.

These tests are behavior contracts, not implementation tests. Each test
is named after the failure mode it guards against and tests only via
the public interface of pre_apply_checks.py.

What we test:
  - Duplicate detection blocks apply before browser navigation
  - Missing artifacts block apply before browser navigation
  - Unsupported platform blocks autonomous mode
  - Confirmation pattern correctly classifies post-submit outcomes
  - Composite gate runs in fail-fast order

What we do NOT test:
  - Internal URL normalisation edge cases (type system + obvious cases cover it)
  - JSON parsing internals of the registry loader
  - Tracker file I/O beyond what the gate interface exposes

Run: pytest tests/test_pre_apply_checks.py -v
"""

from __future__ import annotations

import json
import sys
from datetime import date, timedelta
from pathlib import Path

import pytest

# Allow imports from src/ without installation
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import record_submission
import tracker as tracker_module
from pre_apply_checks import (
    DuplicateApplicationError,
    LeverCooldownError,
    MissingArtifactsError,
    UnsupportedPlatformError,
    _lever_slug,
    check_artifacts_exist,
    check_confirmation_pattern,
    check_duplicate,
    check_lever_cooldown,
    check_platform_supported,
    run_pre_apply_checks,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def tracker_with_bux(tmp_path: Path) -> Path:
    """
    Tracker containing a BUX application at a known URL.
    Regression fixture: BUX 'You already applied' (2026-06-22).
    """
    tracker = tmp_path / "tracker.json"
    tracker.write_text(
        json.dumps(
            [
                {
                    "role_id": "bux_senior_data_platform_engineer_2026",
                    "company": "BUX",
                    "title": "Senior Data Platform Engineer",
                    "url": "https://jobs.bux.com/jobs/1234567890",
                    "status": "applied",
                    "added": "2026-06-22",
                    "applied": "2026-06-22",
                    "last_update": "2026-06-22",
                    "notes": [],
                }
            ]
        )
    )
    return tracker


@pytest.fixture
def empty_tracker(tmp_path: Path) -> Path:
    tracker = tmp_path / "tracker.json"
    tracker.write_text("[]")
    return tracker


@pytest.fixture
def generated_dir_with_pdfs(tmp_path: Path) -> Path:
    """Generated directory with valid (non-empty) stub PDFs."""
    gen = tmp_path / "generated"
    gen.mkdir()
    # Minimal valid PDF header — enough for the size check
    pdf_stub = b"%PDF-1.4\n%stub for testing\n" + b"x" * 600
    (gen / "TestCo_SeniorBackend_CV.pdf").write_bytes(pdf_stub)
    (gen / "TestCo_SeniorBackend_CoverLetter.pdf").write_bytes(pdf_stub)
    return gen


@pytest.fixture
def generated_dir_missing_cv(tmp_path: Path) -> Path:
    gen = tmp_path / "generated"
    gen.mkdir()
    pdf_stub = b"%PDF-1.4\n" + b"x" * 600
    (gen / "TestCo_SeniorBackend_CoverLetter.pdf").write_bytes(pdf_stub)
    return gen


@pytest.fixture
def generated_dir_corrupt_cv(tmp_path: Path) -> Path:
    gen = tmp_path / "generated"
    gen.mkdir()
    (gen / "TestCo_SeniorBackend_CV.pdf").write_bytes(b"x" * 100)  # < 512 bytes
    pdf_stub = b"%PDF-1.4\n" + b"x" * 600
    (gen / "TestCo_SeniorBackend_CoverLetter.pdf").write_bytes(pdf_stub)
    return gen


@pytest.fixture
def confirmation_registry(tmp_path: Path) -> Path:
    registry = tmp_path / "ats_confirmation_patterns.json"
    registry.write_text(
        json.dumps(
            {
                "lever": {
                    "url_contains": "/thanks",
                    "text_contains": ["Thank you for applying"],
                    "failure_text_contains": ["error-message"],
                },
                "workable": {
                    "url_contains": "?success",
                    "text_contains": ["submitted successfully"],
                    "failure_text_contains": ["There are some issues"],
                },
                "greenhouse": {
                    "url_contains": "",
                    "text_contains": ["Application submitted", "received your application"],
                    "failure_text_contains": ["already applied"],
                },
                "teamtailor": {
                    "url_contains": "",
                    "text_contains": ["application has been received"],
                    "failure_text_contains": ["You already applied for this job"],
                },
            }
        )
    )
    return registry


# ---------------------------------------------------------------------------
# Duplicate detection
# Regression: BUX "You already applied" (2026-06-22)
# ---------------------------------------------------------------------------


class TestDuplicateDetection:
    def test_blocks_apply_when_url_already_in_tracker(self, tracker_with_bux: Path):
        """
        Contract: pipeline must raise before browser navigation when job_url
        matches an existing tracker entry.
        """
        with pytest.raises(DuplicateApplicationError, match="BUX"):
            check_duplicate(
                job_url="https://jobs.bux.com/jobs/1234567890",
                tracker_path=tracker_with_bux,
            )

    def test_blocks_on_url_with_trailing_slash(self, tracker_with_bux: Path):
        """URL normalisation: trailing slash must not defeat duplicate detection."""
        with pytest.raises(DuplicateApplicationError):
            check_duplicate(
                job_url="https://jobs.bux.com/jobs/1234567890/",
                tracker_path=tracker_with_bux,
            )

    def test_blocks_on_url_with_uppercase_scheme(self, tracker_with_bux: Path):
        """URL normalisation: scheme case must not defeat duplicate detection."""
        with pytest.raises(DuplicateApplicationError):
            check_duplicate(
                job_url="HTTPS://jobs.bux.com/jobs/1234567890",
                tracker_path=tracker_with_bux,
            )

    def test_allows_apply_for_new_url(self, tracker_with_bux: Path):
        """Different URL on the same company must not be blocked."""
        check_duplicate(
            job_url="https://jobs.bux.com/jobs/9999999999",
            tracker_path=tracker_with_bux,
        )  # must not raise

    def test_allows_apply_when_tracker_empty(self, empty_tracker: Path):
        check_duplicate(
            job_url="https://jobs.lever.co/stripe/abc123/apply",
            tracker_path=empty_tracker,
        )  # must not raise

    def test_allows_apply_when_no_tracker_file(self, tmp_path: Path):
        """No tracker.json means no history — safe to proceed."""
        check_duplicate(
            job_url="https://jobs.lever.co/stripe/abc123/apply",
            tracker_path=tmp_path / "tracker.json",
        )  # must not raise

    def test_submitted_unconfirmed_blocks_resubmission(self, tmp_path):
        tracker = tmp_path / "tracker.json"
        tracker.write_text(
            json.dumps(
                [
                    {
                        "role_id": "stripe_backend",
                        "company": "Stripe",
                        "url": "https://jobs.lever.co/stripe/abc123/apply",
                        "status": "submitted_unconfirmed",
                        "added": "2026-06-28",
                        "applied": "2026-06-28",
                        "last_update": "2026-06-28",
                        "notes": [],
                    }
                ]
            )
        )
        with pytest.raises(DuplicateApplicationError):
            check_duplicate(
                job_url="https://jobs.lever.co/stripe/abc123/apply",
                tracker_path=tracker,
            )

    def test_autonomous_failed_allows_retry(self, tmp_path):
        tracker = tmp_path / "tracker.json"
        tracker.write_text(
            json.dumps(
                [
                    {
                        "role_id": "stripe_backend",
                        "company": "Stripe",
                        "url": "https://jobs.lever.co/stripe/abc123/apply",
                        "status": "autonomous_failed",
                        "added": "2026-06-28",
                        "applied": None,
                        "last_update": "2026-06-28",
                        "notes": [],
                    }
                ]
            )
        )
        # Must NOT raise — autonomous_failed means the submission didn't go through
        check_duplicate(
            job_url="https://jobs.lever.co/stripe/abc123/apply",
            tracker_path=tracker,
        )

    def test_failed_allows_retry(self, tmp_path):
        tracker = tmp_path / "tracker.json"
        tracker.write_text(
            json.dumps(
                [
                    {
                        "role_id": "stripe_backend",
                        "company": "Stripe",
                        "url": "https://jobs.lever.co/stripe/abc123/apply",
                        "status": "failed",
                        "added": "2026-06-28",
                        "applied": None,
                        "last_update": "2026-06-28",
                        "notes": [],
                    }
                ]
            )
        )
        check_duplicate(
            job_url="https://jobs.lever.co/stripe/abc123/apply",
            tracker_path=tracker,
        )  # must not raise


# ---------------------------------------------------------------------------
# Artifact existence
# ---------------------------------------------------------------------------


class TestArtifactExistence:
    def test_blocks_when_cv_missing(self, generated_dir_missing_cv: Path):
        """
        Contract: apply must not start if the CV PDF is not on disk.
        A missing CV means the form upload would silently fail or upload nothing.
        """
        with pytest.raises(MissingArtifactsError, match="CV"):
            check_artifacts_exist(
                output_prefix="TestCo_SeniorBackend",
                generated_dir=generated_dir_missing_cv,
            )

    def test_blocks_when_cv_corrupt(self, generated_dir_corrupt_cv: Path):
        """
        Contract: a CV file that is too small to be a real PDF must be rejected.
        Regression target: corrupt write producing a < 512 byte file.
        """
        with pytest.raises(MissingArtifactsError, match="corrupt"):
            check_artifacts_exist(
                output_prefix="TestCo_SeniorBackend",
                generated_dir=generated_dir_corrupt_cv,
            )

    def test_blocks_when_generated_dir_missing(self, tmp_path: Path):
        with pytest.raises(MissingArtifactsError):
            check_artifacts_exist(
                output_prefix="TestCo_SeniorBackend",
                generated_dir=tmp_path / "generated",
            )

    def test_passes_when_both_pdfs_exist(self, generated_dir_with_pdfs: Path):
        check_artifacts_exist(
            output_prefix="TestCo_SeniorBackend",
            generated_dir=generated_dir_with_pdfs,
        )  # must not raise


# ---------------------------------------------------------------------------
# Platform support gate (autonomous mode only)
# ---------------------------------------------------------------------------


class TestPlatformSupport:
    def test_blocks_autonomous_mode_for_unknown_platform(self, confirmation_registry: Path):
        """
        Contract: autonomous mode must not run on a platform with no verified
        confirmation pattern. An unrecognised confirmation page is indistinguishable
        from a silent failure — retry risks double-submission.
        """
        with pytest.raises(UnsupportedPlatformError, match="bamboohr"):
            check_platform_supported(
                ats_platform="bamboohr",
                registry_path=confirmation_registry,
            )

    def test_allows_known_platform(self, confirmation_registry: Path):
        check_platform_supported(
            ats_platform="lever",
            registry_path=confirmation_registry,
        )  # must not raise

    def test_allows_unknown_ats_string_in_hitl(self, confirmation_registry: Path):
        """
        'unknown' ATS platform is allowed without raising — the apply skill
        will hand off to the user for manual submission.
        """
        check_platform_supported(
            ats_platform="unknown",
            registry_path=confirmation_registry,
        )  # must not raise


# ---------------------------------------------------------------------------
# Confirmation pattern classification (post-submit)
# Regression: Workable CV drop left submission in ambiguous state (2026-06-22)
# ---------------------------------------------------------------------------


class TestConfirmationPatternClassification:
    def test_lever_confirmed_via_url(self, confirmation_registry: Path):
        result = check_confirmation_pattern(
            ats_platform="lever",
            final_url="https://jobs.lever.co/stripe/abc123/thanks",
            page_text="Thank you for applying to Stripe.",
            registry_path=confirmation_registry,
        )
        assert result == "confirmed"

    def test_workable_confirmed_via_url_query_param(self, confirmation_registry: Path):
        """
        Regression: Workable confirmation via ?success query param (2026-06-22).
        The apply skill must use this to distinguish success from silent failure.
        """
        result = check_confirmation_pattern(
            ats_platform="workable",
            final_url="https://apply.workable.com/climax-studios/j/A03E9A31FE/apply/?success",
            page_text="Your application has been submitted successfully.",
            registry_path=confirmation_registry,
        )
        assert result == "confirmed"

    def test_workable_failed_via_known_error_text(self, confirmation_registry: Path):
        """
        Workable error banner 'There are some issues with your application'
        is a known failure — must return 'failed', not 'ambiguous'.
        """
        result = check_confirmation_pattern(
            ats_platform="workable",
            final_url="https://apply.workable.com/climax-studios/j/A03E9A31FE/apply/",
            page_text="There are some issues with your application. Please revisit your data.",
            registry_path=confirmation_registry,
        )
        assert result == "failed"

    def test_teamtailor_duplicate_is_failed_not_ambiguous(self, confirmation_registry: Path):
        """
        'You already applied for this job' is a known failure state on Teamtailor.
        Must be classified as 'failed' so the pipeline does not retry.
        Regression: BUX duplicate (2026-06-22).
        """
        result = check_confirmation_pattern(
            ats_platform="teamtailor",
            final_url="https://jobs.bux.com/jobs/1234567890",
            page_text="You already applied for this job.",
            registry_path=confirmation_registry,
        )
        assert result == "failed"

    def test_unrecognised_page_is_ambiguous_not_confirmed(self, confirmation_registry: Path):
        """
        Contract: an unrecognised confirmation page must return 'ambiguous'.
        The pipeline must halt. It must never retry after Submit.
        """
        result = check_confirmation_pattern(
            ats_platform="lever",
            final_url="https://jobs.lever.co/stripe/abc123/apply",
            page_text="Page not found",
            registry_path=confirmation_registry,
        )
        assert result == "ambiguous"

    def test_unknown_platform_is_always_ambiguous(self, confirmation_registry: Path):
        """Unknown platform cannot verify confirmation — must always be ambiguous."""
        result = check_confirmation_pattern(
            ats_platform="unknown",
            final_url="https://example.com/jobs/123/apply",
            page_text="Application submitted successfully",
            registry_path=confirmation_registry,
        )
        assert result == "ambiguous"


# ---------------------------------------------------------------------------
# Composite gate: run_pre_apply_checks
# Verifies fail-fast order and that all gates are wired up
# ---------------------------------------------------------------------------


class TestCompositeGate:
    def test_duplicate_blocks_before_artifact_check(self, tracker_with_bux: Path, tmp_path: Path):
        """
        Duplicate gate must run before artifact check.
        If both fail, DuplicateApplicationError is raised, not MissingArtifactsError.
        """
        with pytest.raises(DuplicateApplicationError):
            run_pre_apply_checks(
                role_id="bux_test",
                job_url="https://jobs.bux.com/jobs/1234567890",
                ats_platform="teamtailor",
                output_prefix="BUX_SeniorData",
                generated_dir=tmp_path / "generated",  # does not exist
                tracker_path=tracker_with_bux,
            )

    def test_missing_artifacts_blocks_after_duplicate_passes(
        self,
        empty_tracker: Path,
        tmp_path: Path,
        confirmation_registry: Path,
    ):
        """Artifact check runs only after duplicate check passes."""
        with pytest.raises(MissingArtifactsError):
            run_pre_apply_checks(
                role_id="new_role",
                job_url="https://jobs.lever.co/stripe/abc123/apply",
                ats_platform="lever",
                output_prefix="Stripe_SeniorBackend",
                generated_dir=tmp_path / "generated",  # does not exist
                tracker_path=empty_tracker,
                registry_path=confirmation_registry,
            )

    def test_unsupported_platform_blocks_only_in_autonomous_mode(
        self,
        empty_tracker: Path,
        generated_dir_with_pdfs: Path,
        confirmation_registry: Path,
    ):
        """
        UnsupportedPlatformError is raised in autonomous mode.
        In HITL mode (autonomous=False), the same platform must pass.
        """
        # HITL mode: must not raise
        run_pre_apply_checks(
            role_id="new_role",
            job_url="https://jobs.bamboohr.com/company/1",
            ats_platform="bamboohr",
            output_prefix="TestCo_SeniorBackend",
            generated_dir=generated_dir_with_pdfs,
            tracker_path=empty_tracker,
            registry_path=confirmation_registry,
            autonomous=False,
        )

        # Autonomous mode: must raise
        with pytest.raises(UnsupportedPlatformError):
            run_pre_apply_checks(
                role_id="new_role",
                job_url="https://jobs.bamboohr.com/company/1",
                ats_platform="bamboohr",
                output_prefix="TestCo_SeniorBackend",
                generated_dir=generated_dir_with_pdfs,
                tracker_path=empty_tracker,
                registry_path=confirmation_registry,
                autonomous=True,
            )

    def test_autonomous_mode_blocks_when_ats_platform_is_unknown(
        self,
        empty_tracker: Path,
        generated_dir_with_pdfs: Path,
        confirmation_registry: Path,
    ):
        """
        Canary for issue #106: autonomous=True + ats_platform="unknown" must raise
        UnsupportedPlatformError.

        check_platform_supported early-returns for ats_platform="unknown" regardless
        of mode, so without a guard in run_pre_apply_checks the autonomous path
        silently passed and proceeded to browser automation — a double-submission risk.

        HITL mode (autonomous=False) with ats_platform="unknown" must still pass.
        """
        # HITL: unknown ATS is fine — manual handoff
        run_pre_apply_checks(
            role_id="mystery_role",
            job_url="https://example.com/jobs/999",
            ats_platform="unknown",
            output_prefix="TestCo_SeniorBackend",
            generated_dir=generated_dir_with_pdfs,
            tracker_path=empty_tracker,
            registry_path=confirmation_registry,
            autonomous=False,
        )  # must not raise

        # Autonomous: unknown ATS must be blocked
        with pytest.raises(UnsupportedPlatformError, match="unknown"):
            run_pre_apply_checks(
                role_id="mystery_role",
                job_url="https://example.com/jobs/999",
                ats_platform="unknown",
                output_prefix="TestCo_SeniorBackend",
                generated_dir=generated_dir_with_pdfs,
                tracker_path=empty_tracker,
                registry_path=confirmation_registry,
                autonomous=True,
            )

    def test_all_gates_pass_for_clean_application(
        self,
        empty_tracker: Path,
        generated_dir_with_pdfs: Path,
        confirmation_registry: Path,
    ):
        """Happy path: all gates pass, no exception raised."""
        run_pre_apply_checks(
            role_id="stripe_backend_2026",
            job_url="https://jobs.lever.co/stripe/abc123/apply",
            ats_platform="lever",
            output_prefix="TestCo_SeniorBackend",
            generated_dir=generated_dir_with_pdfs,
            tracker_path=empty_tracker,
            registry_path=confirmation_registry,
            autonomous=True,
        )  # must not raise


# ---------------------------------------------------------------------------
# Canary: Workable "Thank you" false-positive regression
# Issue #107: "Thank you" in Workable text_contains triggers confirmed on
# form pages, validation errors, and generic copy — before any submission.
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Provisional submitted_unconfirmed row: upsert + real role_id + retryability
# Issue #135: a crash between Submit and the tracker write must be visible to
# duplicate detection, and the provisional row must transition cleanly.
# ---------------------------------------------------------------------------


class TestMarkSubmittedUnconfirmed:
    def test_upserts_existing_draft_row_no_duplicate(self, tmp_path: Path):
        """
        A pre-existing draft row for the role must be upgraded in place to
        submitted_unconfirmed — not duplicated. Exactly ONE row for the role.
        """
        tracker = tmp_path / "tracker.json"
        tracker.write_text(
            json.dumps(
                [
                    {
                        "role_id": "stripe_backend",
                        "company": "Stripe",
                        "title": "Senior Backend",
                        "url": "https://jobs.lever.co/stripe/abc123/apply",
                        "status": "draft",
                        "added": "2026-06-01",
                        "applied": None,
                        "last_update": "2026-06-01",
                        "notes": [],
                    }
                ]
            )
        )

        tracker_module.mark_submitted_unconfirmed(
            role_id="stripe_backend",
            job_url="https://jobs.lever.co/stripe/abc123/apply",
            tracker_path=tracker,
        )

        entries = json.loads(tracker.read_text())
        rows = [e for e in entries if e["role_id"] == "stripe_backend"]
        assert len(rows) == 1, f"expected exactly one row, got {len(rows)}"
        assert rows[0]["status"] == "submitted_unconfirmed"

    def test_upserts_by_url_when_role_id_differs(self, tmp_path: Path):
        """A row with the same URL (different role_id) is updated, not duplicated."""
        tracker = tmp_path / "tracker.json"
        tracker.write_text(
            json.dumps(
                [
                    {
                        "role_id": "old_id",
                        "company": "Stripe",
                        "url": "https://jobs.lever.co/stripe/abc123/apply",
                        "status": "draft",
                        "added": "2026-06-01",
                        "applied": None,
                        "last_update": "2026-06-01",
                        "notes": [],
                    }
                ]
            )
        )

        tracker_module.mark_submitted_unconfirmed(
            role_id="new_id",
            job_url="https://jobs.lever.co/stripe/abc123/apply/",
            tracker_path=tracker,
        )

        entries = json.loads(tracker.read_text())
        assert len(entries) == 1
        assert entries[0]["status"] == "submitted_unconfirmed"

    def test_url_match_reassigns_role_id_and_transitions(self, tmp_path: Path, monkeypatch):
        """
        URL-matched upsert with a differing role_id must CLAIM the row for the
        incoming role_id, so the later update_status(new_id, ...) — which keys on
        role_id — finds and transitions the same row. Otherwise the row stays
        stuck as submitted_unconfirmed and the URL is blocked forever (issue #135).
        """
        tracker = tmp_path / "tracker.json"
        url = "https://jobs.lever.co/stripe/abc123/apply"
        tracker.write_text(
            json.dumps(
                [
                    {
                        "role_id": "old",
                        "company": "Stripe",
                        "url": url,
                        "status": "draft",
                        "added": "2026-06-01",
                        "applied": None,
                        "last_update": "2026-06-01",
                        "notes": [],
                    }
                ]
            )
        )

        tracker_module.mark_submitted_unconfirmed(
            role_id="new",
            job_url=url + "/",  # trailing slash → normalised URL match, role_id differs
            tracker_path=tracker,
        )

        norm = tracker_module._normalise_url
        entries = json.loads(tracker.read_text())
        rows = [e for e in entries if norm(e["url"]) == norm(url)]
        assert len(rows) == 1, "must remain exactly one row for the URL"
        assert rows[0]["role_id"] == "new", "row must be claimed by the incoming role_id"
        assert rows[0]["status"] == "submitted_unconfirmed"
        assert not any(e["role_id"] == "old" for e in entries)

        # update_status keys on role_id — must find and transition THIS row
        monkeypatch.setattr(tracker_module, "TRACKER_PATH", tracker)
        tracker_module.update_status("new", "autonomous_submitted")
        entries = json.loads(tracker.read_text())
        rows = [e for e in entries if e["role_id"] == "new"]
        assert len(rows) == 1
        assert rows[0]["status"] == "autonomous_submitted"

    def test_appends_when_no_match(self, tmp_path: Path):
        """Brand-new role with no matching row appends a single entry."""
        tracker = tmp_path / "tracker.json"
        tracker.write_text("[]")

        tracker_module.mark_submitted_unconfirmed(
            role_id="fresh_role",
            job_url="https://jobs.lever.co/foo/xyz/apply",
            tracker_path=tracker,
        )

        entries = json.loads(tracker.read_text())
        assert len(entries) == 1
        assert entries[0]["role_id"] == "fresh_role"
        assert entries[0]["status"] == "submitted_unconfirmed"

    def test_end_to_end_retryability(self, tmp_path: Path, monkeypatch):
        """
        mark_submitted_unconfirmed → check_duplicate blocks → update_status
        transitions THE SAME row to autonomous_failed → check_duplicate allows retry.
        """
        tracker = tmp_path / "tracker.json"
        tracker.write_text(
            json.dumps(
                [
                    {
                        "role_id": "stripe_backend",
                        "company": "Stripe",
                        "url": "https://jobs.lever.co/stripe/abc123/apply",
                        "status": "draft",
                        "added": "2026-06-01",
                        "applied": None,
                        "last_update": "2026-06-01",
                        "notes": [],
                    }
                ]
            )
        )
        url = "https://jobs.lever.co/stripe/abc123/apply"

        tracker_module.mark_submitted_unconfirmed(
            role_id="stripe_backend",
            job_url=url,
            tracker_path=tracker,
        )

        # Provisional row blocks a re-run
        with pytest.raises(DuplicateApplicationError):
            check_duplicate(job_url=url, tracker_path=tracker)

        # update_status uses the module-level TRACKER_PATH — point it at our file
        monkeypatch.setattr(tracker_module, "TRACKER_PATH", tracker)
        tracker_module.update_status("stripe_backend", "autonomous_failed")

        # Same row transitioned — exactly one row, now failed
        entries = json.loads(tracker.read_text())
        rows = [e for e in entries if e["role_id"] == "stripe_backend"]
        assert len(rows) == 1
        assert rows[0]["status"] == "autonomous_failed"

        # URL is now retryable
        check_duplicate(job_url=url, tracker_path=tracker)  # must not raise


class TestRecordSubmissionRoleId:
    def test_extract_role_id_top_level(self):
        assert record_submission._extract_role_id({"role_id": "abc"}) == "abc"

    def test_extract_role_id_nested(self):
        assert record_submission._extract_role_id({"role": {"role_id": "nested"}}) == "nested"
        assert record_submission._extract_role_id({"role_intake": {"role_id": "ri"}}) == "ri"

    def test_extract_role_id_absent(self):
        assert record_submission._extract_role_id({"summary": {}}) == ""

    def test_real_role_id_stored_from_manifest_path(self, tmp_path: Path, monkeypatch):
        """
        Given a manifest PATH as arg 1, the provisional row's role_id is the
        manifest's role_id — NOT the manifest file path (issue #135 finding 2).
        """
        manifest = tmp_path / "manifest.json"
        manifest.write_text(json.dumps({"role_id": "stripe_backend", "summary": {}}))
        tracker = tmp_path / "tracker.json"
        output = tmp_path / "audit.json"

        monkeypatch.setattr(
            sys,
            "argv",
            [
                "record_submission.py",
                str(manifest),
                "lever:https://jobs.lever.co/stripe/abc123/apply",
                "yolo-pre-authorized:abcd",
                str(output),
                str(tracker),
            ],
        )
        rc = record_submission.main()
        assert rc == 0

        entries = json.loads(tracker.read_text())
        assert len(entries) == 1
        assert entries[0]["role_id"] == "stripe_backend"
        assert entries[0]["role_id"] != str(manifest)
        assert entries[0]["status"] == "submitted_unconfirmed"

    def test_audit_write_failure_leaves_no_provisional_row(self, tmp_path: Path, monkeypatch):
        """
        If the audit-log write fails (output_path is an existing directory →
        write_text raises), record_submission must return non-zero AND must NOT
        have written a submitted_unconfirmed tracker row — otherwise a
        never-submitted application would falsely block the next retry.
        """
        manifest = tmp_path / "manifest.json"
        manifest.write_text(json.dumps({"role_id": "stripe_backend", "summary": {}}))
        tracker = tmp_path / "tracker.json"

        # Point output_path at an existing directory so write_text raises OSError.
        output_dir = tmp_path / "audit_is_a_dir.json"
        output_dir.mkdir()

        monkeypatch.setattr(
            sys,
            "argv",
            [
                "record_submission.py",
                str(manifest),
                "lever:https://jobs.lever.co/stripe/abc123/apply",
                "yolo-pre-authorized:abcd",
                str(output_dir),
                str(tracker),
            ],
        )
        rc = record_submission.main()
        assert rc != 0  # audit write failed → abort before Submit

        # The provisional row must NOT have been written.
        if tracker.exists():
            entries = json.loads(tracker.read_text())
            assert not any(
                e.get("role_id") == "stripe_backend" and e.get("status") == "submitted_unconfirmed"
                for e in entries
            ), "audit-write failure must not leave a duplicate-blocking row"
        # (tracker not existing at all is also acceptable — no mutation happened)


class TestWorkableThankYouFalsePositive:
    def test_workable_thank_you_does_not_confirm(self):
        """
        Regression: 'Thank you' must NOT classify a Workable page as confirmed.

        'Thank you for your interest' appears on the form page itself and in
        validation-error states. Without ?success in the URL or a specific
        submission phrase, the outcome is ambiguous — not confirmed.

        Uses the production registry (src/ats_confirmation_patterns.json) so
        this test is red while 'Thank you' is present and green after removal.

        Issue #107.
        """
        result = check_confirmation_pattern(
            ats_platform="workable",
            final_url="https://apply.workable.com/company/j/ABC123/apply/",
            page_text="Thank you for your interest",
            # no registry_path override — uses production src/ats_confirmation_patterns.json
        )
        assert result == "ambiguous", (
            "Expected 'ambiguous' but got 'confirmed'. "
            "Remove 'Thank you' from Workable text_contains in "
            "src/ats_confirmation_patterns.json (issue #107)."
        )


# ---------------------------------------------------------------------------
# Canary: Ashby over-broad generic tokens — both sides removed
# Issue #140 (Part D1): the bare "error" token in Ashby failure_text_contains
# matches any page that merely contains the word "error" anywhere (a CSS class,
# a footer, "0 errors", an analytics blob) — misclassifying a SUCCESSFUL
# submission as 'failed', which can drive a retry → double-submit.
#
# Issue #136: the bare "Thank you" token in Ashby text_contains matches any
# page with generic courtesy copy — including error/info pages — false-
# CONFIRMING a non-submission page. These two are coupled: with "error" gone
# from the failure side, an Ashby error page carrying generic "Thank you"
# boilerplate would fall through to the success token and classify 'confirmed'
# (a silent false-success, strictly worse than the false-fail). Both over-broad
# generic tokens are removed; only specific observed signals remain on each side.
# ---------------------------------------------------------------------------


class TestAshbyErrorTokenFalseFail:
    def test_ashby_error_page_with_generic_thank_you_is_ambiguous(self):
        """
        Regression for issue #136 / the #140 D1 coupling: an Ashby error or
        ambiguous page that carries only generic "Thank you" courtesy copy —
        and NOT a specific success signal ("Application submitted",
        "We'll be in touch") nor a known failure signal ("already applied") —
        must classify as 'ambiguous', NOT 'confirmed' and NOT 'failed'.

        With the failure-side "error" token removed (#140 D1), the bare success-
        side "Thank you" token would otherwise turn such a page into a silent
        false-success. 'ambiguous' halts the apply flow for human review instead
        of auto-recording a wrong outcome.

        Uses the production registry so this test is red while "Thank you"
        remains in Ashby text_contains and green after its removal.

        Issues #136, #140 (Part D1).
        """
        result = check_confirmation_pattern(
            ats_platform="ashby",
            final_url="https://jobs.ashbyhq.com/poolside/abc123",
            page_text=(
                "Something went wrong submitting your application. "
                "Thank you for your interest — please try again later."
            ),
            # no registry_path override — uses production src/ats_confirmation_patterns.json
        )
        assert result == "ambiguous", (
            "Expected 'ambiguous' but got 'confirmed'/'failed'. The bare "
            "'Thank you' token matches generic courtesy copy on an Ashby error "
            "page. Remove 'Thank you' from Ashby text_contains in "
            "src/ats_confirmation_patterns.json (issues #136, #140 D1)."
        )

    def test_ashby_confirmed_via_application_submitted(self):
        """Specific observed signal 'Application submitted' → 'confirmed'."""
        result = check_confirmation_pattern(
            ats_platform="ashby",
            final_url="https://jobs.ashbyhq.com/poolside/abc123",
            page_text="Application submitted.",
            # no registry_path override — uses production src/ats_confirmation_patterns.json
        )
        assert result == "confirmed"

    def test_ashby_confirmed_via_well_be_in_touch(self):
        """Specific observed signal 'We'll be in touch' → 'confirmed'."""
        result = check_confirmation_pattern(
            ats_platform="ashby",
            final_url="https://jobs.ashbyhq.com/poolside/abc123",
            page_text="Thanks — we'll be in touch.",
            # no registry_path override — uses production src/ats_confirmation_patterns.json
        )
        assert result == "confirmed"

    def test_ashby_success_with_incidental_error_substring_is_confirmed(self):
        """
        Regression: an Ashby success page whose markup incidentally contains
        the word 'error' (e.g. a CSS class or "0 errors") must NOT classify as
        'failed'. With a real Ashby success signal present, the outcome is
        'confirmed'.

        Uses the production registry (src/ats_confirmation_patterns.json) so
        this test is red while the bare 'error' token is present and green
        after its removal.

        Issue #140 (Part D1).
        """
        result = check_confirmation_pattern(
            ats_platform="ashby",
            final_url="https://jobs.ashbyhq.com/poolside/abc123",
            page_text=(
                '<div class="error-boundary"></div>'
                "Application submitted. We'll be in touch. 0 errors."
            ),
            # no registry_path override — uses production src/ats_confirmation_patterns.json
        )
        assert result == "confirmed", (
            "Expected 'confirmed' but got 'failed'. The bare 'error' token "
            "matches incidental markup on a successful Ashby page. Remove "
            "'error' from Ashby failure_text_contains in "
            "src/ats_confirmation_patterns.json (issue #140 D1)."
        )

    def test_ashby_already_applied_is_still_failed(self):
        """
        Removing the bare 'error' token must not weaken genuine failure
        detection: an Ashby page reporting 'already applied' must still
        classify as 'failed' so the pipeline does not retry.

        Issue #140 (Part D1).
        """
        result = check_confirmation_pattern(
            ats_platform="ashby",
            final_url="https://jobs.ashbyhq.com/poolside/abc123",
            page_text="You have already applied to this role.",
            # no registry_path override — uses production src/ats_confirmation_patterns.json
        )
        assert result == "failed"


# ---------------------------------------------------------------------------
# Lever per-company cooldown gate (issue #147 / #140 Part A)
# ---------------------------------------------------------------------------


def _lever_tracker(tmp_path: Path, *, slug: str, applied: str, status: str = "applied") -> Path:
    """Build a tracker with one Lever entry for `slug`, applied on `applied`."""
    tracker = tmp_path / "tracker.json"
    tracker.write_text(
        json.dumps(
            [
                {
                    "role_id": f"{slug}_role_2026",
                    "company": slug.capitalize(),
                    "title": "Senior Backend Engineer",
                    "url": f"https://jobs.lever.co/{slug}/00000000-1111-2222-3333-444444444444/apply",
                    "status": status,
                    "added": applied,
                    "applied": applied,
                    "last_update": applied,
                    "notes": [],
                }
            ]
        )
    )
    return tracker


def _days_ago(n: int) -> str:
    return str(date.today() - timedelta(days=n))


class TestLeverSlugExtraction:
    @pytest.mark.parametrize(
        "url, expected",
        [
            ("https://jobs.lever.co/acme/abcd-1234", "acme"),
            ("https://jobs.lever.co/acme/abcd-1234/apply", "acme"),
            ("https://jobs.lever.co/acme/abcd-1234/apply?utm=x&lever-source=y", "acme"),
            ("https://jobs.lever.co/acme/abcd-1234#section", "acme"),
            ("https://jobs.eu.lever.co/acme/abcd-1234", "acme"),
            ("https://jobs.lever.co/acme/", "acme"),
            ("https://jobs.lever.co/acme", "acme"),
            ("HTTPS://JOBS.LEVER.CO/acme/abcd-1234", "acme"),
            # FIX 1: mixed-case slug normalises to lowercase
            ("https://jobs.lever.co/Fliff/abcd-1234/apply", "fliff"),
            ("https://jobs.lever.co/ACME/abcd-1234", "acme"),
            # FIX 3: www. (and any subdomain prefix) normalises to the same host
            ("https://www.jobs.lever.co/acme/abcd-1234/apply", "acme"),
            ("https://www.jobs.eu.lever.co/acme/abcd-1234", "acme"),
            # Non-Lever hosts -> None
            ("https://job-boards.greenhouse.io/acme/jobs/123", None),
            ("https://jobs.ashbyhq.com/acme/uuid/application", None),
            ("https://apply.workable.com/j/ABC123/apply/", None),
            ("https://jobs.lever.co/", None),
            ("", None),
        ],
    )
    def test_slug_extraction(self, url, expected):
        assert _lever_slug(url) == expected


class TestLeverCooldownGate:
    def test_blocks_same_slug_within_window(self, tmp_path: Path):
        tracker = _lever_tracker(tmp_path, slug="acme", applied=_days_ago(5))
        with pytest.raises(LeverCooldownError, match="acme"):
            check_lever_cooldown(
                job_url="https://jobs.lever.co/acme/99999999-0000/apply",
                tracker_path=tracker,
            )

    def test_passes_same_slug_outside_window(self, tmp_path: Path):
        tracker = _lever_tracker(tmp_path, slug="acme", applied=_days_ago(45))
        check_lever_cooldown(
            job_url="https://jobs.lever.co/acme/99999999-0000/apply",
            tracker_path=tracker,
        )  # must not raise

    def test_passes_when_prior_is_draft(self, tmp_path: Path):
        """A never-submitted draft must never block, even within the window."""
        tracker = _lever_tracker(tmp_path, slug="acme", applied=_days_ago(2), status="draft")
        check_lever_cooldown(
            job_url="https://jobs.lever.co/acme/99999999-0000/apply",
            tracker_path=tracker,
        )  # must not raise

    def test_passes_when_no_prior_same_slug(self, tmp_path: Path):
        tracker = _lever_tracker(tmp_path, slug="acme", applied=_days_ago(2))
        check_lever_cooldown(
            job_url="https://jobs.lever.co/othercorp/uuid/apply",
            tracker_path=tracker,
        )  # must not raise

    def test_passes_for_different_slug(self, tmp_path: Path):
        tracker = _lever_tracker(tmp_path, slug="acme", applied=_days_ago(2))
        check_lever_cooldown(
            job_url="https://jobs.lever.co/beta/uuid/apply",
            tracker_path=tracker,
        )  # must not raise

    def test_noop_for_non_lever_url(self, tmp_path: Path):
        """Non-Lever inbound URL must pass unconditionally, even if slug collides."""
        tracker = _lever_tracker(tmp_path, slug="acme", applied=_days_ago(1))
        check_lever_cooldown(
            job_url="https://job-boards.greenhouse.io/acme/jobs/123",
            tracker_path=tracker,
        )  # must not raise

    def test_eu_host_matches_same_slug(self, tmp_path: Path):
        """An eu.lever.co prior submission blocks a jobs.lever.co resubmit (same slug)."""
        tracker = _lever_tracker(tmp_path, slug="wypoon", applied=_days_ago(3))
        # rewrite the entry to the EU host
        entries = json.loads(tracker.read_text())
        entries[0]["url"] = "https://jobs.eu.lever.co/wypoon/uuid-1"
        tracker.write_text(json.dumps(entries))
        with pytest.raises(LeverCooldownError, match="wypoon"):
            check_lever_cooldown(
                job_url="https://jobs.lever.co/wypoon/uuid-2/apply",
                tracker_path=tracker,
            )

    def test_blocks_when_matching_entry_has_no_usable_date(self, tmp_path: Path):
        """A submitted same-slug entry with no parseable date is conservatively blocked."""
        tracker = tmp_path / "tracker.json"
        tracker.write_text(
            json.dumps(
                [
                    {
                        "role_id": "acme_role",
                        "company": "Acme",
                        "title": "Engineer",
                        "url": "https://jobs.lever.co/acme/uuid/apply",
                        "status": "applied",
                        "added": None,
                        "applied": None,
                        "last_update": None,
                        "notes": [],
                    }
                ]
            )
        )
        with pytest.raises(LeverCooldownError, match="unknown"):
            check_lever_cooldown(
                job_url="https://jobs.lever.co/acme/other-uuid/apply",
                tracker_path=tracker,
            )

    def test_override_bypasses_block_with_warning(self, tmp_path: Path, capsys):
        tracker = _lever_tracker(tmp_path, slug="acme", applied=_days_ago(5))
        check_lever_cooldown(
            job_url="https://jobs.lever.co/acme/99999999-0000/apply",
            tracker_path=tracker,
            override_ats_policy=True,
        )  # must not raise
        captured = capsys.readouterr()
        assert "WARNING" in captured.err
        # Warning must describe the real mechanism (a parameter), not a CLI flag.
        assert "override_ats_policy=True" in captured.err
        assert "--override-ats-policy" not in captured.err

    def test_no_tracker_file_passes(self, tmp_path: Path):
        check_lever_cooldown(
            job_url="https://jobs.lever.co/acme/uuid/apply",
            tracker_path=tmp_path / "nope.json",
        )  # must not raise

    # --- Regression: FIX 1 — case-insensitive slug (false-allow) ---
    def test_fix1_mixedcase_historic_blocks_lowercase_incoming(self, tmp_path: Path):
        """
        Real repro: tracker stores 'Fliff' (capital F); incoming is lowercase
        'fliff'. Both go through _lever_slug, so the resubmit must block.
        """
        tracker = _lever_tracker(tmp_path, slug="acme", applied=_days_ago(4))
        entries = json.loads(tracker.read_text())
        entries[0]["url"] = "https://jobs.lever.co/Fliff/8d2c958f-uuid/apply"
        tracker.write_text(json.dumps(entries))
        with pytest.raises(LeverCooldownError, match="fliff"):
            check_lever_cooldown(
                job_url="https://jobs.lever.co/fliff/other-uuid/apply",
                tracker_path=tracker,
            )

    def test_fix1_lowercase_historic_blocks_mixedcase_incoming(self, tmp_path: Path):
        """Inverse direction: lowercase historic, mixed-case incoming, same company."""
        tracker = _lever_tracker(tmp_path, slug="acme", applied=_days_ago(4))
        with pytest.raises(LeverCooldownError, match="acme"):
            check_lever_cooldown(
                job_url="https://jobs.lever.co/ACME/other-uuid/apply",
                tracker_path=tracker,
            )

    # --- Regression: FIX 2 — untrusted `added` must not clear the window ---
    def test_fix2_applied_null_old_added_still_blocks_undated(self, tmp_path: Path):
        """
        Real repro: a submitted entry with applied=null, last_update=null, but an
        `added` from 40 days ago (draft created weeks before submit). `added`
        must NOT clear the cooldown — the entry is treated as undated and blocked.
        """
        tracker = tmp_path / "tracker.json"
        tracker.write_text(
            json.dumps(
                [
                    {
                        "role_id": "acme_role",
                        "company": "Acme",
                        "title": "Engineer",
                        "url": "https://jobs.lever.co/acme/uuid/apply",
                        "status": "applied",
                        "added": _days_ago(40),
                        "applied": None,
                        "last_update": None,
                        "notes": [],
                    }
                ]
            )
        )
        with pytest.raises(LeverCooldownError, match="unknown"):
            check_lever_cooldown(
                job_url="https://jobs.lever.co/acme/other-uuid/apply",
                tracker_path=tracker,
            )

    # --- Regression: FIX 3 — www. host normalization (false-allow) ---
    def test_fix3_www_incoming_blocks_against_bare_historic(self, tmp_path: Path):
        """Incoming www.jobs.lever.co must match a bare jobs.lever.co historic entry."""
        tracker = _lever_tracker(tmp_path, slug="acme", applied=_days_ago(3))
        with pytest.raises(LeverCooldownError, match="acme"):
            check_lever_cooldown(
                job_url="https://www.jobs.lever.co/acme/other-uuid/apply",
                tracker_path=tracker,
            )

    def test_fix3_www_historic_blocks_against_bare_incoming(self, tmp_path: Path):
        """Historic stored as www.jobs.lever.co must match a bare incoming URL."""
        tracker = _lever_tracker(tmp_path, slug="acme", applied=_days_ago(3))
        entries = json.loads(tracker.read_text())
        entries[0]["url"] = "https://www.jobs.lever.co/acme/uuid-1/apply"
        tracker.write_text(json.dumps(entries))
        with pytest.raises(LeverCooldownError, match="acme"):
            check_lever_cooldown(
                job_url="https://jobs.lever.co/acme/uuid-2/apply",
                tracker_path=tracker,
            )

    # --- Regression: FIX 4 — case-insensitive status (false-block) ---
    def test_fix4_capitalized_draft_status_passes(self, tmp_path: Path):
        """
        A same-slug entry with status 'Draft'/'DRAFT' (non-lowercase) is still a
        never-submitted draft and must NOT block a brand-new application.
        """
        tracker = _lever_tracker(tmp_path, slug="acme", applied=_days_ago(2), status="Draft")
        check_lever_cooldown(
            job_url="https://jobs.lever.co/acme/other-uuid/apply",
            tracker_path=tracker,
        )  # must not raise

        # And the uppercase variant
        entries = json.loads(tracker.read_text())
        entries[0]["status"] = "DRAFT"
        tracker.write_text(json.dumps(entries))
        check_lever_cooldown(
            job_url="https://jobs.lever.co/acme/other-uuid/apply",
            tracker_path=tracker,
        )  # must not raise


class TestCompositeGateLeverCooldown:
    def test_composite_blocks_on_lever_cooldown(
        self, tmp_path: Path, generated_dir_with_pdfs: Path
    ):
        """
        End-to-end: a same-slug Lever resubmit within the window is blocked by
        run_pre_apply_checks after duplicate + artifact checks pass.
        """
        tracker = _lever_tracker(tmp_path, slug="acme", applied=_days_ago(5))
        with pytest.raises(LeverCooldownError):
            run_pre_apply_checks(
                role_id="acme_other_role",
                job_url="https://jobs.lever.co/acme/different-uuid/apply",
                ats_platform="lever",
                output_prefix="TestCo_SeniorBackend",
                generated_dir=generated_dir_with_pdfs,
                tracker_path=tracker,
            )

    def test_composite_override_allows_lever_cooldown(
        self, tmp_path: Path, generated_dir_with_pdfs: Path
    ):
        """override_ats_policy=True threads through run_pre_apply_checks and bypasses."""
        tracker = _lever_tracker(tmp_path, slug="acme", applied=_days_ago(5))
        run_pre_apply_checks(
            role_id="acme_other_role",
            job_url="https://jobs.lever.co/acme/different-uuid/apply",
            ats_platform="lever",
            output_prefix="TestCo_SeniorBackend",
            generated_dir=generated_dir_with_pdfs,
            tracker_path=tracker,
            override_ats_policy=True,
        )  # must not raise
