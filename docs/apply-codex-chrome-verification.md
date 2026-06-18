# Codex Chrome /apply Verification Matrix

This matrix tracks non-submitting Codex Chrome browser automation evidence for
`$apply` / `/apply` before any ATS platform is described as stable in Codex.

As of 2026-06-18, this task did not run live browser tests against real ATS
forms. Every row below is therefore marked unverified or experimental. Do not
promote Codex Chrome `/apply` support beyond experimental until a non-submitted
test record exists for the platform and URL pattern.

Procedure-only rows are not live ATS evidence. A row that has no committed
non-submitting test record must stay `Experimental` or `Unsupported for
automation`, and its evidence status must say that it is unverified in this
task.

## Verification Rules

- Use Codex Chrome only when the workflow needs signed-in browser state,
  cookies, extensions, or file picker behavior that Codex Browser cannot
  provide.
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
| Greenhouse direct | `https://job-boards.greenhouse.io/<company>/jobs/<id>` or equivalent direct Greenhouse application URL | Experimental | Unverified in this task | Manual fallback if upload, combobox, radio, or safety classification is uncertain |
| Greenhouse embed direct top-level URL | `https://boards.greenhouse.io/embed/job_app?for=<company>&token=<id>` or equivalent top-level embed URL | Experimental | Unverified in this task | Manual fallback unless the embed URL is opened as a top-level page; do not automate inside company iframes |
| Greenhouse EU domain | EU Greenhouse board/application host for a Greenhouse form | Experimental | Unverified in this task | Manual fallback until EU URL/domain handling has non-submitted evidence; `ats_platform` should remain normalized to `greenhouse` unless a separate supported value is intentionally added and tested |
| Lever | `https://jobs.lever.co/<company>/<id>/apply` | Experimental | Unverified in this task | Manual fallback if custom questions or cover-letter text areas cannot be classified safely |
| Workable | `https://apply.workable.com/<company>/j/<id>/apply/` | Experimental | Unverified in this task | Manual fallback for multi-step pages, dropdown uncertainty, or hidden required fields |
| Unknown or unsupported ATS | Any form where `ats_platform` is `unknown` or not `greenhouse`, `lever`, or `workable` | Unsupported for automation | Unverified in this task; stop condition documented by policy only | Do not automate; provide manual guidance |
| Safety boundaries | Submit, irreversible confirmation, credentials, EEO, demographics, disability, veteran, consent, legal attestation, CAPTCHA, ambiguous fields | Required stop boundary | Unverified in this task; policy documented with no live browser evidence | Never fill or click without explicit user confirmation after handoff |

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
