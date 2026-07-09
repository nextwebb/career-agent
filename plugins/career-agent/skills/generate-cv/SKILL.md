---
name: generate-cv
description: Build ATS-safe CV and cover letter PDFs tailored to a specific role using reportlab Platypus
---

# generate-cv

Generate an ATS-safe CV + cover letter PDF pair for a specific role, then run deterministic quality gates before the user reviews or applies.

## Triggers

User says: `/generate-cv`, `generate my CV for`, `build my CV`, `create CV for`, `make my resume for`

In Codex, invoke this skill with `$generate-cv`, the skills/plugin selector, or natural language. Slash-command examples are Claude Code aliases, not Codex built-ins.

## Arguments

```
/generate-cv <role_id>
```

`role_id`: matches a filename under `roles/<role_id>.json`. If not provided, list available role IDs from the `roles/` directory and ask the user to pick one.

## Role config keys (rendering behaviour)

- `openness` *(optional)* — banner line shown under the headline. Overrides `profile.openness`. Omit the key entirely to inherit the profile-level default; set to `""` to suppress the banner for this role.
- `additional_experience` *(optional)* — list of one-line summaries for older/minor roles. Rendered as a single condensed line prefixed `Earlier experience:` and joined by ` · ` to preserve page budget. Set to `[]` to suppress the line for this specific role even when `profile.additional_experience` has entries; omit the key entirely to inherit the profile list.
- `location_strategy` *(optional)* — per-context location rendering override resolved by `src/location_strategy.py::resolve_location`. Applies to the CV contact line, cover-letter contact line, ATS location field, availability banner (renders in the openness slot when set), and relocation statement (renders as an extra line under the availability banner when set). Falls through to `profile.location_strategy_defaults` and then to legacy `profile.location` / `profile.openness`. See `profile.example.json` and `roles.example/example_role.json` for the supported strategy values.

## Steps

### 1. Load data

Read `profile.json`. If it does not exist, tell the user to copy `profile.example.json` to `profile.json` and fill in their details. Stop.

Read `roles/<role_id>.json`. If it does not exist, tell the user to create it (or run `/new-role`) and stop.

### 2. Resolve CV variant

The role config's `variant` field is `A`, `B`, or `C`. `A` targets AI/LLM/Evaluation, `B` targets Data Platform/Pipelines, and `C` targets Senior Backend/APIs.

The selected variant pulls `headline` and `summary` from `profile.variants.<variant>` (only if the role config does not already set those keys) and drives per-job bullet selection.

For each job in `profile.experience`, check if the role config has `experience_overrides` for that job ID. If yes, use those bullets. If no, use the variant-specific bullets from `profile.experience[i].bullets[variant]`. Fall back to `default` if the variant key is missing.

### 3. Validate claims

Use only facts present in `profile.json`, the role config, or explicit user-provided context. Do not invent achievements, metrics, employers, dates, eligibility claims, technologies, or public links.

If evidence is missing, omit the claim or flag it for review. Generated CVs and cover letters are review-ready drafts, not guarantees of recruiter or ATS interpretation.

### 4. Generate CV PDF

Resolve `<career_agent_root>` as the installed package or plugin root that contains `src/generate_application.py`. If running from a repo checkout and `src/generate_application.py` exists in the current directory, the current directory is `<career_agent_root>`.

Do not assume the user's working directory is the package root. The script path comes from `<career_agent_root>`, while `profile.json`, `roles/`, and `generated/` are read and written in the user's current workspace.

Run:

```bash
python3 "<career_agent_root>/src/generate_application.py" --role <role_id>
```

The script reads `profile.json` + `roles/<role_id>.json` and writes:

```
generated/<output_prefix>_CV.pdf
generated/<output_prefix>_CoverLetter.pdf
```

If the packaged script cannot be found, stop and report that the career-agent package or plugin installation is incomplete.

### 5. PDF spec

**Engine:** reportlab Platypus
**Layout:** single column, no tables, no images
**Font:** Helvetica (body 10pt, headings 12pt bold, name 16pt bold)
**Colours:** black body text, `#2563eb` for links
**Links:** clickable: email, LinkedIn, GitHub, blog/website

**ATS-safe rules:**
- No two-column layouts
- No headers/footers that contain text outside the main Platypus story
- No embedded images or logos
- No text boxes with absolute positioning

**Structure order:**
1. Name + headline
2. Contact line: email | phone | location | LinkedIn | GitHub | website
3. Professional Summary (variant-specific)
4. Core Skills
5. Professional Experience (reverse chronological, variant-ordered bullets)
6. Earlier experience *(optional — single condensed line: `Earlier experience: Role @ Company · Role @ Company`)*
7. Education
8. Projects *(optional — merges `open_source` experience entries with `role.projects`)*
9. Awards & Recognition *(optional — sourced from `profile.certifications`)*

**Cover letter structure:**
1. Applicant name + contact line (top)
2. Date
3. Salutation from role config
4. Paragraphs from `role.cover_letter.paragraphs`
5. Closing from `role.cover_letter.closing`
6. Name

### 6. Quality gates

The generator runs deterministic quality gates after writing the PDFs.

Hard failures stop the command unless `--no-quality-gates` is used for diagnostics:
- PDF is unreadable or not text-extractable
- Required CV sections are missing
- Placeholder text appears in generated output
- Name/email or cover-letter role context is missing
- Embedded images are detected in ATS-safe PDFs

Warnings do not block generation, but must be surfaced for review:
- CV is longer than 2 pages
- Cover letter is longer than 1 page
- Expected PDF links are not exposed as clickable annotations
- Repeated bullets, low metric density, or generic wording are detected

`location_consistency` warnings (warning-only, never block) surface configured stories that look contradictory. Sourced from `src/location_strategy.py::collect_location_warnings`:
- `cv_contact` resolves to `remote_label` but `role_config["location"]` names a specific city
- Any strategy is `generated_role_specific` but the corresponding role field is missing
- Any strategy references `custom:<key>` but `profile.location_presentations.custom.<key>` is not defined
- Legacy `profile["location"]` and `profile["location_facts"]["current_residence"]` disagree

### 7. Confirm output

After generation, report:

```
CV:             generated/<prefix>_CV.pdf
Cover letter:   generated/<prefix>_CoverLetter.pdf
Variant:        <A|B|C>: <label>
Role:           <title> @ <company>
Quality gates:  PASS/WARN/FAIL summary
```

Ask: "Ready to apply? Use `/apply <role_id>` in Claude Code or `$apply <role_id>` in Codex. Codex Chrome `/apply` remains experimental until the verification matrix has non-submitted evidence for the target ATS case."

## Error handling

- `profile.json` missing → stop, instruct user to create it
- `roles/<role_id>.json` missing → stop, instruct user to create it, run `/new-role` in Claude Code, or invoke `$new-role` in Codex
- `reportlab` not installed → `pip install reportlab --break-system-packages`
- `pypdf` not installed → `pip install -r requirements.txt`
- `generated/` directory missing → create it
