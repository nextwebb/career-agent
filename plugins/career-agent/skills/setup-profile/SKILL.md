---
name: setup-profile
description: Build profile.json from your CV or LinkedIn PDF by extracting work history, generating 3 CV variants, and writing per-job bullets automatically
---

# setup-profile

Bootstrap `profile.json` from a CV, resume, or LinkedIn PDF export. Extracts your work history, infers three audience-specific CV variants (AI/LLM, Data Platform, Backend), and writes one default bullet set plus three audience-specific variants so you are ready to generate tailored applications immediately.

## Triggers

User says: `/setup-profile`, `/career-agent:setup-profile`, `set up my profile`, `build my profile from my CV`, `import my resume`, `create profile.json`

In Codex, invoke this skill with `$setup-profile`, the skills/plugin selector, or natural language. Slash-command examples are Claude Code aliases, not Codex built-ins.

## Arguments

```
/setup-profile [optional: path to PDF or DOCX]
```

No argument required: the agent accepts a file upload or pasted text in the same message.

## Inputs (priority order)

1. **LinkedIn PDF export**: most structured source. Export via LinkedIn → Me → Settings & Privacy → Data privacy → Get a copy of your data → select "The works" or use the browser print-to-PDF on your profile page.
2. **CV or resume PDF / DOCX**: uploaded directly to the conversation.
3. **Plain text CV**: pasted directly into the chat.
4. **Nothing provided**: the agent asks: "Please paste your CV text or upload your CV/LinkedIn PDF and I'll build your profile.json."

## Steps

### 1. Accept and validate input

Check what the user provided:

- If a file is attached, read it.
- If text is pasted, use it.
- If neither, prompt the user and stop until they provide input.

Do not proceed with fabricated data. Every field written to `profile.json` must come from the source material or be explicitly flagged as an assumption.

### 2. Parse: extract structured data

Extract the following from the CV or LinkedIn export:

**Contact info:**
- Full name (split into `first`, `last`, `preferred`)
- Email address
- Phone number (extract country code if present; default to `+1` only if location is clearly US/CA, otherwise leave blank and flag)
- Location (city, country)
- Relocation preference (infer from "open to relocation" language; leave blank if not stated)
- LinkedIn URL
- GitHub URL
- Personal website / portfolio URL
- Twitter / X URL
- Blog URL

**Professional summary:**
- Total years of experience (calculate from earliest role start date to today; state the calculation explicitly)
- Current or most recent headline / job title
- Top-level summary paragraph if one exists

**Work history**: for each role:
- Job title
- Company name
- Industry / team (if stated)
- Location
- Start date and end date (or "Present")
- All bullet points or responsibility statements verbatim

**Education**: for each entry:
- Degree
- Institution
- Graduation year

**Skills**: capture all listed skills, grouping them as they appear (Languages, Frameworks, Cloud & Infra, etc.)

### 3. Infer CV variants

Analyse the parsed work history and skills to determine which of the three audience variants is the strongest primary fit:

- **Variant A: AI/LLM/Evaluation**: experience with ML, LLMs, model evaluation, alignment, AI safety, embeddings, RAG, prompt engineering, evals frameworks, Weights & Biases, MLflow
- **Variant B: Data Platform/Pipelines**: experience with data engineering, ETL/ELT, Airflow, Spark, dbt, Kafka, data warehouses, AWS Glue, Redshift, BigQuery, pipeline orchestration
- **Variant C: Senior Backend/APIs**: experience with REST/gRPC APIs, microservices, distributed systems, backend frameworks (FastAPI, Django, Flask, Express, Go), open-source contributions, developer tooling

For each variant, produce:
- `label`: short audience label (e.g. "AI/LLM/Evaluation")
- `headline`: 1-line headline tailored to that audience, ≤ 12 words
- `summary`: 2-3 sentence paragraph: lead with years of experience, name the most relevant technical stack for that audience, close with availability/location preference
- `impact_order`: ordered list of 4-6 impact statement keys (defined in step 4) ranked from most to least relevant for that audience

If a variant fit is ambiguous (e.g. no clear AI or data experience), say so: "I could not find strong evidence for Variant A (AI/LLM). I've written a best-effort headline and summary: please review and adjust."

### 4. Build impact_statements

Identify 4-6 named impact areas from the work history. These are reusable bullet building blocks that appear in the CV summary section.

**Naming convention:** short snake_case key, e.g. `llm_eval`, `etl`, `distributed`, `agentic`, `api_design`, `open_source`

For each impact area, write:
- `title`: short display title (3-6 words, title case)
- `body`: 2-3 sentences. Lead with a metric or concrete outcome where the CV provides one. Be specific: name technologies, scale, or business impact. Never invent numbers not present in the source.

Example structure (do not copy verbatim: fill from actual CV):
```json
"llm_eval": {
  "title": "LLM Evaluation",
  "body": "Built evaluation harness for <X> models across <Y> benchmarks, reducing manual review time by <Z>%. Integrated with <tool> to track regression across model versions."
}
```

### 5. Write per-job bullets × 4

For every role in `experience`, produce four bullet sets:

- **`default`**: neutral, achievement-focused bullets suitable for any audience. 3-5 bullets per role.
- **`A`**: same role reframed for AI/LLM/Evaluation audiences: emphasise data quality pipelines that fed models, evaluation logic, experiment tracking, inference infra, or anything ML-adjacent. If the role has no AI angle, write the closest honest approximation and note it.
- **`B`**: reframed for Data Platform audiences: emphasise pipeline reliability, data volumes, orchestration complexity, schema design, warehouse optimisation, SLA adherence.
- **`C`**: reframed for Backend/APIs audiences: emphasise API design, latency, throughput, service reliability (uptime/SLA), open-source contribution, developer experience.

Rules:
- Never invent facts not in the source material.
- It is acceptable to emphasise different aspects of the same fact for different audiences.
- If a bullet truly has no honest angle for a variant, write the default bullet and note the assumption in the report.
- Each bullet should begin with a strong past-tense verb (Built, Designed, Reduced, Led, Migrated, Shipped, etc.).
- Aim for 3-5 bullets per role per variant; 2 is acceptable for short-tenure or early-career roles.

### 6. Check before overwriting

Before writing `profile.json`:

If `profile.json` already exists, ask:

```
profile.json already exists. Overwrite it? (yes/no)
```

If the user says no, stop. If yes, proceed.

If `profile.json` does not exist, proceed without asking.

### 7. Write profile.json

Write a complete, valid JSON file to `profile.json` in the project root. The file must match the exact schema from `profile.example.json`:

```json
{
  "name": { "first": "...", "last": "...", "preferred": "..." },
  "email": "...",
  "phone": { "country_code": "+X", "number": "...", "formatted": "+X..." },
  "location": "City, Country",
  "relocation": "...",
  "links": {
    "linkedin": "...",
    "github": "...",
    "website": "...",
    "twitter": "...",
    "blog": "..."
  },
  "years_experience": 7,
  "headline": "...",
  "summary": "...",
  "variants": {
    "A": { "label": "...", "headline": "...", "summary": "...", "impact_order": ["..."] },
    "B": { "label": "...", "headline": "...", "summary": "...", "impact_order": ["..."] },
    "C": { "label": "...", "headline": "...", "summary": "...", "impact_order": ["..."] }
  },
  "impact_statements": {
    "<key>": { "title": "...", "body": "..." }
  },
  "experience": [
    {
      "id": "job_1",
      "title": "...",
      "company": "...",
      "company_line": "Company · Industry · Location · Start – End",
      "bullets": {
        "default": ["..."],
        "A": ["..."],
        "B": ["..."],
        "C": ["..."]
      }
    }
  ],
  "education": [
    { "degree": "...", "institution": "...", "year": "..." }
  ],
  "skills": [
    { "label": "Languages", "items": "Python · TypeScript · ..." }
  ]
}
```

Do not include the `_comment` field from the example: it is only for the template.

If a field cannot be populated from the source (e.g. GitHub URL not found), write an empty string `""` and flag it in the report.

Roles must be listed in reverse chronological order (most recent first). Assign IDs `job_1`, `job_2`, ... starting from the most recent.

### 8. Report

After writing `profile.json`, output a structured report:

```
profile.json written successfully.

Extracted:
  Name:             Jane Doe
  Email:            jane@example.com
  Phone:            +15551234567
  Location:         Berlin, Germany
  LinkedIn:         https://www.linkedin.com/in/janedoe/
  GitHub:           [not found: update manually]
  Years experience: 7 (calculated from 2017-06 to 2024-06)
  Roles parsed:     3 (job_1, job_2, job_3)
  Education:        1 entry
  Skills groups:    3

Variant fit assessment:
  Primary:   C: Senior Backend/APIs (strongest signal: 5 backend API roles)
  Secondary: B: Data Platform (evidence: 2 years data pipeline work at Acme)
  Tertiary:  A: AI/LLM (limited evidence: mentioned LLM integration in job_1 bullets)

Assumptions made:
  - Phone country code defaulted to +44 based on location (London, UK)
  - Relocation field left blank: no mention in source
  - Variant A summary is best-effort: no dedicated ML/AI role found

Fields left blank (update manually):
  - links.github
  - links.twitter
  - links.blog
```

### 9. Offer edit loop

After the report, ask:

```
Tell me what to adjust: for example:
  - "Rewrite job_1 bullets for AI roles"
  - "Update my LinkedIn URL to https://..."
  - "Make Variant B the primary and reorder impact_order"
  - "Add a GitHub URL: https://github.com/..."
```

Apply any requested edits and re-write `profile.json`. Repeat until the user is satisfied or says "done" / "looks good".

## Evidence standard

- **Never invent facts** not present in the CV or LinkedIn export.
- **State assumptions explicitly** in the report (e.g. "I inferred 7 years experience from date ranges 2017–2024").
- **Flag ambiguity** rather than guess silently (e.g. "The source lists 'machine learning' but no specific models or frameworks: I've placed this under Variant A with low confidence").
- If a URL is partially visible (e.g. `linkedin.com/in/jane`) but not fully qualified, write what you can and flag it.

## Error handling

- No input provided → ask the user for their CV or LinkedIn PDF before proceeding.
- File cannot be read (corrupt PDF, unsupported format) → tell the user and ask them to paste the text instead.
- `profile.json` exists and user declines overwrite → stop cleanly: "No changes made. Your existing profile.json is untouched."
- Variant fit completely unclear → write best-effort variants and flag every uncertain field in the report.
- Skills section is missing from source → write an empty `skills` array and note it: "No skills section found: add your skills manually."
