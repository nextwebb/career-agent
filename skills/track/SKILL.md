---
name: track
description: View and update your job application pipeline; log statuses and add notes across all active roles
---

# track

Track and update job application status across all active roles.

## Triggers

User says: `/track`, `track my application`, `update status`, `mark as applied`, `what's my pipeline`, `show my applications`, `application status`

In Codex, invoke this skill with `$track`, the skills/plugin selector, or natural language. Slash-command examples are Claude Code aliases, not Codex built-ins.

## Arguments

```
/track                         : show full pipeline
/track <role_id>               : show detail for one role
/track <role_id> applied       : update status
/track <role_id> "note text"   : add a note
```

Valid statuses: `draft` → `applied` → `screen` → `interview` → `offer` / `rejected` / `withdrawn`

## Steps

### List pipeline

```bash
python3 src/tracker.py --list
```

Output groups applications by status with icons. Show this after every `/apply` handoff.

### Add a role to tracking

```bash
python3 src/tracker.py --add <role_id>
```

Run this automatically at the end of `/new-role`: every new role config should be tracked from the start as `draft`.

### Update status

```bash
python3 src/tracker.py --update <role_id> --status <status>
```

Run `--update <role_id> --status applied` automatically after a successful `/apply` handoff (when user confirms they clicked Submit).

### Add a note

```bash
python3 src/tracker.py --note <role_id> "Recruiter called: technical screen Thursday 3pm"
```

### When to run automatically

| Event | Action |
|---|---|
| `/new-role` completes | `--add <role_id>` (status: draft) |
| `/generate-cv` completes | no change |
| `/apply` handoff delivered | remind user to run `/track <role_id> applied` after Submit |
| User reports outcome | `--update <role_id> --status <screen|interview|offer|rejected>` |

## tracker.json

Stored at repo root. Gitignored: your application history stays local.

Format:
```json
[
  {
    "role_id": "stripe_backend",
    "company": "Stripe",
    "title": "Senior Backend Engineer",
    "status": "interview",
    "added": "2026-06-10",
    "applied": "2026-06-11",
    "last_update": "2026-06-13",
    "notes": [
      {"date": "2026-06-13", "text": "Technical screen scheduled for June 17"}
    ]
  }
]
```
