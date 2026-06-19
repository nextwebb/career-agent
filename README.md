<p align="center">
  <img src="https://raw.githubusercontent.com/nextwebb/career-agent/main/docs/assets/logo.svg" alt="career-agent logo" width="96" height="96">
</p>

# career-agent

[![Claude Code](https://img.shields.io/badge/Claude_Code-Plugin-000?style=flat&logo=anthropic&logoColor=white)](https://claude.ai/code)
[![Codex](https://img.shields.io/badge/Codex-Plugin-111827?style=flat)](https://developers.openai.com/codex)
[![CI](https://github.com/nextwebb/career-agent/workflows/CI/badge.svg)](https://github.com/nextwebb/career-agent/actions/workflows/ci.yml)
[![Security](https://github.com/nextwebb/career-agent/workflows/Security/badge.svg)](https://github.com/nextwebb/career-agent/actions/workflows/security.yml)
[![npm](https://img.shields.io/npm/v/@nextwebb/career-agent?style=flat&logo=npm)](https://www.npmjs.com/package/@nextwebb/career-agent)
[![npm downloads](https://img.shields.io/npm/dm/@nextwebb/career-agent?style=flat&logo=npm&label=downloads)](https://www.npmjs.com/package/@nextwebb/career-agent)
[![GitHub Stars](https://img.shields.io/github/stars/nextwebb/career-agent?style=flat&logo=github)](https://github.com/nextwebb/career-agent/stargazers)
[![Node.js 18+](https://img.shields.io/badge/node-18+-339933?style=flat&logo=node.js&logoColor=white)](https://nodejs.org/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-3776AB?style=flat&logo=python&logoColor=white)](https://www.python.org/downloads/)
[![Conventional Commits](https://img.shields.io/badge/Conventional_Commits-1.0.0-FE5196?style=flat&logo=conventionalcommits&logoColor=white)](https://conventionalcommits.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow?style=flat)](https://opensource.org/licenses/MIT)

**Agentic job application workflow for Claude Code and Codex.**

One command generates a tailored CV + cover letter PDF per role with deterministic quality gates. For browser workflows with enough platform evidence and safe field classification, the agent fills safe ATS fields, then hands off sensitive, consent, attestation, legal, and Submit controls to you.

Not a template engine. Not a job tracker. An agent-assisted workflow with deterministic handoff points.

Design philosophy: keep the workflow lightweight, keep career data local, and make generated application materials comprehensive enough for review without pretending to guarantee recruiter or ATS outcomes.

**[📖 Live Demo & Docs](https://nextwebb.github.io/career-agent/)** | **[⭐ Star on GitHub](https://github.com/nextwebb/career-agent)**

Public docs describe npm `latest`. For pinned installs, use the README and files shipped with that npm package version plus the changelog.

![career-agent demo](https://raw.githubusercontent.com/nextwebb/career-agent/main/demo.gif)

---

## What it does

0. **`/setup-profile`**: Build `profile.json` from your CV or LinkedIn PDF, extract work history, generate 3 CV variants, and draft source-backed per-job bullets for review
1. **`/source`**: Discover leads from available public/search sources, verify open roles on company-controlled pages, and rank them with a documented heuristic fit score
2. **`/new-role`**: Scaffold a new role config interactively by scraping the JD
3. **`/generate-cv`**: Build ATS-safe CV + cover letter PDFs tailored to the role, then run deterministic quality gates
4. **`/apply`**: Open the job URL in a browser, fill safe fields only when the ATS case is understood, upload PDFs when safe, answer safe custom questions, then hand off to you for sensitive fields and Submit
5. **`/track`**: View your application pipeline, update statuses, add notes

The agent never submits on your behalf. That boundary is intentional.

`/source` evidence and ranking rules are documented in [docs/source-methodology.md](docs/source-methodology.md).

---

## Why this is different

| | career-agent | career-ops |
|---|---|---|
| Profile bootstrap from CV/LinkedIn | ✅ `/setup-profile` | ❌ manual markdown file |
| CV variant system (A/B/C by audience) | ✅ per-role | ❌ single template |
| Per-role cover letter PDF | ✅ | ✅ `/cover` |
| Browser form filling | ✅ guarded handoff with Greenhouse, Lever, Workable notes | ✅ `/apply` |
| ATS-aware single-column PDF | ✅ reportlab | ✅ HTML→PDF |
| Human-in-loop handoff | ✅ sensitive fields + Submit | ✅ |
| Profile data local + gitignored | ✅ | ✅ |
| npx setup check | ✅ | ✅ |
| Claude Code CLI + desktop | ✅ | ✅ + Gemini/OpenCode |
| Codex plugin metadata | ✅ | ❌ |

---

## Testing & Quality

- **CI/CD**: GitHub Actions with focused checks on every PR
- **Security**: CodeQL + Trivy + bandit + safety scanning (daily + on push)
- **Code Quality**: Ruff linting + mypy type checking
- **Tests**: Smoke tests (structure/syntax) + integration tests (real PDF generation with synthetic non-PII fixtures)
- **Python Support**: 3.10, 3.11, 3.12

All checks must pass before merge. See [ENGINEERING_PRINCIPLES.md](ENGINEERING_PRINCIPLES.md) for detailed standards.

---

## Support matrix

| Workflow | Claude Code | Codex |
|---|---|---|
| Setup and doctor | ✅ supported | ✅ supported |
| Profile bootstrap | ✅ `/setup-profile` | ✅ `$setup-profile` or skill selector |
| Job sourcing | ✅ `/source` | ✅ `$source` or natural language |
| Role config | ✅ `/new-role` | ✅ `$new-role` or natural language |
| CV and cover letter PDFs | ✅ `/generate-cv` | ✅ `$generate-cv` or natural language |
| Pipeline tracking | ✅ `/track` | ✅ `$track` or natural language |
| ATS form filling | ✅ with Claude in Chrome | ⚠️ experimental; see [Codex Chrome verification](docs/apply-codex-chrome-verification.md) |

Codex support means the package includes `.codex-plugin/plugin.json`, Codex-compatible skill metadata, host-neutral skill instructions, and Codex-aware setup checks. It does not mean `npx` installs the plugin into Codex. How you make the plugin available in Codex depends on the Codex surface and configured plugin source.

## Prerequisites

- [Claude Code](https://claude.ai/code) CLI or [Codex](https://developers.openai.com/codex) CLI/app
- Python 3.10+ with `reportlab` and `pypdf` (`pip install -r requirements.txt`)
- Node 18+ for the `npx` setup and doctor commands
- Browser automation for `/apply`:
  - Claude Code: Claude in Chrome extension
  - Codex: Browser for public pages, Chrome for signed-in browser state; see [ATS platform support notes](#ats-platform-support-notes)

---

## Install

### Setup check

```bash
# Check Python 3.10+, PDF dependencies, Claude/Codex host availability, and create profile.json
npx @nextwebb/career-agent
```

Run a health check without creating `profile.json`:

```bash
npx @nextwebb/career-agent doctor
```

### Claude Code plugin install

```bash
claude plugin marketplace add nextwebb/career-agent
claude plugin install career-agent
```

### Codex plugin metadata

Codex metadata is packaged at `.codex-plugin/plugin.json`. Making it available in Codex depends on the Codex surface you use and the plugin source you configure. Do not treat `npx` or the Claude marketplace commands above as Codex plugin setup.

Then bootstrap your profile:

```
/setup-profile               # Claude Code alias
$setup-profile               # Codex skill invocation
/source Germany backend      # Find and verify matching role leads
/new-role                    # Create role config
/generate-cv <role_id>       # Generate PDFs
/apply <role_id>             # Browser form handoff
/track                       # View pipeline
```

---

## Profile setup

The fastest way is to let the agent build it for you:

```
/setup-profile               # Upload or paste your CV/LinkedIn PDF
```

The agent extracts your work history, infers three CV variants (AI/LLM, Data Platform, Backend), and writes one default bullet set plus three audience-specific variants, ready for `/generate-cv` or `$generate-cv` immediately.

Or create it manually: `profile.json` (gitignored: never committed) holds your personal data:

```json
{
  "name": { "first": "Jane", "last": "Doe" },
  "email": "jane@example.com",
  "phone": { "country_code": "+1", "number": "5551234567" },
  "location": "Berlin, Germany",
  "relocation": "Open to EU/UK relocation with visa sponsorship",
  "links": {
    "linkedin": "https://www.linkedin.com/in/janedoe/",
    "github": "https://github.com/janedoe",
    "website": "https://janedoe.dev",
    "twitter": "https://x.com/janedoe"
  },
  "headline": "Senior Software Engineer: Python · Distributed Systems · AI",
  "summary": "7+ years building production Python systems..."
}
```

See `profile.example.json` for the full schema including `variants`, `impact_statements`, and per-job bullet sets.

---

## Role config

Each role lives in `roles/<role_id>.json` (gitignored):

```json
{
  "role_id": "stripe_backend_2026",
  "company": "Stripe",
  "title": "Senior Backend Engineer",
  "url": "https://stripe.com/jobs/listing/...",
  "ats_platform": "greenhouse",
  "variant": "C",
  "cover_letter": {
    "paragraphs": [
      "Stripe's payment infrastructure serves...",
      "My background in distributed systems...",
      "...",
      "I would welcome a conversation..."
    ]
  },
  "custom_answers": {
    "why_company": "...",
    "hear_about_us": "LinkedIn"
  }
}
```

See `roles.example/example_role.json` for the full schema including CV bullet overrides.

---

## CV variants

Define named variants in `profile.json` under `"variants"`. Each variant emphasises a different slice of your experience:

- **A**: AI/LLM/Evaluation focused
- **B**: Data Platform/Pipelines focused
- **C**: Senior Backend/APIs focused

The role config picks a variant. The CV builder selects the matching experience ordering and impact statements.

---

## ATS platform support notes

These are implementation notes for supported ATS patterns, not a guarantee that every live form variant will work. Verify each form before filling, and stop on unsupported ATS pages, login walls, CAPTCHA, ambiguous consent, or hidden fields that cannot be classified.

Codex Chrome `/apply` is not stable by assumption. Use the [Codex Chrome verification matrix](docs/apply-codex-chrome-verification.md) to decide whether a platform has non-submitting evidence for a Codex run. As of 2026-06-18, no live Codex Chrome ATS tests are committed in this repository, so all named ATS rows below are experimental for Codex Chrome. Failed, ambiguous, or unverified platforms should use manual fallback and handoff.

| Platform | General behavior | Codex Chrome status |
|---|---|---|
| Greenhouse (direct) | Fill safe fields, upload resume, answer safe custom questions | Experimental until a non-submitted evidence record exists |
| Greenhouse (iframe embed) | Use the embed URL as a top-level page, not a company iframe | Experimental until a non-submitted evidence record exists |
| Greenhouse (EU domain) | Keep `ats_platform` normalized to `greenhouse` unless a separate supported value is intentionally added and tested | Experimental until EU URL/domain handling is verified |
| Lever | Upload resume, paste cover-letter text when a field exists, answer safe custom questions | Experimental until a non-submitted evidence record exists |
| Workable | Use `/apply/` URL, upload resume, handle dropdowns and multi-step forms carefully | Experimental until a non-submitted evidence record exists |
| Unknown/unsupported ATS | Stop and provide manual guidance | Unsupported for automation |
| More | PRs welcome | Experimental until verified |

---

---

## Human-in-the-loop handoff

The agent fills safe fields it can verify from your profile and the role config. It does **not**:

- Click Submit
- Fill EEO/voluntary self-identification fields (gender, race, ethnicity, veteran status, disability)
- Enter passwords or credentials
- Enter national IDs, SSN/tax IDs, passport/visa document numbers, or dates of birth
- Enter bank, payment, or payroll details
- Select privacy, GDPR, data-retention, talent-pool, terms, consent, or attestation checkboxes
- Solve CAPTCHA or anti-bot challenges
- Answer fields requiring legal judgment or uncertain interpretation

This is a deliberate design boundary, not a limitation. The agent flags exactly what it has filled and what remains for you.

---

## Project structure

```
career-agent/
├── README.md
├── AGENTS.md                        # Codex repo guidance
├── CLAUDE.md                        # Claude Code context + slash commands
├── plugin.json                      # Legacy/shared plugin manifest
├── .claude-plugin/plugin.json       # Claude Code plugin manifest
├── .codex-plugin/plugin.json        # Codex plugin manifest
├── requirements.txt                 # pip install reportlab and pypdf
├── profile.example.json             # Copy → profile.json (gitignored)
├── .gitignore
│
├── skills/
│   ├── setup-profile/SKILL.md       # Bootstrap profile.json from CV or LinkedIn PDF
│   ├── source/SKILL.md              # Find + verify open role leads from your profile
│   ├── new-role/SKILL.md            # Scaffold a new role JSON interactively
│   ├── generate-cv/SKILL.md         # Build PDF from profile + role config
│   ├── apply/SKILL.md               # Fill ATS form + upload + handoff
│   └── track/SKILL.md               # Application pipeline tracker
│
├── src/
│   ├── cv_builder.py                # reportlab Platypus PDF engine
│   ├── cl_builder.py                # Cover letter PDF builder
│   ├── generate_application.py      # CLI: python src/generate_application.py <role_id>
│   └── tracker.py                   # Pipeline tracker CLI
│
├── roles.example/
│   └── example_role.json            # Role config schema reference
│
├── roles/                           # gitignored: your role configs
├── generated/                       # gitignored: output PDFs
├── tracker.json                     # gitignored: application pipeline
└── profile.json                     # gitignored: your profile data
```

---

## Troubleshooting

### `npx @nextwebb/career-agent` fails with "career-agent: command not found"

This is usually a stale shell hash from a prior global install. Clear it and retry:

```bash
hash -r                        # zsh / bash: clears the command hash table
npx @nextwebb/career-agent
```

If that doesn't help, use the explicit form that bypasses hash resolution:

```bash
npx --package=@nextwebb/career-agent career-agent
```

### PDF generation fails

Ensure `reportlab` and `pypdf` are installed and use the correct flag syntax:

```bash
pip install -r requirements.txt
python src/generate_application.py --role <role_id>   # correct
python src/generate_application.py <role_id>           # wrong: positional args not accepted
```

The `generated/` output directory is created automatically on first run.

---

## Contributing

ATS platforms to add: Ashby, SmartRecruiters, Taleo, iCIMS, BambooHR.

Each platform needs:
- A `src/ats/<platform>.py` helper (optional: for complex flows)
- Notes in the `apply` skill about platform-specific quirks (hidden file inputs, React comboboxes, cross-origin iframes, etc.)

**Before contributing:**
1. Read [ENGINEERING_PRINCIPLES.md](ENGINEERING_PRINCIPLES.md) for coding standards
2. Install pre-commit hooks: `pip install pre-commit && pre-commit install`
3. Run tests locally: `pytest tests/ && bash tests/integration_test.sh`
4. Open an issue before starting to avoid duplication

**CI Requirements:**
- All code must pass Ruff linting + mypy type checking
- Security scans (bandit) must pass
- Smoke tests + integration tests must pass
- Conventional commit message format required

---

## License

MIT
