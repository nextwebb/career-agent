# Contributing

Thanks for your interest in career-agent. Contributions are welcome — please read this first.

## Issues first

Open an issue before writing code. This lets us align on scope and avoid duplicate effort. PRs without a linked issue may be closed.

## Setup

```bash
pip install -r requirements.txt

# Install git hooks — order matters:
# 1. Set the hook path (if you have Node/npm available)
npm install          # runs `git config core.hooksPath .githooks`
# 2. Install pre-commit into .githooks/ (not .git/hooks/)
pip install pre-commit
pre-commit install
```

If you skip `npm install`, run this manually first so pre-commit installs to the right place:

```bash
git config core.hooksPath .githooks
pre-commit install
```

If you already had `pre-commit install` done before setting the hook path, re-run `pre-commit install` — it will move the hook to `.githooks/pre-commit`.

## Before pushing

Run the full check suite locally:

```bash
pytest tests/ && bash tests/integration_test.sh && ruff check . && mypy src/
```

All checks must pass before opening a PR.

## Commit style

Use [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add Ashby ATS support
fix: handle missing city field in Greenhouse combobox
docs: update README install steps
chore: bump reportlab to 4.2.0
```

See `ENGINEERING_PRINCIPLES.md` for the full commit and branching conventions used in this project.

## What makes a good contribution

- Bug fixes with a clear reproduction case
- New ATS platform support (Greenhouse, Lever, Workable are already covered)
- Skill improvements that reduce manual steps for the user

## What to avoid

Do not open PRs for:

- A web UI or database layer
- Multi-user or SaaS features
- Any feature that contradicts the principles in `ENGINEERING_PRINCIPLES.md` section 13

When in doubt, open an issue and ask first.

## Code standards

Follow `ENGINEERING_PRINCIPLES.md` — it covers Python style, type hints, error handling, security, and testing requirements.
