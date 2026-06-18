---
name: apply
description: Fill an ATS form via browser automation, upload PDFs, answer safe required fields, then hand off for sensitive, consent, attestation, legal, and Submit controls
---

# apply

Fill an ATS job application form using browser automation. Upload CV + cover letter PDFs, answer safe required fields, then hand off to the user for sensitive, consent, attestation, legal, and Submit controls.

## Triggers

User says: `/apply`, `fill the form for`, `apply for`, `complete the application for`, `fill in the job application`

In Codex, invoke this skill with `$apply`, the skills/plugin selector, or natural language. Slash-command examples are Claude Code aliases, not Codex built-ins.

## Arguments

```
/apply <role_id>
```

`role_id`: matches `roles/<role_id>.json`. If not provided, list available role IDs and ask the user to pick one.

## Prerequisites

Check before starting:

1. `profile.json` exists: if not, stop and ask user to create it
2. `roles/<role_id>.json` exists: if not, stop and direct user to run `/new-role <url>`
3. `generated/<output_prefix>_CV.pdf` exists: if not, run `/generate-cv <role_id>` first
4. A browser surface is available. In Codex, use Browser for public ATS pages and Chrome only when signed-in browser state, cookies, extensions, or file URL access are required. Codex `/apply` remains experimental until issue #65 verifies non-submitted ATS workflows.

## Steps

### 1. Load configs

Read `profile.json` and `roles/<role_id>.json`. Extract:

- `role.url`: the direct application URL (not job listing)
- `role.ats_platform`: `greenhouse`, `lever`, or `workable`
- `role.output_prefix`: used to locate the generated PDFs
- All `role.custom_answers` fields
- All `profile` personal data needed for the form

If `role.ats_platform` is missing, `unknown`, or not one of `greenhouse`, `lever`, or `workable`, stop and hand off manually. Do not attempt unsupported ATS automation.

### 2. Navigate to the application URL

Open `role.url` in the available browser surface.

**Platform-specific URL notes:**

- **Greenhouse embed** (when `role.url` contains `boards.greenhouse.io/embed`):  
  Navigate directly to the embed URL as a top-level page: do NOT try to interact with it inside an iframe on a company careers page. Cross-origin iframes block all DOM tools.
- **Workable**: URL must end in `/apply/`: e.g. `https://apply.workable.com/<company>/j/<id>/apply/`
- **Lever**: URL is typically `https://jobs.lever.co/<company>/<uuid>/apply`

Take a screenshot to verify the page loaded and the form is visible before proceeding.

### 3. Sensitive-field classifier

Before filling any visible field, dropdown, radio group, checkbox, upload input, or mapped `role.custom_answers` key, inspect the field label, name, placeholder, help text, surrounding copy, and available options.

Do not fill the field when any of that text suggests:

- Submit, final confirmation, or irreversible action
- EEO, voluntary self-identification, demographic, gender, race, ethnicity, disability, veteran, or self-identification data
- Passwords, credentials, API keys, tokens, or account recovery answers
- National IDs, SSN/tax IDs, passport or visa document numbers, or date of birth
- Bank, payment, payroll, or compensation account details
- Privacy, GDPR, data protection, data retention, talent pool, marketing, terms, consent, disclosure, background check, attestation, authorization, or certification checkboxes
- CAPTCHA or anti-bot challenges
- Any field that requires legal judgment, an attestation of truth, or uncertain interpretation

This policy overrides `role.custom_answers`. If a custom answer key or mapped field looks sensitive, leave it blank and report it in the handoff.

### 4. Fill safe personal fields

Locate each text input, classify it using the sensitive-field policy above, click into safe fields only, and type the value. Do NOT rely on direct form value injection alone; it may not trigger React onChange events on Greenhouse or Workable.

Fill in this order:
1. First name
2. Last name
3. Email
4. Phone
5. Location / City (if required)
6. LinkedIn URL
7. GitHub URL (if field exists)
8. Portfolio / website (if field exists)
9. Any other non-sensitive personal fields visible after classification

After filling each field, verify the value is present before moving to the next section.

### 5. Upload CV

Locate the CV file input using visible labels such as "resume upload", "CV upload", or "attach resume".

**Greenhouse hidden file inputs:**

```javascript
// Evaluate before file upload if the browser tool supports JavaScript.
const el = document.querySelector('input[type="file"]');
el.style.opacity = '1';
el.style.display = 'block';
```

Then upload the file through the browser tool's file-upload action.

**Workable:** file inputs are visible by default.

**Lever:** locate the resume file input by label.

Upload path: `generated/<output_prefix>_CV.pdf`

Verify the filename appears on screen after upload. Take a screenshot.

### 6. Upload cover letter (if field exists)

Check if a cover letter upload field or text area exists.

- **File upload field:** upload `generated/<output_prefix>_CoverLetter.pdf`
- **Text area:** paste the cover letter text (read paragraphs from `role.cover_letter.paragraphs`)
- **Lever:** Lever has no cover letter file upload: always paste text if a cover letter field exists

### 7. Answer dropdown and select fields

**"How did you hear about this opportunity?"**
Use value from `role.custom_answers.hear_about_us`. Common values: `"LinkedIn"`, `"Referral"`, `"Company website"`.

For React-based dropdowns (Greenhouse): click the dropdown toggle, type to filter, then click the matching option. Do not rely on direct form value injection alone.

**Work authorisation / sponsorship:**
Use `role.custom_answers.work_authorization` and `role.custom_answers.visa_sponsorship`.

**Location / cities available:**
Use `role.custom_answers.cities_available` array.

**Salary expectation:**
Use `role.custom_answers.salary_expectation` if non-empty.

Do not answer work authorization, sponsorship, salary, or other custom fields when the visible field wording turns them into a legal attestation, consent, demographic, national-ID, or other sensitive-field decision. Hand off instead.

### 8. Answer custom text questions

For any free-text question that maps to a key in `role.custom_answers` (e.g. `why_company`), fill it.

**Reading check detection:** Before answering any "Why [company]?" or similarly titled question, check if the job description contains a hidden reading check phrase (e.g. "start your answer with the words X"). If the JD URL is accessible, read the rendered page text and scan for such instructions. Include the required phrase if found.

### 9. Handle country / city comboboxes (Greenhouse)

Greenhouse uses React comboboxes for country and city. Standard approach:

1. Locate the combobox toggle button
2. Click it to open
3. Type the country or city name to filter
4. Locate the option in the dropdown list
5. Click the option

Verify the value is selected before continuing.

### 10. Verify radio buttons

After clicking any radio button, verify selection via JavaScript:

```javascript
document.querySelectorAll('input[type="radio"][name="<field_name>"]')
  .forEach(r => console.log(r.value, r.checked))
```

If the expected radio is not checked, click it again as a standalone call (not inside a batch).

### 11. Scroll and confirm completeness

Scroll the full form from top to bottom. Take a screenshot at each major section. Check:

- No required fields are empty (look for red borders or asterisks)
- CV upload is confirmed
- All visible required questions are answered

### 12. Hand off

**Stop here. Do not click Submit.**

Report to the user:

```
✅ Form filled for <title> @ <company>
✅ CV uploaded: <filename>
✅ Cover letter: <uploaded|pasted|not required>

Fields filled:
  - [list every field you filled with the value]

Remaining (your action required):
  🔲 Sensitive, consent, attestation, legal, or EEO fields
  🔲 Click Submit

Tab: [tab ID or URL]
```

Wait for user confirmation before any further action on this form.

## Human-in-the-loop rules (always enforced)

The agent NEVER:
- Clicks Submit or any irreversible confirmation button
- Fills EEO / voluntary self-identification fields (gender, race, ethnicity, veteran status, disability status)
- Enters passwords or credentials of any kind
- Enters national IDs, SSN/tax IDs, passport/visa document numbers, or dates of birth
- Enters bank, payment, or payroll details
- Selects privacy, GDPR, data-retention, talent-pool, terms, consent, or attestation checkboxes
- Solves CAPTCHA or anti-bot challenges
- Answers fields requiring legal judgment or uncertain interpretation

The agent ALWAYS:
- States exactly what it has filled and what the values are
- Flags any field it is uncertain about rather than guessing
- Waits for explicit user confirmation before any action after hand-off

## Platform quirks reference

| Platform | File input | React combobox | Cover letter |
|---|---|---|---|
| Greenhouse (direct) | Hidden: unhide via JS before upload | Click toggle → type → click option | File upload field |
| Greenhouse (embed) | Same as above | Same | Same |
| Lever | Visible | N/A | Text paste only |
| Workable | Visible | Direct value injection can miss React state; fall back to click+type | File upload or text |

## Error handling

- Page not loading: take screenshot, check URL, try navigating again
- File upload failing on Greenhouse: run the JS unhide snippet, retry
- React field not accepting value: switch to click+type
- Radio not registering: re-click as standalone (not in a batch), re-verify via JS
- Cross-origin iframe blocking tools: navigate directly to the embed URL as a top-level page
- Unsupported ATS, CAPTCHA, login wall, hidden required field, or ambiguous consent/legal field: stop and hand off with the exact field label and URL
- Multiple file inputs, multi-step flow, or hidden required fields that cannot be confidently classified: stop and hand off with screenshots and the field labels found
