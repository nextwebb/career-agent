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
from pathlib import Path

import pytest

# Allow imports from src/ without installation
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from pre_apply_checks import (
    DuplicateApplicationError,
    MissingArtifactsError,
    UnsupportedPlatformError,
    check_artifacts_exist,
    check_confirmation_pattern,
    check_duplicate,
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
