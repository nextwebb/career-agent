# AGENTS.md

## Repository expectations

- This repository is `career-agent`, a local-first job application workflow for Claude Code and Codex.
- Keep user career data local. Never commit `profile.json`, `roles/`, `tracker.json`, `generated/`, or files containing personal application data.
- Preserve the product philosophy: keep the user workflow lightweight and intuitive, put deterministic quality gates behind agent actions, and make only evidence-backed claims.
- Treat generated CVs, cover letters, role configs, sourced roles, and ATS-filled pages as review-ready drafts. Do not claim recruiter outcomes, ATS acceptance, or "world-class" quality without external evidence.
- Generated application claims must be traceable to `profile.json`, the role config, or explicit user-provided facts. If evidence is missing, omit the claim or flag it for review.
- Follow `ENGINEERING_PRINCIPLES.md` for Python style, testing, commit format, and review expectations.
- Prefer focused changes tied to a linked GitHub issue. Avoid unrelated refactors.
- Keep PRs small: change only what the ticket requires, preserve existing architecture, and avoid style or whitespace churn outside the touched behavior.
- Before editing schema-shaped data, confirm the relevant validators, examples, fixtures, or call sites instead of guessing payload shapes.
- In PR or final summaries, separate confirmed facts, inferences, unknowns, and assumptions when evidence quality matters.
- Use repo-relative commands in docs and skills unless a host-specific variable is explicitly required.
- When changing skill behavior, update the relevant `skills/*/SKILL.md` file and add or adjust smoke/static checks.
- Treat browser automation as high-risk. The agent must stop before Submit, irreversible confirmations, credentials, legal attestations, consent fields, EEO/voluntary self-identification, CAPTCHA, or ambiguous fields.

## Verification

- Run `python3 -m pytest tests/smoke_test.py -q` after structure, installer, manifest, or skill changes.
- Run `npm run check:package` after package metadata or npm allowlist changes.
- Run `npm run check:codeowners` after review-routing changes.
- Run `bash tests/integration_test.sh` when PDF generation behavior changes.
