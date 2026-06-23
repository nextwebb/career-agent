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
/apply <role_id> --dry-run
```

`role_id`: matches `roles/<role_id>.json`. If not provided, list available role IDs and ask the user to pick one.
`--dry-run`: print a redacted preflight plan via `src/generate_application.py --role <role_id> --dry-run`; do not open a browser, generate PDFs, upload files, update tracker state, or print raw applicant values.

## Prerequisites

Check before starting:

1. `profile.json` exists: if not, stop and ask user to create it
2. `roles/<role_id>.json` exists: if not, stop and direct user to run `/new-role <url>`
3. For live fills only, `generated/<output_prefix>_CV.pdf` exists: if not, run `/generate-cv <role_id>` first. Do not generate PDFs for `--dry-run`; the dry-run plan reports missing artifacts without creating them.
4. A browser surface is available. Preflight the selected browser surface before any ATS navigation. Browser setup failures, including metadata errors such as `sandboxCwd must be an absolute file URI`, are browser/tool setup failures; report them distinctly from ATS automation failures and stop or use only an explicitly approved fallback.
5. Open a fresh tab/page for every ATS run before navigating. Never reuse an arbitrary active tab. If the user explicitly asks to continue in an existing SPA tab, first clear `window.onbeforeunload`, patch `history.pushState` / `history.replaceState` only for the navigation attempt, and verify within 3 seconds that the URL changed. If navigation is blocked, stop with a setup-specific handoff reason.
6. In Codex, use Browser for public ATS pages and Chrome only when signed-in browser state, cookies, extensions, or file URL access are required. Codex Chrome `/apply` remains experimental unless `docs/apply-codex-chrome-verification.md` contains a non-submitted evidence record for the exact ATS case and URL pattern.
7. For Codex Chrome runs, review `docs/apply-codex-chrome-verification.md` before filling. If the ATS case is unverified, failed, ambiguous, or missing from the matrix, tell the user it is experimental and stop or proceed only with a manual fallback/handoff plan that never submits.

## Steps

### 0. Preflight and dry-run plan

Resolve the active package/plugin version and the active `skills/apply/SKILL.md` path before browser work. If a stale installed plugin copy differs from repo HEAD, report that drift before proceeding.

If the user requested `--dry-run`, run:

```
python3 <career_agent_root>/src/generate_application.py --role <role_id> --dry-run
```

Then stop. The dry run prints target URL, ATS platform, package/skill path, planned safe fields with redacted values, planned handoff fields, redacted artifact status, file sizes when files exist, and upload strategy. It does not open a browser, generate PDFs, upload files, update tracker state, or print raw applicant values.

For a live fill, preflight the selected browser surface, open a fresh tab/page (Prerequisites 5), and start elapsed-time logging before navigation.

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

Locate each text input, classify it using the sensitive-field policy above, click into safe fields only, and type the value.

**Do NOT set `.value` directly on a React-controlled input.** React 16+ uses a synthetic event system — direct DOM assignment does not trigger `onChange`, so the controlled value does not update and the field visually reverts. Use the native prototype setter pattern instead:

```javascript
function setReactValue(el, value) {
  const proto = el instanceof HTMLTextAreaElement
    ? HTMLTextAreaElement.prototype
    : HTMLInputElement.prototype;
  const setter = Object.getOwnPropertyDescriptor(proto, 'value')?.set;
  if (!setter) throw new Error('missing native value setter');
  setter.call(el, value);
  el.dispatchEvent(new Event('input', { bubbles: true }));
  el.dispatchEvent(new Event('change', { bubbles: true }));
  el.blur();
}
```

After each call, scroll away and back, then verify the visible value persists — this is why the function dispatches bubbled `input` and `change` events rather than setting `.value` alone. If the value still reverts, fall back to `click()` + character-by-character `type()`.

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

After filling each field, verify after blur and after scrolling away/back that the value is present and persists before moving to the next section.

### 5. Upload CV

Locate the CV file input by the field container's visible label such as "resume upload", "CV upload", or "attach resume". Scope the selector to that label's container — do not use `document.querySelectorAll('input[type="file"]')[0]` or any global index.

**Primary upload method — browser-native file upload when available:**

Use the browser surface's native file upload path when available, such as Playwright `setInputFiles()` or an equivalent browser-client file chooser API. This avoids large `Runtime.evaluate` payloads and gives the browser a normal file selection event.

Upload path: `generated/<output_prefix>_CV.pdf`

**Chrome-extension fallback — bounded transport only:**

Do not inject one large inline base64 string into `Runtime.evaluate` as a JS string literal. A 13 KB PDF produces a ~17 K-char base64 string; combined with `atob()` decoding and `Uint8Array` construction in a single CDP evaluate call, this blocks the renderer event loop synchronously and trips the CDP timeout (30 s outer / 40 s evaluate), disconnecting the debugger session.

If the browser surface cannot perform native file upload, use one of these bounded transports:

**Option A — localhost server fetch (preferred):**

Before browser automation, start a temporary HTTP server for the `generated/` directory:

```python
import threading, http.server, os, socket

class CORSHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        super().end_headers()
    def log_message(self, *a): pass

with socket.socket() as s:
    s.bind(('127.0.0.1', 0))
    port = s.getsockname()[1]

server = http.server.HTTPServer(('127.0.0.1', port), CORSHandler)
thread = threading.Thread(target=server.serve_forever, daemon=True)
os.chdir('/path/to/generated/')
thread.start()
# use port below; call server.shutdown() when done
```

In-page JS via `javascript_tool`:

```javascript
async function injectFileFromUrl(container, url, filename) {
  const buf = await fetch(url).then(r => {
    if (!r.ok) throw new Error('file fetch failed: ' + r.status);
    return r.arrayBuffer();
  });
  const file = new File([buf], filename, { type: 'application/pdf' });
  const input = container.querySelector('input[type="file"]');
  if (!input) throw new Error('missing scoped file input');
  const dt = new DataTransfer();
  dt.items.add(file);
  input.files = dt.files;
  const tracker = input._valueTracker;
  if (tracker) tracker.setValue('');
  ['change', 'input'].forEach(ev => input.dispatchEvent(new Event(ev, { bubbles: true })));
  return input.files.length;
}
// e.g. await injectFileFromUrl(container, 'http://127.0.0.1:' + port + '/<output_prefix>_CV.pdf', '<output_prefix>_CV.pdf')
```

`http://127.0.0.1` is a "potentially trustworthy origin" under the Secure Contexts spec, so Chrome permits the fetch from an HTTPS ATS page.

**Option B — sessionStorage chunking in small chunks (fallback):**

Use only when localhost fetch is unavailable. Split the base64 string into ~4 KB chunks across several `javascript_tool` calls, assemble in a final call, then clear storage. Do not write PDF chunks to persistent ATS `localStorage`.

```javascript
// Before call 1: remove leftovers from any interrupted attempt
Object.keys(sessionStorage)
  .filter(k => k.startsWith('_ca_chunk_'))
  .forEach(k => sessionStorage.removeItem(k));

// Calls 1-N: store chunks for this tab/session only
sessionStorage.setItem('_ca_chunk_0', chunk0);
sessionStorage.setItem('_ca_chunk_1', chunk1);

// Final call: assemble, inject, clean up
const chunkKeys = ['_ca_chunk_0', '_ca_chunk_1'];
try {
  const b64 = chunkKeys.map(k => sessionStorage.getItem(k) || '').join('');
  const binary = atob(b64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
  const file = new File([bytes], '<filename>.pdf', { type: 'application/pdf' });
  // then DataTransfer inject as in Option A
} finally {
  chunkKeys.forEach(k => sessionStorage.removeItem(k));
}
```

**Greenhouse remount handling:**

Greenhouse's React reconciler may replace the `<input type="file">` DOM node after a `change` event, clearing `input.files` on the new node. Use a `MutationObserver` on the upload container to detect and re-inject:

```javascript
function injectWithRemountGuard(container, fileObj) {
  function inject(input) {
    if (!input) return;
    input.style.opacity = '1';
    input.style.display = 'block';
    const dt = new DataTransfer();
    dt.items.add(fileObj);
    input.files = dt.files;
    const tracker = input._valueTracker;
    if (tracker) tracker.setValue('');
    ['change', 'input'].forEach(ev => input.dispatchEvent(new Event(ev, { bubbles: true })));
  }
  // Keep observing until the 3 s safety timeout: Greenhouse can remount the input
  // more than once (initial change-event + later form-level validation), so we
  // re-inject every time the slot reappears empty, not just on the first remount.
  const obs = new MutationObserver(() => {
    const fresh = container.querySelector('input[type="file"]');
    if (fresh && fresh.files.length === 0) inject(fresh);
  });
  obs.observe(container, { childList: true, subtree: true });
  setTimeout(() => obs.disconnect(), 3000);
  inject(container.querySelector('input[type="file"]'));
}
```

If both CV and cover-letter slots exist, invoke this separately per label-scoped container with the correct `File` object. Verify the visible filename after each injection — a mismatched or empty filename means the inject did not hold.

**Observed behaviour by platform (do not overclaim):**
- **Lever:** previous non-submitting runs observed visible filename success after upload.
- **Greenhouse:** label-scope the input; unhide before inject when needed; use a remount guard. Resume upload has been observed succeed in a prior run; the separate cover-letter upload slot has not been re-proven end-to-end on this skill version and remains a known gap.
- **Workable:** `react-dropzone` does not re-render from DataTransfer injection — UI shows "Choose file" despite `input.files` being set. Manual upload required until a Workable-compatible injection is confirmed.

After injection, re-query the file input after every upload by re-reading the container. Verify the filename appears on screen after upload. Record upload method, payload size, field label, remount/reacquire count, distinct filenames per slot, visible filename result, and elapsed ms.

### 6. Upload cover letter (if field exists)

Check if a cover letter upload field or text area exists.

- **File upload field:** upload `generated/<output_prefix>_CoverLetter.pdf`
- **Text area:** paste the cover letter text (read paragraphs from `role.cover_letter.paragraphs`)
- **Lever:** Lever has no cover letter file upload: always paste text if a cover letter field exists

### 7. Answer dropdown and select fields

**"How did you hear about this opportunity?"**
Use value from `role.custom_answers.hear_about_us`. Common values: `"LinkedIn"`, `"Referral"`, `"Company website"`.

For React-based dropdowns (Greenhouse): scope the control to the field container's visible label, use `setReactValue` or `click()` + `type()` inside that container, then click the matching option. Do not rely on direct form value injection alone.

**Work authorisation / sponsorship:**
Use `role.custom_answers.work_authorization` and `role.custom_answers.visa_sponsorship`.

Hand off US-person status, tax status, right-to-work confirmations, immigration attestations, and any authorization question phrased as a certification, legal declaration, or consent. Do not infer these answers from location or resume history.

**Location / cities available:**
Use `role.custom_answers.cities_available` array.

**Salary expectation:**
Use `role.custom_answers.salary_expectation` if non-empty.

Do not answer work authorization, sponsorship, salary, or other custom fields when the visible field wording turns them into a legal attestation, consent, demographic, national-ID, or other sensitive-field decision. Hand off instead.

### 8. Answer custom text questions

For any free-text question that maps to a key in `role.custom_answers` (e.g. `why_company`), fill it.

**Reading check detection:** Before answering any "Why [company]?" or similarly titled question, check if the job description contains a hidden reading check phrase (e.g. "start your answer with the words X"). If the JD URL is accessible, read the rendered page text and scan for such instructions. Include the required phrase if found.

### 9. Handle country / city comboboxes (Greenhouse)

Greenhouse uses React comboboxes for country and city. Use label-scoped controls only — never positional refs or unscoped global selectors:

1. Locate the field container by its visible label text ("Country", "Location", "City", or the exact question label).
2. Inside that container only, find `input[role="combobox"]`, `[aria-autocomplete="list"]`, or the container's listbox trigger.
3. **Never click a generic `[aria-label="Toggle flyout"]` without first confirming it is inside the intended field container.** The Google Drive / Resume file-picker uses the same flyout pattern and sits adjacent to the phone/country field in Greenhouse's accessibility tree. Clicking the wrong element opens a Google Drive modal that blocks all further automation until dismissed.
4. Click the scoped input/trigger, type the intended value with React-safe events, locate the matching option in the opened listbox, and click it.
5. Verify selected visible text after blur and after scrolling away/back.

**Phone country combobox:** The phone country selector is adjacent to the Resume/Google Drive file-picker toggle in the DOM. Scope to the phone container:

```javascript
const phoneContainer = [...document.querySelectorAll('[class*="phone" i], [data-qa*="phone" i]')]
  .find(el => el.querySelector('input'));
if (!phoneContainer) throw new Error('phone container not found; hand off phone country selector');
const phoneInput = phoneContainer.querySelector('input[role="combobox"], [aria-autocomplete="list"], input');
if (!phoneInput) throw new Error('phone combobox not found inside scoped phone container');
// Click phoneInput, type country name, click the matching listbox option
```

If the flyout that opens shows file/Drive icons rather than country names, close it immediately, record a selector failure, and hand off the phone field.

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

Record a structured, redacted observation per section: timestamp, browser surface, field label, action type, selector strategy, upload method and payload size, remount/reacquire count, visible filename result, React state verification result, and final proof that Submit was not clicked.

### 12. Hand off

**Stop here. Do not click Submit.**

Report to the user:

```
Form filled for <title> @ <company>
CV uploaded: <filename>
Cover letter: <uploaded|pasted|not required>

Fields filled:
  - [list every field you filled with the value]

Remaining (your action required):
  Sensitive, consent, attestation, legal, or EEO fields
  Click Submit

Tab: [tab ID or URL]
```

Wait for user confirmation before any further action on this form.

## Platform quirks reference

| Platform | File input | React state | React combobox | Cover letter |
|---|---|---|---|---|
| Greenhouse (direct) | Label-scoped; unhide before inject; MutationObserver remount guard | Native setter + `input`/`change` events; verify after blur | Label-scoped only; never bare `Toggle flyout`; phone field scoped to phone container | File upload field |
| Greenhouse (embed) | Same; open embed URL as top-level page | Same | Same | Same |
| Greenhouse (EU domain) | Treat as Greenhouse after URL verification | Same | Same | Same |
| Lever | Label-scoped visible upload; DataTransfer confirmed working | Verify after blur | N/A | Text paste only — no file upload field |
| Workable | `inputs[1]` is CV (index 0 is photo); `react-dropzone` ignores DataTransfer injection — manual upload required | Verify after blur/step change | Scoped click+type fallback | File upload or text |

## Error handling

- Browser setup or metadata failure: report as a browser/tool preflight failure, not an ATS automation failure; stop
- Existing SPA tab blocks navigation: open a fresh tab; if explicitly requested tab remains blocked, stop and hand off
- Page not loading: take screenshot, check URL, try navigating again
- File upload failing on Greenhouse: re-query label-scoped input after React remount; use MutationObserver guard; verify visible filename
- React field not accepting value: use native prototype setter + bubbled events, verify after blur/scroll
- Dropdown not opening: scope to field container; use `setReactValue` or click+type; never use unscoped value assignment alone
- Radio not registering: re-click as standalone (not in a batch), re-verify via JS
- Cross-origin iframe blocking tools: navigate directly to embed URL as a top-level page
- Greenhouse `Toggle flyout` opens Google Drive / file-provider UI: close immediately, record selector failure, hand off the field
- CDP timeout / debugger disconnect: reduce payload size — do not inject large inline base64; use localhost fetch or chunked sessionStorage
- Unsupported ATS, CAPTCHA, login wall, hidden required field, or ambiguous consent/legal field: stop and hand off with exact field label and URL
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

Run gates 1-2 using `run_pre_apply_checks(autonomous=True)`:
1. `check_duplicate()` -- halt: `DUPLICATE`
2. `check_artifacts_exist()` + `check_platform_supported()` -- halt: `PLATFORM_CHECK_FAILED`

If either fails, fall to HITL.

Then run the yolo gate battery via `src/yolo.py:run_yolo_gates(profile, role_config, workspace_dir, tracker_path)`:

3. Tier in `permitted_tiers` -- halt: `TIER_NOT_PERMITTED`, fall to HITL
4. Company not in `excluded_companies` -- halt: `COMPANY_EXCLUDED`, fall to HITL
5. Daily cap check -- halt: `DAILY_CAP_REACHED`
6. Cover letter present -- halt: `COVER_LETTER_REQUIRED`
7. Cover letter specificity -- halt: `QUALITY_GATE_FAILED`
8. jobqa workspace gate (`jobqa run <workspace_dir>`) -- halt: `JOBQA_GATE_FAILED: {errors}`
   - jobqa warnings pass through and are logged in the sidecar
   - If `jobqa` is not in PATH: skip this gate, log a warning, continue

Generate the workspace before gate 8 using `src/jobqa_workspace.py:generate_jobqa_workspace()`.

### Step C -- Autonomous form fill

Proceed with Steps 0-11 (preflight, load configs, navigate, classify, fill, upload, answer, scroll).
Do not pause at Step 12.

**Codex Chrome restriction applies here too.** Yolo mode does not bypass the Codex Chrome
experimental status established in Prerequisites 6-7. If running on Codex Chrome, the same
evidence requirement applies: `docs/apply-codex-chrome-verification.md` must contain a
non-submitted end-to-end pass record for the target ATS case. The gate battery is not a
substitute for that evidence. Passing all yolo gates does not promote a Codex Chrome ATS
platform from experimental to stable -- that promotion requires a committed evidence record in
the verification matrix, independent of the gate battery outcome.

### Step D -- Pre-submit record

Before clicking Submit, call `src/record_submission.py` (packaged with career-agent -- no
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
as the first argument instead -- the script accepts either.

If `record_submission.py` exits non-zero: **abort with `SUBMISSION_LOG_FAILED`, do NOT click Submit.**
The `authorization_key_prefix` is the first 4 characters of `profile.yolo_mode.authorization_key`.

### Step E -- Submit and confirm

Click Submit once. Call `check_confirmation_pattern(ats_platform, final_url, page_text)`:

- `confirmed` -> proceed to Step F
- `ambiguous` -> write sidecar `outcome: ambiguous`, tracker `autonomous_ambiguous`, **halt, do not retry**
- `failed` -> write sidecar `outcome: failed`, tracker `autonomous_failed`, halt

### Step F -- Post-submit

1. Take a screenshot of the confirmation page
2. Write audit sidecar via `src/audit.py:write_sidecar()` with `outcome: confirmed`
3. Update tracker status to `autonomous_submitted`

Report:
```
Autonomous submission completed: <title> @ <company>
   Outcome: confirmed
   Confirmation: <excerpt>
   Sidecar: audits/<role_id>_<timestamp>_submission.json
   Remaining: EEO fields (not filled -- human action required if asked later)
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
| `SUBMISSION_LOG_FAILED` | record_submission.py exited non-zero | Abort -- do NOT click Submit |
