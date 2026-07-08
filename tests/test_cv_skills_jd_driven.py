"""Behavior contracts for JD-driven skills tailoring.

Focus: ``cv_builder._tailor_skills_to_jd`` — the pure-data helper that
intersects profile skill items with ``role.jd_skills``, prunes empty
categories, pads short matches from profile order, and enforces per-category
plus global caps.

Run: pytest tests/test_cv_skills_jd_driven.py -v
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from cv_builder import (  # noqa: E402
    SKILLS_MAX_CATEGORIES,
    SKILLS_MAX_ITEMS_PER_CATEGORY,
    SKILLS_MAX_TOTAL_ITEMS,
    SKILLS_PADDING_FLOOR,
    _split_items,
    _tailor_skills_to_jd,
)


def _cat(label: str, *items: str) -> dict:
    return {"label": label, "items": " · ".join(items)}


def test_missing_jd_skills_renders_profile_order_capped_at_6_categories():
    skills = [_cat(f"Cat{i}", f"item{i}a", f"item{i}b") for i in range(9)]

    result = _tailor_skills_to_jd(skills, None)

    assert [entry["label"] for entry in result] == [f"Cat{i}" for i in range(SKILLS_MAX_CATEGORIES)]


def test_missing_jd_skills_caps_each_category_at_6_items():
    skills = [_cat("Languages", *[f"item{i}" for i in range(10)])]

    result = _tailor_skills_to_jd(skills, None)

    assert len(_split_items(result[0]["items"])) == SKILLS_MAX_ITEMS_PER_CATEGORY


def test_missing_jd_skills_caps_total_items_at_40():
    # Six categories × six items = 36 after per-category cap. Extend the last
    # (tail-of-profile) category further so the global 40 cap has to kick in.
    skills = [_cat(f"Cat{i}", *[f"item{i}_{j}" for j in range(6)]) for i in range(6)]
    skills[-1] = _cat("Cat5", *[f"item5_{j}" for j in range(20)])

    result = _tailor_skills_to_jd(skills, None)

    total = sum(len(_split_items(entry["items"])) for entry in result)
    assert total <= SKILLS_MAX_TOTAL_ITEMS


def test_category_with_zero_jd_matches_is_dropped():
    skills = [
        _cat("Languages", "Python", "TypeScript"),
        _cat("Frontend", "React", "Vue"),
    ]

    result = _tailor_skills_to_jd(skills, ["Python"])

    labels = [entry["label"] for entry in result]
    assert "Frontend" not in labels
    assert "Languages" in labels


def test_category_with_one_to_three_jd_matches_is_padded_to_four():
    skills = [_cat("Cloud", "Lambda", "S3", "ECS", "SQS", "Terraform", "Docker")]

    result = _tailor_skills_to_jd(skills, ["Lambda"])

    items = _split_items(result[0]["items"])
    assert items[0] == "Lambda"
    assert len(items) == SKILLS_PADDING_FLOOR
    # Padding must come from the same category in profile-declared order,
    # skipping the already-matched item.
    assert items[1:] == ["S3", "ECS", "SQS"]


def test_category_with_four_or_more_jd_matches_takes_top_six_in_profile_order():
    skills = [
        _cat("Cloud", "Lambda", "S3", "ECS", "SQS", "Terraform", "Docker", "Kinesis", "DynamoDB"),
    ]

    result = _tailor_skills_to_jd(
        skills,
        ["Lambda", "S3", "ECS", "SQS", "Terraform", "Docker", "Kinesis"],
    )

    items = _split_items(result[0]["items"])
    assert items == ["Lambda", "S3", "ECS", "SQS", "Terraform", "Docker"]


def test_more_than_six_matching_categories_drops_padded_only_categories_first():
    # Seven categories: six have exactly one JD hit (will be padded);
    # one is padded-only (0 hits) via a JD term that only matches one
    # unrelated category — actually let's build the shape explicitly.
    skills = [
        _cat("A", "a1", "a2", "a3", "a4"),
        _cat("B", "b1", "b2", "b3", "b4"),
        _cat("C", "c1", "c2", "c3", "c4"),
        _cat("D", "d1", "d2", "d3", "d4"),
        _cat("E", "e1", "e2", "e3", "e4"),
        _cat("F", "f1", "f2", "f3", "f4"),
        _cat("G", "g1", "g2", "g3", "g4"),
    ]
    # JD hits every category — none is padded-only. Drop should fall on
    # the last profile-declared category (G) via the deterministic tiebreak.
    jd = ["a1", "b1", "c1", "d1", "e1", "f1", "g1"]

    result = _tailor_skills_to_jd(skills, jd)

    labels = [entry["label"] for entry in result]
    assert len(labels) == SKILLS_MAX_CATEGORIES
    assert "G" not in labels


def test_more_than_six_no_jd_categories_drops_tail_of_profile_order():
    # With no jd_skills the cap-only path applies to a 9-category profile:
    # the six earliest categories in profile order survive.
    skills = [_cat(f"Cat{i}", f"item{i}a", f"item{i}b") for i in range(9)]

    result = _tailor_skills_to_jd(skills, None)

    labels = [entry["label"] for entry in result]
    assert labels == [f"Cat{i}" for i in range(SKILLS_MAX_CATEGORIES)]


def test_jd_asks_for_skill_not_in_profile_does_not_render():
    skills = [_cat("Languages", "Python", "TypeScript")]

    result = _tailor_skills_to_jd(skills, ["Python", "Rust", "Haskell"])

    rendered = _split_items(result[0]["items"])
    assert "Rust" not in rendered
    assert "Haskell" not in rendered
    assert "Python" in rendered


def test_case_insensitive_matching_between_jd_and_profile_items():
    skills = [_cat("Cloud", "AWS Lambda", "S3")]

    result = _tailor_skills_to_jd(skills, ["aws lambda", "s3"])

    rendered = _split_items(result[0]["items"])
    # Rendered casing follows profile.json, not the JD input.
    assert "AWS Lambda" in rendered
    assert "S3" in rendered
    assert "aws lambda" not in rendered


def test_property_every_rendered_item_exists_in_profile():
    skills = [
        _cat("Languages", "Python", "TypeScript", "Go", "SQL"),
        _cat("Cloud", "AWS Lambda", "S3", "ECS", "SQS", "Terraform"),
        _cat("Frontend", "React", "Vue", "Svelte"),
    ]
    profile_items = {item for entry in skills for item in _split_items(entry["items"])}

    result = _tailor_skills_to_jd(skills, ["python", "aws lambda", "react", "made-up-skill"])

    for entry in result:
        for item in _split_items(entry["items"]):
            assert item in profile_items, f"Invented item leaked into output: {item}"


def test_deterministic_output_across_two_runs():
    skills = [
        _cat("Languages", "Python", "TypeScript", "Go"),
        _cat("Cloud", "Lambda", "S3", "ECS", "SQS", "Terraform"),
        _cat("Frontend", "React", "Vue"),
        _cat("Data", "Airflow", "dbt", "Snowflake"),
        _cat("Messaging", "Kafka", "RabbitMQ"),
        _cat("Observability", "Datadog", "Grafana"),
        _cat("AI", "OpenAI", "Anthropic"),
    ]
    jd = ["Python", "Lambda", "S3", "Airflow", "dbt", "Kafka"]

    first = _tailor_skills_to_jd(skills, jd)
    second = _tailor_skills_to_jd(skills, jd)

    assert first == second


def test_category_shorter_than_padding_floor_uses_whatever_it_has():
    skills = [_cat("Languages", "Python", "Go")]

    result = _tailor_skills_to_jd(skills, ["Python"])

    items = _split_items(result[0]["items"])
    assert items == ["Python", "Go"]


def test_empty_jd_skills_list_behaves_like_missing_jd_skills():
    skills = [
        _cat("Languages", "Python", "TypeScript"),
        _cat("Frontend", "React"),
    ]

    with_none = _tailor_skills_to_jd(skills, None)
    with_empty = _tailor_skills_to_jd(skills, [])

    assert with_none == with_empty


def test_rendered_casing_preserves_profile_casing_when_jd_uses_different_case():
    skills = [_cat("Cloud", "AWS Lambda", "S3", "Terraform")]

    result = _tailor_skills_to_jd(skills, ["AWS LAMBDA", "TERRAFORM"])

    rendered = _split_items(result[0]["items"])
    assert rendered[0] == "AWS Lambda"
    assert "Terraform" in rendered
