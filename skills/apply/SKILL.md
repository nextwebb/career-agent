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
4. A browser surface is available. In Codex, use Browser for public ATS pages and Chrome only when signed-in browser state, cookies, extensions, or file URL access are required. Codex Chrome `/apply` remains experimental unless `docs/apply-codex-chrome-verification.md` contains a non-submitted evidence record for the exact ATS case and URL pattern.
5. For Codex Chrome runs, review `docs/apply-codex-chrome-verification.md` before filling. If the ATS case is unverified, failed, ambiguous, or missing from the matrix, tell the user it is experimental and stop or proceed only with a manual fallback/handoff plan that never submits.

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
- **Greenhouse EU domain**: treat a confirmed Greenhouse EU application URL as `ats_platform: "greenhouse"` unless the repo intentionally adds and tests a separate supported value. In Codex Chrome, keep EU-domain automation experimental until the verification matrix records a non-submitted pass for that URL/domain pattern.
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
- bank, payment, payroll, or compensation account details
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

**Primary upload method — base64 DataTransfer injection (all platforms):**

The `mcp__claude-in-chrome__file_upload` tool requires a Claude Desktop version that passes file contents directly; older versions fail with "no longer accepts host filesystem paths." Use the base64 injection instead:

```python
# Step 1 — encode the PDF in Python
import base64
with open("generated/<output_prefix>_CV.pdf", "rb") as f:
    b64 = base64.b64encode(f.read()).decode()
```

```javascript
// Step 2 — inject via javascript_tool
(function() {
  const b64 = "<INSERT_BASE64_STRING>";
  const binary = atob(b64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
  const file = new File([bytes], "<filename>.pdf", { type: "application/pdf" });
  const input = document.querySelectorAll('input[type="file"]')[<index>];
  const dt = new DataTransfer();
  dt.items.add(file);
  input.files = dt.files;
  const tracker = input._valueTracker;
  if (tracker) tracker.setValue('');
  ['change','input'].forEach(ev => input.dispatchEvent(new Event(ev, {bubbles:true})));
  return `files=${input.files.length}`;
})()
```

**Confirmed behaviour by platform (2026-06-22):**
- **Lever:** injection works. UI shows "✅ Success!" with filename. Use `inputs[0]` (single file input).
- **Greenhouse:** unhide the input first (`el.style.opacity='1'; el.style.display='block'`), then inject. Expected to work — not yet confirmed end-to-end.
- **Workable:** injection sets `input.files` but Workable's `react-dropzone` component does **not** re-render. The file is in the DOM but the UI still shows "Choose file". Manual upload required on Workable until a `react-dropzone` compatible injection is confirmed. Use `inputs[1]` (index 0 is the photo input).

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

## Platform quirks reference

| Platform | File input | React combobox | Cover letter |
|---|---|---|---|
| Greenhouse (direct) | Hidden: unhide via JS before upload | Click toggle → type → click option | File upload field |
| Greenhouse (embed) | Same as above | Same | Same |
| Greenhouse (EU domain) | Treat as Greenhouse only after URL/domain verification | Same | Same |
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

---

## Yolo mode (autonomous submission)

Yolo mode allows the agent to Submit without per-application human confirmation.
It is opt-in, requires deliberate profile setup, and passes every application
through a gate battery before any Submit action.

**All gate failures fall to HITL — not hard abort.** The user sees what blocked.

### Step A — Yolo detection

Read `profile.yolo_mode`. If absent or `enabled: false`, use standard HITL flow (Step 12 above).

Call `src/yolo.py:is_yolo_enabled(profile)`. If it returns `False` (key mismatch or disabled):
- Report: `YOLO_AUTH_FAILED — falling back to HITL`
- Proceed with standard HITL flow; do not abort

### Step B — Pre-apply gates (autonomous mode)

Run gates 1–2 using `run_pre_apply_checks(autonomous=True)`:
1. `check_duplicate()` — halt: `DUPLICATE`
2. `check_artifacts_exist()` + `check_platform_supported()` — halt: `PLATFORM_CHECK_FAILED`

If either fails, fall to HITL.

Then run the yolo gate battery via `src/yolo.py:run_yolo_gates(profile, role_config, workspace_dir, tracker_path)`:

3. Tier in `permitted_tiers` — halt: `TIER_NOT_PERMITTED`, fall to HITL
4. Company not in `excluded_companies` — halt: `COMPANY_EXCLUDED`, fall to HITL
5. Daily cap check — halt: `DAILY_CAP_REACHED`
6. Cover letter present — halt: `COVER_LETTER_REQUIRED`
7. Cover letter specificity — halt: `QUALITY_GATE_FAILED`
8. jobqa workspace gate (`jobqa run <workspace_dir>`) — halt: `JOBQA_GATE_FAILED: {errors}`
   - jobqa warnings pass through and are logged in the sidecar
   - If `jobqa` is not in PATH: skip this gate, log a warning, continue

Generate the workspace before gate 8 using `src/jobqa_workspace.py:generate_jobqa_workspace()`.

### Step C — Autonomous form fill

Proceed with Steps 1–11 (load configs, navigate, classify, fill, upload, answer, scroll).
Do not pause at Step 12.

**Codex Chrome restriction applies here too.** Yolo mode does not bypass the Codex Chrome
experimental status established in Prerequisites 4–5. If running on Codex Chrome, the same
evidence requirement applies: `docs/apply-codex-chrome-verification.md` must contain a
non-submitted end-to-end pass record for the target ATS case. The gate battery is not a
substitute for that evidence.

### Step D — Pre-submit record

Before clicking Submit, call `src/record_submission.py` (packaged with career-agent — no
external dependency required) to write an audit log and satisfy the `missing_submission_log`
hard-fail criterion:

```
python <career_agent_root>/src/record_submission.py \
  <workspace_dir>/output/manifest.json \
  <ats_platform>:<job_url> \
  "yolo-pre-authorized:<authorization_key_prefix>" \
  audits/<role_id>_<timestamp>_submission.json
```

If `jobqa` was not run (workspace has no `output/manifest.json`), pass the `role_id` string
as the first argument instead — the script accepts either.

If `record_submission.py` exits non-zero: **abort with `SUBMISSION_LOG_FAILED`, do NOT click Submit.**
The `authorization_key_prefix` is the first 4 characters of `profile.yolo_mode.authorization_key`.

### Step E — Submit and confirm

Click Submit once. Call `check_confirmation_pattern(ats_platform, final_url, page_text)`:

- `confirmed` → proceed to Step F
- `ambiguous` → write sidecar `outcome: ambiguous`, tracker `autonomous_ambiguous`, **halt, do not retry**
- `failed` → write sidecar `outcome: failed`, tracker `autonomous_failed`, halt

### Step F — Post-submit

1. Take a screenshot of the confirmation page
2. Write audit sidecar via `src/audit.py:write_sidecar()` with `outcome: confirmed`
3. Update tracker status to `autonomous_submitted`

Report:
```
🤖 Autonomous submission completed: <title> @ <company>
   Outcome: confirmed
   Confirmation: <excerpt>
   Sidecar: audits/<role_id>_<timestamp>_submission.json
   Remaining: EEO fields (not filled — human action required if asked later)
```

### Yolo mode halt codes

| Code | Meaning | Action |
|---|---|---|
| `YOLO_AUTH_FAILED` | Key mismatch or yolo disabled | Fall to HITL |
| `DUPLICATE` | URL already in tracker | Halt |
| `PLATFORM_CHECK_FAILED` | Artifacts missing or platform unverified | Fall to HITL |
| `TIER_NOT_PERMITTED` | Role tier not in permitted_tiers | Fall to HITL |
| `COMPANY_EXCLUDED` | Company in excluded_companies | Fall to HITL |
| `DAILY_CAP_REACHED` | Autonomous cap met today | Halt |
| `COVER_LETTER_REQUIRED` | No cover letter paragraphs | Fall to HITL |
| `QUALITY_GATE_FAILED` | Placeholder or non-specific cover letter | Fall to HITL |
| `WORKSPACE_GENERATION_FAILED` | Translator raised an error | Fall to HITL |
| `JOBQA_GATE_FAILED` | jobqa exited non-zero | Fall to HITL |
| `SUBMISSION_LOG_FAILED` | record_submission.py exited non-zero | Abort — do NOT click Submit |
