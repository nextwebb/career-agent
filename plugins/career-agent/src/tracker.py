#!/usr/bin/env python3
"""
tracker.py — Application status tracker for career-agent.

Maintains tracker.json in the current workspace.
Each entry records one application: role, company, status, dates, notes.

Usage:
    python src/tracker.py --add stripe_backend
    python src/tracker.py --update stripe_backend --status interview
    python src/tracker.py --list
    python src/tracker.py --list --status applied
    python src/tracker.py --note stripe_backend "Recruiter called, technical screen Thu"
"""

from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path
from typing import Any

WORKSPACE_DIR = Path.cwd()
TRACKER_PATH = WORKSPACE_DIR / "tracker.json"
ROLES_DIR = WORKSPACE_DIR / "roles"

STATUSES = [
    "draft",
    "applied",
    "screen",
    "interview",
    "offer",
    "rejected",
    "withdrawn",
    "autonomous_submitted",
    "autonomous_ambiguous",
    "submitted_unconfirmed",
    "autonomous_failed",
]

GHOST_THRESHOLD_DAYS = 7

CLOSE_REASONS = [
    "company_closed",
    "user_withdrew",
    "ghost",
    "position_filled",
    "explicit_reject",
]


def _normalise_url(url: str) -> str:
    """Normalise a URL for matching, consistent with pre_apply_checks.check_duplicate.

    Strips trailing slashes and lowercases scheme + host; preserves path case.
    """
    url = (url or "").strip()
    if "://" in url:
        scheme, rest = url.split("://", 1)
        if "/" in rest:
            host, path = rest.split("/", 1)
            url = f"{scheme.lower()}://{host.lower()}/{path}"
        else:
            url = f"{scheme.lower()}://{rest.lower()}"
    return url.rstrip("/")


def mark_submitted_unconfirmed(
    role_id: str,
    job_url: str,
    company: str = "",
    title: str = "",
    tracker_path: Path = TRACKER_PATH,
) -> None:
    """Write a provisional tracker entry immediately before Submit.

    Step F updates the status to autonomous_submitted or autonomous_failed.
    check_duplicate() will block a re-run on this URL until the entry is
    explicitly failed/autonomous_failed.
    """
    if tracker_path.exists():
        with open(tracker_path, encoding="utf-8") as f:
            entries: list[dict] = json.load(f)
    else:
        entries = []

    today = str(date.today())

    # Upsert: if a row already exists for this role (or the same URL), update it
    # in place so update_status() later transitions THE SAME row. Appending a new
    # row would leave a stale submitted_unconfirmed duplicate that check_duplicate
    # keeps blocking even after a post-submit autonomous_failed update (issue #135).
    normalised_url = _normalise_url(job_url)
    for existing in entries:
        if existing.get("role_id") == role_id or (
            job_url and _normalise_url(existing.get("url", "")) == normalised_url
        ):
            # Claim the row for the incoming role_id. On a URL-only match where the
            # stored role_id differs, the later update_status() keys on role_id, so
            # without this reassignment it could never find and transition this row —
            # the URL would stay duplicate-blocked forever (issue #135).
            existing["role_id"] = role_id
            existing["url"] = job_url
            existing["status"] = "submitted_unconfirmed"
            existing["applied"] = today
            existing["last_update"] = today
            if company:
                existing["company"] = company
            if title:
                existing["title"] = title
            existing.setdefault("added", today)
            existing.setdefault("notes", [])
            tracker_path.parent.mkdir(parents=True, exist_ok=True)
            with open(tracker_path, "w", encoding="utf-8") as f:
                json.dump(entries, f, indent=2)
            return

    entry = {
        "role_id": role_id,
        "company": company,
        "title": title,
        "url": job_url,
        "status": "submitted_unconfirmed",
        "added": today,
        "applied": today,
        "last_update": today,
        "notes": [],
    }
    entries.append(entry)
    tracker_path.parent.mkdir(parents=True, exist_ok=True)
    with open(tracker_path, "w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2)


def load() -> list[Any]:
    if not TRACKER_PATH.exists():
        return []
    with open(TRACKER_PATH, encoding="utf-8") as f:
        return json.load(f)  # type: ignore[no-any-return]


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
        # Propagated from role config for retrospective outcome analysis
        # (issue #139). Use None (JSON null) when absent so the field is
        # always present and queryable, never silently missing.
        "ats_platform": cfg.get("ats_platform"),
        "variant": cfg.get("variant"),
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
        # ats_platform / variant read from the role config (issue #139).
        # Written unconditionally; None (JSON null) when absent from config.
        "ats_platform": meta.get("ats_platform"),
        "variant": meta.get("variant"),
        "status": "draft",
        "added": str(date.today()),
        "applied": None,
        "last_update": str(date.today()),
        "close_reason": None,
        "notes": [],
    }
    entries.append(entry)
    save(entries)
    print(f"  ✓ Added: {role_id} ({entry['company']} — {entry['title']}) [draft]")


# Statuses that represent a submission event. On transitioning a row into one
# of these, ats_platform/variant are refreshed from the CURRENT role config so
# the entry reflects the metadata actually used for the application (issue #139):
# the role JSON may be edited (ATS re-detection, CV variant change) between the
# draft `--add` and submission, and legacy drafts predating #139 carry no fields.
SUBMISSION_STATUSES = frozenset(
    {
        "applied",
        "autonomous_submitted",
        "submitted_unconfirmed",
        "autonomous_ambiguous",
        "autonomous_failed",
    }
)


def _refresh_submission_metadata(entry: dict, role_id: str) -> None:
    """Refresh ats_platform/variant on `entry` from the current role config.

    Defensive: never raises (a missing/unreadable role file or a non-role entry
    just leaves the entry untouched), and never clobbers an existing value with
    null — only a non-null role-config value overwrites the tracker field.
    """
    try:
        meta = load_role_meta(role_id)
    except Exception:
        return
    for key in ("ats_platform", "variant"):
        value = meta.get(key)
        if value is not None:
            entry[key] = value


CLOSE_REASON_STATUSES = frozenset({"rejected", "withdrawn"})


def update_status(role_id: str, status: str, close_reason: str | None = None) -> None:
    if status not in STATUSES:
        print(f"  Invalid status '{status}'. Choose: {', '.join(STATUSES)}")
        return
    if close_reason is not None and close_reason not in CLOSE_REASONS:
        print(f"  Invalid close_reason '{close_reason}'. Choose: {', '.join(CLOSE_REASONS)}")
        return
    if close_reason is not None and status not in CLOSE_REASON_STATUSES:
        print(
            f"  Warning: --close-reason is normally set on withdrawn/rejected, "
            f"not '{status}'. Writing anyway."
        )
    entries = load()
    for e in entries:
        if e["role_id"] == role_id:
            old = e["status"]
            e["status"] = status
            e["last_update"] = str(date.today())
            if status == "applied" and not e["applied"]:
                e["applied"] = str(date.today())
            if status in SUBMISSION_STATUSES:
                _refresh_submission_metadata(e, role_id)
            if close_reason is not None:
                e["close_reason"] = close_reason
            elif status not in ("rejected", "withdrawn"):
                e["close_reason"] = None
            save(entries)
            reason_str = f" [close_reason: {close_reason}]" if close_reason else ""
            print(f"  ✓ {role_id}: {old} → {status}{reason_str}")
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
    "autonomous_submitted": "🤖",
    "autonomous_ambiguous": "⚠️ ",
    "autonomous_failed": "🚫",
}


def _ghost_risk_days(entry: dict) -> int | None:
    """Return days since last_update if the entry is ghost-risk, else None.

    Ghost risk: status == "applied" and last_update is >= GHOST_THRESHOLD_DAYS ago.
    Returns the number of days (int) when the condition is met, None otherwise.
    """
    if entry.get("status") != "applied":
        return None
    last_update_str = entry.get("last_update")
    if not last_update_str:
        return None
    try:
        days = (date.today() - date.fromisoformat(last_update_str)).days
    except ValueError:
        return None
    return days if days >= GHOST_THRESHOLD_DAYS else None


def list_entries(filter_status: str | None = None, ghost_only: bool = False) -> None:
    entries = load()
    if not entries:
        print("  No applications tracked yet. Run --add <role_id>")
        return

    if filter_status:
        entries = [e for e in entries if e["status"] == filter_status]

    if ghost_only:
        entries = [e for e in entries if _ghost_risk_days(e) is not None]

    # Group by status
    order = [
        "offer",
        "interview",
        "screen",
        "applied",
        "autonomous_submitted",
        "autonomous_ambiguous",
        "autonomous_failed",
        "draft",
        "rejected",
        "withdrawn",
    ]
    grouped: dict[str, list[Any]] = {s: [] for s in order}
    for e in entries:
        grouped.get(e["status"], grouped["draft"]).append(e)

    total = len(entries)
    inactive = {"rejected", "withdrawn", "autonomous_failed"}
    active = sum(1 for e in entries if e["status"] not in inactive)
    print(f"\n  Applications: {total} total, {active} active\n")

    for status in order:
        group = grouped[status]
        if not group:
            continue
        icon = STATUS_ICONS.get(status, "·")
        print(f"  {icon} {status.upper()} ({len(group)})")
        for e in group:
            applied_str = f"  applied {e['applied']}" if e.get("applied") else ""
            ghost_days = _ghost_risk_days(e)
            ghost_str = f"  ⚠ ghost risk ({ghost_days}d)" if ghost_days is not None else ""
            close_reason = e.get("close_reason")
            reason_str = f" [{close_reason}]" if close_reason else ""
            print(
                f"     {e['role_id']:35s} {e['company']} — {e['title']}{applied_str}{ghost_str}{reason_str}"
            )
            if e.get("notes"):
                last = e["notes"][-1]
                print(f"     {'':35s} └ {last['date']}: {last['text']}")
        print()


def main():
    parser = argparse.ArgumentParser(description="Track job application status.")
    parser.add_argument("--add", metavar="ROLE_ID", help="Add a role to the tracker")
    parser.add_argument("--update", metavar="ROLE_ID", help="Update status for a role")
    parser.add_argument("--status", metavar="STATUS", help=f"Status: {', '.join(STATUSES)}")
    parser.add_argument(
        "--close-reason",
        metavar="REASON",
        dest="close_reason",
        choices=CLOSE_REASONS,
        help=f"Close reason (use with --update --status withdrawn/rejected): {', '.join(CLOSE_REASONS)}",
    )
    parser.add_argument("--note", metavar="ROLE_ID", help="Add a note to a role")
    parser.add_argument("--list", action="store_true", help="List all tracked applications")
    parser.add_argument(
        "--ghost",
        action="store_true",
        help="With --list: show only applied entries with ghost risk (>= 7 days without update)",
    )
    parser.add_argument("text", nargs="?", help="Note text (used with --note)")
    args = parser.parse_args()

    if args.add:
        add(args.add)
    elif args.update:
        if not args.status:
            print(f"  --update requires --status. Options: {', '.join(STATUSES)}")
        else:
            update_status(args.update, args.status, close_reason=args.close_reason)
    elif args.note:
        if not args.text:
            print("  --note requires note text as final argument")
        else:
            add_note(args.note, args.text)
    elif args.list:
        list_entries(filter_status=args.status, ghost_only=args.ghost)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
