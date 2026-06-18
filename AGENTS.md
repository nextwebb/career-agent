# AGENTS.md

## Repository expectations

- This repository is `career-agent`, a local-first job application workflow for Claude Code and Codex.
- Keep user career data local. Never commit `profile.json`, `roles/`, `tracker.json`, `generated/`, or files containing personal application data.
- Follow `ENGINEERING_PRINCIPLES.md` for Python style, testing, commit format, and review expectations.
- Prefer focused changes tied to a linked GitHub issue. Avoid unrelated refactors.
- Use repo-relative commands in docs and skills unless a host-specific variable is explicitly required.
- When changing skill behavior, update the relevant `skills/*/SKILL.md` file and add or adjust smoke/static checks.
- Treat browser automation as high-risk. The agent must stop before Submit, irreversible confirmations, credentials, legal attestations, consent fields, EEO/voluntary self-identification, CAPTCHA, or ambiguous fields.

## Verification

- Run `python3 -m pytest tests/smoke_test.py -q` after structure, installer, manifest, or skill changes.
- Run `npm run check:package` after package metadata or npm allowlist changes.
- Run `npm run check:codeowners` after review-routing changes.
- Run `bash tests/integration_test.sh` when PDF generation behavior changes.
