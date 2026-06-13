#!/usr/bin/env python3
"""
tracker.py — Application status tracker for career-agent.

Maintains tracker.json in the repo root (gitignored).
Each entry records one application: role, company, status, dates, notes.

Usage:
    python src/tracker.py --add stripe_backend
    python src/tracker.py --update stripe_backend --status interview
    python src/tracker.py --list
    python src/tracker.py --list --status applied
    python src/tracker.py --note stripe_backend "Recruiter called, technical screen Thu"
"""

import argparse
import json
from datetime import date
from pathlib import Path

TRACKER_PATH = Path(__file__).parent.parent / "tracker.json"
ROLES_DIR = Path(__file__).parent.parent / "roles"

STATUSES = ["draft", "applied", "screen", "interview", "offer", "rejected", "withdrawn"]


def load() -> list:
    if not TRACKER_PATH.exists():
        return []
    with open(TRACKER_PATH, encoding="utf-8") as f:
        return json.load(f)


def save(entries: list) -> None:
    with open(TRACKER_PATH, "w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2)


def load_role_meta(role_id: str) -> dict:
    path = ROLES_DIR / f"{role_id}.json"
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        cfg = json.load(f)
    return {
        "company": cfg.get("company", ""),
        "title": cfg.get("title", ""),
        "url": cfg.get("url", ""),
    }


def add(role_id: str) -> None:
    entries = load()
    if any(e["role_id"] == role_id for e in entries):
        print(f"  Already tracking: {role_id}")
        return
    meta = load_role_meta(role_id)
    entry = {
        "role_id": role_id,
        "company": meta.get("company", ""),
        "title": meta.get("title", ""),
        "url": meta.get("url", ""),
        "status": "draft",
        "added": str(date.today()),
        "applied": None,
        "last_update": str(date.today()),
        "notes": [],
    }
    entries.append(entry)
    save(entries)
    print(f"  ✓ Added: {role_id} ({entry['company']} — {entry['title']}) [draft]")


def update_status(role_id: str, status: str) -> None:
    if status not in STATUSES:
        print(f"  Invalid status '{status}'. Choose: {', '.join(STATUSES)}")
        return
    entries = load()
    for e in entries:
        if e["role_id"] == role_id:
            old = e["status"]
            e["status"] = status
            e["last_update"] = str(date.today())
            if status == "applied" and not e["applied"]:
                e["applied"] = str(date.today())
            save(entries)
            print(f"  ✓ {role_id}: {old} → {status}")
            return
    print(f"  Not found: {role_id}. Run --add first.")


def add_note(role_id: str, note: str) -> None:
    entries = load()
    for e in entries:
        if e["role_id"] == role_id:
            e["notes"].append({"date": str(date.today()), "text": note})
            e["last_update"] = str(date.today())
            save(entries)
            print(f"  ✓ Note added to {role_id}")
            return
    print(f"  Not found: {role_id}. Run --add first.")


STATUS_ICONS = {
    "draft": "📝",
    "applied": "📤",
    "screen": "📞",
    "interview": "🎯",
    "offer": "🎉",
    "rejected": "❌",
    "withdrawn": "↩️ ",
}


def list_entries(filter_status: str = None) -> None:
    entries = load()
    if not entries:
        print("  No applications tracked yet. Run --add <role_id>")
        return

    if filter_status:
        entries = [e for e in entries if e["status"] == filter_status]

    # Group by status
    order = ["offer", "interview", "screen", "applied", "draft", "rejected", "withdrawn"]
    grouped = {s: [] for s in order}
    for e in entries:
        grouped.get(e["status"], grouped["draft"]).append(e)

    total = len(entries)
    active = sum(1 for e in entries if e["status"] not in ("rejected", "withdrawn"))
    print(f"\n  Applications: {total} total, {active} active\n")

    for status in order:
        group = grouped[status]
        if not group:
            continue
        icon = STATUS_ICONS.get(status, "·")
        print(f"  {icon} {status.upper()} ({len(group)})")
        for e in group:
            applied_str = f"  applied {e['applied']}" if e.get("applied") else ""
            print(f"     {e['role_id']:35s} {e['company']} — {e['title']}{applied_str}")
            if e.get("notes"):
                last = e["notes"][-1]
                print(f"     {'':35s} └ {last['date']}: {last['text']}")
        print()


def main():
    parser = argparse.ArgumentParser(description="Track job application status.")
    parser.add_argument("--add", metavar="ROLE_ID", help="Add a role to the tracker")
    parser.add_argument("--update", metavar="ROLE_ID", help="Update status for a role")
    parser.add_argument("--status", metavar="STATUS", help=f"Status: {', '.join(STATUSES)}")
    parser.add_argument("--note", metavar="ROLE_ID", help="Add a note to a role")
    parser.add_argument("--list", action="store_true", help="List all tracked applications")
    parser.add_argument("text", nargs="?", help="Note text (used with --note)")
    args = parser.parse_args()

    if args.add:
        add(args.add)
    elif args.update:
        if not args.status:
            print(f"  --update requires --status. Options: {', '.join(STATUSES)}")
        else:
            update_status(args.update, args.status)
    elif args.note:
        if not args.text:
            print("  --note requires note text as final argument")
        else:
            add_note(args.note, args.text)
    elif args.list:
        list_entries(filter_status=args.status)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
