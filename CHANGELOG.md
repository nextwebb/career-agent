# Changelog

## [1.5.1](https://github.com/nextwebb/career-agent/compare/v1.5.0...v1.5.1) (2026-06-22)


### Fixes

* **confirmation:** remove 'Thank you' from Workable text_contains to prevent false positives (closes [#107](https://github.com/nextwebb/career-agent/issues/107)) ([#110](https://github.com/nextwebb/career-agent/issues/110)) ([c792138](https://github.com/nextwebb/career-agent/commit/c7921380c3677fc58e0e2b575720b9aed97248f3))
* **pre-apply:** block autonomous mode when ats_platform is unknown (closes [#106](https://github.com/nextwebb/career-agent/issues/106)) ([#117](https://github.com/nextwebb/career-agent/issues/117)) ([98d293e](https://github.com/nextwebb/career-agent/commit/98d293e5e27d7cab1731d28c8f67683ffff82061))
* **yolo:** skip jobqa gate when not installed, only re-raise on actual failure (closes [#109](https://github.com/nextwebb/career-agent/issues/109)) ([#118](https://github.com/nextwebb/career-agent/issues/118)) ([a4c6df0](https://github.com/nextwebb/career-agent/commit/a4c6df06491fd07b4a63bf4ed28d357ddcd25c2e))


### Documentation

* **codex-chrome:** sync experimental status with current evidence ([#116](https://github.com/nextwebb/career-agent/issues/116)) ([d0aa8d4](https://github.com/nextwebb/career-agent/commit/d0aa8d4546868e07442ec0b817a2a1de4bb6346a)), closes [#100](https://github.com/nextwebb/career-agent/issues/100)

## [1.5.0](https://github.com/nextwebb/career-agent/compare/v1.4.0...v1.5.0) (2026-06-22)


### Features

* **cv:** align section order to reference CV layout ([#105](https://github.com/nextwebb/career-agent/issues/105)) ([bff95bb](https://github.com/nextwebb/career-agent/commit/bff95bb2ad00ba36657b75420af5e38a84b10aeb))


### Documentation

* **apply:** document base64 upload workaround and Workable react-dropzone limitation ([#104](https://github.com/nextwebb/career-agent/issues/104)) ([baa5d43](https://github.com/nextwebb/career-agent/commit/baa5d438fa74aee278db115a5efb06d9bd981674))

## [1.4.0](https://github.com/nextwebb/career-agent/compare/v1.3.0...v1.4.0) (2026-06-22)


### Features

* yolo mode — autonomous submission with pre-authorized gate battery ([#102](https://github.com/nextwebb/career-agent/issues/102)) ([05e8e25](https://github.com/nextwebb/career-agent/commit/05e8e259d6a4d98de602011f309e9ab5f6562e35))

## [1.3.0](https://github.com/nextwebb/career-agent/compare/v1.2.2...v1.3.0) (2026-06-19)


### Features

* expose Codex marketplace install path ([#97](https://github.com/nextwebb/career-agent/issues/97)) ([38155c6](https://github.com/nextwebb/career-agent/commit/38155c6a57578056da9461fa41dce56b67c1ba97))


### Documentation

* clarify Codex setup boundaries ([#96](https://github.com/nextwebb/career-agent/issues/96)) ([0853ebb](https://github.com/nextwebb/career-agent/commit/0853ebb550c1e8ca8d0b9e6ec360c26fda68480a))

## [1.2.2](https://github.com/nextwebb/career-agent/compare/v1.2.1...v1.2.2) (2026-06-19)


### Fixes

* include requirements in npm package ([#88](https://github.com/nextwebb/career-agent/issues/88)) ([2a0d64f](https://github.com/nextwebb/career-agent/commit/2a0d64f037582f6506fe8084e2f9c5388c1d85b0))

## [1.2.1](https://github.com/nextwebb/career-agent/compare/v1.2.0...v1.2.1) (2026-06-19)


### Features

* add deterministic CV and cover-letter quality gates for generated PDFs ([#73](https://github.com/nextwebb/career-agent/issues/73)) ([5725caa](https://github.com/nextwebb/career-agent/commit/5725caa63af14470a529fa21ae3a99bc052b25f0))


### Fixes

* fail generation when deterministic quality gates fail, with `--no-quality-gates` kept for diagnostics ([#73](https://github.com/nextwebb/career-agent/issues/73)) ([5725caa](https://github.com/nextwebb/career-agent/commit/5725caa63af14470a529fa21ae3a99bc052b25f0))


### Dependencies

* add `pypdf` for generated PDF text extraction checks ([#73](https://github.com/nextwebb/career-agent/issues/73)) ([5725caa](https://github.com/nextwebb/career-agent/commit/5725caa63af14470a529fa21ae3a99bc052b25f0))


### Documentation

* document Codex Chrome ATS verification evidence ([#70](https://github.com/nextwebb/career-agent/issues/70)) ([9ffe371](https://github.com/nextwebb/career-agent/commit/9ffe371c7e0f4352bbb110c204c4ff83899173e0))
* document coding-agent change discipline ([#79](https://github.com/nextwebb/career-agent/issues/79)) ([46e91aa](https://github.com/nextwebb/career-agent/commit/46e91aa6f691aab14302cf214e46feefdd2944a7))
* document source methodology ([#71](https://github.com/nextwebb/career-agent/issues/71)) ([44abc32](https://github.com/nextwebb/career-agent/commit/44abc3236fba184964be879e4d967cf34aa8e70b))
* document validation contact policy ([#69](https://github.com/nextwebb/career-agent/issues/69)) ([ea0ca63](https://github.com/nextwebb/career-agent/commit/ea0ca6313383168273ca404b8114da5393514dd9))
* document release-safe PR titles ([#78](https://github.com/nextwebb/career-agent/issues/78)) ([aa0f443](https://github.com/nextwebb/career-agent/commit/aa0f4433875d50df9088b6717bdf26880466f88e))
* prune guidance boilerplate ([#86](https://github.com/nextwebb/career-agent/issues/86)) ([8da64fb](https://github.com/nextwebb/career-agent/commit/8da64fbe1bdc2e8410fef5e69a6dabe21ec352a6))
* prune redundant skill instructions ([#83](https://github.com/nextwebb/career-agent/issues/83)) ([1e7941b](https://github.com/nextwebb/career-agent/commit/1e7941bc2dd57fab03f1742078a4c3f04dd9fc87))

## [1.2.0](https://github.com/nextwebb/career-agent/compare/v1.1.5...v1.2.0) (2026-06-18)


### Features

* **codex:** add intrinsic support ([#66](https://github.com/nextwebb/career-agent/issues/66)) ([7ba2676](https://github.com/nextwebb/career-agent/commit/7ba267600c6ba3c4bdfb0d21a2311909723858d8))

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
