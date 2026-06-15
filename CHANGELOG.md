# Changelog

## [1.0.0] — 2026-06-15

### Features
- Five agentic skills: /source, /new-role, /generate-cv, /apply, /track
- ATS support: Greenhouse (direct + iframe embed), Lever, Workable
- CV variant system (A/B/C) for different role types
- Claude Code marketplace distribution via .claude-plugin/marketplace.json
- Human-in-the-loop handoff — Claude never clicks Submit or fills EEO fields
- GitHub Pages documentation site

### Infrastructure
- CI/CD: Ruff, mypy, bandit, smoke tests, integration tests (Python 3.10/3.11/3.12)
- Security: CodeQL, Trivy, dependency scanning, secret detection
