---
name: source
description: Discover role leads, verify open roles on official posts, and rank verified matches with heuristic sponsorship and relocation confidence
---

# source

Discover role leads, verify currently-open roles on official or company-controlled posts, and rank verified matches against your profile. Uses your CV, LinkedIn export, or profile.json as the candidate baseline. Optionally reads uploaded company/sponsorship documents as a starting source list.

Aims to return up to 20 ranked roles when enough matches can be verified, with fit scores, CV variant suggestions, cover letter angles, and sponsorship/relocation confidence labels. Each role should cite the official job post or careers page, and blocked or inconclusive checks should be marked clearly. Fit scores are heuristic recruiter judgment, not verified facts.

Follow `docs/source-methodology.md` for the source hierarchy, broad-search strategy, verification standard, scoring rubric, sponsorship/relocation confidence labels, and fewer-than-20 fallback behavior. Do not claim private recruiter database access, paid feed access, internal ATS access, or guaranteed complete job-search coverage unless the user explicitly provides and authorizes that source in the session.

## Triggers

User says: `/source`, `find me jobs`, `find roles for me`, `search for jobs`, `what jobs match my profile`, `find backend roles`, `find Python roles`, `source jobs`

In Codex, invoke this skill with `$source`, the skills/plugin selector, or natural language. Slash-command examples are Claude Code aliases, not Codex built-ins.

## Arguments

```
/source                                   : run with all defaults
/source [country]                         : focus on a specific country or region
/source [role_type]                       : focus on a role type (backend, data, AI)
/source [country] [role_type]
```

Examples:
```
/source
/source UK backend
/source EU "data platform"
/source remote AI infrastructure
```

## Step 1: Build the candidate profile

Check inputs in this priority order:

### Option A: profile.json exists

Read `profile.json`. Extract:
- Name, years of experience, location, relocation openness
- All skills (languages, cloud, backend, data, AI/LLM sections)
- Experience (titles, companies, key bullets)
- CV variants (A/B/C labels and their focus areas)

### Option B: File uploaded by user

Accept any of:
- **LinkedIn PDF export**: File → Save as PDF from linkedin.com/in/yourprofile
- **CV PDF or DOCX**: Any recent comprehensive CV
- **Plain text resume**: Pasted directly into the conversation

Read the file and extract the same fields as Option A. If parsing is ambiguous, state your assumptions explicitly.

### Option C: Neither exists

Ask the user:
> "To find matching roles I need your profile. Please either:
> 1. Share your CV (PDF, DOCX, or paste it here)
> 2. Upload your LinkedIn profile PDF (LinkedIn → More → Save to PDF)
> 3. Or run `/setup-profile` to build profile.json from your CV/LinkedIn export, or create profile.json manually from profile.example.json"

Do not proceed without a profile source.

---

## Step 2: Load company source list (optional)

If the user uploads one or more PDF documents listing companies by country (e.g. visa-sponsoring companies, relocation-friendly employers):

- Extract company names and countries from the uploaded documents
- Treat these as a **starting source list only**: not as proof of current active hiring
- Keep source-list sponsorship or relocation claims separate from current job-post facts
- You will verify each company's actual careers page in Step 3

If no documents are uploaded, proceed without a source list: search broadly using the candidate's profile and target parameters. Broad search means public web/search and browser-accessible sources available in the current Claude Code or Codex session; it does not imply private data-source access or exhaustive market coverage.

Primary sources:
- Company careers pages on official company domains
- Company-controlled ATS postings linked from company sites (Greenhouse, Lever, Workable, Ashby, SmartRecruiters, Workday, etc.)
- User-uploaded source lists as company-discovery inputs only

Fallback discovery sources:
- Public web search results
- Public LinkedIn job pages or company posts
- Public job aggregators, community boards, and search snippets

Use fallback sources to discover leads, then prefer company-hosted or company-controlled posts for verification. If only a LinkedIn or aggregator page is available, mark the source type and uncertainty clearly.

---

## Step 3: Run the sourcing analysis

Act as a senior technical recruiter and job search strategist.

Using the candidate profile from Step 1, find and verify currently-open roles.

When there is no uploaded source list:
- Derive 2-4 role families from the candidate profile and user request
- Derive target markets from the request, profile location, relocation openness, and remote preference
- Search combinations of seniority, role family, target market, sponsorship, relocation, and ATS terms
- Expand to adjacent titles only after higher-confidence searches are exhausted
- Note blocked, stale, or inconclusive searches when they materially reduce coverage

When there is an uploaded source list:
- Normalize company names and obvious duplicates
- Search each company with its careers page, ATS page, target role family, country, remote, sponsorship, and relocation terms
- Verify current roles on official company or ATS pages
- Preserve any uploaded-list sponsorship claim as source-list evidence, not as a job-post fact

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

## Step 4: Verify each role

For every candidate role:

1. Visit the company's **official careers page or job board** (Greenhouse, Lever, Workable, LinkedIn, etc.)
2. Confirm the role is **currently open**: not expired, not archived
3. Extract: title, location, work setup (remote / hybrid / onsite), application link
4. Check the job post for explicit sponsorship / relocation language
5. If the company came from an uploaded source list but the job post says nothing about sponsorship, note: *"Relocation/sponsorship claim from uploaded source list: not confirmed in job post"*
6. If the careers page has no matching roles today, skip it or add to Watched Companies

Count a role as verified only when the company identity is clear, title and location/work setup are visible, the post appears current, the application URL or careers-page link is reachable, and the verification URL is cited.

Use LinkedIn and aggregators carefully:
- Use LinkedIn and aggregators for discovery when useful
- Prefer the company-hosted or company-controlled post as the verification source
- If only a public LinkedIn company posting is available, mark `Source type: public platform`, keep the evidence-quality score conservative, and state that no stronger official post was reachable
- Do not treat aggregator text as proof of sponsorship, relocation, compensation, or seniority unless the same claim appears in the cited company-controlled post

---

## Step 5: Return output

Return **up to 20 verified roles**, ranked in this order. If fewer than 20 suitable roles can be verified, return the verified set and explain what was blocked or inconclusive.

Rank by the fit score in `docs/source-methodology.md`, using these weights:

1. Technical match: 35
2. Seniority match: 15
3. Domain and product relevance: 10
4. Location and work authorization practicality: 15
5. Sponsorship or relocation signal: 10
6. Compensation potential: 5
7. Evidence quality and freshness: 10

Apply these caps:
- Do not score unverified leads
- Cap evidence quality at 6 when the only reachable source is a public platform post
- Cap sponsorship or relocation signal at 5 when it comes only from a source list or company-level history, not the current job post
- Score sponsorship or relocation signal as 0 when the post says sponsorship is unavailable or requires existing local work authorization that the candidate lacks

If fewer than 20 suitable roles can be verified, do not pad with unverified leads. Return the verified set and include a coverage note describing searches attempted, blocked pages, fallback expansions, and any watched companies or unverified leads.

### Per-role format

```
## [Rank]. [Company]: [Role Title]
Location:       [City / Country / Remote]
Work setup:     [Remote | Hybrid | Onsite | Relocation]
Apply:          [Direct application URL]
Source:         [Company careers page URL used to verify]
Source type:    [company-hosted | company-controlled ATS | public platform]
Sponsorship:    [Confirmed in job post | Source list claim only, not confirmed in job post | Company-level signal only | Not mentioned | Likely blocker]

Fit score:      [X/100]
Probability:    [High | Medium | Stretch]

Verified facts:
  [2-4 bullets from cited sources only]

Recruiter judgment:
  [2-3 sentences linking candidate's specific experience to this role's requirements and explaining score/rank]

Key gaps / risks:
  [Honest assessment: missing skills, location complexity, competition level]

Suggested CV version:
  [Backend/Cloud | Data Platform | AI Infrastructure | LLM Evaluation | Hybrid Senior]

Cover letter angle:
  [1 sentence on the specific hook for this company/role]
```

### Watched companies section (optional)

Companies from the source list that look promising but have no matching open roles today:

```
- [Company] ([Country]): Strong profile match. No current openings. Check back: [careers page URL]
```

---

## Evidence standard

- If a role is currently open: cite the company careers page or official job post URL
- If sponsorship/relocation is only from uploaded documents: say so explicitly and do not treat it as confirmed for the current job post
- If a careers page returned no matching roles: do not count it toward the 20
- Separate verified facts from inferred recruiter judgment
- Do not present inference as fact
- Do not fabricate URLs or job post links
- Do not claim complete coverage of all open roles

---

## After output: suggested next steps

For each role the user wants to pursue:

```
/new-role <application_url>    ← scaffold the role config
/generate-cv <role_id>         ← build tailored CV + cover letter
/apply <role_id>               ← fill the ATS form
/track <role_id> applied       ← log it in your pipeline
```

In Codex, use `$new-role`, `$generate-cv`, `$apply`, and `$track` or invoke the installed skills through the selector. Codex Chrome `/apply` remains experimental; use the verification matrix as risk context and stop before sensitive controls or Submit.

The `/source` output feeds directly into `/new-role`: paste the application URL from any role above to scaffold its config automatically.
