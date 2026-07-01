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

Resolve `<career_agent_root>` as the installed package or plugin root that contains `src/tracker.py`. If running from a repo checkout and `src/tracker.py` exists in the current directory, the current directory is `<career_agent_root>`.

Do not assume the user's working directory is the package root. The script path comes from `<career_agent_root>`, while `tracker.json` and `roles/` are read and written in the user's current workspace.

### List pipeline

```bash
python3 "<career_agent_root>/src/tracker.py" --list
```

Output groups applications by status with icons. Show this after every `/apply` handoff.

#### Ghost risk annotation

Applied entries with no update for 7 or more days are annotated inline:

```
📤 APPLIED (3)
   stripe_backend                      Stripe — Backend Engineer  applied 2026-06-10  ⚠ ghost risk (21d)
   acme_sre                            Acme — SRE                 applied 2026-06-18
```

The `⚠ ghost risk (Nd)` suffix shows the number of days since the last update. With a median rejection turnaround of 1 day, entries silent for 7+ days are very likely already decided but not yet logged.

**Action:** mark ghost-risk entries as `rejected` with a note explaining the silence:

```bash
python3 "<career_agent_root>/src/tracker.py" --update stripe_backend --status rejected
python3 "<career_agent_root>/src/tracker.py" --note stripe_backend "No response after 21d — marking rejected"
```

#### Filter to ghost-risk entries only

```bash
python3 "<career_agent_root>/src/tracker.py" --list --ghost
```

Shows only `applied` entries that meet the ghost-risk threshold (>= 7 days without update). Useful for pipeline cleanup: run periodically to surface stale applications and close them out.

### Add a role to tracking

```bash
python3 "<career_agent_root>/src/tracker.py" --add <role_id>
```

Run this automatically at the end of `/new-role`: every new role config should be tracked from the start as `draft`.

### Update status

```bash
python3 "<career_agent_root>/src/tracker.py" --update <role_id> --status <status>
```

Run `--update <role_id> --status applied` automatically after the user confirms they clicked Submit.

### Add a note

```bash
python3 "<career_agent_root>/src/tracker.py" --note <role_id> "Recruiter called: technical screen Thursday 3pm"
```

### When to run automatically

| Event | Action |
|---|---|
| `/new-role` completes | `--add <role_id>` (status: draft) |
| `/generate-cv` completes | no change |
| User confirms Submit after `/apply` handoff | `--update <role_id> --status applied` |
| User reports outcome | `--update <role_id> --status <screen|interview|offer|rejected>` |

## tracker.json

Stored in the current workspace. Gitignored in repo checkouts: your application history stays local.

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
