# Codex Chrome /apply Verification Matrix

This matrix tracks non-submitting Codex Chrome browser automation evidence for
`$apply` / `/apply` before any ATS platform is described as stable in Codex.

As of 2026-06-18, this matrix includes live Codex Chrome page observations for
representative public Greenhouse, Lever, Workable, and unsupported ATS pages.
The run did not fill applicant data, upload files, advance multi-step flows, or
click Submit. These are therefore partial non-submitting observations, not
evidence of successful end-to-end ATS automation.

This matrix is promotion evidence, not a hard prerequisite for every
human-in-the-loop Codex Chrome attempt. Missing target-specific evidence keeps a
run experimental; it does not by itself block a user-approved attempt after
browser setup preflight passes. Do not promote Codex Chrome `/apply` support
beyond experimental until a non-submitted test record exists for the platform
and URL pattern that includes a generated PDF upload result, field-fill result,
handoff result, and final state proving Submit was not clicked.

## Verification Rules

- Use Codex Chrome only when the workflow needs signed-in browser state,
  cookies, extensions, or file picker behavior that Codex Browser cannot
  provide.
- Preflight the Codex Chrome extension before any ATS navigation. If browser
  setup fails, record the failure as blocked evidence and use Browser or manual
  handoff instead.
- Stop before Submit, final confirmation, irreversible actions, credentials,
  legal attestations, consent fields, EEO, voluntary self-identification,
  demographic, disability, veteran, CAPTCHA, or ambiguous fields.
- Navigate Greenhouse embed applications as top-level embed URLs. Do not try to
  control a cross-origin iframe inside a company careers page.
- Keep screenshots out of the repository unless they are sanitized and contain
  no personal data, application answers, or employer-confidential content.
  Written observations are preferred for committed evidence.
- If a form fails, changes unexpectedly, or requires manual judgment, leave that
  platform experimental and hand off with the exact URL, field label, and final
  browser state.

## Support Status

| ATS case | URL pattern to verify | Codex Chrome status | Evidence status | Stable support decision |
|---|---|---|---|---|
| Greenhouse direct | `https://job-boards.greenhouse.io/<company>/jobs/<id>` or equivalent direct Greenhouse application URL | Experimental | Live page observed 2026-06-18; no upload/fill | Manual fallback if upload, combobox, radio, or safety classification is uncertain |
| Greenhouse embed direct top-level URL | `https://boards.greenhouse.io/embed/job_app?for=<company>&token=<id>` or equivalent top-level embed URL | Experimental | Live page observed 2026-06-18; no upload/fill | Manual fallback unless the embed URL is opened as a top-level page; do not automate inside company iframes |
| Greenhouse EU domain | EU Greenhouse board/application host for a Greenhouse form | Experimental | Live page observed 2026-06-18; no upload/fill | Experimental HITL only; keep `ats_platform` normalized to `greenhouse` unless a separate supported value is intentionally added and tested |
| Lever | `https://jobs.lever.co/<company>/<id>/apply` | Experimental | Live page observed 2026-06-18; no upload/fill | Manual fallback if custom questions or cover-letter text areas cannot be classified safely |
| Workable | `https://apply.workable.com/<company>/j/<id>/apply/` | Experimental | Live page observed 2026-06-18; no upload/fill | Manual fallback for multi-step pages, dropdown uncertainty, or hidden required fields |
| Unknown or unsupported ATS | Any form where `ats_platform` is `unknown` or not `greenhouse`, `lever`, or `workable` | Unsupported for automation | Live unsupported ATS page observed 2026-06-18; no automation attempted | Do not automate; provide manual guidance |
| Codex Chrome setup preflight | Any Codex Chrome run before ATS navigation | Required preflight | Blocked 2026-06-23 in one workspace by browser-tool metadata rejection before Chrome control | Report as browser setup failure; use Browser or manual fallback |
| Safety boundaries | Submit, irreversible confirmation, credentials, EEO, demographics, disability, veteran, consent, legal attestation, CAPTCHA, ambiguous fields | Required stop boundary | Live pages observed 2026-06-18; stop controls detected, not clicked | Never fill or click without explicit user confirmation after handoff |

## Evidence Template

Copy one record per non-submitted test. Keep employer/user-sensitive data out of
committed evidence.

```markdown
### <ATS case> - <YYYY-MM-DD>

- Date tested:
- Tester:
- Codex surface:
- Browser surface: Codex Chrome
- ATS platform:
- URL pattern:
- Test URL or sanitized URL:
- Role config `ats_platform` value:
- Generated CV PDF upload result:
- Generated cover letter result:
- Fields filled:
- Fields handed off:
- Sensitive/safety fields detected:
- Screenshots or written observations:
- Final state proving Submit was not clicked:
- Result: verified / failed / blocked / experimental
- Follow-up needed:
```

### Codex Chrome Setup Preflight

- Confirm the Chrome browser tool can list or open tabs before any ATS
  navigation.
- Treat workspace metadata errors, extension communication failures, and native
  host failures as browser setup failures, not ATS automation failures.
- Do not use alternate scripting paths to claim Codex Chrome behavior when the
  Chrome interface itself failed.

## Minimum Checks Per ATS

### Greenhouse Direct

- Verify text fields for first name, last name, email, phone, and profile links.
- Verify country/city combobox interaction with click, type, and selected option
  confirmation.
- Verify radio button selection state after each click.
- Verify hidden resume upload can be made interactable and that the uploaded PDF
  filename appears.
- Verify cover-letter upload or handoff behavior, depending on the form.
- Stop with Submit visible or reachable, no confirmation page loaded, and no
  irreversible control clicked.

### Greenhouse Embed

- Open the embed application URL directly as the top-level page.
- Record that automation did not interact through a cross-origin company iframe.
- Re-run the same Greenhouse direct checks that are visible in the embed flow.
- Stop with Submit visible or reachable and not clicked.

### Greenhouse EU Domain

- Verify the EU URL/domain is recognized as a Greenhouse application.
- Record whether `role.ats_platform` remains `greenhouse` or whether a new
  explicitly supported value was added.
- Run direct or embed Greenhouse checks against the EU-hosted form.
- Keep the status experimental until URL handling and upload behavior are both
  observed in Codex Chrome.

### Lever

- Verify resume PDF upload and visible filename/attachment state.
- Paste cover-letter text only if a text area exists; do not expect a cover
  letter file input.
- Fill safe custom questions only after label and surrounding-copy
  classification.
- Hand off EEO, demographic, consent, authorization, legal, or ambiguous
  questions.
- Stop with Submit visible or reachable and not clicked.

### Workable

- Normalize or navigate to the `/apply/` URL before filling.
- Verify visible resume file upload and filename/attachment state.
- Verify dropdowns by user-like click/type/select interactions rather than
  direct value injection alone.
- Record any multi-step behavior and stop before advancing through ambiguous or
  irreversible steps.
- Stop with Submit visible or reachable and not clicked.

### Unknown Or Unsupported ATS

- Confirm the platform is not confidently one of `greenhouse`, `lever`, or
  `workable`.
- Do not fill fields or upload PDFs.
- Report the unsupported URL, visible platform signals, and manual fallback
  guidance to the user.

## Evidence Records

These records were collected through Codex Chrome on 2026-06-18. The run was
intentionally read-only on live employer ATS pages: no applicant data was
entered, no PDF was uploaded, no multi-step flow was advanced after the
application form was visible, and Submit was not clicked. A live ATS file upload
can transmit data to the employer's ATS backend even when the final application
is not submitted, so upload verification still requires explicit target-level
approval or a sandbox/test form.

### Greenhouse direct - 2026-06-18

- Date tested: 2026-06-18
- Tester: Codex
- Codex surface: Codex with Chrome extension browser control
- Browser surface: Codex Chrome
- ATS platform: Greenhouse
- URL pattern: `https://job-boards.greenhouse.io/<company>/jobs/<id>`
- Test URL or sanitized URL:
  `https://job-boards.greenhouse.io/branch/jobs/7771615003`
- Role config `ats_platform` value: `greenhouse`
- Generated CV PDF upload result: Not attempted; live ATS upload would transmit
  a file to the employer ATS.
- Generated cover letter result: Not attempted; cover-letter file input was
  visible.
- Fields filled: None.
- Fields handed off: All applicant identity, contact, location, compensation,
  work-authorization, visa-sponsorship, custom, file-upload, and Submit fields.
- Sensitive/safety fields detected: Work authorization, visa sponsorship,
  compensation expectations, demographic/legal terms, and `Submit application`.
- Screenshots or written observations: Form loaded with required first name,
  last name, email, country, phone, resume/CV file input accepting
  `.pdf,.doc,.docx,.txt,.rtf`, optional cover-letter file input, custom
  questions, and `Submit application`.
- Final state proving Submit was not clicked: Browser remained on the
  application form URL; no input values were changed; no file was selected;
  `Submit application` remained visible.
- Result: experimental partial observation, not verified automation.
- Follow-up needed: Repeat with an approved sandbox or explicitly approved live
  target to verify file upload, combobox selection, safe field fill, and handoff.

### Greenhouse embed direct top-level URL - 2026-06-18

- Date tested: 2026-06-18
- Tester: Codex
- Codex surface: Codex with Chrome extension browser control
- Browser surface: Codex Chrome
- ATS platform: Greenhouse
- URL pattern: `https://job-boards.greenhouse.io/embed/job_app?for=<company>&token=<id>`
- Test URL or sanitized URL:
  `https://job-boards.greenhouse.io/embed/job_app?for=branch&token=7771615003`
- Role config `ats_platform` value: `greenhouse`
- Generated CV PDF upload result: Not attempted; live ATS upload would transmit
  a file to the employer ATS.
- Generated cover letter result: Not attempted; cover-letter file input was
  visible.
- Fields filled: None.
- Fields handed off: All applicant identity, contact, location, compensation,
  work-authorization, visa-sponsorship, custom, file-upload, CAPTCHA/anti-bot,
  and Submit fields.
- Sensitive/safety fields detected: Work authorization, visa sponsorship,
  compensation expectations, a `g-recaptcha-response` field, demographic/legal
  terms, and `Submit application`.
- Screenshots or written observations: The top-level embed URL resolved to the
  same Greenhouse application form without interacting through a company iframe.
  Resume/CV and cover-letter file inputs accepted `.pdf,.doc,.docx,.txt,.rtf`.
- Final state proving Submit was not clicked: Browser remained on the embed
  application form URL; no input values were changed; no file was selected;
  `Submit application` remained visible.
- Result: experimental partial observation, not verified automation.
- Follow-up needed: Repeat with an approved sandbox or explicitly approved live
  target to verify top-level embed fill/upload behavior end to end.

### Greenhouse EU domain - 2026-06-18

- Date tested: 2026-06-18
- Tester: Codex
- Codex surface: Codex with Chrome extension browser control
- Browser surface: Codex Chrome
- ATS platform: Greenhouse
- URL pattern: `https://job-boards.eu.greenhouse.io/<company>/jobs/<id>`
- Test URL or sanitized URL:
  `https://job-boards.eu.greenhouse.io/nice/jobs/4838610101`
- Role config `ats_platform` value: `greenhouse`
- Generated CV PDF upload result: Not attempted; live ATS upload would transmit
  a file to the employer ATS.
- Generated cover letter result: Not attempted; cover-letter file input was
  visible.
- Fields filled: None.
- Fields handed off: All applicant identity, contact, address, salary,
  eligibility, relationship, AI-tool narrative, EEO, disability, veteran, file
  upload, CAPTCHA/anti-bot, and Submit fields.
- Sensitive/safety fields detected: Address, US citizenship/green-card status,
  salary, voluntary self-identification, gender, race/ethnicity, veteran status,
  disability status, `g-recaptcha-response`, and `Submit application`.
- Screenshots or written observations: EU Greenhouse host loaded a standard
  Greenhouse application form with visible resume/CV and cover-letter file
  inputs accepting `.pdf,.doc,.docx,.txt,.rtf`.
- Final state proving Submit was not clicked: Browser remained on the EU
  Greenhouse form URL; no input values were changed; no file was selected;
  `Submit application` remained visible.
- Result: experimental partial observation, not verified automation.
- Follow-up needed: Keep `ats_platform` normalized to `greenhouse`; verify
  domain recognition, safe fill, upload, and handoff only with an approved
  non-submitting target.

### Lever - 2026-06-18

- Date tested: 2026-06-18
- Tester: Codex
- Codex surface: Codex with Chrome extension browser control
- Browser surface: Codex Chrome
- ATS platform: Lever
- URL pattern: `https://jobs.lever.co/<company>/<id>/apply`
- Test URL or sanitized URL:
  `https://jobs.lever.co/arcadia/a5711ac1-89d9-4441-bb3c-e4b08e9ff0db/apply`
- Role config `ats_platform` value: `lever`
- Generated CV PDF upload result: Not attempted; live ATS upload would transmit
  a file to the employer ATS.
- Generated cover letter result: Not attempted; no cover-letter file input was
  observed in this form.
- Fields filled: None.
- Fields handed off: All applicant identity, contact, location, resume upload,
  pronouns, custom text questions, EEO, race, veteran, disability, and Submit
  fields.
- Sensitive/safety fields detected: Pronouns, EEO gender/race, protected
  veteran status, disability status/signature, visa/sponsorship terms, and
  `SUBMIT APPLICATION`.
- Screenshots or written observations: Lever `/apply` URL loaded a single form
  with one visible `resume` file input and custom text areas. Cover letter would
  require text-area handling only if a form-specific field exists.
- Final state proving Submit was not clicked: Browser remained on the Lever
  `/apply` URL; no input values were changed; no file was selected;
  `SUBMIT APPLICATION` remained visible.
- Result: experimental partial observation, not verified automation.
- Follow-up needed: Verify resume upload, safe custom-question fill, and
  cover-letter text paste on an approved non-submitting target.

### Workable - 2026-06-18

- Date tested: 2026-06-18
- Tester: Codex
- Codex surface: Codex with Chrome extension browser control
- Browser surface: Codex Chrome
- ATS platform: Workable
- URL pattern: `https://apply.workable.com/<company>/j/<id>/apply/`
- Test URL or sanitized URL:
  `https://apply.workable.com/mlabs/j/610BE8F665/apply/`
- Role config `ats_platform` value: `workable`
- Generated CV PDF upload result: Not attempted; live ATS upload would transmit
  a file to the employer ATS.
- Generated cover letter result: Not attempted; cover letter was a text area,
  not a file input.
- Fields filled: None.
- Fields handed off: All applicant identity, email, photo upload, resume upload,
  cover-letter text, yes/no custom questions, work-authorization/location/salary
  details, and Submit fields.
- Sensitive/safety fields detected: Required yes/no custom questions, combined
  current-location/salary/work-authorization text prompt, resume upload, and
  `Submit application`.
- Screenshots or written observations: The overview page exposed an application
  tab; opening it navigated to `/apply/`. The form included a required resume
  file input accepting `.pdf,.doc,.docx,.odt,.rtf` and an optional photo file
  input accepting image formats.
- Final state proving Submit was not clicked: Browser remained on the Workable
  `/apply/` URL; no input values were changed; no file was selected;
  `Submit application` remained visible.
- Result: experimental partial observation, not verified automation.
- Follow-up needed: Verify visible resume upload, safe radio/custom-question
  classification, and any multi-step behavior on an approved non-submitting
  target.

### Unknown or unsupported ATS - 2026-06-18

- Date tested: 2026-06-18
- Tester: Codex
- Codex surface: Codex with Chrome extension browser control
- Browser surface: Codex Chrome
- ATS platform: Ashby, treated as unsupported by current `/apply` policy
- URL pattern: `https://jobs.ashbyhq.com/<company>/<id>`
- Test URL or sanitized URL:
  `https://jobs.ashbyhq.com/cohere/df93ec57-d51e-4466-93be-4878c5fda4da`
- Role config `ats_platform` value: `unknown`
- Generated CV PDF upload result: Not attempted.
- Generated cover letter result: Not attempted.
- Fields filled: None.
- Fields handed off: Entire application flow.
- Sensitive/safety fields detected: Unsupported ATS platform and visible
  application/submit flow.
- Screenshots or written observations: Page identified as an Ashby job page,
  not Greenhouse, Lever, or Workable. Current policy requires stopping with
  manual guidance.
- Final state proving Submit was not clicked: Browser remained on the job page;
  no application form fields were filled; no file was selected.
- Result: unsupported for automation.
- Follow-up needed: Add explicit Ashby support and a separate non-submitting
  evidence matrix before automation.

### Codex Chrome setup preflight - 2026-06-23

- Date tested: 2026-06-23
- Tester: Codex
- Codex surface: Codex with Chrome extension browser control
- Browser surface: Codex Chrome
- ATS platform: N/A
- URL pattern: Any Codex Chrome run before ATS navigation
- Test URL or sanitized URL: Local setup preflight only; no ATS URL opened.
- Role config `ats_platform` value: N/A
- Generated CV PDF upload result: Not attempted; browser setup failed before
  navigation.
- Generated cover letter result: Not attempted; browser setup failed before
  navigation.
- Fields filled: None.
- Fields handed off: Entire run.
- Sensitive/safety fields detected: N/A.
- Screenshots or written observations: The Node-backed Chrome interface rejected
  workspace metadata before Chrome setup completed with
  `sandboxCwd must be an absolute file URI`.
- Final state proving Submit was not clicked: No ATS page was opened, no field
  was filled, no file was selected, and no Submit control was reached.
- Result: blocked setup preflight, not verified automation.
- Follow-up needed: Retry after the browser tool accepts workspace metadata;
  record any successful non-submitting fill/upload/handoff run separately.

## Promotion Criteria

A platform may move from experimental to supported in Codex Chrome docs only
when committed evidence includes at least one non-submitted record with:

- Date tested.
- ATS platform and URL pattern.
- Generated PDF upload result.
- Fields filled versus fields handed off.
- Sanitized screenshots or written observations.
- Final browser state proving Submit was not clicked.

Failed, ambiguous, or partially verified platforms remain experimental with
manual fallback guidance.
