# Changelog

## [1.11.0](https://github.com/nextwebb/career-agent/compare/v1.10.1...v1.11.0) (2026-07-09)


### Features

* **cv:** configurable, context-aware location rendering — closes [#198](https://github.com/nextwebb/career-agent/issues/198) ([#206](https://github.com/nextwebb/career-agent/issues/206)) ([f1e8129](https://github.com/nextwebb/career-agent/commit/f1e81297c914285b302c23ebf2ccfa20eaa690d2))


### Fixes

* **apply:** address live yolo run regressions ([#208](https://github.com/nextwebb/career-agent/issues/208)) ([e65d2fb](https://github.com/nextwebb/career-agent/commit/e65d2fb3935b5875b25683621d37c0f8a3e1945b))

## [1.10.1](https://github.com/nextwebb/career-agent/compare/v1.10.0...v1.10.1) (2026-07-08)


### Documentation

* **agents:** add reading order and doc map, sync stale CV section list ([#192](https://github.com/nextwebb/career-agent/issues/192)) ([b1b64f5](https://github.com/nextwebb/career-agent/commit/b1b64f50efe272c57b8365b7c6142de6647a3dc2))
* **polish:** match Lever URL pattern and add yolo qualifier to apply skill description ([#197](https://github.com/nextwebb/career-agent/issues/197)) ([6c02f2f](https://github.com/nextwebb/career-agent/commit/6c02f2f8d4adc4d5904af6ef9c4b9a01abf2d8d4))
* **skills:** remove dead impact_statements and impact_order references ([#195](https://github.com/nextwebb/career-agent/issues/195)) ([3158511](https://github.com/nextwebb/career-agent/commit/31585111f269ca158727aec9fd25feaf46fa3d2f))

## [1.10.0](https://github.com/nextwebb/career-agent/compare/v1.9.0...v1.10.0) (2026-07-08)


### Features

* **cv:** JD-driven skills rendering with intersection and caps ([#186](https://github.com/nextwebb/career-agent/issues/186)) ([ae93191](https://github.com/nextwebb/career-agent/commit/ae93191f2d3345a2ddf11fffd362eefe5bdc3f22)), closes [#184](https://github.com/nextwebb/career-agent/issues/184)


### Fixes

* **cv:** inject summary_closing_line into rendered summary ([#191](https://github.com/nextwebb/career-agent/issues/191)) ([92cb999](https://github.com/nextwebb/career-agent/commit/92cb9999a1aff24a4824edb190df00f4a9801fa0))
* **cv:** section ordering, drop Selected Impact, rename Certifications, add Tech Stack per role ([#188](https://github.com/nextwebb/career-agent/issues/188)) ([a682b5f](https://github.com/nextwebb/career-agent/commit/a682b5fda4eacf7de78811d498928953e578f6a8)), closes [#187](https://github.com/nextwebb/career-agent/issues/187)
* **cv:** truncate additional_experience entries — closes [#183](https://github.com/nextwebb/career-agent/issues/183) ([#185](https://github.com/nextwebb/career-agent/issues/185)) ([845cfaf](https://github.com/nextwebb/career-agent/commit/845cfaf8603f0b08f5591a5e2dbfa4d4e271e35a))

## [1.9.0](https://github.com/nextwebb/career-agent/compare/v1.8.0...v1.9.0) (2026-07-08)


### Features

* **cv:** add optional start/end fields to experience entries — closes [#171](https://github.com/nextwebb/career-agent/issues/171) ([#176](https://github.com/nextwebb/career-agent/issues/176)) ([83bea9f](https://github.com/nextwebb/career-agent/commit/83bea9fbbcc6e7110d0c6212883999cb2fb5da1a))
* **cv:** experience type field for auto section routing — closes [#169](https://github.com/nextwebb/career-agent/issues/169) ([#179](https://github.com/nextwebb/career-agent/issues/179)) ([70d969d](https://github.com/nextwebb/career-agent/commit/70d969d7f483c7a83306a3bd4660c24b53d2081c))
* **cv:** render additional_experience as condensed one-line section — closes [#172](https://github.com/nextwebb/career-agent/issues/172) ([#180](https://github.com/nextwebb/career-agent/issues/180)) ([9423287](https://github.com/nextwebb/career-agent/commit/942328760428e91a5b6aaababcfbe6ea2c8ecfa2))
* **cv:** skills grouping via optional group field — partial [#174](https://github.com/nextwebb/career-agent/issues/174) ([#175](https://github.com/nextwebb/career-agent/issues/175)) ([4f72211](https://github.com/nextwebb/career-agent/commit/4f7221122c1decbd9f33bb6d10113b9d82dcb11b))
* **quality:** detect same-company date overlap in experience entries — closes [#170](https://github.com/nextwebb/career-agent/issues/170) ([#177](https://github.com/nextwebb/career-agent/issues/177)) ([79ce845](https://github.com/nextwebb/career-agent/commit/79ce8453c2b6e7912cd21d4f645fce2249d8cee7))


### Fixes

* **quality:** remove duplicate _entry_label definition ([#182](https://github.com/nextwebb/career-agent/issues/182)) ([8a1193f](https://github.com/nextwebb/career-agent/commit/8a1193f5043f27834bada01790ee53c5e945aa59))

## [1.8.0](https://github.com/nextwebb/career-agent/compare/v1.7.1...v1.8.0) (2026-07-01)


### Features

* **source:** posting-age freshness gate before role scoring ([#163](https://github.com/nextwebb/career-agent/issues/163)) ([ab0fb29](https://github.com/nextwebb/career-agent/commit/ab0fb291e2051872a75bf3d571fa5aeb58c461f5))
* **tracker:** close_reason field for withdrawn/rejected entries ([#164](https://github.com/nextwebb/career-agent/issues/164)) ([5e95146](https://github.com/nextwebb/career-agent/commit/5e95146d996ca83a9e1cba15c0f9123676aeeb1a))
* **tracker:** ghost detection for stale applied entries ([#162](https://github.com/nextwebb/career-agent/issues/162)) ([ecf9e84](https://github.com/nextwebb/career-agent/commit/ecf9e847661ef45bf8296a74fc8b4dcc35b08be3))

## [1.7.1](https://github.com/nextwebb/career-agent/compare/v1.7.0...v1.7.1) (2026-06-29)


### Documentation

* **apply:** update SKILL.md platform list to reflect v1.7 support ([#157](https://github.com/nextwebb/career-agent/issues/157)) ([7753b09](https://github.com/nextwebb/career-agent/commit/7753b09f79f86aecdccbdd2e8f683eb5154eafb2))
* sync README and GH Pages to v1.7 platform support ([#158](https://github.com/nextwebb/career-agent/issues/158)) ([5fc05ef](https://github.com/nextwebb/career-agent/commit/5fc05ef5674a804f951ed554457b3711a701948b))

## [1.7.0](https://github.com/nextwebb/career-agent/compare/v1.6.0...v1.7.0) (2026-06-29)


### Features

* **pre-apply:** add location-eligibility gate to run_pre_apply_checks ([#149](https://github.com/nextwebb/career-agent/issues/149)) ([0ee3cb0](https://github.com/nextwebb/career-agent/commit/0ee3cb04b1a32b2957bf20b1ccb6b24f0a916fd6))
* **pre-apply:** company-repeat gate — block after N same-company rejections — [#138](https://github.com/nextwebb/career-agent/issues/138) ([#153](https://github.com/nextwebb/career-agent/issues/153)) ([6cf9392](https://github.com/nextwebb/career-agent/commit/6cf9392604189a70ea061f94cf82d0939916d4b1))
* **pre-apply:** Lever per-company cooldown gate (URL-slug) — [#147](https://github.com/nextwebb/career-agent/issues/147) / [#140](https://github.com/nextwebb/career-agent/issues/140) Part A ([#150](https://github.com/nextwebb/career-agent/issues/150)) ([7e58e62](https://github.com/nextwebb/career-agent/commit/7e58e6250be27254ea6f78cb5c6c70e8f6d35ccf))
* **tracker:** propagate ats_platform and variant fields to tracker entries — [#139](https://github.com/nextwebb/career-agent/issues/139) ([#152](https://github.com/nextwebb/career-agent/issues/152)) ([f162716](https://github.com/nextwebb/career-agent/commit/f1627163ebaef32f5ecacc476cbe211d944f08a3))


### Fixes

* **confirmation:** drop over-broad Ashby 'error' failure token — [#140](https://github.com/nextwebb/career-agent/issues/140) D1 ([#151](https://github.com/nextwebb/career-agent/issues/151)) ([dd3f3b2](https://github.com/nextwebb/career-agent/commit/dd3f3b2bf4fec8481d192163e43e3c182ac047c3))
* **pre-apply:** write submitted_unconfirmed before Submit; allow retry on failed entries ([#148](https://github.com/nextwebb/career-agent/issues/148)) ([3958e8e](https://github.com/nextwebb/career-agent/commit/3958e8e167839c7fb09faf043f049f4080df45c9))

## [1.6.0](https://github.com/nextwebb/career-agent/compare/v1.5.2...v1.6.0) (2026-06-27)


### Features

* **dx:** scaffold openness, document additional_experience, separate display from ATS relocation ([#133](https://github.com/nextwebb/career-agent/issues/133)) ([ed920c1](https://github.com/nextwebb/career-agent/commit/ed920c132cc0dc1a04bf25b1cf3a26a80721b3ec))


### Fixes

* **cv-display:** honour show_location/show_phone/show_relocation in CV and cover letter ([#132](https://github.com/nextwebb/career-agent/issues/132)) ([c17c049](https://github.com/nextwebb/career-agent/commit/c17c049231c7d42ed6e996eae8146c98c78da2d5))
* **quality-gates:** drop 'relevant experience' false-positive pattern ([#131](https://github.com/nextwebb/career-agent/issues/131)) ([4434286](https://github.com/nextwebb/career-agent/commit/44342868c0a6dd93f408d7b525f775379fa201fe))

## [1.5.2](https://github.com/nextwebb/career-agent/compare/v1.5.1...v1.5.2) (2026-06-23)


### Fixes

* **apply:** align CLAUDE.md storage policy and harden server lifecycle ([#127](https://github.com/nextwebb/career-agent/issues/127)) ([13b7625](https://github.com/nextwebb/career-agent/commit/13b7625031f88d0ad27e507c777c13b9e34cafb8))
* **apply:** harden Greenhouse apply preflight and add dry-run ([#122](https://github.com/nextwebb/career-agent/issues/122)) ([0994779](https://github.com/nextwebb/career-agent/commit/09947792bf6290a6f2372c4c48206bfffacdc9ce))

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
