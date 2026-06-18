---
name: generate-cv
description: Build ATS-optimised CV and cover letter PDFs tailored to a specific role using reportlab Platypus
---

# generate-cv

Generate an ATS-optimised CV + cover letter PDF pair for a specific role.

## Triggers

User says: `/generate-cv`, `generate my CV for`, `build my CV`, `create CV for`, `make my resume for`

In Codex, invoke this skill with `$generate-cv`, the skills/plugin selector, or natural language. Slash-command examples are Claude Code aliases, not Codex built-ins.

## Arguments

```
/generate-cv <role_id>
```

`role_id`: matches a filename under `roles/<role_id>.json`. If not provided, list available role IDs from the `roles/` directory and ask the user to pick one.

## Steps

### 1. Load data

Read `profile.json`. If it does not exist, tell the user to copy `profile.example.json` to `profile.json` and fill in their details. Stop.

Read `roles/<role_id>.json`. If it does not exist, tell the user to create it (or run `/new-role`) and stop.

### 2. Resolve CV variant

The role config's `variant` field is `A`, `B`, or `C`.

- **A**: AI/LLM/Evaluation roles: order experience bullets by `impact_order` in `profile.variants.A`
- **B**: Data Platform/Pipelines: order by `profile.variants.B.impact_order`
- **C**: Senior Backend/APIs: order by `profile.variants.C.impact_order`

For each job in `profile.experience`, check if the role config has `experience_overrides` for that job ID. If yes, use those bullets. If no, use the variant-specific bullets from `profile.experience[i].bullets[variant]`. Fall back to `default` if the variant key is missing.

### 3. Generate CV PDF

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

### 4. PDF spec

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
3. Summary (variant-specific)
4. Experience (reverse chronological, variant-ordered bullets)
5. Education
6. Skills

**Cover letter structure:**
1. Applicant name + contact line (top)
2. Date
3. Salutation from role config
4. Paragraphs from `role.cover_letter.paragraphs`
5. Closing from `role.cover_letter.closing`
6. Name

### 5. Confirm output

After generation, report:

```
✅ CV:           generated/<prefix>_CV.pdf
✅ Cover letter: generated/<prefix>_CoverLetter.pdf
Variant:        <A|B|C>: <label>
Role:           <title> @ <company>
```

Ask: "Ready to apply? Use `/apply <role_id>` in Claude Code or `$apply <role_id>` in Codex. Codex Chrome `/apply` remains experimental until the verification matrix has non-submitted evidence for the target ATS case."

## Error handling

- `profile.json` missing → stop, instruct user to create it
- `roles/<role_id>.json` missing → stop, instruct user to create it, run `/new-role` in Claude Code, or invoke `$new-role` in Codex
- `reportlab` not installed → `pip install reportlab --break-system-packages`
- `generated/` directory missing → create it
