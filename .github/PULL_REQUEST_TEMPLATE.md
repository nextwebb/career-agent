## What
<!-- One sentence describing the change -->

## Why
<!-- Link to issue: Closes #N -->

## Checklist
- [ ] CI passes locally: `pytest tests/ && ruff check . && mypy src/`
- [ ] Scope is minimal, schemas/types were verified where touched, and assumptions are documented
- [ ] Conventional commit messages (`feat:`, `fix:`, `docs:`, `chore:`)
- [ ] PR title is a release-parseable Conventional Commit with no `[codex]` or other agent prefix
- [ ] SKILL.md updated if skill behaviour changed
- [ ] Review path verified (valid CODEOWNERS, branch protection, or documented manual review)
- [ ] ENGINEERING_PRINCIPLES.md followed
- [ ] No PII in committed files (`git diff --name-only | grep -v ".gitignore"`)
