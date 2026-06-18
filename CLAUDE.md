# career-agent

Agentic job application workflow. Generates tailored CVs and fills safe ATS fields via browser automation, then hands off sensitive fields and Submit to the user.

## Skills

- `/setup-profile`: Build profile.json from your CV or LinkedIn PDF: extracts work history, generates 3 CV variants, writes per-job bullets automatically
- `/generate-cv <role_id>`: Build ATS-optimised CV + cover letter PDFs for a role
- `/apply <role_id>`: Fill safe ATS fields, upload PDFs, answer safe questions, hand off to user for sensitive fields + Submit
- `/new-role [url]`: Scaffold a new role config interactively
- `/track [role_id] [status]`: View pipeline, update application status, add notes
- `/source [country] [role_type]`: Find verified open roles from your CV/LinkedIn/profile.json + optional company docs

## Key files

- `profile.json`: User's personal data (gitignored, never committed)
- `roles/<role_id>.json`: Per-role config with CV variant, cover letter, custom answers
- `.claude-plugin/plugin.json`: Claude Code plugin manifest
- `.codex-plugin/plugin.json`: Codex plugin manifest
- `AGENTS.md`: Codex repository guidance
- `src/cv_builder.py`: reportlab Platypus PDF engine (single-column, Helvetica, ATS-safe)
- `src/generate_application.py`: CLI PDF generator: `python src/generate_application.py --role <role_id>`
- `src/tracker.py`: Application pipeline tracker: `python src/tracker.py --list`
- `generated/`: Output PDFs (gitignored)

## ATS platforms supported

- **Greenhouse** (direct): `https://job-boards.greenhouse.io/<company>/jobs/<id>`
- **Greenhouse** (iframe embed): navigate to `https://boards.greenhouse.io/embed/job_app?for=<company>&token=<id>` as a top-level page: cross-origin iframes block all DOM tools
- **Lever**: `https://jobs.lever.co/<company>/<id>`
- **Workable**: `https://apply.workable.com/<company>/j/<id>/apply/`

## Known ATS quirks

- **Greenhouse hidden file inputs**: JS `el.style.opacity='1'; el.style.display='block'` before file upload
- **Greenhouse React comboboxes** (country, city): click toggle → type to filter → click option: direct value injection alone does not trigger React state
- **Workable file inputs**: visible by default
- **Lever**: no file upload for cover letter: paste cover letter text into the platform's text field

## Human-in-the-loop rules

Claude NEVER:
- Clicks Submit / irreversible confirmation buttons
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
