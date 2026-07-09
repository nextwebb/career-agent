from __future__ import annotations

import copy
import json
import sys
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "src"))

from location_strategy import collect_location_warnings, resolve_location  # noqa: E402

FIXTURE_PROFILE = ROOT / "tests" / "fixtures" / "non_pii" / "profile.synthetic.json"
FIXTURE_ROLE = (
    ROOT / "tests" / "fixtures" / "non_pii" / "roles" / "synthetic_quality_gate_pass.json"
)


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _legacy_profile() -> dict[str, Any]:
    profile = _load(FIXTURE_PROFILE)
    profile.pop("location_facts", None)
    profile.pop("location_presentations", None)
    profile.pop("location_strategy_defaults", None)
    return profile


def _legacy_role() -> dict[str, Any]:
    role = _load(FIXTURE_ROLE)
    role.pop("location_strategy", None)
    return role


def test_legacy_profile_only_returns_legacy_value_for_artifact_contexts():
    profile = _legacy_profile()
    role = _legacy_role()

    legacy = profile["location"]
    assert resolve_location(profile, role, "cv_contact") == legacy
    assert resolve_location(profile, role, "cover_letter_contact") == legacy
    assert resolve_location(profile, role, "ats_location") == legacy
    assert resolve_location(profile, role, "availability_banner") is None
    assert resolve_location(profile, role, "relocation_statement") is None


def test_legacy_profile_renders_identical_contact_line_in_generated_pdfs(tmp_path):
    pytest.importorskip("reportlab")
    pypdf = pytest.importorskip("pypdf")

    from cl_builder import build_cover_letter
    from cv_builder import build_cv
    from generate_application import prepare_generation_config

    profile = _legacy_profile()
    role = _legacy_role()
    config = prepare_generation_config(profile, role, create_output_dir=False)

    cv_path = tmp_path / "cv.pdf"
    cl_path = tmp_path / "cl.pdf"
    build_cv(profile, config, str(cv_path))
    build_cover_letter(profile, config, str(cl_path))

    cv_text = "\n".join(page.extract_text() or "" for page in pypdf.PdfReader(str(cv_path)).pages)
    cl_text = "\n".join(page.extract_text() or "" for page in pypdf.PdfReader(str(cl_path)).pages)

    assert profile["location"] in cv_text
    assert profile["location"] in cl_text


def test_profile_defaults_remote_label_overrides_legacy_for_cv_contact():
    profile = _legacy_profile()
    profile["location_facts"] = {"current_residence": "Lagos, Nigeria"}
    profile["location_presentations"] = {"remote_label": "Remote"}
    profile["location_strategy_defaults"] = {"cv_contact": "remote_label"}
    role = _legacy_role()

    assert resolve_location(profile, role, "cv_contact") == "Remote"


def test_role_override_current_residence_wins_over_profile_default():
    profile = _legacy_profile()
    profile["location_facts"] = {"current_residence": "Lagos, Nigeria"}
    profile["location_strategy_defaults"] = {"cv_contact": "remote_label"}
    role = _legacy_role()
    role["location_strategy"] = {"cv_contact": "current_residence"}

    assert resolve_location(profile, role, "cv_contact") == "Lagos, Nigeria"


def test_hide_strategy_returns_none_and_omits_cv_contact_fragment(tmp_path):
    pytest.importorskip("reportlab")
    pypdf = pytest.importorskip("pypdf")

    from cv_builder import build_cv
    from generate_application import prepare_generation_config

    profile = _legacy_profile()
    profile["location_strategy_defaults"] = {"cv_contact": "hide"}
    role = _legacy_role()
    config = prepare_generation_config(profile, role, create_output_dir=False)

    cv_path = tmp_path / "cv.pdf"
    build_cv(profile, config, str(cv_path))

    cv_text = "\n".join(page.extract_text() or "" for page in pypdf.PdfReader(str(cv_path)).pages)

    assert resolve_location(profile, role, "cv_contact") is None
    assert profile["location"] not in cv_text


def test_custom_strategy_renders_presentation_verbatim():
    profile = _legacy_profile()
    profile["location_presentations"] = {
        "custom": {"eu_timezone": "Relocating to an EU timezone shortly"}
    }
    profile["location_strategy_defaults"] = {"cv_contact": "custom:eu_timezone"}
    role = _legacy_role()

    assert resolve_location(profile, role, "cv_contact") == "Relocating to an EU timezone shortly"


def test_undefined_custom_strategy_resolves_none_and_gate_warns():
    profile = _legacy_profile()
    profile["location_presentations"] = {"custom": {"eu_timezone": "..."}}
    profile["location_strategy_defaults"] = {"cv_contact": "custom:missing_key"}
    role = _legacy_role()

    assert resolve_location(profile, role, "cv_contact") is None
    warnings = collect_location_warnings(profile, role)
    assert any("custom:missing_key" in w for w in warnings)


def test_legacy_location_disagrees_with_current_residence_emits_warning_and_new_field_wins():
    profile = _legacy_profile()
    profile["location"] = "Berlin, Germany"
    profile["location_facts"] = {"current_residence": "Lagos, Nigeria"}
    profile["location_strategy_defaults"] = {"cv_contact": "current_residence"}
    role = _legacy_role()

    assert resolve_location(profile, role, "cv_contact") == "Lagos, Nigeria"
    warnings = collect_location_warnings(profile, role)
    assert any("disagree" in w for w in warnings)


def test_precedence_role_strategy_wins_over_profile_default_and_legacy():
    profile = _legacy_profile()
    profile["location"] = "Berlin, Germany"
    profile["location_facts"] = {"current_residence": "Lagos, Nigeria"}
    profile["location_presentations"] = {"remote_label": "Remote"}
    profile["location_strategy_defaults"] = {"cv_contact": "current_residence"}
    role = _legacy_role()
    role["location_strategy"] = {"cv_contact": "remote_label"}

    assert resolve_location(profile, role, "cv_contact") == "Remote"


def test_inherit_at_role_level_falls_through_to_profile_default():
    profile = _legacy_profile()
    profile["location_facts"] = {"current_residence": "Lagos, Nigeria"}
    profile["location_strategy_defaults"] = {"cv_contact": "current_residence"}
    role = _legacy_role()
    role["location_strategy"] = {"cv_contact": "inherit"}

    assert resolve_location(profile, role, "cv_contact") == "Lagos, Nigeria"


def test_hide_returns_none_not_empty_string():
    profile = _legacy_profile()
    profile["location_strategy_defaults"] = {"cv_contact": "hide"}
    role = _legacy_role()

    assert resolve_location(profile, role, "cv_contact") is None


def test_resolver_does_not_mutate_inputs():
    profile = _legacy_profile()
    profile["location_facts"] = {"current_residence": "Lagos, Nigeria"}
    profile["location_strategy_defaults"] = {"cv_contact": "current_residence"}
    role = _legacy_role()
    role["location_strategy"] = {"ats_location": "remote_label"}

    profile_before = copy.deepcopy(profile)
    role_before = copy.deepcopy(role)
    for context in (
        "cv_contact",
        "cover_letter_contact",
        "ats_location",
        "availability_banner",
        "relocation_statement",
    ):
        resolve_location(profile, role, context)
    collect_location_warnings(profile, role)

    assert profile == profile_before
    assert role == role_before


def test_generated_role_specific_reads_role_field_only():
    profile = _legacy_profile()
    profile["location_strategy_defaults"] = {"availability_banner": "generated_role_specific"}
    role = _legacy_role()
    role["availability_banner"] = "Available Aug 1 in Berlin"

    assert resolve_location(profile, role, "availability_banner") == "Available Aug 1 in Berlin"


def test_generated_role_specific_missing_field_returns_none_and_warns():
    profile = _legacy_profile()
    profile["location_strategy_defaults"] = {"availability_banner": "generated_role_specific"}
    role = _legacy_role()
    role.pop("availability_banner", None)

    assert resolve_location(profile, role, "availability_banner") is None
    warnings = collect_location_warnings(profile, role)
    assert any("generated_role_specific" in w and "availability_banner" in w for w in warnings)


def test_remote_label_against_specific_role_location_emits_warning():
    profile = _legacy_profile()
    profile["location_strategy_defaults"] = {"cv_contact": "remote_label"}
    role = _legacy_role()
    role["location"] = "San Francisco, CA"

    warnings = collect_location_warnings(profile, role)
    assert any("remote_label" in w or "specific city" in w for w in warnings)


def test_remote_label_against_remote_role_location_does_not_warn():
    profile = _legacy_profile()
    profile["location_strategy_defaults"] = {"cv_contact": "remote_label"}
    role = _legacy_role()
    role["location"] = "Remote"

    warnings = collect_location_warnings(profile, role)
    assert not any("remote_label" in w for w in warnings)


def test_no_configured_story_produces_no_warnings():
    profile = _legacy_profile()
    role = _legacy_role()

    assert collect_location_warnings(profile, role) == []


def test_country_only_reads_country_of_residence():
    profile = _legacy_profile()
    profile["location_facts"] = {"country_of_residence": "Nigeria"}
    profile["location_strategy_defaults"] = {"ats_location": "country_only"}
    role = _legacy_role()

    assert resolve_location(profile, role, "ats_location") == "Nigeria"


def test_role_location_strategy_reads_role_config_location():
    profile = _legacy_profile()
    profile["location_strategy_defaults"] = {"ats_location": "role_location"}
    role = _legacy_role()
    role["location"] = "Berlin, Germany"

    assert resolve_location(profile, role, "ats_location") == "Berlin, Germany"


def test_current_residence_falls_back_to_legacy_when_fact_absent():
    profile = _legacy_profile()
    profile["location"] = "Berlin, Germany"
    profile["location_strategy_defaults"] = {"cv_contact": "current_residence"}
    role = _legacy_role()

    assert resolve_location(profile, role, "cv_contact") == "Berlin, Germany"


def test_remote_label_defaults_when_presentation_absent():
    profile = _legacy_profile()
    profile["location_strategy_defaults"] = {"cv_contact": "remote_label"}
    role = _legacy_role()

    assert resolve_location(profile, role, "cv_contact") == "Remote"
