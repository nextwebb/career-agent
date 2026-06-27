#!/usr/bin/env python3
"""
generate_application.py — career-agent PDF generator

Generates a tailored CV PDF + Cover Letter PDF for a given role,
then optionally opens the application URL in your browser.

Usage:
    python src/generate_application.py --role stripe_backend
    python src/generate_application.py --role stripe_backend --dry-run
    python src/generate_application.py --all
    python src/generate_application.py --all --open
    python src/generate_application.py --list

Setup:
    1. cp profile.example.json profile.json   # fill in your details
    2. cp roles.example/example_role.json roles/my_role.json
    3. pip install -r requirements.txt
    4. python src/generate_application.py --role my_role

Role configs:    ./roles/<role_id>.json in the current workspace
Profile:         ./profile.json in the current workspace
Output PDFs:     ./generated/ in the current workspace
"""

import argparse
import importlib.util
import json
import sys
import time
import webbrowser
from copy import deepcopy
from pathlib import Path
from typing import Any, cast

HAS_REPORTLAB = importlib.util.find_spec("reportlab") is not None

# Reportlab is only required for actual PDF generation. --dry-run and --list
# never reach generate(), so we defer the missing-dependency error to generate()
# itself rather than gating the module load on a fragile sys.argv inspection.

WORKSPACE_DIR = Path.cwd()
ROLES_DIR = WORKSPACE_DIR / "roles"
OUTPUT_DIR = WORKSPACE_DIR / "generated"
PROFILE_PATH = WORKSPACE_DIR / "profile.json"

sys.path.insert(0, str(Path(__file__).parent))

from quality_gates import QualityGateError, format_quality_report, run_quality_gates
from validation import (
    ValidationError,
    validate_and_report,
    validate_profile,
    validate_role_config,
)


def load_profile() -> dict[str, Any]:
    if not PROFILE_PATH.exists():
        print("ERROR: profile.json not found.")
        print("Run:  cp profile.example.json profile.json")
        print("Then fill in your personal details.")
        sys.exit(1)

    try:
        with open(PROFILE_PATH, encoding="utf-8") as f:
            profile = cast(dict[str, Any], json.load(f))
    except json.JSONDecodeError as e:
        print("ERROR: Invalid JSON in profile.json")
        print(f"  {e}")
        print("\nCheck for:")
        print("  - Missing commas between fields")
        print("  - Unmatched brackets or braces")
        print("  - Trailing commas before closing braces")
        sys.exit(1)

    # Validate profile schema
    try:
        validate_and_report(profile, validate_profile, "profile", str(PROFILE_PATH))
    except ValidationError as e:
        print(f"ERROR: {e}")
        sys.exit(1)

    # Non-fatal nudge: relocation is ATS-only metadata, openness is the CV
    # banner. Only warn when the two fields are byte-for-byte identical after
    # whitespace/case normalisation — substring heuristics fire on the
    # documented profile.example.json and on every reasonable English
    # phrasing that happens to mention "relocation", which is the opposite
    # of helpful.
    def _normalize(value: Any) -> str:
        return " ".join(str(value or "").strip().lower().split())

    relocation_norm = _normalize(profile.get("relocation"))
    openness_norm = _normalize(profile.get("openness"))
    if relocation_norm and openness_norm and relocation_norm == openness_norm:
        print(
            "WARNING: profile.relocation and profile.openness contain identical text. "
            "openness is the CV banner; relocation is ATS form metadata. "
            "Consider deduplicating so the two fields have distinct purposes.",
            file=sys.stderr,
        )

    return profile


def load_role(role_id: str) -> dict[str, Any]:
    # Ensure roles directory exists
    ROLES_DIR.mkdir(exist_ok=True)

    config_path = ROLES_DIR / f"{role_id}.json"
    if not config_path.exists():
        available = [f.stem for f in sorted(ROLES_DIR.glob("*.json"))] if ROLES_DIR.exists() else []
        print(f"ERROR: No config found for role '{role_id}'")
        if available:
            print(f"Available roles: {', '.join(available)}")
        else:
            print("No role configs found. Add one to roles/")
            print("Example: cp roles.example/example_role.json roles/my_role.json")
        sys.exit(1)

    try:
        with open(config_path, encoding="utf-8") as f:
            config = cast(dict[str, Any], json.load(f))
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON in {config_path}")
        print(f"  {e}")
        print("\nCheck for:")
        print("  - Missing commas between fields")
        print("  - Unmatched brackets or braces")
        print("  - Trailing commas before closing braces")
        sys.exit(1)

    # Validate role config schema
    try:
        validate_and_report(config, validate_role_config, "role config", str(config_path))
    except ValidationError as e:
        print(f"ERROR: {e}")
        sys.exit(1)

    return config


def _resolve_impact_statements(profile: dict[str, Any], variant: str) -> list[dict[str, Any]]:
    impact = profile.get("impact_statements", [])
    if not isinstance(impact, dict):
        return list(impact) if isinstance(impact, list) else []

    ordered_keys = []
    variant_data = profile.get("variants", {}).get(variant, {})
    if isinstance(variant_data, dict):
        impact_order = variant_data.get("impact_order", [])
        if isinstance(impact_order, list):
            ordered_keys = [key for key in impact_order if key in impact]

    remaining_keys = [key for key in impact if key not in ordered_keys]
    return [impact[key] for key in [*ordered_keys, *remaining_keys]]


def _select_bullets(experience: dict[str, Any], variant: str, override: Any = None) -> list[str]:
    if isinstance(override, dict) and isinstance(override.get("bullets"), list):
        return [str(bullet) for bullet in override["bullets"] if str(bullet).strip()]

    bullets = experience.get("bullets", [])
    if isinstance(bullets, list):
        return [str(bullet) for bullet in bullets if str(bullet).strip()]

    if not isinstance(bullets, dict):
        return []

    selected = bullets.get(variant) or bullets.get("default") or []
    if not isinstance(selected, list):
        return []
    return [str(bullet) for bullet in selected if str(bullet).strip()]


def _resolve_experience(profile: dict[str, Any], config: dict[str, Any]) -> list[dict[str, Any]]:
    variant = str(config.get("variant", ""))
    overrides = config.get("experience_overrides", {})
    resolved = []

    for experience in profile.get("experience", []):
        if not isinstance(experience, dict):
            continue

        experience_id = experience.get("id", "")
        override = overrides.get(experience_id) if isinstance(overrides, dict) else None
        bullets = _select_bullets(experience, variant, override)
        resolved.append(
            {
                "title": experience.get("title", ""),
                "company_line": experience.get("company_line", experience.get("company", "")),
                "client_line": experience.get("client_line", ""),
                "bullets": bullets,
            }
        )

    return resolved


def prepare_generation_config(
    profile: dict[str, Any],
    config: dict[str, Any],
    create_output_dir: bool = True,
) -> dict[str, Any]:
    """Resolve profile defaults, selected variant content, and role overrides."""

    prepared = deepcopy(config)
    variant = str(prepared.get("variant", ""))

    if create_output_dir:
        OUTPUT_DIR.mkdir(exist_ok=True)

    # Merge profile variant data into config for CV generation
    if variant and "variants" in profile:
        variant_data = profile["variants"].get(variant, {})
        # Add variant-specific fields if not in role config
        if "headline" not in prepared and "headline" in variant_data:
            prepared["headline"] = variant_data["headline"]
        if "summary" not in prepared and "summary" in variant_data:
            prepared["summary"] = variant_data["summary"]

    # Fall back to profile defaults if still missing
    prepared.setdefault("headline", profile.get("headline", ""))
    prepared.setdefault("summary", profile.get("summary", ""))
    # openness resolution (only when role config omits the key):
    # - Profile explicitly sets openness (even to "") → honour it, including
    #   the empty-string case which suppresses the CV banner intentionally.
    # - Profile has no openness key → fall back to relocation for migration
    #   compat (pre-#130 profiles stored availability there).
    if "openness" not in prepared:
        if "openness" in profile:
            prepared["openness"] = profile["openness"]
        else:
            prepared["openness"] = profile.get("relocation") or ""

    prepared.setdefault("impact_statements", _resolve_impact_statements(profile, variant))
    prepared.setdefault("experience", _resolve_experience(profile, prepared))
    prepared.setdefault("skills", profile.get("skills", []))

    # Role config may set additional_experience: [] to suppress the
    # "Additional Relevant Experience" section for a specific submission.
    # setdefault preserves an explicit empty list, so the per-role suppress
    # wins over a non-empty profile default.
    prepared.setdefault("additional_experience", profile.get("additional_experience", []))

    return prepared


def _present(value: Any) -> str:
    """Return a redacted presence marker for dry-run output."""

    if isinstance(value, dict):
        return "present" if any(str(item).strip() for item in value.values()) else "missing"
    if isinstance(value, list):
        return "present" if any(str(item).strip() for item in value) else "missing"
    return "present" if str(value or "").strip() else "missing"


def _profile_name_parts(profile: dict[str, Any]) -> tuple[Any, Any]:
    name = profile.get("name", {})
    if isinstance(name, dict):
        return name.get("first", ""), name.get("last", "")
    parts = str(name).split()
    return (parts[0] if parts else "", parts[-1] if len(parts) > 1 else "")


def _file_status(path: Path) -> str:
    if not path.exists():
        return "missing"
    return f"exists, {path.stat().st_size} bytes"


def _package_version() -> str:
    root = Path(__file__).resolve().parent.parent
    candidates = [
        root / "package.json",
        root / "plugin.json",
        root / ".codex-plugin" / "plugin.json",
    ]
    for path in candidates:
        if not path.exists():
            continue
        try:
            version = json.loads(path.read_text(encoding="utf-8")).get("version")
        except json.JSONDecodeError:
            continue
        if version:
            return str(version)
    return "unknown"


def print_apply_dry_run(profile: dict[str, Any], role_id: str) -> None:
    """Print a redacted apply plan without creating PDFs or opening a browser."""

    # Redact tracebacks: an unhandled exception here would surface absolute
    # role/profile paths from the user's home, defeating the no-raw-values contract.
    try:
        config = prepare_generation_config(profile, load_role(role_id), create_output_dir=False)
    except Exception as error:
        print(f"\nERROR: Could not prepare dry-run plan for role '{role_id}'.")
        print(f"  Cause: {type(error).__name__}")
        print("  Fix the role config or profile and re-run --dry-run.")
        sys.exit(2)
    prefix = config["output_prefix"]
    cv_path = OUTPUT_DIR / f"{prefix}_CV.pdf"
    cl_path = OUTPUT_DIR / f"{prefix}_CoverLetter.pdf"
    first_name, last_name = _profile_name_parts(profile)
    links = profile.get("links", {})
    custom_answers = config.get("custom_answers", {})
    apply_skill_path = Path(__file__).resolve().parent.parent / "skills" / "apply" / "SKILL.md"
    # Surface plugin-vs-repo drift in the preflight without leaking absolute paths.
    # If __file__ is under plugins/career-agent/, label it so users can spot a
    # stale installed plugin copy diverging from repo HEAD.
    script_resolved = Path(__file__).resolve()
    is_plugin_copy = "plugins/career-agent" in script_resolved.as_posix()
    root_marker = (
        "<career_agent_root>/plugins/career-agent" if is_plugin_copy else "<career_agent_root>"
    )

    safe_fields = [
        ("First name", _present(first_name)),
        ("Last name", _present(last_name)),
        ("Email", _present(profile.get("email"))),
        ("Phone", _present(profile.get("phone"))),
        ("Location / City", _present(profile.get("location"))),
        ("LinkedIn URL", _present(links.get("linkedin") if isinstance(links, dict) else "")),
        ("GitHub URL", _present(links.get("github") if isinstance(links, dict) else "")),
        ("Portfolio / website", _present(links.get("website") if isinstance(links, dict) else "")),
        ("Hear-about-us answer", _present(custom_answers.get("hear_about_us"))),
        ("Non-sensitive long-answer drafts", _present(custom_answers.get("why_company"))),
    ]
    handoff_fields = [
        "Browser/tool setup failure",
        "Unsupported ATS or login wall",
        "Right-to-work or work authorization",
        "Visa sponsorship",
        "US-person/tax status",
        "Salary or compensation when phrased as an attestation",
        "Privacy notice, GDPR, data retention, or consent checkboxes",
        "Demographic, EEO, disability, veteran, or self-identification fields",
        "CAPTCHA",
        "Submit or final confirmation",
    ]

    print(f"\n{'─' * 60}")
    print(f"  Apply dry run: {config['company']} — {config['title']}")
    print(f"{'─' * 60}")
    print(f"Role ID: {role_id}")
    print(f"Target URL: {config.get('url', '')}")
    print(f"ATS platform: {config.get('ats_platform', 'unknown')}")
    print(f"Package version: {_package_version()}")
    print(f"Generator path: {root_marker}/src/generate_application.py")
    print(
        "Apply skill path: "
        f"{root_marker + '/skills/apply/SKILL.md' if apply_skill_path.exists() else 'not found'}"
    )
    print("\nFiles:")
    print(f"  CV: generated/<redacted>_CV.pdf ({_file_status(cv_path)})")
    print(f"  Cover letter: generated/<redacted>_CoverLetter.pdf ({_file_status(cl_path)})")
    print("\nPlanned safe fields (values redacted):")
    for label, status in safe_fields:
        print(f"  - {label}: {status}")
    print("\nPlanned upload strategy:")
    print("  - Prefer native browser file upload when the selected browser surface supports it.")
    print("  - For Chrome-extension-only paths, use localhost fetch or chunked storage.")
    print("  - Do not send one large inline base64 string through Runtime.evaluate.")
    print("  - Re-query file inputs after each upload and verify visible filenames.")
    print("\nHandoff fields / stop boundaries:")
    for label in handoff_fields:
        print(f"  - {label}")
    print("\nDry run only: no PDFs generated, browser opened, files uploaded, or tracker updated.")


def generate(
    profile: dict[str, Any],
    role_id: str,
    open_url: bool = False,
    quality_gates: bool = True,
) -> tuple[str, str]:
    if not HAS_REPORTLAB:
        print("ERROR: reportlab is not installed.")
        print("Install it with:  pip install -r requirements.txt")
        print("Or directly:      pip install reportlab")
        sys.exit(1)

    from cl_builder import build_cover_letter
    from cv_builder import build_cv

    config = prepare_generation_config(profile, load_role(role_id))
    prefix = config["output_prefix"]
    cv_path = str(OUTPUT_DIR / f"{prefix}_CV.pdf")
    cl_path = str(OUTPUT_DIR / f"{prefix}_CoverLetter.pdf")

    print(f"\n{'─' * 60}")
    print(f"  {config['company']} — {config['title']}")
    print(f"  {config.get('location', '')}")
    print(f"{'─' * 60}")

    build_cv(profile, config, cv_path)
    build_cover_letter(profile, config, cl_path)

    if quality_gates:
        report = run_quality_gates(profile, config, cv_path, cl_path)
        print(format_quality_report(report))
        if report.has_failures:
            raise QualityGateError(
                "Generated PDFs failed deterministic quality gates. "
                "Fix profile.json or the role config, then regenerate. "
                "Use --no-quality-gates only for diagnostics."
            )

    url = config.get("url", "")
    if open_url and url:
        print(f"  ↗  Opening: {url}")
        webbrowser.open(url)

    return cv_path, cl_path


def list_roles():
    # Ensure roles directory exists
    ROLES_DIR.mkdir(exist_ok=True)

    roles = sorted(ROLES_DIR.glob("*.json"))
    if not roles:
        print("No role configs found in ./roles/")
        print("Add one with: cp roles.example/example_role.json roles/my_role.json")
        return
    print("\nAvailable roles:")
    for r in roles:
        try:
            with open(r) as f:
                cfg = json.load(f)
            print(f"  {r.stem:35s}  {cfg.get('company', '')} — {cfg.get('title', '')}")
        except Exception:
            print(f"  {r.stem:35s}  (could not read config)")


def main():
    parser = argparse.ArgumentParser(
        description="Generate tailored CV + Cover Letter PDFs per role.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--role", help="Role ID to generate (e.g. stripe_backend)")
    parser.add_argument("--all", action="store_true", help="Generate all roles in roles/")
    parser.add_argument("--list", action="store_true", help="List available role configs")
    parser.add_argument(
        "--open", action="store_true", help="Open each job URL in your browser after generating"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print a redacted apply preflight plan without generating PDFs or opening a browser",
    )
    parser.add_argument(
        "--no-quality-gates",
        action="store_true",
        help="Generate PDFs without deterministic quality gates (diagnostics only)",
    )
    args = parser.parse_args()

    if args.list:
        list_roles()
        return

    if args.dry_run and args.open:
        parser.error("--dry-run cannot be combined with --open")

    profile = load_profile()

    if args.all:
        role_ids = [f.stem for f in sorted(ROLES_DIR.glob("*.json"))]
        if not role_ids:
            print("No role configs found in ./roles/")
            sys.exit(1)
        if args.dry_run:
            for role_id in role_ids:
                print_apply_dry_run(profile, role_id)
            return
        results = []
        try:
            for i, role_id in enumerate(role_ids):
                cv, cl = generate(
                    profile,
                    role_id,
                    open_url=args.open,
                    quality_gates=not args.no_quality_gates,
                )
                results.append((role_id, cv, cl))
                if args.open and i < len(role_ids) - 1:
                    time.sleep(1.5)
        except QualityGateError as e:
            print(f"\nERROR: {e}")
            sys.exit(2)
        print(f"\n{'=' * 60}")
        print(f"  Generated {len(results)} application(s) → {OUTPUT_DIR}/")
        print(f"{'=' * 60}")
        for role_id, cv, cl in results:
            cfg = load_role(role_id)
            print(f"\n  {cfg['company']} — {cfg['title']}")
            print(f"    CV:  {Path(cv).name}")
            print(f"    CL:  {Path(cl).name}")
            if cfg.get("url"):
                print(f"    URL: {cfg['url']}")
        return

    if args.role:
        if args.dry_run:
            print_apply_dry_run(profile, args.role)
            return
        try:
            cv, cl = generate(
                profile,
                args.role,
                open_url=args.open,
                quality_gates=not args.no_quality_gates,
            )
        except QualityGateError as e:
            print(f"\nERROR: {e}")
            sys.exit(2)
        cfg = load_role(args.role)
        print("\n  Done.")
        print(f"  CV:  {Path(cv).name}")
        print(f"  CL:  {Path(cl).name}")
        if args.open and cfg.get("url"):
            print("  Application page opened → upload the two PDFs above.")
        return

    parser.print_help()


if __name__ == "__main__":
    main()
