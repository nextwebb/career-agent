# Validation Policy

This repository treats validation evidence as concrete check runs, reproducible
local commands, or documented manual review. Status-only noise from integrations
is recorded separately so it does not blur the result of required gates.

## Public Contact Policy

Do not publish maintainer email addresses in public package metadata, plugin
metadata, security policy files, or repository docs. Public contact paths should
use repository URLs, project pages, or GitHub-native private reporting flows.

Applicant example data in skills and sample profile files may still show
placeholder email fields when needed to explain local user data shape.

## Required Checks

Required validation is based on check runs that GitHub can evaluate and on the
local commands listed in `AGENTS.md`. The current required repository-owned
GitHub Actions gates are:

- `CI / All Checks Passed`
- `Security / CodeQL Analysis`
- `Security / Dependency Vulnerability Check`
- `Security / Trivy Filesystem Scan`
- `Security / Trivy Secret Scan`
- `Security / Security Summary`
- `Deploy GitHub Pages / Deploy docs/ to GitHub Pages`
- `Release Please / release-please`

Other local checks, such as `npm run check:package`, `npm run check:codeowners`,
and `python3 -m pytest tests/smoke_test.py -q`, should be cited in pull request
validation when they are relevant to the files changed.

## External App Suites

External app check suites that remain `queued` with zero check runs are not
evidence of either success or failure. They should be documented as residual
external-suite noise, but they do not block a green post-merge validation claim
unless the repository has explicitly made that app a required check.

An external app is required only when it produces a real GitHub check run that
branch protection or repository policy names as required. If an external service
is expected to gate merges, configure it to create a concrete check run with logs
and a terminal conclusion. If it is not expected to gate merges and continues to
emit empty queued suites, remove or disable the stale integration where possible.

Post-merge validation reports should list required GitHub Actions gates and
relevant local commands under passed or failed validation. Empty external app
suites belong in a separate residual-notes section unless they produce a named
required check run.
