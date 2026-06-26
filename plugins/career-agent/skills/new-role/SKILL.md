---
name: new-role
description: Scaffold a role config by fetching and analysing a job posting, detecting the ATS platform, and pre-filling roles/<role_id>.json
---

# new-role

Scaffold a new role config file interactively. Inspects the job posting, detects the ATS platform, pre-fills what it can, and saves a ready-to-edit `roles/<role_id>.json`.

## Triggers

User says: `/new-role`, `add a role`, `set up a role`, `new job`, `create role config`, `add application for`

In Codex, invoke this skill with `$new-role`, the skills/plugin selector, or natural language. Slash-command examples are Claude Code aliases, not Codex built-ins.

## Arguments

```
/new-role [url]
```

`url`: the job listing or application URL. If not provided, ask the user for it before proceeding.

## Steps

### 1. Fetch the job description

Fetch the provided URL with the available web retrieval tool.

- If the page returns only HTML shell / meta tags (client-rendered), use a browser surface to render the full page and read the visible page text. In Codex, use Browser for public pages and Chrome only when signed-in browser state is required.
- Extract: job title, company name, location, key requirements.

### 2. Detect ATS platform and application URL

Examine the URL and page content:

| Signals | Platform | Application URL pattern |
|---|---|---|
| `greenhouse.io` in URL or page links | Greenhouse | `https://job-boards.greenhouse.io/<company>/jobs/<id>` |
| `boards.greenhouse.io/embed` | Greenhouse embed | Navigate to embed URL as top-level |
| `jobs.lever.co` | Lever | `https://jobs.lever.co/<company>/<uuid>/apply` |
| `apply.workable.com` | Workable | `https://apply.workable.com/<company>/j/<id>/apply/` |

Set `ats_platform` accordingly. If undetectable, set `"ats_platform": "unknown"` and note it.

### 3. Determine CV variant

Analyse the job title and key requirements:

- **A**: Primary focus on LLM, evaluation, AI safety, ML systems, model training
- **B**: Primary focus on data engineering, ETL/ELT, Airflow, Spark, data platform
- **C**: Primary focus on backend APIs, microservices, open-source, developer tooling, general SWE

State which variant you picked and why, in one sentence.

### 4. Generate role_id

`role_id` = `<company_slug>_<title_slug>_<YYYY>`, e.g. `stripe_backend_2026`.

- Lowercase, underscores only, no special characters
- Check that no file named `roles/<role_id>.json` already exists; if it does, append `_2` etc.

### 5. Scaffold the role config

Write `roles/<role_id>.json` using this template, filled with what you extracted:

```json
{
  "role_id": "<role_id>",
  "company": "<company>",
  "title": "<title>",
  "location": "<location>",
  "url": "<direct_application_url>",
  "ats_platform": "<greenhouse|lever|workable|unknown>",
  "variant": "<A|B|C>",
  "openness": "Open to fully remote roles globally and relocation to <location> for the right opportunity.",
  "output_prefix": "<FirstName_LastName_Company_Role_YYYY-MM>",
  "custom_answers": {
    "hear_about_us": "LinkedIn",
    "visa_sponsorship": "",
    "work_authorization": "",
    "cities_available": [],
    "why_company": "",
    "salary_expectation": ""
  },
  "cover_letter": {
    "salutation": "Dear <Company> Engineering Team,",
    "paragraphs": [
      "TODO: Opening: specific hook to this company and role...",
      "TODO: Paragraph 2: relevant experience, concrete evidence...",
      "TODO: Paragraph 3: fit with the JD requirements...",
      "TODO: Closing: availability and call to action."
    ],
    "closing": "Best regards,"
  },
  "experience_overrides": {},
  "notes": "Added <YYYY-MM-DD>. Status: draft."
}
```

Use `profile.json` to fill `output_prefix` with the user's actual name. Pre-fill `openness` by substituting the job location for `<location>` so the CV banner is role-specific; leave the field as-is if no location was extractable. Users can edit the line after scaffolding, or omit it entirely to fall back to `profile.openness`.

### 6. Check for reading check phrases

Scan the job description text for hidden instructions like:
- "start your answer with"
- "begin your response with"
- "to show you read this"
- "include the phrase"
- "your first sentence must"

If found, note the exact phrase and field it applies to in the `notes` field and in your report to the user. This is a common filter technique used by companies to check application quality.

### 7. Report

```
✅ Created: roles/<role_id>.json

  Company:  <company>
  Title:    <title>
  Platform: <ats_platform>
  Variant:  <A|B|C>: <rationale>
  URL:      <application_url>

Action required:
  1. Fill in cover_letter.paragraphs in roles/<role_id>.json
  2. Fill in custom_answers fields (visa, salary, why_company)
  3. Run /generate-cv <role_id> when ready
```

If a reading check phrase was found:
```
⚠️  Reading check detected:
    Field: <field name>
    Required phrase: "<exact phrase>"
    This must appear in your answer: already noted in roles/<role_id>.json
```

## Error handling

- URL not reachable: ask user to paste the job description text directly
- ATS undetectable: set `"unknown"`, list the signals found, ask user to fill the URL manually
- `profile.json` not found: scaffold with placeholder `output_prefix` and note it
