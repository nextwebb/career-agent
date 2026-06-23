# career-agent

Agentic job application workflow. Generates tailored CVs with deterministic quality gates and fills safe ATS fields via browser automation, then hands off sensitive fields and Submit to the user.

Philosophy: keep the workflow lightweight and local-first, put deterministic gates behind agent actions, and treat generated materials as review-ready drafts rather than guarantees of recruiter or ATS outcomes.

## Skills

- `/setup-profile`: Build profile.json from your CV or LinkedIn PDF: extracts work history, generates 3 CV variants, drafts source-backed per-job bullets for review
- `/generate-cv <role_id>`: Build ATS-safe CV + cover letter PDFs for a role and run deterministic quality gates
- `/apply <role_id>`: Fill safe ATS fields, upload PDFs, answer safe questions, hand off to user for sensitive fields + Submit
- `/new-role [url]`: Scaffold a new role config interactively
- `/track [role_id] [status]`: View pipeline, update application status, add notes
- `/source [country] [role_type]`: Find roles and verify source pages are open from your CV/LinkedIn/profile.json + optional company docs

## Key files

- `profile.json`: User's personal data (gitignored, never committed)
- `roles/<role_id>.json`: Per-role config with CV variant, cover letter, custom answers
- `.claude-plugin/plugin.json`: Claude Code plugin manifest
- `.codex-plugin/plugin.json`: Codex plugin manifest
- `AGENTS.md`: Codex repository guidance
- `src/cv_builder.py`: reportlab Platypus PDF engine (single-column, Helvetica, ATS-safe)
- `src/generate_application.py`: CLI PDF generator with quality gates: `python src/generate_application.py --role <role_id>`
- `src/quality_gates.py`: Deterministic PDF and content-hygiene quality gates
- `src/tracker.py`: Application pipeline tracker: `python src/tracker.py --list`
- `generated/`: Output PDFs (gitignored)

## ATS platforms supported

- **Greenhouse** (direct): `https://job-boards.greenhouse.io/<company>/jobs/<id>`
- **Greenhouse** (iframe embed): navigate to `https://boards.greenhouse.io/embed/job_app?for=<company>&token=<id>` as a top-level page: cross-origin iframes block all DOM tools
- **Lever**: `https://jobs.lever.co/<company>/<id>`
- **Workable**: `https://apply.workable.com/<company>/j/<id>/apply/`

## Known ATS quirks

- **File upload — primary path**: prefer the browser surface's native file upload API (e.g. Playwright `setInputFiles()`). For Chrome-extension paths, use a localhost HTTP server fetch or chunked `localStorage` — do NOT send a large inline base64 string to `Runtime.evaluate` (a 13 KB PDF produces a ~17 K-char literal that blocks the renderer and trips the CDP 30 s timeout). See `skills/apply/SKILL.md` Step 5. `mcp__claude-in-chrome__file_upload` requires base64 data, not filesystem paths (`paths` parameter is deprecated). Workable's `react-dropzone` does not re-render from DataTransfer injection — manual upload required.
- **Greenhouse file inputs**: label-scope the input to the CV or cover-letter field container; unhide with `el.style.opacity='1'; el.style.display='block'` before injection when needed; re-query after upload because React may replace the `<input>` node after a `change` event. The 2026-06-23 Monzo run observed visible resume upload success, but did not re-prove a separate cover-letter upload slot.
- **Greenhouse React comboboxes** (country, city, phone): label-scope to field container; never click a bare `[aria-label="Toggle flyout"]` — the adjacent Google Drive file-picker uses the same pattern. Phone country: scope to `[class*="phone"]` container. Direct value injection does not trigger React state — use native prototype setter or click+type.
- **Workable file inputs**: `inputs[1]` is the CV input (index 0 is photo); `react-dropzone` does not respond to DataTransfer injection — requires manual upload
- **Lever**: no file upload for cover letter: paste cover letter text into the platform's text field

## Human-in-the-loop rules

Claude NEVER:
- Clicks Submit or irreversible confirmation buttons, except when all pre-apply gates have passed, `record_submission.py` has been called with a pre-authorized approval token, and `profile.yolo_mode.enabled` is `true` with a valid authorization key for this platform and tier
- Fills EEO/voluntary self-identification fields (gender, race, ethnicity, veteran status, disability)
- Enters passwords or credentials
- Enters national IDs, SSN/tax IDs, passport/visa document numbers, or dates of birth
- Enters bank, payment, or payroll details
- Selects privacy, GDPR, data-retention, talent-pool, terms, consent, or attestation checkboxes
- Solves CAPTCHA or anti-bot challenges
- Answers fields requiring legal judgment or uncertain interpretation

Claude ALWAYS:
- Fills only safe required fields it can verify from profile.json and the role config
- States exactly what it has filled and what remains
- Flags any field it is uncertain about before leaving it blank

## Data model

```
profile.json          → personal info, links, experience, skills, CV variants
roles/<id>.json       → role-specific: URL, ATS platform, CV variant, cover letter, custom answers
generated/<prefix>_CV.pdf
generated/<prefix>_CoverLetter.pdf
```

## PDF spec

- Engine: reportlab Platypus
- Layout: single column, no tables, no images
- Font: Helvetica
- Colours: black body, #2563eb links
- Links: clickable (email, LinkedIn, GitHub, blog)
- ATS-safe: no headers/footers with text outside main flow, no two-column layouts
- Quality gates: generated PDFs must be readable, text-extractable, free of placeholder text, and complete enough for human review before applying
