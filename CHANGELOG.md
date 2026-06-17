# Changelog

## [1.1.5](https://github.com/nextwebb/career-agent/compare/v1.1.4...v1.1.5) (2026-06-17)


### Fixes

* **ci:** update actions for Node 24 runtime ([#55](https://github.com/nextwebb/career-agent/issues/55)) ([18f304d](https://github.com/nextwebb/career-agent/commit/18f304de0f3cd7ec1194fdc4f4dd8cb932097f11))

## [1.1.4](https://github.com/nextwebb/career-agent/compare/v1.1.3...v1.1.4) (2026-06-16)


### Fixes

* **ci:** deploy GH Pages on every push to main ([#52](https://github.com/nextwebb/career-agent/issues/52)) ([10f6f1d](https://github.com/nextwebb/career-agent/commit/10f6f1da41f98992bd16647591883e24cc5c7495))

## [1.1.3](https://github.com/nextwebb/career-agent/compare/v1.1.2...v1.1.3) (2026-06-16)


### Fixes

* align install instructions to claude plugin commands ([#48](https://github.com/nextwebb/career-agent/issues/48)) ([8733f5b](https://github.com/nextwebb/career-agent/commit/8733f5b93c3edd37935913d016736c3baaa129ab))
* **ci:** opt into Node.js 24 for release-please-action ([#50](https://github.com/nextwebb/career-agent/issues/50)) ([3b93674](https://github.com/nextwebb/career-agent/commit/3b936747b1321e60e255f35259fb7eed7527a595))

## [1.1.1] — 2026-06-16

### Fixes
- Enforce the documented Python 3.10+ minimum in the npm installer.
- Probe versioned Python executables such as `python3.12`, `python3.11`, and `python3.10` before failing.

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
