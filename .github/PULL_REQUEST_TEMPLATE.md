## What
<!-- One sentence describing the change -->

## Why
<!-- Link to issue: Closes #N -->

## Checklist
- [ ] CI passes locally: `pytest tests/ && ruff check . && mypy src/`
- [ ] Conventional commit messages (`feat:`, `fix:`, `docs:`, `chore:`)
- [ ] SKILL.md updated if skill behaviour changed
- [ ] ENGINEERING_PRINCIPLES.md followed
- [ ] No PII in committed files (`git diff --name-only | grep -v ".gitignore"`)
