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

from pre_apply_checks import (
    CompanyRepeatError,
    DuplicateApplicationError,
    LeverCooldownError,
    MissingArtifactsError,
    UnsupportedPlatformError,
    _lever_slug,
    check_artifacts_exist,
    check_company_repeat,
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
# Company-repeat gate
# Issue #138: block after N prior same-company rejections.
# Distinct from check_duplicate (URL-exact) — operates at company granularity
# and only counts "rejected" outcomes.
# ---------------------------------------------------------------------------


def _make_tracker(tmp_path: Path, entries: list[dict]) -> Path:
    tracker = tmp_path / "tracker.json"
    tracker.write_text(json.dumps(entries))
    return tracker


_entry_counter = [0]


def _entry(
    company: str,
    status: str,
    url: str | None = None,
    role_id: str | None = None,
) -> dict:
    # Default role_id/url are unique per call so distinct entries represent
    # distinct applications (the gate dedupes rejected rows by role_id/url).
    _entry_counter[0] += 1
    n = _entry_counter[0]
    return {
        "role_id": role_id if role_id is not None else f"{company.lower()}_role_{n}",
        "company": company,
        "title": "Engineer",
        "url": url if url is not None else f"https://x/{n}",
        "status": status,
    }


class TestCompanyRepeatGate:
    def test_zero_rejections_passes(self, tmp_path: Path):
        """No prior rejected entries for the company — must not raise."""
        tracker = _make_tracker(tmp_path, [_entry("Acme", "applied")])
        check_company_repeat({"company": "Acme"}, tracker)  # must not raise

    def test_one_rejection_under_threshold_passes(self, tmp_path: Path):
        """One rejection with threshold 2 is under the bar — must not raise."""
        tracker = _make_tracker(tmp_path, [_entry("Acme", "rejected")])
        check_company_repeat({"company": "Acme"}, tracker, threshold=2)  # must not raise

    def test_two_rejections_blocks_with_company_and_count(self, tmp_path: Path):
        """Two rejections meets threshold 2 — must raise naming company + count."""
        tracker = _make_tracker(
            tmp_path,
            [_entry("Acme", "rejected"), _entry("Acme", "rejected")],
        )
        with pytest.raises(CompanyRepeatError) as exc:
            check_company_repeat({"company": "Acme"}, tracker, threshold=2)
        msg = str(exc.value)
        assert "Acme" in msg
        assert "2" in msg

    def test_override_allows_repeat_and_warns(self, tmp_path: Path, capsys):
        """allow_company_repeat=True downgrades the block to a stderr warning."""
        tracker = _make_tracker(
            tmp_path,
            [_entry("Acme", "rejected"), _entry("Acme", "rejected")],
        )
        check_company_repeat(
            {"company": "Acme"}, tracker, threshold=2, allow_company_repeat=True
        )  # must not raise
        captured = capsys.readouterr()
        assert "WARNING" in captured.err
        assert "company-repeat" in captured.err.lower()

    def test_normalisation_matches_suffix_and_case_variants(self, tmp_path: Path):
        """'Acme Inc' / 'acme' / 'ACME, LLC' all normalise to the same company."""
        tracker = _make_tracker(
            tmp_path,
            [_entry("Acme Inc", "rejected"), _entry("ACME, LLC", "rejected")],
        )
        # role config gives the bare "acme" form; both rejections must be counted
        with pytest.raises(CompanyRepeatError):
            check_company_repeat({"company": "acme"}, tracker, threshold=2)

    def test_distinct_companies_do_not_collide(self, tmp_path: Path):
        """
        FALSE-BLOCK guard: two genuinely different companies must NOT be merged
        by normalisation. 'Acme Corp' vs 'Acme Data' share a token but are
        distinct — applying to 'Acme Data' must not be blocked by 'Acme Corp'
        rejections.
        """
        tracker = _make_tracker(
            tmp_path,
            [_entry("Acme Corp", "rejected"), _entry("Acme Corp", "rejected")],
        )
        # Different company — must not raise despite shared "Acme" token.
        check_company_repeat({"company": "Acme Data"}, tracker, threshold=2)

    def test_non_rejected_statuses_are_not_counted(self, tmp_path: Path):
        """applied/withdrawn/offer at the company must NOT count toward the gate."""
        tracker = _make_tracker(
            tmp_path,
            [
                _entry("Acme", "applied"),
                _entry("Acme", "withdrawn"),
                _entry("Acme", "offer"),
            ],
        )
        check_company_repeat({"company": "Acme"}, tracker, threshold=2)  # must not raise

    def test_missing_tracker_file_passes(self, tmp_path: Path):
        check_company_repeat({"company": "Acme"}, tmp_path / "nope.json")  # must not raise

    def test_empty_company_in_role_config_passes(self, tmp_path: Path):
        tracker = _make_tracker(tmp_path, [_entry("Acme", "rejected"), _entry("Acme", "rejected")])
        check_company_repeat({"company": ""}, tracker, threshold=2)  # must not raise

    def test_run_pre_apply_checks_blocks_on_company_repeat(
        self, tmp_path: Path, generated_dir_with_pdfs: Path
    ):
        """
        Composite: run_pre_apply_checks raises CompanyRepeatError when role_config
        is supplied and the company has >= threshold rejections — wired after
        check_duplicate, before the artifact check.
        """
        tracker = _make_tracker(
            tmp_path,
            [_entry("Acme", "rejected"), _entry("Acme", "rejected")],
        )
        with pytest.raises(CompanyRepeatError):
            run_pre_apply_checks(
                role_id="acme_role",
                job_url="https://jobs.acme.com/new-role",
                ats_platform="lever",
                output_prefix="TestCo_SeniorBackend",
                generated_dir=generated_dir_with_pdfs,
                tracker_path=tracker,
                role_config={"company": "Acme"},
            )

    def test_run_pre_apply_checks_override_passes(
        self, tmp_path: Path, generated_dir_with_pdfs: Path
    ):
        """allow_company_repeat=True threads through run_pre_apply_checks."""
        tracker = _make_tracker(
            tmp_path,
            [_entry("Acme", "rejected"), _entry("Acme", "rejected")],
        )
        run_pre_apply_checks(
            role_id="acme_role",
            job_url="https://jobs.acme.com/new-role",
            ats_platform="lever",
            output_prefix="TestCo_SeniorBackend",
            generated_dir=generated_dir_with_pdfs,
            tracker_path=tracker,
            role_config={"company": "Acme"},
            allow_company_repeat=True,
        )  # must not raise

    # -- F1: null/None company must not crash (false-block via AttributeError) --

    def test_null_company_in_role_config_does_not_crash(self, tmp_path: Path):
        """
        Regression (F1): role JSON with explicit "company": null returns None
        (load_role_meta's "" default only applies to a MISSING key). The gate must
        normalise None to "" and no-op/pass — never crash and abort the whole run.
        """
        tracker = _make_tracker(
            tmp_path,
            [_entry("Acme", "rejected"), _entry("Acme", "rejected")],
        )
        check_company_repeat({"company": None}, tracker, threshold=2)  # must not raise

    def test_null_company_in_tracker_row_does_not_crash_and_counts_correctly(self, tmp_path: Path):
        """
        Regression (F1): a tracker entry with "company": null must not crash the
        counting loop, and the genuine same-company rejections must still be counted.
        Two real "Acme" rejections + one null-company row -> still blocks at threshold 2.
        """
        null_row = _entry("Acme", "rejected")
        null_row["company"] = None
        tracker = _make_tracker(
            tmp_path,
            [
                _entry("Acme", "rejected"),
                _entry("Acme", "rejected"),
                null_row,
            ],
        )
        with pytest.raises(CompanyRepeatError) as exc:
            check_company_repeat({"company": "Acme"}, tracker, threshold=2)
        assert "2" in str(exc.value)  # null row not counted; 2 real rejections

    # -- F2: dedupe rejected rows by application key (false-block via dup rows) --

    def test_duplicate_rejected_rows_same_role_id_count_as_one(self, tmp_path: Path):
        """
        Regression (F2): two rejected rows with the SAME role_id (corrupt/hand-edited
        tracker) are one application, not two. At threshold 2 this must PASS.
        """
        tracker = _make_tracker(
            tmp_path,
            [
                _entry("Acme", "rejected", role_id="acme_dup", url="https://x/dup"),
                _entry("Acme", "rejected", role_id="acme_dup", url="https://x/dup"),
            ],
        )
        check_company_repeat({"company": "Acme"}, tracker, threshold=2)  # must not raise

    def test_distinct_rejected_role_ids_same_company_count_separately(self, tmp_path: Path):
        """
        Regression (F2): two rejected rows with DIFFERENT role_ids at the same company
        are two distinct applications and must BLOCK at threshold 2 (cross-role signal).
        """
        tracker = _make_tracker(
            tmp_path,
            [
                _entry("Acme", "rejected", role_id="acme_role_a", url="https://x/a"),
                _entry("Acme", "rejected", role_id="acme_role_b", url="https://x/b"),
            ],
        )
        with pytest.raises(CompanyRepeatError):
            check_company_repeat({"company": "Acme"}, tracker, threshold=2)


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
