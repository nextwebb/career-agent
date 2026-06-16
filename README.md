# career-agent

[![Claude Code](https://img.shields.io/badge/Claude_Code-Plugin-000?style=flat&logo=anthropic&logoColor=white)](https://claude.ai/code)
[![CI](https://github.com/nextwebb/career-agent/workflows/CI/badge.svg)](https://github.com/nextwebb/career-agent/actions/workflows/ci.yml)
[![Security](https://github.com/nextwebb/career-agent/workflows/Security/badge.svg)](https://github.com/nextwebb/career-agent/actions/workflows/security.yml)
[![npm](https://img.shields.io/npm/v/@nextwebb/career-agent?style=flat&logo=npm)](https://www.npmjs.com/package/@nextwebb/career-agent)
[![npm downloads](https://img.shields.io/npm/dm/@nextwebb/career-agent?style=flat&logo=npm&label=downloads)](https://www.npmjs.com/package/@nextwebb/career-agent)
[![GitHub Stars](https://img.shields.io/github/stars/nextwebb/career-agent?style=flat&logo=github)](https://github.com/nextwebb/career-agent/stargazers)
[![Node.js 18+](https://img.shields.io/badge/node-18+-339933?style=flat&logo=node.js&logoColor=white)](https://nodejs.org/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-3776AB?style=flat&logo=python&logoColor=white)](https://www.python.org/downloads/)
[![Conventional Commits](https://img.shields.io/badge/Conventional_Commits-1.0.0-FE5196?style=flat&logo=conventionalcommits&logoColor=white)](https://conventionalcommits.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow?style=flat)](https://opensource.org/licenses/MIT)

**Agentic job application workflow for Claude Code.**

One command generates a tailored CV + cover letter PDF per role. Claude fills the ATS form. You review and click Submit.

Not a template engine. Not a job tracker. An agent that does the work.

**[📖 Live Demo & Docs](https://nextwebb.github.io/career-agent/)** | **[⭐ Star on GitHub](https://github.com/nextwebb/career-agent)**

![career-agent demo](demo.gif)

---

## What it does

0. **`/setup-profile`** — Build `profile.json` from your CV or LinkedIn PDF — extracts work history, generates 3 CV variants, writes per-job bullets automatically
1. **`/source`** — Find and verify open roles matching your profile from company career pages
2. **`/new-role`** — Scaffold a new role config interactively by scraping the JD
3. **`/generate-cv`** — Build ATS-optimised CV + cover letter PDFs tailored to the role
4. **`/apply`** — Open the job URL in Chrome, fill every required field, upload PDFs, answer custom questions — then hand off to you for EEO/voluntary fields and Submit
5. **`/track`** — View your application pipeline, update statuses, add notes

Claude never submits on your behalf. That boundary is intentional.

---

## Why this is different

| | career-agent | career-ops |
|---|---|---|
| Profile bootstrap from CV/LinkedIn | ✅ `/setup-profile` | ❌ manual markdown file |
| CV variant system (A/B/C by audience) | ✅ per-role | ❌ single template |
| Per-role cover letter PDF | ✅ | ✅ `/cover` |
| Browser form filling | ✅ Greenhouse, Lever, Workable | ✅ `/apply` |
| ATS-safe single-column PDF | ✅ reportlab | ✅ HTML→PDF |
| Human-in-loop handoff | ✅ EEO + Submit only | ✅ |
| Profile data local + gitignored | ✅ | ✅ |
| npx one-command install | ✅ | ✅ |
| Claude Code CLI + desktop | ✅ both | ✅ + Gemini/OpenCode |

---

## Testing & Quality

- **CI/CD**: GitHub Actions with comprehensive testing on every PR
- **Security**: CodeQL + Trivy + bandit + safety scanning (daily + on push)
- **Code Quality**: Ruff linting + mypy type checking
- **Tests**: Smoke tests (structure/syntax) + integration tests (real PDF generation)
- **Python Support**: 3.10, 3.11, 3.12

All checks must pass before merge. See [ENGINEERING_PRINCIPLES.md](ENGINEERING_PRINCIPLES.md) for detailed standards.

---

## Prerequisites

- [Claude Code](https://claude.ai/code) CLI or Claude Code desktop app
- Python 3.10+ with `reportlab` (`pip install reportlab`)
- [Claude in Chrome extension](https://chrome.google.com/webstore) connected to Claude Code (CLI or desktop) — **not** the Claude.ai consumer app

---

## Install as Plugin

### Option 1: One command (Recommended)

```bash
npx @nextwebb/career-agent
```

This checks Python 3, installs `reportlab`, registers the marketplace, installs the plugin, and creates `profile.json`. Node 18+ required.

### Option 2: Via Marketplace

```bash
claude plugin marketplace add nextwebb/career-agent
claude plugin install career-agent@career-agent
```

Or in Claude Code:

```
/plugin marketplace add nextwebb/career-agent
/plugin install career-agent@career-agent
```

### Option 3: Direct Install

```bash
claude plugin install github:nextwebb/career-agent
```

After installation, bootstrap your profile from your CV or LinkedIn PDF:

```
/setup-profile               # Build profile.json from your CV/LinkedIn PDF
/source Germany backend      # Find matching roles
/new-role                    # Create role config
/generate-cv <role_id>       # Generate PDFs
/apply <role_id>             # Fill ATS form
/track                       # View pipeline
```

---

## Quick start (Manual Setup)

```bash
git clone https://github.com/nextwebb/career-agent
cd career-agent

# Install dependencies and verify
pip install -r requirements.txt
python -c "import reportlab; print('reportlab installed successfully')"
```

Then in Claude Code (CLI or desktop app):

```
/setup-profile               # Build profile.json from your CV or LinkedIn PDF
/source Germany backend      # Find matching roles
/new-role                    # Interactively create a role config
/generate-cv my_role         # Generate tailored PDFs
/apply my_role               # Fill the ATS form
/track                       # View your application pipeline
```

---

## Profile setup

The fastest way is to let the agent build it for you:

```
/setup-profile               # Upload or paste your CV/LinkedIn PDF
```

Claude extracts your work history, infers three CV variants (AI/LLM, Data Platform, Backend), and writes per-job bullets four ways — ready for `/generate-cv` immediately.

Or create it manually: `profile.json` (gitignored — never committed) holds your personal data:

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
  "headline": "Senior Software Engineer — Python · Distributed Systems · AI",
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

- **A** — AI/LLM/Evaluation focused
- **B** — Data Platform/Pipelines focused  
- **C** — Senior Backend/APIs focused

The role config picks a variant. The CV builder selects the matching experience ordering and impact statements.

---

## ATS platform support

| Platform | Fill fields | Upload resume | Custom questions |
|---|---|---|---|
| Greenhouse (direct) | ✅ | ✅ | ✅ |
| Greenhouse (iframe embed) | ✅ via embed URL | ✅ | ✅ |
| Lever | ✅ | ✅ | ✅ (text) |
| Workable | ✅ | ✅ | ✅ |
| More | PRs welcome | | |

---

## Install as plugin

### Claude Code desktop app

1. Open Claude Code desktop → Settings → Plugins
2. Click **Install from folder** → select this repo root
3. Skills appear as `/source`, `/new-role`, `/generate-cv`, `/apply`, `/track`

### Claude Code (CLI)

```bash
# In your project or home directory
cp -r skills ~/.claude/skills/career-agent
```

Then in any Claude Code session:
```
/career-agent:apply my_role
```

Or add to your project's `CLAUDE.md`:
```
@~/.claude/skills/career-agent/apply/SKILL.md
```

---

## Human-in-the-loop handoff

Claude fills every required field it can verify from your profile and the role config. It does **not**:

- Click Submit
- Fill EEO/voluntary self-identification fields (gender, race, veteran status, disability)
- Enter passwords or credentials

This is a deliberate design boundary, not a limitation. The agent flags exactly what it has filled and what remains for you.

---

## Project structure

```
career-agent/
├── README.md
├── CLAUDE.md                        # Claude Code context + slash commands
├── plugin.json                      # Claude Code plugin manifest
├── requirements.txt                 # pip install reportlab
├── profile.example.json             # Copy → profile.json (gitignored)
├── .gitignore
│
├── skills/
│   ├── setup-profile/SKILL.md       # Bootstrap profile.json from CV or LinkedIn PDF
│   ├── source/SKILL.md              # Find + verify open roles from your profile
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
├── roles/                           # gitignored — your role configs
├── generated/                       # gitignored — output PDFs
├── tracker.json                     # gitignored — application pipeline
└── profile.json                     # gitignored — your profile data
```

---

## Troubleshooting

### Plugin installation fails with schema errors

```
Failed to add marketplace: Invalid schema
Failed to install plugin: Plugin has an invalid manifest file
```

Clear the cached marketplace clone and reinstall:

```bash
claude plugin marketplace remove career-agent
rm -rf ~/.claude/plugins/marketplaces/career-agent
claude plugin marketplace add nextwebb/career-agent
claude plugin install career-agent@career-agent
```

### Cached plugin not picking up latest changes

Plugin caches persist at `~/.claude/plugins/cache/`. The Claude CLI skips updates when the resolved version is unchanged, so `claude plugin update` only works if the version in `plugin.json` has been bumped. If the version was bumped, force a refresh:

```bash
claude plugin update career-agent@career-agent
```

If the version was **not** bumped (e.g. you are developing locally against a pinned `1.0.0`), clear and reinstall entirely:

```bash
claude plugin marketplace remove career-agent
rm -rf ~/.claude/plugins/marketplaces/career-agent ~/.claude/plugins/cache/*career-agent*
claude plugin marketplace add nextwebb/career-agent
claude plugin install career-agent@career-agent
```

Cache locations:
- `~/.claude/plugins/marketplaces/<name>/` — marketplace clone
- `~/.claude/plugins/cache/<marketplace>/<plugin>/` — installed plugin

### PDF generation fails

Ensure `reportlab` is installed and use the correct flag syntax:

```bash
pip install reportlab
python src/generate_application.py --role <role_id>   # correct
python src/generate_application.py <role_id>           # wrong — positional args not accepted
```

The `generated/` output directory is created automatically on first run.

---

## Contributing

ATS platforms to add: Ashby, SmartRecruiters, Taleo, iCIMS, BambooHR.

Each platform needs:
- A `src/ats/<platform>.py` helper (optional — for complex flows)
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
