# Review Routing

This repository uses GitHub issues for scope and acceptance criteria, and pull
requests for implementation review.

## Current Verified Path

- CODEOWNERS routes all pull requests to `@nextwebb`.
- Branch protection is not currently required on `main`.
- AI review is not configured through CODEOWNERS.

## AI Review Policy

Do not add AI assistant handles to CODEOWNERS unless GitHub confirms that the
owner exists and has write access to this repository. At the time this document
was added, GitHub reported `@copilot` and `@chatgpt-codex-connector` as invalid
CODEOWNERS owners for this repository.

When Codex, Copilot, Claude, or another AI review system is used, request it
through the supported integration, workflow, or PR comment mechanism for that
tool. Document the actual trigger in the pull request so reviewers can verify
which path was used.

## Codex Support Issue Readiness

Issues #57-#62 should move from `needs-review` to `implementation-ready` only
after one of these is true:

- a valid CODEOWNERS or branch-protection review path is active; or
- a manual reviewer explicitly approves the issue scope and acceptance criteria.

Do not treat issue labels alone as approval. The evidence should be visible in
GitHub comments, review state, branch protection settings, or repository files.
