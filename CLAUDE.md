# career-agent

Agentic job application workflow. Generates tailored CVs and fills ATS forms via browser automation.

## Skills

- `/generate-cv <role_id>` — Build ATS-optimised CV + cover letter PDFs for a role
- `/apply <role_id>` — Fill the ATS form, upload PDFs, answer questions, hand off to user for EEO + Submit
- `/new-role [url]` — Scaffold a new role config interactively

## Key files

- `profile.json` — User's personal data (gitignored, never committed)
- `roles/<role_id>.json` — Per-role config with CV variant, cover letter, custom answers
- `src/cv_builder.py` — reportlab Platypus PDF engine (single-column, Helvetica, ATS-safe)
- `src/generate_application.py` — CLI PDF generator: `python src/generate_application.py <role_id>`
- `generated/` — Output PDFs (gitignored)

## ATS platforms supported

- **Greenhouse** (direct): `https://job-boards.greenhouse.io/<company>/jobs/<id>`
- **Greenhouse** (iframe embed): navigate to `https://boards.greenhouse.io/embed/job_app?for=<company>&token=<id>` as a top-level page — cross-origin iframes block all DOM tools
- **Lever**: `https://jobs.lever.co/<company>/<id>`
- **Workable**: `https://apply.workable.com/<company>/j/<id>/apply/`

## Known ATS quirks

- **Greenhouse hidden file inputs**: JS `el.style.opacity='1'; el.style.display='block'` before `file_upload`
- **Greenhouse React comboboxes** (country, city): click toggle → type to filter → click option — `form_input` alone does not trigger React state
- **Workable file inputs**: visible by default, `find` returns correct ref directly
- **Lever**: no file upload for cover letter — paste cover letter text into the platform's text field

## Human-in-the-loop rules

Claude NEVER:
- Clicks Submit / irreversible confirmation buttons
- Fills EEO/voluntary self-identification fields (gender, race, veteran status, disability)
- Enters passwords or credentials

Claude ALWAYS:
- Fills all required fields it can verify from profile.json and the role config
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
