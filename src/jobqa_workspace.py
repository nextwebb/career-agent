"""
jobqa_workspace.py — Translate career-agent data into a job-application-quality workspace.

job-application-quality expects a workspace directory containing:
  candidate.json  (profile schema)
  role.json       (role intake schema)
  artifacts/      (CV, cover letter PDFs)

career-agent uses different schemas. This module translates between them.

The translation is lossy in two places:
  - claims[] are derived from experience bullets with confidence: "inferred"
  - work_authorization defaults to Nigeria-based / requires-sponsorship unless
    profile.eeo overrides it

Add profile.eeo and profile.forbidden_claims for more accurate policy gates.
"""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path
from typing import Any

# ATS name mapping: career-agent -> job-application-quality
# "workable" (Workable.com) != "workday" (Workday HCM) — these are different platforms
# job-application-quality has no workable entry; map to "other"
ATS_MAP: dict[str, str] = {
    "greenhouse": "greenhouse",
    "greenhouse_eu": "greenhouse",
    "lever": "lever",
    "ashby": "ashby",
    "workable": "other",
    "teamtailor": "other",
    "unknown": "other",
}

_MEASURABLE = re.compile(
    r"(\d[\d,]*\s*(%|x|×|times?|ms|s\b|seconds?|minutes?|hours?|days?|weeks?)|"
    r"\$\d|reduced|increased|improved|saved|cut|doubled|tripled|halved)",
    re.IGNORECASE,
)


class WorkspaceTranslationError(Exception):
    """Raised when required fields are missing or the workspace cannot be generated."""


def generate_jobqa_workspace(
    profile_path: Path,
    role_config_path: Path,
    workspace_dir: Path,
    artifacts: list[Path] | None = None,
) -> Path:
    """
    Translate a career-agent profile + role config into a job-application-quality workspace.

    Outputs:
      workspace_dir/candidate.json
      workspace_dir/role.json
      workspace_dir/artifacts/<filename> for each artifact in artifacts

    Returns workspace_dir.

    Raises WorkspaceTranslationError if required fields are absent in either input.
    """
    with open(profile_path, encoding="utf-8") as f:
        profile: dict[str, Any] = json.load(f)
    with open(role_config_path, encoding="utf-8") as f:
        role: dict[str, Any] = json.load(f)

    workspace_dir.mkdir(parents=True, exist_ok=True)
    artifacts_dir = workspace_dir / "artifacts"
    artifacts_dir.mkdir(exist_ok=True)

    candidate = _build_candidate(profile)
    role_intake = _build_role_intake(role)

    (workspace_dir / "candidate.json").write_text(
        json.dumps(candidate, indent=2, ensure_ascii=False)
    )
    (workspace_dir / "role.json").write_text(json.dumps(role_intake, indent=2, ensure_ascii=False))

    for artifact in artifacts or []:
        if artifact.exists():
            shutil.copy2(artifact, artifacts_dir / artifact.name)

    return workspace_dir


def _build_candidate(profile: dict[str, Any]) -> dict[str, Any]:
    name = profile.get("name", {})
    first = name.get("first", "").strip()
    last = name.get("last", "").strip()
    candidate_name = f"{first} {last}".strip()
    if not candidate_name:
        raise WorkspaceTranslationError(
            "profile.name.first and profile.name.last are required for workspace translation"
        )

    phone = profile.get("phone", {})
    links = profile.get("links", {})

    # Work authorization: use profile.eeo if present; default to requires-sponsorship.
    # Callers with a real profile should set profile.eeo explicitly for accurate policy gates.
    eeo = profile.get("eeo", {})
    work_auth: dict[str, Any] = {
        "current_right_to_work": eeo.get("current_right_to_work", []),
        "requires_sponsorship_for_eu_uk_us": eeo.get("requires_sponsorship_for_eu_uk_us", True),
        "contractor_globally": eeo.get("contractor_globally", True),
    }

    claims = _derive_claims(profile.get("experience", []))
    forbidden_claims: list[Any] = profile.get("forbidden_claims", [])

    yolo = profile.get("yolo_mode", {})

    return {
        "candidate_name": candidate_name,
        "tenant_id": profile.get("email", ""),
        "contact": {
            "email": profile.get("email", ""),
            "phone": phone.get("formatted", ""),
            "current_location": profile.get("location", ""),
            "linkedin": links.get("linkedin", ""),
            "github": links.get("github", ""),
        },
        "work_authorization": work_auth,
        "claims": claims,
        "forbidden_claims": forbidden_claims,
        "application_policy": yolo.get("permitted_tiers", ["volume"]),
    }


def _derive_claims(experience: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Derive claims from experience bullets with confidence: "inferred".

    Only bullets with measurable signals (numbers, percentages, verb outcomes)
    are included to reduce noise. These claims are truth-checked by
    qa_artifacts.py against the artifact text — if the CV omits a claim, the
    gate will flag it. That is correct behavior.
    """
    claims: list[dict[str, Any]] = []
    seen: set[str] = set()

    for exp in experience:
        bullets_data = exp.get("bullets", {})
        all_bullets: list[str] = []
        if isinstance(bullets_data, dict):
            for v in bullets_data.values():
                if isinstance(v, list):
                    all_bullets.extend(str(b) for b in v)
        elif isinstance(bullets_data, list):
            all_bullets = [str(b) for b in bullets_data]

        for bullet in all_bullets:
            text = bullet.strip()
            if not text or text in seen:
                continue
            if _MEASURABLE.search(text):
                seen.add(text)
                claims.append(
                    {
                        "claim_id": f"exp_{len(claims) + 1:03d}",
                        "text": text,
                        "confidence": "inferred",
                        "allowed_contexts": ["cv", "cover_letter"],
                    }
                )

    return claims


def _build_role_intake(role: dict[str, Any]) -> dict[str, Any]:
    ats_raw = role.get("ats_platform", "unknown").lower()
    ats_mapped = ATS_MAP.get(ats_raw, "other")

    # sponsorship_available / remote_status are new optional fields on role configs.
    # Default "unknown" means check_policy_gates.py will block via
    # skip_if_sponsorship_unknown_for_relocation — intentional fail-closed behavior.
    sponsorship_status = role.get("sponsorship_available", "unknown")
    remote_status_val = role.get("remote_status", "unknown")
    required_skills: list[str] = role.get("required_skills", [])

    return {
        "role_id": role.get("role_id", ""),
        "company": role.get("company", ""),
        "title": role.get("title", ""),
        "job_url": role.get("url", ""),
        "ats": ats_mapped,
        "remote": {
            "status": remote_status_val,
            "allowed_regions": [],
        },
        "sponsorship": {
            "status": sponsorship_status,
            "evidence": "",
        },
        "required_skills": required_skills,
    }
