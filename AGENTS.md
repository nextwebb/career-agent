# AGENTS.md

## Read order for LLM and coding agents

If you are an LLM or coding agent working in this repo, read these files in this order before writing code. Do not skip.

1. **AGENTS.md** (this file) — repository expectations and doc map
2. **ENGINEERING_PRINCIPLES.md** — Python style, type hints, testing, commit format, security, deps
3. **CLAUDE.md** — project overview, skills, ATS platforms, human-in-the-loop rules, PDF spec
4. **docs/validation-policy.md** — required CI gates and validation policy
5. Domain-specific docs when the surface applies:
   - `skills/<name>/SKILL.md` for the skill you are touching
   - `docs/source-methodology.md` if working on `/source`
   - `docs/apply-codex-chrome-verification.md` if working on browser automation
   - `docs/review-routing.md` if changing CODEOWNERS or review flow

For humans contributing PRs, start with `CONTRIBUTING.md` instead.

## Docs map

| File | Scope | When to read |
|---|---|---|
| `AGENTS.md` | Agent entry point, doc map, high-level expectations | Always first |
| `ENGINEERING_PRINCIPLES.md` | Coding standards (style, types, tests, commits, security) | Before writing Python |
| `CLAUDE.md` | Project purpose, skills, HITL rules, PDF spec | Before touching the workflow, `/apply`, or PDF layer |
| `CONTRIBUTING.md` | Human contributor setup + local checks | Human PRs |
| `SECURITY.md` | Vulnerability reporting | Never inline — direct users here |
| `docs/validation-policy.md` | CI gates, docs-versioning, external-app-suite policy | Before making claims about validation status |
| `docs/review-routing.md` | CODEOWNERS + review flow | When changing `.github/CODEOWNERS` |
| `docs/source-methodology.md` | `/source` evidence and ranking rules | When editing `skills/source/` |
| `docs/apply-codex-chrome-verification.md` | Codex Chrome verification matrix per ATS | When editing `skills/apply/` or verifying a new ATS |
| `README.md` | Public-facing overview | Do not rely on it for engineering rules |

## Repository expectations

- This repository is `career-agent`, a local-first job application workflow for Claude Code and Codex.
- Keep user career data local. Never commit `profile.json`, `roles/`, `tracker.json`, `generated/`, or files containing personal application data.
- Preserve the product philosophy: keep the user workflow lightweight and intuitive, put deterministic quality gates behind agent actions, and make only evidence-backed claims.
- Treat generated CVs, cover letters, role configs, sourced roles, and ATS-filled pages as review-ready drafts. Do not claim recruiter outcomes, ATS acceptance, or "world-class" quality without external evidence.
- Generated application claims must be traceable to `profile.json`, the role config, or explicit user-provided facts. If evidence is missing, omit the claim or flag it for review.
- Follow `ENGINEERING_PRINCIPLES.md` for Python style, testing, commit format, and review expectations.
- Prefer small, focused changes tied to a linked GitHub issue. Preserve existing architecture and avoid unrelated refactors, style churn, or whitespace churn.
- Use branch names that mirror Conventional Commit types, such as `docs/release-safe-pr-titles` or `fix/pdf-link-validation`; do not use coding-agent prefixes such as `codex/`, `claude/`, or `agent/`.
- Before editing schema-shaped data, confirm the relevant validators, examples, fixtures, or call sites instead of guessing payload shapes.
- In PR or final summaries, separate confirmed facts, inferences, unknowns, and assumptions when evidence quality matters.
- Use repo-relative commands in docs and skills unless a host-specific variable is explicitly required.
- When changing skill behavior, update the relevant `skills/*/SKILL.md` file and add or adjust smoke/static checks.
- Treat browser automation as high-risk. The agent must stop before Submit, irreversible confirmations, credentials, legal attestations, consent fields, EEO/voluntary self-identification, CAPTCHA, or ambiguous fields — except when all pre-apply gates in `src/yolo.py` have passed, `record_submission.py` has been called with a pre-authorized approval token derived from `profile.yolo_mode.authorization_key`, and the profile explicitly permits autonomous submission for this platform and tier. This conditional is in CLAUDE.md and the apply SKILL.md; do not expand it without a linked issue.

## Verification

- Run `python3 -m pytest tests/smoke_test.py -q` after structure, installer, manifest, or skill changes.
- Run `npm run check:package` after package metadata or npm allowlist changes.
- Run `npm run check:codeowners` after review-routing changes.
- Run `bash tests/integration_test.sh` when PDF generation behavior changes.
