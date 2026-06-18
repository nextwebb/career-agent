#!/usr/bin/env python3
"""
smoke_test.py — Smoke tests for career-agent

Validates project structure, configuration files, and basic functionality
without requiring external dependencies or PII data.

Run: pytest tests/smoke_test.py -v
"""

import json
import os
import py_compile
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

# Project root
ROOT = Path(__file__).parent.parent


# Canonical skill names — single source of truth used by both structure and manifest tests.
EXPECTED_SKILLS = ["apply", "generate-cv", "new-role", "setup-profile", "source", "track"]


def parse_skill_frontmatter(skill_file: Path) -> dict[str, str]:
    lines = skill_file.read_text(encoding="utf-8").splitlines()
    assert lines and lines[0].strip() == "---", f"{skill_file} missing YAML frontmatter"

    end = next((i for i, line in enumerate(lines[1:], 1) if line.strip() == "---"), None)
    assert end is not None, f"{skill_file} frontmatter is not closed"

    metadata: dict[str, str] = {}
    for line in lines[1:end]:
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        metadata[key.strip()] = value.strip().strip('"')
    return metadata


class TestProjectStructure:
    """Validate directory structure and required files exist."""

    def test_required_directories_exist(self):
        """Check that all required directories are present."""
        required_dirs = [
            ROOT / "src",
            ROOT / "skills",
            ROOT / "roles.example",
        ]
        for directory in required_dirs:
            assert directory.exists(), f"Missing required directory: {directory}"
            assert directory.is_dir(), f"Path exists but is not a directory: {directory}"

    def test_skill_directories_exist(self):
        """Verify all skill directories have SKILL.md files."""
        skills_dir = ROOT / "skills"

        for skill in EXPECTED_SKILLS:
            skill_dir = skills_dir / skill
            assert skill_dir.exists(), f"Missing skill directory: {skill}"
            skill_md = skill_dir / "SKILL.md"
            assert skill_md.exists(), f"Missing SKILL.md in {skill}"

    def test_example_files_exist(self):
        """Check that example configuration files exist."""
        example_files = [
            ROOT / "profile.example.json",
            ROOT / "roles.example" / "example_role.json",
        ]
        for file in example_files:
            assert file.exists(), f"Missing example file: {file}"
            assert file.is_file(), f"Path exists but is not a file: {file}"


class TestSetupInstaller:
    """Validate installer prerequisite checks."""

    def _write_executable(self, path, content):
        path.write_text(textwrap.dedent(content), encoding="utf-8")
        path.chmod(0o755)

    def _write_python_shim(self, path, python_version):
        python_shim = f"""\
            #!/usr/bin/env sh
            if [ "$1" = "--version" ]; then
              echo "Python {python_version}"
              exit 0
            fi
            if [ "$1" = "-c" ]; then
              exit 0
            fi
            exit 0
        """
        self._write_executable(path, python_shim)

    def _write_missing_command_shim(self, path):
        self._write_executable(
            path,
            """\
            #!/usr/bin/env sh
            exit 127
            """,
        )

    def _write_host_shim(self, path, version):
        self._write_executable(
            path,
            f"""\
            #!/usr/bin/env sh
            if [ "$1" = "--version" ]; then
              echo "{version}"
              exit 0
            fi
            exit 0
            """,
        )

    def _run_setup_with_python(
        self,
        tmp_path,
        python_version,
        versioned_python=None,
        host_commands=("claude",),
        args=None,
    ):
        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()

        versioned_python = versioned_python or {}
        self._write_python_shim(bin_dir / "python3", python_version)
        self._write_python_shim(bin_dir / "python", python_version)
        for command in ["python3.12", "python3.11", "python3.10"]:
            if command not in versioned_python:
                self._write_missing_command_shim(bin_dir / command)
        for command, version in versioned_python.items():
            self._write_python_shim(bin_dir / command, version)

        for command in ("claude", "codex"):
            if command in host_commands:
                version = "2.1.153 (Claude Code)" if command == "claude" else "codex-cli 0.140.0"
                self._write_host_shim(bin_dir / command, version)
            else:
                self._write_missing_command_shim(bin_dir / command)

        node_bin = shutil.which("node")
        assert node_bin, "node is required for installer smoke tests"

        env = {
            **os.environ,
            "PATH": f"{bin_dir}{os.pathsep}/bin",
            "HOME": str(tmp_path / "home"),
        }
        env["HOME"] and Path(env["HOME"]).mkdir()

        return subprocess.run(
            [node_bin, str(ROOT / "bin" / "setup.js"), *(args or [])],
            cwd=tmp_path,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )

    def test_setup_rejects_python_39(self, tmp_path):
        """Installer should enforce documented Python 3.10+ minimum."""
        result = self._run_setup_with_python(tmp_path, "3.9.6")

        output = result.stdout + result.stderr
        assert result.returncode == 1
        assert "Python 3.10+ not found." in output
        assert not (tmp_path / "profile.json").exists()

    @pytest.mark.parametrize("python_version", ["3.10.14", "3.11.13", "3.12.11"])
    def test_setup_accepts_supported_python_versions(self, tmp_path, python_version):
        """Installer should continue for documented supported Python versions."""
        result = self._run_setup_with_python(tmp_path, python_version)

        output = result.stdout + result.stderr
        assert result.returncode == 0, output
        assert f"Python found: Python {python_version}" in output
        assert "Prerequisites met." in output
        assert (tmp_path / "profile.json").exists()

    def test_setup_accepts_codex_only_environment(self, tmp_path):
        """Installer should not require Claude when Codex is available."""
        result = self._run_setup_with_python(
            tmp_path,
            "3.11.13",
            host_commands=("codex",),
        )

        output = result.stdout + result.stderr
        assert result.returncode == 0, output
        assert "Codex CLI found: codex-cli 0.140.0" in output
        assert "Claude Code CLI not found" in output
        assert (tmp_path / "profile.json").exists()

    def test_setup_rejects_missing_agent_hosts(self, tmp_path):
        """Installer should fail when neither Claude nor Codex is available."""
        result = self._run_setup_with_python(
            tmp_path,
            "3.11.13",
            host_commands=(),
        )

        output = result.stdout + result.stderr
        assert result.returncode == 1
        assert "Neither Claude Code nor Codex CLI was found." in output
        assert not (tmp_path / "profile.json").exists()

    def test_setup_doctor_dispatches_to_doctor(self, tmp_path):
        """`career-agent doctor` should run doctor behavior, not setup."""
        result = self._run_setup_with_python(
            tmp_path,
            "3.11.13",
            host_commands=("codex",),
            args=["doctor"],
        )

        output = result.stdout + result.stderr
        assert "career-agent health check" in output
        assert "Setting up profile" not in output
        assert not (tmp_path / "profile.json").exists()

    def test_doctor_rejects_python_39(self, tmp_path):
        """Doctor should enforce the documented Python 3.10+ minimum."""
        result = self._run_setup_with_python(
            tmp_path,
            "3.9.6",
            host_commands=("codex",),
            args=["doctor"],
        )

        output = result.stdout + result.stderr
        assert result.returncode == 1
        assert "Python 3.10+" in output
        assert "FAIL" in output

    def test_doctor_reports_codex_without_claude(self, tmp_path):
        """Doctor should report Claude and Codex status independently."""
        (tmp_path / "profile.json").write_text('{"name": "Test User"}', encoding="utf-8")

        result = self._run_setup_with_python(
            tmp_path,
            "3.11.13",
            host_commands=("codex",),
            args=["doctor"],
        )

        output = result.stdout + result.stderr
        assert result.returncode == 0, output
        assert "Codex CLI" in output
        assert "codex-cli 0.140.0" in output
        assert "Claude Code CLI" in output
        assert "required only for Claude Code plugin usage" in output

    def test_setup_accepts_versioned_python_when_default_is_unsupported(self, tmp_path):
        """Installer should try supported versioned Python executables before failing."""
        result = self._run_setup_with_python(
            tmp_path,
            "3.9.6",
            versioned_python={"python3.11": "3.11.13"},
        )

        output = result.stdout + result.stderr
        assert result.returncode == 0, output
        assert "Python found: Python 3.11.13" in output
        assert "Prerequisites met." in output
        assert (tmp_path / "profile.json").exists()


class TestPythonSyntax:
    """Validate all Python files compile without syntax errors."""

    def test_all_python_files_compile(self):
        """Check that all .py files have valid syntax."""
        python_files = list(ROOT.glob("src/**/*.py")) + list(ROOT.glob("*.py"))
        python_files = [f for f in python_files if "__pycache__" not in str(f)]

        assert len(python_files) > 0, "No Python files found!"

        for py_file in python_files:
            try:
                py_compile.compile(str(py_file), doraise=True)
            except py_compile.PyCompileError as e:
                pytest.fail(f"Syntax error in {py_file}: {e}")

    def test_python_modules_import(self):
        """Verify core modules can be imported (requires reportlab)."""
        sys.path.insert(0, str(ROOT / "src"))

        # Check if reportlab is available
        try:
            import reportlab  # noqa: F401
        except ImportError:
            pytest.skip("reportlab not installed - skipping module import test")

        try:
            import cl_builder
            import cv_builder
            import tracker

            # Check key functions exist
            assert hasattr(cv_builder, "build_cv"), "Missing build_cv function"
            assert hasattr(cl_builder, "build_cover_letter"), "Missing build_cover_letter"
            assert hasattr(tracker, "load"), "Missing tracker.load function"
        except ImportError as e:
            pytest.fail(f"Failed to import core modules: {e}")
        finally:
            sys.path.pop(0)


class TestJSONConfigs:
    """Validate all JSON configuration files are valid."""

    def test_plugin_json_valid(self):
        """Verify plugin.json is valid JSON with required fields."""
        plugin_file = ROOT / "plugin.json"
        assert plugin_file.exists(), "Missing plugin.json"

        with open(plugin_file, encoding="utf-8") as f:
            data = json.load(f)

        required_fields = ["name", "version", "description", "skills"]
        for field in required_fields:
            assert field in data, f"Missing required field in plugin.json: {field}"

        assert data["name"] == "career-agent", "Incorrect plugin name"
        # Per the Claude Code marketplace spec, skills points to the parent directory
        # containing <name>/SKILL.md subdirectories, not individual skill dirs.
        assert set(data["skills"]) == {"./skills"}, (
            f"plugin.json skills must be ['./skills'] (parent dir per marketplace spec).\n"
            f"  got: {sorted(data['skills'])}"
        )

    def test_claude_plugin_json_valid(self):
        """Verify .claude-plugin/plugin.json is the canonical marketplace manifest."""
        plugin_file = ROOT / ".claude-plugin" / "plugin.json"
        assert (
            plugin_file.exists()
        ), "Missing .claude-plugin/plugin.json (canonical marketplace manifest)"

        with open(plugin_file, encoding="utf-8") as f:
            data = json.load(f)

        required_fields = ["name", "version", "description", "skills"]
        for field in required_fields:
            assert field in data, f"Missing required field in .claude-plugin/plugin.json: {field}"

        assert data["name"] == "career-agent", "Incorrect plugin name in .claude-plugin/plugin.json"
        assert set(data["skills"]) == {"./skills"}, (
            f".claude-plugin/plugin.json skills must be ['./skills'].\n"
            f"  got: {sorted(data['skills'])}"
        )

    def test_codex_plugin_json_valid(self):
        """Verify .codex-plugin/plugin.json is the Codex plugin manifest."""
        plugin_file = ROOT / ".codex-plugin" / "plugin.json"
        assert plugin_file.exists(), "Missing .codex-plugin/plugin.json"

        with open(plugin_file, encoding="utf-8") as f:
            data = json.load(f)

        required_fields = ["name", "version", "description", "skills", "interface"]
        for field in required_fields:
            assert field in data, f"Missing required field in .codex-plugin/plugin.json: {field}"

        assert data["name"] == "career-agent", "Incorrect plugin name in Codex manifest"
        assert data["skills"] == "./skills/", "Codex manifest skills must be './skills/'"
        assert data["version"] == json.loads((ROOT / "package.json").read_text())["version"]

    def test_release_versions_match(self):
        """Release metadata should not drift across maintained manifests."""
        package_version = json.loads((ROOT / "package.json").read_text())["version"]
        manifest_version = json.loads((ROOT / ".release-please-manifest.json").read_text())["."]
        plugin_version = json.loads((ROOT / "plugin.json").read_text())["version"]
        claude_version = json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text())[
            "version"
        ]
        codex_version = json.loads((ROOT / ".codex-plugin" / "plugin.json").read_text())["version"]

        pyproject_text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
        assert f'version = "{package_version}"' in pyproject_text
        assert {manifest_version, plugin_version, claude_version, codex_version} == {
            package_version
        }

    def test_profile_example_valid(self):
        """Verify profile.example.json is valid JSON."""
        profile_file = ROOT / "profile.example.json"
        assert profile_file.exists(), "Missing profile.example.json"

        with open(profile_file, encoding="utf-8") as f:
            data = json.load(f)

        # Check expected structure
        assert "name" in data or ("name" in data and isinstance(data["name"], dict))
        assert "email" in data or "contact" in data

    def test_role_example_valid(self):
        """Verify example role config is valid JSON."""
        role_file = ROOT / "roles.example" / "example_role.json"
        assert role_file.exists(), "Missing example_role.json"

        with open(role_file, encoding="utf-8") as f:
            data = json.load(f)

        # Check expected fields
        expected_fields = ["role_id", "company", "title"]
        for field in expected_fields:
            assert field in data, f"Missing field in example role: {field}"

    def test_marketplace_json_valid(self):
        """Verify marketplace.json is valid if it exists."""
        marketplace_file = ROOT / ".claude-plugin" / "marketplace.json"
        if marketplace_file.exists():
            with open(marketplace_file, encoding="utf-8") as f:
                data = json.load(f)
            # Check that repository exists (either at root or in plugins array)
            has_root_repo = "repository" in data
            has_plugin_repos = (
                "plugins" in data
                and isinstance(data["plugins"], list)
                and len(data["plugins"]) > 0
                and "repository" in data["plugins"][0]
            )
            assert has_root_repo or has_plugin_repos, "Missing repository field in marketplace.json"


class TestSKILLMarkdown:
    """Validate SKILL.md files have proper structure."""

    def test_skill_md_files_have_titles(self):
        """Check that all SKILL.md files have a markdown title (after optional frontmatter)."""
        skills_dir = ROOT / "skills"
        skill_files = list(skills_dir.glob("*/SKILL.md"))

        assert len(skill_files) >= 5, "Expected at least 5 skill files"

        for skill_file in skill_files:
            lines = skill_file.read_text(encoding="utf-8").splitlines()
            # Skip YAML frontmatter block (--- ... ---)
            if lines and lines[0].strip() == "---":
                end = next(
                    (i for i, line in enumerate(lines[1:], 1) if line.strip() == "---"), None
                )
                lines = lines[end + 1 :] if end is not None else lines[1:]
            heading = next((line for line in lines if line.strip()), "")
            assert heading.startswith("#"), f"{skill_file.name} missing markdown title"

    def test_skill_md_files_have_content(self):
        """Verify SKILL.md files are not empty."""
        skills_dir = ROOT / "skills"
        skill_files = list(skills_dir.glob("*/SKILL.md"))

        for skill_file in skill_files:
            content = skill_file.read_text(encoding="utf-8")
            assert len(content) > 100, f"{skill_file.name} appears to be incomplete"
            assert "##" in content, f"{skill_file.name} missing section headers"

    def test_skill_frontmatter_has_codex_metadata(self):
        """Codex skills require name and description frontmatter."""
        for skill_file in (ROOT / "skills").glob("*/SKILL.md"):
            metadata = parse_skill_frontmatter(skill_file)
            assert metadata.get("name") == skill_file.parent.name
            assert metadata.get("description"), f"{skill_file} missing description"

    def test_shared_skills_do_not_reference_claude_only_tools(self):
        """Shared skills should not call Claude-only MCP tools or env vars."""
        forbidden = [
            "mcp__Claude_in_Chrome",
            "mcp__workspace__web_fetch",
            "CLAUDE_PLUGIN_ROOT",
            "Claude-in-Chrome",
        ]

        for skill_file in (ROOT / "skills").glob("*/SKILL.md"):
            content = skill_file.read_text(encoding="utf-8")
            for token in forbidden:
                assert token not in content, f"{skill_file} contains Claude-only token {token}"

    def test_installed_skill_commands_do_not_use_workspace_relative_src_paths(self):
        """Installed skills should resolve packaged scripts instead of cwd-relative src paths."""
        for skill_name in ["generate-cv", "track"]:
            skill_file = ROOT / "skills" / skill_name / "SKILL.md"
            content = skill_file.read_text(encoding="utf-8")

            assert "python3 src/" not in content
            assert "<career_agent_root>" in content

    def test_apply_sensitive_field_policy_present(self):
        """The /apply policy should include the expanded human handoff boundary."""
        content = (ROOT / "skills" / "apply" / "SKILL.md").read_text(encoding="utf-8")
        required_terms = [
            "GDPR",
            "data retention",
            "talent pool",
            "attestation",
            "CAPTCHA",
            "National IDs",
            "SSN/tax IDs",
            "passport",
            "date of birth",
            "bank",
            "payroll",
            "unsupported ATS",
            "This policy overrides `role.custom_answers`",
        ]
        for term in required_terms:
            assert term in content, f"/apply missing sensitive-field term: {term}"

    def test_apply_sensitive_field_policy_precedes_personal_field_fill(self):
        """/apply must classify fields before filling any personal data."""
        content = (ROOT / "skills" / "apply" / "SKILL.md").read_text(encoding="utf-8")

        classifier_index = content.index("### 3. Sensitive-field classifier")
        fill_index = content.index("### 4. Fill safe personal fields")

        assert classifier_index < fill_index
        assert "Any other non-sensitive personal fields visible after classification" in content

    def test_source_profile_recovery_points_to_setup_profile(self):
        """/source should not direct missing-profile recovery to /new-role."""
        content = (ROOT / "skills" / "source" / "SKILL.md").read_text(encoding="utf-8")
        recovery_start = content.index("### Option C")
        recovery_end = content.index("---", recovery_start)
        recovery = content[recovery_start:recovery_end]

        assert "/setup-profile" in recovery
        assert "/new-role" not in recovery

    def test_agents_md_exists_for_codex(self):
        """Codex should have repository-level project guidance."""
        agents_md = ROOT / "AGENTS.md"
        assert agents_md.exists(), "Missing AGENTS.md"

        content = agents_md.read_text(encoding="utf-8")
        for term in ["career-agent", "profile.json", "roles/", "generated/", "Submit"]:
            assert term in content

    def test_npm_packlist_is_validated(self):
        """npm pack should include runtime assets and exclude local artifacts."""
        node_bin = shutil.which("node")
        npm_bin = shutil.which("npm")
        if not node_bin or not npm_bin:
            pytest.skip("node and npm are required for package packlist validation")

        result = subprocess.run(
            [node_bin, str(ROOT / "scripts" / "check-package.js")],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, result.stdout + result.stderr


class TestPublicContactPolicy:
    """Validate the public metadata/doc contact policy enforced by check-package."""

    def _copy_repo_for_package_check(self, tmp_path):
        repo = tmp_path / "repo"
        shutil.copytree(
            ROOT,
            repo,
            ignore=shutil.ignore_patterns(
                ".git",
                ".mypy_cache",
                ".pytest_cache",
                ".ruff_cache",
                "__pycache__",
                "build",
                "dist",
                "node_modules",
                "*.pyc",
            ),
        )
        return repo

    def _run_check_package(self, repo):
        node_bin = shutil.which("node")
        npm_bin = shutil.which("npm")
        if not node_bin or not npm_bin:
            pytest.skip("node and npm are required for package policy validation")

        return subprocess.run(
            [node_bin, str(repo / "scripts" / "check-package.js")],
            cwd=repo,
            capture_output=True,
            text=True,
            check=False,
        )

    def test_check_package_rejects_personal_security_email(self, tmp_path):
        """SECURITY.md must use private GitHub reporting, not a direct maintainer email."""
        repo = self._copy_repo_for_package_check(tmp_path)
        security = repo / "SECURITY.md"
        security.write_text(
            "\n".join(
                [
                    "# Security Policy",
                    "",
                    "## Reporting a Vulnerability",
                    "",
                    "Email: security.contact@gmail.com",
                    "",
                    "Response: within 72 hours",
                ]
            ),
            encoding="utf-8",
        )

        result = self._run_check_package(repo)
        output = result.stdout + result.stderr

        assert result.returncode != 0
        assert "Public metadata/docs contain direct email contact(s)." in output
        assert "SECURITY.md:" in output

    def test_check_package_scans_packaged_plugin_docs(self, tmp_path):
        """The contact scan should include public docs discovered through npm pack."""
        repo = self._copy_repo_for_package_check(tmp_path)
        plugin_readme = repo / ".claude-plugin" / "README.md"
        plugin_readme.write_text(
            plugin_readme.read_text(encoding="utf-8")
            + "\n\nSecurity contact: maintainer.person@proton.me\n",
            encoding="utf-8",
        )

        result = self._run_check_package(repo)
        output = result.stdout + result.stderr

        assert result.returncode != 0
        assert ".claude-plugin/README.md:" in output

    def test_check_package_ignores_local_private_data_areas(self, tmp_path):
        """Local-only career data may contain applicant emails and must stay out of public scans."""
        repo = self._copy_repo_for_package_check(tmp_path)
        (repo / "profile.json").write_text('{"email": "applicant@gmail.com"}', encoding="utf-8")
        (repo / "tracker.json").write_text('{"contact": "recruiter@company.com"}', encoding="utf-8")
        (repo / "roles" / "private.json").write_text(
            '{"recruiter_email": "recruiter@company.com"}',
            encoding="utf-8",
        )
        (repo / "generated" / "note.txt").write_text(
            "Application contact: applicant@gmail.com",
            encoding="utf-8",
        )

        result = self._run_check_package(repo)

        assert result.returncode == 0, result.stdout + result.stderr

    def test_validation_policy_documents_required_external_suite_distinction(self):
        """Post-merge reports must distinguish empty app suites from required gates."""
        content = (ROOT / "docs" / "validation-policy.md").read_text(encoding="utf-8")
        normalized_content = " ".join(content.split())

        required_policy_terms = [
            "zero check runs",
            "not evidence of either success or failure",
            "do not block a green post-merge validation claim",
            "explicitly made that app a required check",
            "concrete check run with logs",
            "terminal conclusion",
        ]
        for term in required_policy_terms:
            assert term in normalized_content, f"validation policy missing invariant: {term}"

        required_gates = [
            "CI / All Checks Passed",
            "Security / CodeQL Analysis",
            "Security / Dependency Vulnerability Check",
            "Security / Trivy Filesystem Scan",
            "Security / Trivy Secret Scan",
            "Security / Security Summary",
            "Deploy GitHub Pages / Deploy docs/ to GitHub Pages",
            "Release Please / release-please",
        ]
        for gate in required_gates:
            assert gate in content, f"validation policy missing required gate: {gate}"


class TestPackagedScriptWorkspace:
    """Installed scripts should operate on the caller's workspace data."""

    def test_tracker_uses_current_workspace_for_user_data(self, tmp_path):
        """tracker.py should not require the repo root as cwd."""
        roles_dir = tmp_path / "roles"
        roles_dir.mkdir()
        shutil.copy(ROOT / "roles.example" / "example_role.json", roles_dir / "example_role.json")

        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "src" / "tracker.py"),
                "--add",
                "example_role",
            ],
            cwd=tmp_path,
            capture_output=True,
            text=True,
            check=False,
        )

        assert result.returncode == 0, result.stderr or result.stdout
        tracker_path = tmp_path / "tracker.json"
        assert tracker_path.exists()
        entries = json.loads(tracker_path.read_text(encoding="utf-8"))
        assert entries[0]["role_id"] == "example_role"
        assert entries[0]["company"] == "Stripe"

    def test_generate_application_uses_current_workspace_for_user_data(self, tmp_path):
        """generate_application.py should support an installed script path from a workspace cwd."""
        pytest.importorskip("reportlab")

        roles_dir = tmp_path / "roles"
        roles_dir.mkdir()
        shutil.copy(ROOT / "profile.example.json", tmp_path / "profile.json")
        shutil.copy(ROOT / "roles.example" / "example_role.json", roles_dir / "example_role.json")

        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "src" / "generate_application.py"),
                "--role",
                "example_role",
            ],
            cwd=tmp_path,
            capture_output=True,
            text=True,
            check=False,
        )

        assert result.returncode == 0, result.stderr or result.stdout
        generated_dir = tmp_path / "generated"
        assert list(generated_dir.glob("*_CV.pdf"))
        assert list(generated_dir.glob("*_CoverLetter.pdf"))


class TestGitignore:
    """Validate .gitignore prevents committing PII."""

    def test_gitignore_blocks_pii_files(self):
        """Check that sensitive files are in .gitignore."""
        gitignore_file = ROOT / ".gitignore"
        assert gitignore_file.exists(), "Missing .gitignore file"

        with open(gitignore_file, encoding="utf-8") as f:
            content = f.read()

        # Critical files that must be gitignored
        critical_patterns = [
            "profile.json",
            "roles/",
            "tracker.json",
            "generated/",
            ".env",
        ]

        for pattern in critical_patterns:
            assert pattern in content, f"SECURITY: .gitignore missing pattern: {pattern}"


class TestRequirementsTxt:
    """Validate requirements.txt structure."""

    def test_requirements_file_exists(self):
        """Check that requirements.txt exists and has content."""
        req_file = ROOT / "requirements.txt"
        assert req_file.exists(), "Missing requirements.txt"

        content = req_file.read_text(encoding="utf-8")
        assert "reportlab" in content, "Missing reportlab dependency"

    def test_requirements_format(self):
        """Verify requirements.txt has proper version pinning."""
        req_file = ROOT / "requirements.txt"
        with open(req_file, encoding="utf-8") as f:
            lines = [line.strip() for line in f if line.strip() and not line.startswith("#")]

        for line in lines:
            # Should have version constraint
            assert any(
                op in line for op in ["==", ">=", "~=", "<="]
            ), f"Requirement '{line}' should specify version constraint"


class TestReadmeAndDocs:
    """Validate documentation files."""

    def test_readme_exists(self):
        """Check that README.md exists and has content."""
        readme = ROOT / "README.md"
        assert readme.exists(), "Missing README.md"

        content = readme.read_text(encoding="utf-8")
        assert len(content) > 500, "README.md appears incomplete"
        assert "career-agent" in content.lower(), "README missing project name"

    def test_claude_md_exists(self):
        """Verify CLAUDE.md exists for plugin context."""
        claude_md = ROOT / "CLAUDE.md"
        assert claude_md.exists(), "Missing CLAUDE.md"

        content = claude_md.read_text(encoding="utf-8")
        assert "career-agent" in content.lower(), "CLAUDE.md missing project context"


if __name__ == "__main__":
    import pytest

    sys.exit(pytest.main([__file__, "-v"]))
