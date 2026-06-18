# /source Methodology

`/source` is a lead-generation plus official-post verification workflow. It helps an
agent discover job leads, verify that each role is open on a company-controlled post,
and rank the verified roles against the candidate profile. It is not a complete
job-search index, does not use private data-source access, and cannot guarantee
exhaustive market coverage.

The workflow depends on the browser, search, and page-access capabilities available in
the local Claude Code or Codex session. If search, a careers page, or an ATS page is
blocked, the output must say what could not be verified instead of filling gaps with
assumptions.

## Evidence Model

Separate every claim into one of two buckets:

- **Verified facts**: facts visible in a cited source, such as a company-hosted job post,
  official ATS page, company careers page, or user-uploaded source document. A source
  list can verify only that the list made a company-level claim; it does not verify that
  a current job post offers sponsorship, relocation, compensation, or a specific role.
- **Inferred recruiter judgment**: fit score, probability, compensation potential,
  seniority fit, immigration practicality, and suggested CV or cover-letter strategy.

Do not present inferred judgment as a verified fact. If a claim comes only from an
uploaded source list, say that directly.

## Data Sources

Primary sources:

- Company careers pages on official company domains.
- Company-controlled ATS postings, such as Greenhouse, Lever, Workable, Ashby,
  SmartRecruiters, Workday, or similar systems linked from the company site.
- User-uploaded source lists, such as visa-sponsor lists or relocation-friendly company
  PDFs, used only as a starting list of companies to check.

Fallback discovery sources:

- Public web search results.
- Public LinkedIn job pages or company posts.
- Public job aggregators, community job boards, and search-result snippets.
- Company blog, engineering, or hiring pages that point to the official careers flow.

Fallback discovery sources can suggest leads, but they are weaker evidence than an
official company or ATS post. Prefer a company-hosted or company-controlled job post
before counting a role as verified. If no official or company-controlled post can be
reached, place the item under **Unverified leads** instead of scoring it as a verified
role, unless the user explicitly asks for discovery-only leads.

Do not claim access to private recruiter databases, paid job feeds, internal ATS data,
or guaranteed complete coverage unless the user explicitly provides and authorizes that
source inside the session.

## Search Strategy

When the user uploads a company source list:

1. Extract company names, countries, source-list categories, and any stated visa or
   relocation claims.
2. Normalize duplicates and obvious subsidiaries.
3. Search each company by combining the company name with `careers`, `jobs`, the target
   role family, and the target country or remote term.
4. Verify matching roles on the official company or ATS page.
5. Preserve the source-list claim separately from the verified job-post facts.

When no uploaded source list exists:

1. Derive 2-4 role families from the candidate profile, for example `senior backend`,
   `python platform`, `data infrastructure`, or `AI infrastructure`.
2. Derive target markets from the request and profile, for example `remote`, `UK`,
   `EU`, `Canada`, or `relocation`.
3. Run broad public searches that combine role family, seniority, market, sponsorship,
   relocation, and likely ATS terms.
4. Expand through adjacent titles only after higher-confidence searches are exhausted.
5. Record blocked searches or pages in the output summary when they materially reduce
   coverage.

Useful broad-query patterns:

```text
site:greenhouse.io senior python engineer remote visa sponsorship
site:lever.co data platform engineer Europe relocation
"Senior Backend Engineer" "visa sponsorship" "careers"
"AI Infrastructure Engineer" remote "Greenhouse"
"Platform Engineer" "relocation" "UK" "jobs"
```

These patterns are examples, not a required search engine API. Use whatever public
search or browser capability is available in the host session.

## Role Verification

A role can be counted as verified only when all of the following are true:

- The company identity is clear.
- The role title and location or work setup are visible.
- The post appears current and accepting applications.
- The application URL is reachable or the careers page clearly links to the role.
- The source URL is cited.

Do not count a role when:

- The post is expired, archived, removed, or only visible in a stale search snippet.
- The company cannot be identified confidently.
- The only evidence is an uncited memory, model knowledge, or unsupported inference.
- The role is materially outside the requested or profile-derived target area.

LinkedIn and aggregator treatment:

- A LinkedIn or aggregator page can be used for discovery.
- A company-controlled LinkedIn job post can be cited when no better official post is
  available, but mark the source as `public platform`, keep the evidence-quality score
  conservative, and state that no stronger official post was reachable.
- Aggregator text does not verify sponsorship, relocation, compensation, or seniority
  unless the same claim appears in the cited company-controlled post.
- If a LinkedIn or aggregator link points to a company-hosted post, cite the
  company-hosted post as the verification source.

## Fit Score Rubric

The fit score is a heuristic recruiter judgment, not a fact from the job post. Score
verified roles out of 100 using this weighting:

| Factor | Weight | What to evaluate |
|---|---:|---|
| Technical match | 35 | Core languages, systems, cloud, data, AI, domain tools, and evidence of production depth. |
| Seniority match | 15 | Years, scope, leadership expectations, staff/principal signals, and whether the role is too junior or too senior. |
| Domain and product relevance | 10 | Similar industry, scale, user type, regulated environment, developer tools, or infrastructure context. |
| Location and work authorization practicality | 15 | Remote policy, target country, time-zone fit, right-to-work constraints, and relocation complexity. |
| Sponsorship or relocation signal | 10 | Explicit job-post language, source-list claim, company history, or lack of evidence. |
| Compensation potential | 5 | Published salary, market, seniority, company stage, and likely pay band. |
| Evidence quality and freshness | 10 | Official source quality, current application flow, complete JD, and low ambiguity. |

Caps and guardrails:

- Do not score an unverified lead.
- Cap `Evidence quality and freshness` at 6 when the only reachable source is a public
  platform post rather than an official company or ATS post.
- Cap `Sponsorship or relocation signal` at 5 when the only positive signal is a source
  list claim or company-level history that is not confirmed in the current job post.
- Score `Sponsorship or relocation signal` as 0 when the post says sponsorship is
  unavailable or requires existing local work authorization that the candidate lacks.

Use score bands consistently:

- `85-100`: strong match with clear evidence and few practical blockers.
- `70-84`: good match with manageable gaps or incomplete sponsorship/compensation
  evidence.
- `55-69`: plausible stretch or useful lead, but with meaningful gaps.
- `<55`: normally exclude unless the user asks for stretch leads.

## Sponsorship and Relocation Confidence

Use explicit confidence labels:

- `Confirmed in job post`: the cited job post says sponsorship, visa support, or
  relocation is available.
- `Source list claim only, not confirmed in job post`: an uploaded source list says the
  company sponsors or relocates, but the current job post does not.
- `Company-level signal only`: public company information or repeated historical posts
  suggest sponsorship or relocation, but this role does not confirm it.
- `Not mentioned`: no sponsorship or relocation evidence was found.
- `Likely blocker`: the post excludes sponsorship, requires existing work authorization,
  or requires an impractical onsite location.

Never upgrade sponsorship or relocation from inferred to confirmed without cited
job-post language.

## Fewer Than 20 Verified Matches

`/source` aims to return up to 20 roles. If fewer than 20 roles can be verified, do not
pad the list with unverified leads. Return the verified set and add a short coverage
note that explains:

- How many verified roles were found.
- Which searches, markets, or source-list companies were checked.
- Which pages were blocked, stale, or inconclusive.
- Which fallback expansions were used.
- What the user can provide next, such as a source list, target countries, or a narrower
  role family.

Optional fallback sections:

- **Watched companies**: companies with strong profile fit but no matching open role.
- **Unverified leads**: discovery-only links that need official-post verification before
  ranking or application work.

## Example Output

The example below is illustrative. The URLs use reserved example domains to show
citation style; they are not live job claims.

```text
## 1. ExampleCloud: Senior Python Platform Engineer
Location:       Berlin, Germany / Remote EU
Work setup:     Remote within EU
Apply:          https://jobs.example.com/examplecloud/senior-python-platform-engineer
Source:         https://jobs.example.com/examplecloud/senior-python-platform-engineer
Source type:    company-controlled ATS post

Verified facts:
  - The cited ATS post lists Python, distributed systems, AWS, and platform ownership.
  - The post says the role is remote within the EU.
  - The post does not mention visa sponsorship or relocation.

Sponsorship:    Source list claim only, not confirmed in job post
Source-list evidence:
  - Uploaded "EU relocation companies 2026.pdf" lists ExampleCloud as Germany relocation-friendly.

Fit score:      82/100
Probability:    Medium

Recruiter judgment:
  Strong technical match for Python services, platform ownership, and AWS production work.
  Score is held below the top band because sponsorship is not confirmed in the job post.

Key gaps / risks:
  Sponsorship may be unavailable for this specific role. Confirm with the recruiter before
  investing in a tailored application.

Suggested CV version:
  Backend/Cloud

Cover letter angle:
  Emphasize production Python systems, cloud platform ownership, and EU remote readiness.
```
