---
description: Find verified open roles matching your profile, ranked by fit score with sponsorship and relocation signals
---

# source

Find verified, currently-open roles that match your profile. Uses your CV, LinkedIn export, or profile.json as the candidate baseline. Optionally reads uploaded company/sponsorship documents as a starting source list.

Returns at least 20 ranked, evidence-verified roles with fit scores, CV variant suggestions, cover letter angles, and sponsorship/relocation signals.

## Triggers

User says: `/source`, `find me jobs`, `find roles for me`, `search for jobs`, `what jobs match my profile`, `find backend roles`, `find Python roles`, `source jobs`

## Arguments

```
/source                                    — run with all defaults
/source [country]                          — focus on a specific country or region
/source [role_type]                        — focus on a role type (backend, data, AI)
/source [country] [role_type]
```

Examples:
```
/source
/source UK backend
/source EU "data platform"
/source remote AI infrastructure
```

## Step 1 — Build the candidate profile

Check inputs in this priority order:

### Option A — profile.json exists

Read `profile.json`. Extract:
- Name, years of experience, location, relocation openness
- All skills (languages, cloud, backend, data, AI/LLM sections)
- Experience (titles, companies, key bullets)
- CV variants (A/B/C labels and their focus areas)

### Option B — File uploaded by user

Accept any of:
- **LinkedIn PDF export** — File → Save as PDF from linkedin.com/in/yourprofile
- **CV PDF or DOCX** — Any recent comprehensive CV
- **Plain text resume** — Pasted directly into the conversation

Read the file and extract the same fields as Option A. If parsing is ambiguous, state your assumptions explicitly.

### Option C — Neither exists

Ask the user:
> "To find matching roles I need your profile. Please either:
> 1. Share your CV (PDF, DOCX, or paste it here)
> 2. Upload your LinkedIn profile PDF (LinkedIn → More → Save to PDF)
> 3. Or run `/new-role` first to set up your profile.json"

Do not proceed without a profile source.

---

## Step 2 — Load company source list (optional)

If the user uploads one or more PDF documents listing companies by country (e.g. visa-sponsoring companies, relocation-friendly employers):

- Extract company names and countries from the uploaded documents
- Treat these as a **starting source list only** — not as proof of current active hiring
- You will verify each company's actual careers page in Step 3

If no documents are uploaded, proceed without a source list — search broadly using the candidate's profile and target parameters.

---

## Step 3 — Run the sourcing analysis

Act as a senior technical recruiter and job search strategist.

Using the candidate profile from Step 1, find and verify currently-open roles.

### Target role types (match to profile)

Prioritise any role where the candidate's background gives a clear advantage:

- Senior Backend Engineer
- Senior Python Engineer
- Cloud Engineer / Platform Engineer
- Data Platform / Data Infrastructure Engineer
- AI Infrastructure Engineer
- Agentic Workflow / AI Systems Engineer
- LLM Evaluation / AI Safety / RLHF roles
- Staff / Principal Engineer (if experience supports it)

### Target markets

- Remote (global)
- EU (with visa sponsorship or right-to-work flexibility)
- UK (with visa sponsorship)
- US (with H1B / O1 sponsorship)
- Canada, Australia, New Zealand
- Any high-paying remote-first market

### Exclude

- Fresher / graduate / internship / junior / entry-level roles
- Frontend-only roles
- Roles where Kubernetes is the **core** requirement and the rest does not fit
- Mobile, QA, IT helpdesk, support-only roles
- Roles with no seniority signal

---

## Step 4 — Verify each role

For every candidate role:

1. Visit the company's **official careers page or job board** (Greenhouse, Lever, Workable, LinkedIn, etc.)
2. Confirm the role is **currently open** — not expired, not archived
3. Extract: title, location, work setup (remote / hybrid / onsite), application link
4. Check the job post for explicit sponsorship / relocation language
5. If the company came from an uploaded source list but the job post says nothing about sponsorship, note: *"Relocation/sponsorship claim from uploaded source list — not confirmed in job post"*
6. If the careers page has no matching roles today, skip it or add to Watched Companies

---

## Step 5 — Return output

Return **at least 20 verified roles**, ranked in this order:

1. Best technical fit
2. Strongest sponsorship / relocation signal
3. Highest compensation potential
4. Best immigration / relocation practicality
5. Best match for seniority

### Per-role format

```
## [Rank]. [Company] — [Role Title]
Location:       [City / Country / Remote]
Work setup:     [Remote | Hybrid | Onsite | Relocation]
Apply:          [Direct application URL]
Source:         [Company careers page URL used to verify]
Sponsorship:    [Confirmed in JD | From uploaded source list only | Not mentioned]

Fit score:      [X/100]
Probability:    [High | Medium | Stretch]

Why it fits:
  [2–3 sentences linking candidate's specific experience to this role's requirements]

Key gaps / risks:
  [Honest assessment — missing skills, location complexity, competition level]

Suggested CV version:
  [Backend/Cloud | Data Platform | AI Infrastructure | LLM Evaluation | Hybrid Senior]

Cover letter angle:
  [1 sentence on the specific hook for this company/role]
```

### Watched companies section (optional)

Companies from the source list that look promising but have no matching open roles today:

```
- [Company] ([Country]) — Strong profile match. No current openings. Check back: [careers page URL]
```

---

## Evidence standard

- If a role is currently open: cite the company careers page or official job post URL
- If sponsorship/relocation is only from uploaded documents: say so explicitly
- If a careers page returned no matching roles: do not count it toward the 20
- Do not present inference as fact
- Do not fabricate URLs or job post links

---

## After output — suggested next steps

For each role the user wants to pursue:

```
/new-role <application_url>    ← scaffold the role config
/generate-cv <role_id>         ← build tailored CV + cover letter
/apply <role_id>               ← fill the ATS form
/track <role_id> applied       ← log it in your pipeline
```

The `/source` output feeds directly into `/new-role` — paste the application URL from any role above to scaffold its config automatically.
