"""Behavior contracts for optional ``group`` field on CV skills entries.

Focus: ``cv_builder._collapse_skill_groups`` — the pure-data helper that
merges skills entries sharing a ``group`` value into a single rendered line.
Kept as a data-level test (no PDF render) so the contract is fast and
independent of reportlab.

Run: pytest tests/test_cv_skills_grouping.py -v
"""

from __future__ import annotations

import sys
from pathlib import Path

# Allow imports from src/ without installation
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from cv_builder import _collapse_skill_groups  # noqa: E402


def test_entries_without_group_render_individually_unchanged():
    skills = [
        {"label": "Languages", "items": "Python · Go"},
        {"label": "Backend", "items": "REST · gRPC"},
    ]

    result = _collapse_skill_groups(skills)

    assert result == skills
    # ensure we returned copies, not aliases (defensive against later mutation)
    assert result[0] is not skills[0]


def test_two_entries_with_same_group_merge_into_one_line():
    skills = [
        {"label": "AWS Compute", "group": "Cloud", "items": "Lambda · ECS"},
        {"label": "AWS Data", "group": "Cloud", "items": "S3 · SQS"},
    ]

    result = _collapse_skill_groups(skills)

    assert len(result) == 1
    assert result[0]["label"] == "Cloud"
    assert result[0]["items"] == "Lambda · ECS · S3 · SQS"


def test_group_members_with_duplicate_items_are_deduped_order_preserving():
    skills = [
        {"label": "AWS A", "group": "Cloud", "items": "Lambda · S3 · ECS"},
        {"label": "AWS B", "group": "Cloud", "items": "S3 · SQS · Lambda"},
    ]

    result = _collapse_skill_groups(skills)

    assert result[0]["items"] == "Lambda · S3 · ECS · SQS"


def test_first_seen_group_appears_in_original_position():
    skills = [
        {"label": "Languages", "items": "Python"},
        {"label": "AWS Compute", "group": "Cloud", "items": "Lambda"},
        {"label": "Backend", "items": "REST"},
        {"label": "AWS Data", "group": "Cloud", "items": "S3"},
    ]

    result = _collapse_skill_groups(skills)

    # Cloud takes slot 1 (first appearance), ungrouped entries keep positions
    labels = [entry["label"] for entry in result]
    assert labels == ["Languages", "Cloud", "Backend"]
    cloud = next(entry for entry in result if entry["label"] == "Cloud")
    assert cloud["items"] == "Lambda · S3"


def test_falsy_group_value_is_treated_as_ungrouped():
    skills = [
        {"label": "Languages", "group": "", "items": "Python"},
        {"label": "Backend", "group": None, "items": "REST"},
    ]

    result = _collapse_skill_groups(skills)

    assert [entry["label"] for entry in result] == ["Languages", "Backend"]
