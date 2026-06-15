---
description: Fill an ATS form via browser automation, upload PDFs, answer all required fields, then hand off to you for EEO fields and Submit
---

# apply

Fill an ATS job application form using browser automation. Upload CV + cover letter PDFs, answer all required fields, then hand off to the user for EEO fields and Submit.

## Triggers

User says: `/apply`, `fill the form for`, `apply for`, `complete the application for`, `fill in the job application`

## Arguments

```
/apply <role_id>
```

`role_id` — matches `roles/<role_id>.json`. If not provided, list available role IDs and ask the user to pick one.

## Prerequisites

Check before starting:

1. `profile.json` exists — if not, stop and ask user to create it
2. `roles/<role_id>.json` exists — if not, stop and direct user to run `/new-role <url>`
3. `generated/<output_prefix>_CV.pdf` exists — if not, run `/generate-cv <role_id>` first
4. Claude-in-Chrome extension is connected — required for all DOM-based form filling

## Steps

### 1. Load configs

Read `profile.json` and `roles/<role_id>.json`. Extract:

- `role.url` — the direct application URL (not job listing)
- `role.ats_platform` — `greenhouse`, `lever`, or `workable`
- `role.output_prefix` — used to locate the generated PDFs
- All `role.custom_answers` fields
- All `profile` personal data needed for the form

### 2. Navigate to the application URL

```
mcp__Claude_in_Chrome__navigate { url: role.url }
```

**Platform-specific URL notes:**

- **Greenhouse embed** (when `role.url` contains `boards.greenhouse.io/embed`):  
  Navigate directly to the embed URL as a top-level page — do NOT try to interact with it inside an iframe on a company careers page. Cross-origin iframes block all DOM tools.
- **Workable**: URL must end in `/apply/` — e.g. `https://apply.workable.com/<company>/j/<id>/apply/`
- **Lever**: URL is typically `https://jobs.lever.co/<company>/<uuid>/apply`

Take a screenshot to verify the page loaded and the form is visible before proceeding.

### 3. Fill personal fields

Use `find` + `left_click` + `type` for all text inputs. Do NOT use `form_input` alone — it does not trigger React onChange events on Greenhouse or Workable.

Fill in this order:
1. First name
2. Last name
3. Email
4. Phone
5. Location / City (if required)
6. LinkedIn URL
7. GitHub URL (if field exists)
8. Portfolio / website (if field exists)
9. Any other personal fields visible

After filling each field, verify the value is present before moving to the next section.

### 4. Upload CV

Locate the CV file input using `find` with query "resume upload" or "CV upload" or "attach resume".

**Greenhouse hidden file inputs:**

```javascript
// Run via javascript_tool before file_upload
const el = document.querySelector('input[type="file"]');
el.style.opacity = '1';
el.style.display = 'block';
```

Then use `file_upload` with the ref.

**Workable:** file inputs are visible by default — use `find` to get the ref directly.

**Lever:** use `find` to locate the resume file input.

Upload path: `generated/<output_prefix>_CV.pdf`

Verify the filename appears on screen after upload. Take a screenshot.

### 5. Upload cover letter (if field exists)

Check if a cover letter upload field or text area exists.

- **File upload field:** upload `generated/<output_prefix>_CoverLetter.pdf`
- **Text area:** paste the cover letter text (read paragraphs from `role.cover_letter.paragraphs`)
- **Lever:** Lever has no cover letter file upload — always paste text if a cover letter field exists

### 6. Answer dropdown and select fields

**"How did you hear about this opportunity?"**
Use value from `role.custom_answers.hear_about_us`. Common values: `"LinkedIn"`, `"Referral"`, `"Company website"`.

For React-based dropdowns (Greenhouse): click the dropdown toggle → type to filter → click the matching option. Do not use `form_input` alone.

**Work authorisation / sponsorship:**
Use `role.custom_answers.work_authorization` and `role.custom_answers.visa_sponsorship`.

**Location / cities available:**
Use `role.custom_answers.cities_available` array.

**Salary expectation:**
Use `role.custom_answers.salary_expectation` if non-empty.

### 7. Answer custom text questions

For any free-text question that maps to a key in `role.custom_answers` (e.g. `why_company`), fill it.

**Reading check detection:** Before answering any "Why [company]?" or similarly titled question, check if the job description contains a hidden reading check phrase (e.g. "start your answer with the words X"). If the JD URL is accessible, fetch it via `get_page_text` and scan for such instructions. Include the required phrase if found.

### 8. Handle country / city comboboxes (Greenhouse)

Greenhouse uses React comboboxes for country and city. Standard approach:

1. `find` the combobox toggle button
2. `left_click` it to open
3. `type` the country or city name to filter
4. `find` the option in the dropdown list
5. `left_click` the option

Verify the value is selected before continuing.

### 9. Verify radio buttons

After clicking any radio button, verify selection via JavaScript:

```javascript
document.querySelectorAll('input[type="radio"][name="<field_name>"]')
  .forEach(r => console.log(r.value, r.checked))
```

If the expected radio is not checked, click it again as a standalone call (not inside a batch).

### 10. Scroll and confirm completeness

Scroll the full form from top to bottom. Take a screenshot at each major section. Check:

- No required fields are empty (look for red borders or asterisks)
- CV upload is confirmed
- All visible required questions are answered

### 11. Hand off

**Stop here. Do not click Submit.**

Report to the user:

```
✅ Form filled for <title> @ <company>
✅ CV uploaded: <filename>
✅ Cover letter: <uploaded|pasted|not required>

Fields filled:
  - [list every field you filled with the value]

Remaining (your action required):
  🔲 EEO / voluntary self-identification fields (gender, race, veteran status, disability)
  🔲 Click Submit

Tab: [tab ID or URL]
```

Wait for user confirmation before any further action on this form.

## Human-in-the-loop rules (always enforced)

Claude NEVER:
- Clicks Submit or any irreversible confirmation button
- Fills EEO / voluntary self-identification fields (gender, race, veteran status, disability status)
- Enters passwords or credentials of any kind

Claude ALWAYS:
- States exactly what it has filled and what the values are
- Flags any field it is uncertain about rather than guessing
- Waits for explicit user confirmation before any action after hand-off

## Platform quirks reference

| Platform | File input | React combobox | Cover letter |
|---|---|---|---|
| Greenhouse (direct) | Hidden — unhide via JS before upload | Click toggle → type → click option | File upload field |
| Greenhouse (embed) | Same as above | Same | Same |
| Lever | Visible | N/A | Text paste only |
| Workable | Visible — find returns ref directly | `form_input` sometimes works; fall back to click+type | File upload or text |

## Error handling

- Page not loading: take screenshot, check URL, try navigating again
- File upload failing on Greenhouse: run the JS unhide snippet, retry
- React field not accepting value: switch from `form_input` to `left_click` + `type`
- Radio not registering: re-click as standalone (not in a batch), re-verify via JS
- Cross-origin iframe blocking tools: navigate directly to the embed URL as a top-level page
