#!/usr/bin/env python3
"""
generate_application.py — career-agent PDF generator

Generates a tailored CV PDF + Cover Letter PDF for a given role,
then optionally opens the application URL in your browser.

Usage:
    python src/generate_application.py --role stripe_backend
    python src/generate_application.py --all
    python src/generate_application.py --all --open
    python src/generate_application.py --list

Setup:
    1. cp profile.example.json profile.json   # fill in your details
    2. cp roles.example/example_role.json roles/my_role.json
    3. pip install reportlab
    4. python src/generate_application.py --role my_role

Role configs:    ./roles/<role_id>.json
Profile:         ./profile.json
Output PDFs:     ./generated/
"""

import argparse

# Check for reportlab early
import importlib.util
import json
import sys
import time
import webbrowser
from pathlib import Path
from typing import Any, cast

if importlib.util.find_spec("reportlab") is None:
    print("ERROR: reportlab is not installed.")
    print("Install it with:  pip install -r requirements.txt")
    print("Or directly:      pip install reportlab")
    sys.exit(1)

SCRIPT_DIR  = Path(__file__).parent.parent   # repo root
ROLES_DIR   = SCRIPT_DIR / "roles"
OUTPUT_DIR  = SCRIPT_DIR / "generated"
PROFILE_PATH = SCRIPT_DIR / "profile.json"

sys.path.insert(0, str(Path(__file__).parent))

from cl_builder import build_cover_letter
from cv_builder import build_cv
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


def generate(profile: dict[str, Any], role_id: str, open_url: bool = False) -> tuple[str, str]:
    config = load_role(role_id)
    OUTPUT_DIR.mkdir(exist_ok=True)

    # Merge profile variant data into config for CV generation
    variant = config.get("variant", "")
    if variant and "variants" in profile:
        variant_data = profile["variants"].get(variant, {})
        # Add variant-specific fields if not in role config
        if "headline" not in config and "headline" in variant_data:
            config["headline"] = variant_data["headline"]
        if "summary" not in config and "summary" in variant_data:
            config["summary"] = variant_data["summary"]

    # Fall back to profile defaults if still missing
    config.setdefault("headline", profile.get("headline", ""))
    config.setdefault("summary", profile.get("summary", ""))

    # Convert impact_statements from dict to list if needed
    impact = profile.get("impact_statements", [])
    if isinstance(impact, dict):
        impact = list(impact.values())
    config.setdefault("impact_statements", impact)

    config.setdefault("experience", profile.get("experience", []))
    config.setdefault("skills", profile.get("skills", []))

    prefix = config["output_prefix"]
    cv_path = str(OUTPUT_DIR / f"{prefix}_CV.pdf")
    cl_path = str(OUTPUT_DIR / f"{prefix}_CoverLetter.pdf")

    print(f"\n{'─' * 60}")
    print(f"  {config['company']} — {config['title']}")
    print(f"  {config.get('location', '')}")
    print(f"{'─' * 60}")

    build_cv(profile, config, cv_path)
    build_cover_letter(profile, config, cl_path)

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
    args = parser.parse_args()

    if args.list:
        list_roles()
        return

    profile = load_profile()

    if args.all:
        role_ids = [f.stem for f in sorted(ROLES_DIR.glob("*.json"))]
        if not role_ids:
            print("No role configs found in ./roles/")
            sys.exit(1)
        results = []
        for i, role_id in enumerate(role_ids):
            cv, cl = generate(profile, role_id, open_url=args.open)
            results.append((role_id, cv, cl))
            if args.open and i < len(role_ids) - 1:
                time.sleep(1.5)
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
        cv, cl = generate(profile, args.role, open_url=args.open)
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
