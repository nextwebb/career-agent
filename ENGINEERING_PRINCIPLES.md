# Engineering Principles

**career-agent coding standards and best practices**

These principles were derived from code analysis and established to maintain consistency as the project grows.

---

## 1. Code Style Standards

### Python Version
- **Minimum**: Python 3.10+
- **Target**: Python 3.10 for compatibility
- **Rationale**: Leverages modern Python features (match statements, union types) while maintaining broad compatibility

### PEP 8 Compliance
- Follow [PEP 8](https://peps.python.org/pep-0008/) with the following adjustments:
  - **Line length**: 100 characters (enforced by Ruff)
  - **String quotes**: Double quotes preferred (enforced by Ruff formatter)
  - **Indentation**: 4 spaces (no tabs)

### Code Formatting
- **Tool**: [Ruff](https://github.com/astral-sh/ruff) (replaces Black, isort, flake8)
- **Configuration**: See `pyproject.toml`
- **Auto-format**: `ruff format .`
- **Pre-commit hook**: Optional but recommended

### Import Organization
```python
# 1. Standard library
import json
import sys
from pathlib import Path

# 2. Third-party dependencies
from reportlab.platypus import SimpleDocTemplate

# 3. Local imports
from cv_builder import build_cv
```

### Naming Conventions
- **Functions/variables**: `snake_case`
- **Classes**: `PascalCase`
- **Constants**: `SCREAMING_SNAKE_CASE`
- **Private**: `_leading_underscore`

**Examples:**
```python
# Good
def build_cv(profile: dict, config: dict) -> None: ...
DARK = colors.HexColor("#1a1a2e")

# Avoid
def BuildCV(...): ...  # Use snake_case
dark = "#1a1a2e"       # Use SCREAMING_SNAKE_CASE for constants
```

---

## 2. Type Hint Policy

### Current State
- **Existing code**: Partially typed (function signatures)
- **New code**: MUST include type hints on public APIs
- **Gradual typing**: Encouraged but not required for internal helpers

### Requirements
- ✅ **Required**: Type hints on public function signatures
- ✅ **Recommended**: Return type annotations
- ⚠️ **Optional**: Internal variable type annotations
- ❌ **Not required**: Full strict typing (mypy --strict)

**Examples:**
```python
# Required: Public API with types
def build_cv(profile: dict, config: dict, output_path: str) -> None:
    """Build a tailored CV PDF."""
    ...

# Good: Helper with types
def _s(name: str, **kw) -> ParagraphStyle:
    ...

# Acceptable: Internal helper without exhaustive types
def rule():
    return HRFlowable(...)
```

### Type Checking
- **Tool**: mypy (non-strict mode)
- **Run**: `mypy src/`
- **CI**: Type checking runs on every PR
- **Ignore missing imports**: For third-party libraries without stubs (reportlab)

---

## 3. Documentation Standards

### Module Docstrings
Every module MUST have a docstring with:
1. Brief description
2. Usage example
3. Key parameters/structure

**Example:**
```python
"""cv_builder.py: ATS-optimised CV PDF builder.

Reads personal data from profile.json; role-specific content from the role config dict.

Usage:
    from cv_builder import build_cv
    build_cv(profile, config, "/path/to/output.pdf")
"""
```

### Function Docstrings
Public functions SHOULD have docstrings explaining:
- Purpose
- Parameters
- Return value (if not obvious)

**Example:**
```python
def build_cv(profile: dict, config: dict, output_path: str) -> None:
    """
    Build a tailored CV PDF.

    profile keys (from profile.json):
        name, email, location, links, education

    config keys (from roles/<id>.json):
        company, title, headline, summary, experience, skills
    """
```

### Comments
- Use inline comments for complex logic
- Prefer self-documenting code over excessive comments
- Include "why" not "what" (code shows what, comments explain why)

### User-Facing Errors
All error messages MUST guide the user on what to do next:

**Good:**
```python
print("ERROR: profile.json not found.")
print("Run:  cp profile.example.json profile.json")
print("Then fill in your personal details.")
```

**Bad:**
```python
raise FileNotFoundError("profile.json")
```

---

## 4. Testing Requirements

### Test Coverage Strategy
- **Smoke tests**: REQUIRED for all PRs
- **Integration tests**: REQUIRED for core functionality (PDF generation)
- **Unit tests**: Optional for complex logic
- **E2E tests**: Not feasible (requires browser automation setup)

### What We Test
✅ **Structure validation**: Directory structure, file existence
✅ **Syntax validation**: Python files compile, JSON is valid
✅ **Import chains**: Modules can be imported
✅ **Integration paths**: Real PDF generation with example data
❌ **Browser automation**: Requires Claude in Chrome or Codex Browser/Chrome state (CI can't test)

### Test Organization
```
tests/
├── smoke_test.py         # Fast structural/syntax validation
└── integration_test.sh   # Real PDF generation end-to-end
```

### Running Tests Locally
```bash
# Smoke tests (fast)
pytest tests/smoke_test.py -v

# Integration tests (requires reportlab)
bash tests/integration_test.sh

# All checks (CI simulation)
ruff check .
ruff format --check .
mypy src/
bandit -r src/ -c pyproject.toml
pytest tests/smoke_test.py
bash tests/integration_test.sh
```

### CI Requirements
- All tests MUST pass before merge
- No warnings suppression without justification
- Integration tests run on Python 3.10, 3.11, 3.12 matrix

---

## 5. Security Practices

### PII Protection
**CRITICAL**: Never commit personally identifiable information.

**Gitignored files:**
- `profile.json`: User's personal data
- `roles/`: Company-specific configs (may contain emails, phone numbers)
- `tracker.json`: Application history
- `generated/`: PDFs with PII

**Verification:**
- Pre-commit hooks prevent accidental commits
- Regular audits of `.gitignore` completeness

### Dependency Security
- **Minimal dependencies**: Only add dependencies with clear justification
- **Pin versions**: Use `>=` for minimum, specific versions in CI
- **Automated scanning**: Dependabot runs monthly
- **Vulnerability scanning**: `safety check` runs daily in CI

### Code Security
- **Bandit**: Python security linting (runs on every PR)
- **CodeQL**: Semantic analysis (runs daily)
- **Trivy**: Secret detection + filesystem scanning
- **No credentials in code**: Ever. Period.

### Security Scanning Tools
| Tool | Scope | Frequency |
|------|-------|-----------|
| bandit | Python security anti-patterns | Every PR |
| safety | Dependency vulnerabilities | Daily |
| CodeQL | Semantic code analysis | Daily + PR |
| Trivy | Secrets, misconfigurations | Daily |

---

## 6. Commit Message Convention

Follow [Conventional Commits](https://www.conventionalcommits.org/):

**Format:**
```
<type>: <description>

[optional body]
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `chore`: Maintenance (deps, config)
- `test`: Test additions/changes
- `refactor`: Code restructuring (no behavior change)
- `perf`: Performance improvements

**Examples:**
```bash
feat: add /source skill for job discovery
fix: correct SKILL.md frontmatter parsing
docs: add GitHub Pages link to README
chore: update GitHub username to nextwebb
test: add comprehensive smoke test suite
```

**Rules:**
- Imperative mood ("add" not "added")
- Lowercase (except proper nouns)
- No period at end
- Keep under 72 characters
- Include scope when helpful: `fix(cv_builder): handle missing education field`

---

## 7. Dependency Management

### Philosophy
**Minimal by default. Every dependency is a liability.**

### Before Adding a Dependency
Ask:
1. Can I implement this in <100 lines of code?
2. Is this dependency actively maintained?
3. Does it have known security issues?
4. Will it complicate installation for users?

### Current Dependencies
- **reportlab**: PDF generation (REQUIRED, no viable alternative)

### Dependency Pinning
**requirements.txt:**
```
reportlab>=4.0
```

**CI (pyproject.toml):**
```toml
dependencies = [
    "reportlab>=4.0",
]
```

**Development tools** (not in requirements.txt):
- ruff, mypy, bandit, pytest, pre-commit (installed separately)

### Updates
- **Dependabot**: Monthly automated PRs
- **Manual review**: Quarterly audit of dependencies
- **Breaking changes**: Document in CHANGELOG, notify users

---

## 8. CI/CD Requirements

### Continuous Integration
All PRs MUST pass:
- ✅ Ruff linting + formatting
- ✅ mypy type checking
- ✅ bandit security scan
- ✅ Smoke tests
- ✅ Integration tests (Python 3.10, 3.11, 3.12)
- ✅ JSON/YAML validation

### Continuous Security
Daily automated scans:
- CodeQL semantic analysis
- Dependency vulnerability scanning (safety)
- Secret detection (Trivy)
- Filesystem security scan (Trivy)

### Branch Protection
**main branch requirements:**
- Status checks must pass
- No force push
- No direct commits (PR only)

### Pre-commit Hooks (Optional)
Install locally for faster feedback:
```bash
pip install pre-commit
pre-commit install
```

Hooks run automatically before each commit:
- Ruff linting + formatting
- Trailing whitespace removal
- JSON/YAML validation
- Large file prevention
- PII file blocking

---

## 9. Code Review Standards

### What to Look For
✅ **Correctness**: Does it work as intended?
✅ **Security**: Any PII leaks? SQL injection vectors?
✅ **Readability**: Can another developer understand it?
✅ **Tests**: Are changes covered by tests?
✅ **Documentation**: Updated README/SKILL.md if needed?
✅ **Style**: Passes Ruff/mypy without warnings?

### PR Checklist (Author)
Before requesting review:
- [ ] All CI checks pass
- [ ] Added/updated tests
- [ ] Updated documentation
- [ ] No console.log or debug prints
- [ ] Conventional commit messages
- [ ] No merge conflicts

### PR Checklist (Reviewer)
- [ ] Code is readable and maintainable
- [ ] No security vulnerabilities introduced
- [ ] Tests cover new functionality
- [ ] Documentation is accurate
- [ ] Conventional commit format followed

---

## 10. Plugin Development Standards

### Skill Structure
Each skill lives in `skills/<name>/SKILL.md`:

```markdown
# skill-name

Brief description.

## Triggers
User says: `/skill-name`, `natural language variant`

## Arguments
```
/skill-name <arg1> [optional]
```

## Steps
1. Load data
2. Process
3. Output
```

### Skill Naming
- **Lowercase**: `generate-cv` not `GenerateCV`
- **Hyphenated**: `new-role` not `new_role`
- **Imperative**: `apply` not `applicator`

### Plugin Manifests

Claude Code uses `plugin.json` and `.claude-plugin/plugin.json`:

```json
{
  "name": "career-agent",
  "version": "1.0.0",
  "description": "Brief description",
  "skills": ["./skills"]
}
```

The `"skills"` array takes a single `./`-prefixed path to the **skills directory** (not individual skill paths). The Claude CLI discovers all `SKILL.md` files under that directory automatically. The `./` prefix is required by the Claude CLI validator.

Codex uses `.codex-plugin/plugin.json`:

```json
{
  "name": "career-agent",
  "version": "1.0.0",
  "description": "Brief description",
  "skills": "./skills/"
}
```

Codex skill frontmatter must include both `name` and `description`. The `name` must match the skill directory.

**Version format**: Semantic versioning (major.minor.patch)

---

## 11. Error Handling Philosophy

### CLI Scripts
- **No stack traces**: Users don't need them
- **Helpful messages**: Always explain what to do next
- **Exit codes**: Use `sys.exit(1)` for errors, `0` for success

**Example:**
```python
if not PROFILE_PATH.exists():
    print("ERROR: profile.json not found.")
    print("Run:  cp profile.example.json profile.json")
    print("Then fill in your personal details.")
    sys.exit(1)
```

### Library Functions
- Return `None` or empty containers for missing data
- Raise exceptions for truly exceptional conditions
- Document error conditions in docstrings

---

## 12. Performance Considerations

### Current Scale
- Small codebase (~500 lines)
- Single-user tool (not web service)
- PDF generation is I/O bound (not CPU)

### Optimization Guidelines
- **Prefer readability over micro-optimizations**
- **Don't prematurely optimize**
- **Profile before optimizing**
- No caching needed (single-use script)

---

## 13. Future Considerations

### Planned Improvements
- [ ] Add more ATS platform support (Ashby, SmartRecruiters)
- [ ] Improve type coverage (gradual typing)
- [ ] Add unit tests for complex logic
- [ ] Consider pytest-cov for coverage metrics

### Not Planned
- ❌ Web interface (CLI is the design)
- ❌ Database persistence (JSON is sufficient)
- ❌ Cloud deployment (local-first by design)
- ❌ Multi-user support (single-user tool)

---

## Questions?

Open an issue or discussion on GitHub:
https://github.com/nextwebb/career-agent/discussions

Last updated: 2026-06-13
