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
from typing import Any

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


def read_markdown_table_after_heading(content: str, heading: str) -> list[dict[str, str]]:
    """Return the first Markdown table after a heading as row dictionaries."""
    lines = content.splitlines()
    heading_index = lines.index(heading)
    table_start = next(i for i in range(heading_index + 1, len(lines)) if lines[i].startswith("|"))
    headers = [cell.strip() for cell in lines[table_start].strip("|").split("|")]
    rows: list[dict[str, str]] = []

    for line in lines[table_start + 2 :]:
        if not line.startswith("|"):
            break
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        assert len(cells) == len(headers), f"Malformed table row: {line}"
        rows.append(dict(zip(headers, cells, strict=True)))

    return rows


def normalize_whitespace(content: str) -> str:
    return " ".join(content.split())


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
        assert "does not install the Codex plugin" in output
        assert "codex plugin marketplace add nextwebb/career-agent" in output
        assert "codex plugin add career-agent@career-agent" in output
        assert "Codex plugin install and verification commands require Codex" not in output
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

    def test_setup_output_does_not_claim_codex_plugin_install(self, tmp_path):
        """Setup output should not imply npx installed the Codex plugin."""
        result = self._run_setup_with_python(
            tmp_path,
            "3.11.13",
            host_commands=("codex",),
        )

        output = result.stdout + result.stderr
        assert result.returncode == 0, output
        assert "does not install the Codex plugin" in output
        assert "codex plugin marketplace add nextwebb/career-agent" in output
        assert "codex plugin add career-agent@career-agent" in output
        assert "Codex plugin install and verification commands require Codex" not in output

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


class TestPublicInstallCopy:
    """Guard install docs against host setup ambiguity."""

    def test_readme_separates_codex_setup_from_npx_and_claude_install(self):
        content = (ROOT / "README.md").read_text(encoding="utf-8")
        normalized = normalize_whitespace(content)

        assert "### Codex setup" in content
        assert "`npx @nextwebb/career-agent` checks local prerequisites" in content
        assert "It does not install the Codex plugin." in content
        assert "The Claude marketplace commands above are Claude Code setup only." in content
        assert "Codex plugin install and verification commands require Codex" not in content
        assert "plugin marketplace add nextwebb/career-agent" in normalized
        assert "plugin add career-agent@career-agent" in normalized

    def test_docs_site_separates_codex_setup_from_npx_and_claude_install(self):
        content = (ROOT / "docs" / "index.html").read_text(encoding="utf-8")
        normalized = normalize_whitespace(content)

        assert "it does not install the Codex plugin" in normalized
        assert "Install the Codex plugin from this repository's marketplace" in normalized
        assert "The Claude commands above are Claude Code setup only" in normalized
        assert "plugin marketplace add nextwebb/career-agent" in normalized
        assert "plugin add career-agent@career-agent" in normalized


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
            from quality_gates import run_quality_gates

            # Check key functions exist
            assert hasattr(cv_builder, "build_cv"), "Missing build_cv function"
            assert hasattr(cl_builder, "build_cover_letter"), "Missing build_cover_letter"
            assert callable(run_quality_gates), "Missing run_quality_gates"
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

    def test_codex_marketplace_json_valid(self):
        """Verify Codex marketplace metadata exposes the packaged plugin."""
        marketplace_file = ROOT / ".agents" / "plugins" / "marketplace.json"
        assert marketplace_file.exists(), "Missing Codex marketplace catalog"

        data = json.loads(marketplace_file.read_text(encoding="utf-8"))
        assert data["name"] == "career-agent"
        assert data["interface"]["displayName"] == "career-agent"
        assert len(data["plugins"]) == 1

        plugin = data["plugins"][0]
        assert plugin["name"] == "career-agent"
        assert plugin["source"] == {
            "source": "local",
            "path": "./plugins/career-agent",
        }
        assert plugin["policy"] == {
            "installation": "AVAILABLE",
            "authentication": "ON_INSTALL",
        }
        assert plugin["category"] == "Productivity"

    def test_codex_marketplace_copy_matches_canonical_files(self):
        """Codex marketplace plugin files should not drift from root sources."""
        copied_paths = [
            ".codex-plugin/plugin.json",
            "AGENTS.md",
            "LICENSE",
            "README.md",
            "docs/apply-codex-chrome-verification.md",
            "docs/source-methodology.md",
            "profile.example.json",
            "requirements.txt",
            "roles.example/example_role.json",
            "skills/apply/SKILL.md",
            "skills/generate-cv/SKILL.md",
            "skills/new-role/SKILL.md",
            "skills/setup-profile/SKILL.md",
            "skills/source/SKILL.md",
            "skills/track/SKILL.md",
            "src/cl_builder.py",
            "src/cv_builder.py",
            "src/generate_application.py",
            "src/quality_gates.py",
            "src/tracker.py",
            "src/validation.py",
        ]

        plugin_root = ROOT / "plugins" / "career-agent"
        assert plugin_root.exists(), "Missing Codex marketplace plugin copy"

        for relative_path in copied_paths:
            canonical = ROOT / relative_path
            copied = plugin_root / relative_path
            assert copied.exists(), f"Missing Codex marketplace copy: {relative_path}"
            assert (
                copied.read_bytes() == canonical.read_bytes()
            ), f"Codex marketplace copy drifted: {relative_path}"

    def test_release_versions_match(self):
        """Release metadata should not drift across maintained manifests."""
        package_version = json.loads((ROOT / "package.json").read_text())["version"]
        manifest_version = json.loads((ROOT / ".release-please-manifest.json").read_text())["."]
        plugin_version = json.loads((ROOT / "plugin.json").read_text())["version"]
        claude_version = json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text())[
            "version"
        ]
        codex_version = json.loads((ROOT / ".codex-plugin" / "plugin.json").read_text())["version"]
        marketplace_codex_version = json.loads(
            (ROOT / "plugins" / "career-agent" / ".codex-plugin" / "plugin.json").read_text()
        )["version"]

        pyproject_text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
        assert f'version = "{package_version}"' in pyproject_text
        assert {
            manifest_version,
            plugin_version,
            claude_version,
            codex_version,
            marketplace_codex_version,
        } == {package_version}

    def test_release_please_updates_all_versioned_manifests(self):
        """Release Please should bump every maintained versioned manifest."""
        config = json.loads((ROOT / ".github" / "release-please-config.json").read_text())
        extra_file_paths = {item["path"] for item in config["packages"]["."]["extra-files"]}

        required_paths = {
            "plugin.json",
            ".claude-plugin/plugin.json",
            ".codex-plugin/plugin.json",
            "plugins/career-agent/.codex-plugin/plugin.json",
            "pyproject.toml",
        }
        assert required_paths <= extra_file_paths

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

    def test_apply_greenhouse_reliability_contracts_present(self):
        content = (ROOT / "skills" / "apply" / "SKILL.md").read_text(encoding="utf-8")
        normalized = normalize_whitespace(content)

        required_terms = [
            "### 0. Preflight and dry-run plan",
            "Do not generate PDFs for `--dry-run`",
            "sandboxCwd must be an absolute file URI",
            "Open a fresh tab/page for every ATS run",
            "stale installed plugin copy differs from repo HEAD",
            "native prototype setter",
            "bubbled `input` and `change` events",
            "verify after blur and after scrolling away/back",
            "browser-native file upload",
            "Do not inject one large inline base64 string into `Runtime.evaluate`",
            "localhost server",
            "small chunks",
            "Do not write PDF chunks to persistent ATS `localStorage`",
            "sessionStorage.setItem",
            "re-query the file input after every upload",
            "remount/reacquire count",
            "distinct filenames",
            "field container's visible label",
            'Never click a generic `[aria-label="Toggle flyout"]`',
            "Google Drive",
            "structured, redacted observation",
            "final proof that Submit was not clicked",
            "hidden required field",
            "Multiple file inputs, multi-step flow",
        ]
        for term in required_terms:
            assert term in content, f"/apply missing Greenhouse reliability contract: {term}"

        forbidden_fragments = [
            'const b64 = "<INSERT_BASE64_STRING>"',
            "document.querySelectorAll('input[type=\"file\"]')[<index>]",
            "Primary upload method — base64 DataTransfer injection",
            "Expected to work — not yet confirmed end-to-end",
            "Confirmed behaviour by platform",
            "End-to-end confirmed",
            'document.querySelector(\'[aria-label*="phone" i] input, input[aria-autocomplete="list"]\')',
            "localStorage.setItem",
        ]
        for fragment in forbidden_fragments:
            assert fragment not in content

        assert normalized.index("### 0. Preflight and dry-run plan") < normalized.index(
            "### 1. Load configs"
        )
        assert normalized.index("### 3. Sensitive-field classifier") < normalized.index(
            "### 4. Fill safe personal fields"
        )

    def test_apply_codex_chrome_verification_matrix_present(self):
        """Codex Chrome /apply support should be tied to structured evidence."""
        doc = ROOT / "docs" / "apply-codex-chrome-verification.md"
        assert doc.exists(), "Missing Codex Chrome /apply verification matrix"

        content = doc.read_text(encoding="utf-8")
        rows = read_markdown_table_after_heading(content, "## Support Status")
        rows_by_case = {row["ATS case"]: row for row in rows}

        required_cases = {
            "Greenhouse direct",
            "Greenhouse embed direct top-level URL",
            "Greenhouse EU domain",
            "Lever",
            "Workable",
            "Unknown or unsupported ATS",
            "Safety boundaries",
        }
        assert required_cases <= rows_by_case.keys()

        live_ats_cases = [
            "Greenhouse direct",
            "Greenhouse embed direct top-level URL",
            "Greenhouse EU domain",
            "Lever",
            "Workable",
        ]
        for case in live_ats_cases:
            row = rows_by_case[case]
            assert row["Codex Chrome status"] == "Experimental"
            assert row["Evidence status"] == "Live page observed 2026-06-18; no upload/fill"
            assert "Manual fallback" in row["Stable support decision"]

        unsupported = rows_by_case["Unknown or unsupported ATS"]
        assert unsupported["Codex Chrome status"] == "Unsupported for automation"
        assert "Live unsupported ATS page observed 2026-06-18" in unsupported["Evidence status"]
        assert "Do not automate" in unsupported["Stable support decision"]

        safety = rows_by_case["Safety boundaries"]
        assert safety["Codex Chrome status"] == "Required stop boundary"
        assert "Live pages observed 2026-06-18" in safety["Evidence status"]
        for term in ["Submit", "consent", "legal attestation", "CAPTCHA", "ambiguous"]:
            assert term in safety["URL pattern to verify"]
        assert "Never fill or click" in safety["Stable support decision"]

        required_evidence_fields = [
            "Date tested",
            "Codex surface",
            "Browser surface: Codex Chrome",
            "ATS platform",
            "URL pattern",
            "Generated CV PDF upload result",
            "Fields filled",
            "Fields handed off",
            "Sensitive/safety fields detected",
            "Final state proving Submit was not clicked",
            "Result: verified / failed / blocked / experimental",
        ]
        for field in required_evidence_fields:
            assert field in content, f"Codex Chrome evidence template missing: {field}"

        skill_content = (ROOT / "skills" / "apply" / "SKILL.md").read_text(encoding="utf-8")
        assert "docs/apply-codex-chrome-verification.md" in skill_content
        assert "non-submitted evidence record" in skill_content

    def test_apply_codex_chrome_live_observations_remain_experimental(self):
        """Live page observations must not be inflated into stable automation claims."""
        content = (ROOT / "docs" / "apply-codex-chrome-verification.md").read_text(encoding="utf-8")
        normalized = normalize_whitespace(content)

        for heading in [
            "### Greenhouse direct - 2026-06-18",
            "### Greenhouse embed direct top-level URL - 2026-06-18",
            "### Greenhouse EU domain - 2026-06-18",
            "### Lever - 2026-06-18",
            "### Workable - 2026-06-18",
            "### Unknown or unsupported ATS - 2026-06-18",
        ]:
            assert heading in content, f"missing live observation record: {heading}"

        for term in [
            "partial non-submitting observations, not evidence of successful end-to-end ATS automation",
            "no applicant data was entered",
            "no PDF was uploaded",
            "Submit was not clicked",
            "live ATS upload would transmit a file to the employer ATS",
            "Result: experimental partial observation, not verified automation",
            "Result: unsupported for automation",
        ]:
            assert term in normalized, f"missing experimental evidence boundary: {term}"

        evidence_records = content.split("## Evidence Records", maxsplit=1)[1]
        assert "- Result: verified" not in evidence_records
        assert "Codex Chrome status | Supported" not in content

    def test_source_profile_recovery_points_to_setup_profile(self):
        """/source should not direct missing-profile recovery to /new-role."""
        content = (ROOT / "skills" / "source" / "SKILL.md").read_text(encoding="utf-8")
        recovery_start = content.index("### Option C")
        recovery_end = content.index("---", recovery_start)
        recovery = content[recovery_start:recovery_end]

        assert "/setup-profile" in recovery
        assert "/new-role" not in recovery

    def test_source_methodology_links_skill_and_defines_evidence_model(self):
        """/source should separate verified facts from recruiter judgment."""
        skill_content = (ROOT / "skills" / "source" / "SKILL.md").read_text(encoding="utf-8")
        methodology = ROOT / "docs" / "source-methodology.md"

        assert methodology.exists(), "Missing /source methodology doc"
        assert "docs/source-methodology.md" in skill_content

        content = normalize_whitespace(methodology.read_text(encoding="utf-8"))
        for term in [
            "lead-generation plus official-post verification workflow",
            "does not use private data-source access",
            "cannot guarantee exhaustive market coverage",
            "Verified facts",
            "Inferred recruiter judgment",
            "A source list can verify only that the list made a company-level claim",
            "does not verify that a current job post offers sponsorship",
        ]:
            assert term in content, f"/source methodology missing evidence term: {term}"

    def test_source_methodology_defines_primary_and_fallback_sources(self):
        """/source should define source hierarchy without implying private access."""
        content = normalize_whitespace(
            (ROOT / "docs" / "source-methodology.md").read_text(encoding="utf-8")
        )

        for term in [
            "Primary sources",
            "Company careers pages on official company domains",
            "Company-controlled ATS postings",
            "User-uploaded source lists",
            "Fallback discovery sources",
            "Public web search results",
            "Public LinkedIn job pages or company posts",
            "Public job aggregators",
            "Unverified leads",
            "private recruiter databases",
            "paid job feeds",
            "internal ATS data",
        ]:
            assert term in content, f"/source methodology missing source term: {term}"

    def test_source_methodology_defines_verification_and_aggregator_treatment(self):
        """/source should require official-post verification and demote aggregators."""
        content = normalize_whitespace(
            (ROOT / "docs" / "source-methodology.md").read_text(encoding="utf-8")
        )

        for criterion in [
            "The company identity is clear",
            "The role title and location or work setup are visible",
            "The post appears current and accepting applications",
            "The application URL is reachable",
            "The source URL is cited",
            "stale search snippet",
            "uncited memory, model knowledge, or unsupported inference",
        ]:
            assert criterion in content, f"/source methodology missing verification: {criterion}"

        for term in [
            "A LinkedIn or aggregator page can be used for discovery",
            "mark the source as `public platform`",
            "no stronger official post was reachable",
            "Aggregator text does not verify sponsorship, relocation, compensation, or seniority",
            "cite the company-hosted post as the verification source",
        ]:
            assert term in content, f"/source methodology missing aggregator rule: {term}"

    def test_source_methodology_defines_score_weights_and_caps(self):
        """/source fit scores should have explicit components and conservative caps."""
        content = (ROOT / "docs" / "source-methodology.md").read_text(encoding="utf-8")
        normalized = normalize_whitespace(content)

        expected_weights = [
            ("Technical match", "35"),
            ("Seniority match", "15"),
            ("Domain and product relevance", "10"),
            ("Location and work authorization practicality", "15"),
            ("Sponsorship or relocation signal", "10"),
            ("Compensation potential", "5"),
            ("Evidence quality and freshness", "10"),
        ]
        for factor, weight in expected_weights:
            assert f"| {factor} | {weight} |" in content

        for term in [
            "The fit score is a heuristic recruiter judgment",
            "Do not score an unverified lead",
            "Cap `Evidence quality and freshness` at 6",
            "Cap `Sponsorship or relocation signal` at 5",
            "Score `Sponsorship or relocation signal` as 0",
        ]:
            assert term in normalized, f"/source methodology missing scoring rule: {term}"

    def test_source_methodology_defines_sponsorship_confidence_levels(self):
        """/source should label sponsorship evidence instead of upgrading inference."""
        content = normalize_whitespace(
            (ROOT / "docs" / "source-methodology.md").read_text(encoding="utf-8")
        )

        for label in [
            "Confirmed in job post",
            "Sponsorship and Relocation Confidence",
            "Source list claim only, not confirmed in job post",
            "Company-level signal only",
            "Not mentioned",
            "Likely blocker",
            "Never upgrade sponsorship or relocation from inferred to confirmed",
        ]:
            assert label in content, f"/source methodology missing confidence label: {label}"

        assert "Source-list evidence:" in content
        assert "The post does not mention visa sponsorship or relocation" in content

    def test_source_methodology_defines_fewer_than_20_behavior(self):
        """/source should return fewer verified matches instead of padding the list."""
        content = normalize_whitespace(
            (ROOT / "docs" / "source-methodology.md").read_text(encoding="utf-8")
        )

        for term in [
            "Fewer Than 20 Verified Matches",
            "do not pad the list with unverified leads",
            "How many verified roles were found",
            "Which searches, markets, or source-list companies were checked",
            "Which pages were blocked, stale, or inconclusive",
            "Which fallback expansions were used",
            "Watched companies",
            "Unverified leads",
        ]:
            assert term in content, f"/source methodology missing fewer-than-20 rule: {term}"

    def test_source_public_copy_avoids_overclaiming_coverage(self):
        """/source README/docs copy should describe lead verification, not exhaustive search."""
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        docs_index = (ROOT / "docs" / "index.html").read_text(encoding="utf-8")
        combined = readme + "\n" + docs_index

        for term in [
            "Discover leads from available public/search sources",
            "verify open roles on company-controlled pages",
            "verified role leads",
            "Official posts are cited when roles are counted as verified",
            "source-list claims kept separate from job-post facts",
        ]:
            assert term in combined, f"/source public copy missing cautious wording: {term}"

        forbidden = [
            "private recruiter database",
            "Crawls company career pages directly",
            "relocation requirements",
            "Market Intelligence",
        ]
        for term in forbidden:
            assert term not in combined, f"/source public copy overclaims with: {term}"

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
            "Security / Dependency Vulnerability Scan",
            "Security / Secret Detection",
            "Security / Filesystem Security Scan",
            "Security / Generate SBOM",
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
        pytest.importorskip("pypdf")

        roles_dir = tmp_path / "roles"
        roles_dir.mkdir()
        shutil.copy(
            ROOT / "tests/fixtures/non_pii/profile.synthetic.json", tmp_path / "profile.json"
        )
        shutil.copy(
            ROOT / "tests/fixtures/non_pii/roles/synthetic_quality_gate_pass.json",
            roles_dir / "synthetic_quality_gate_pass.json",
        )

        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "src" / "generate_application.py"),
                "--role",
                "synthetic_quality_gate_pass",
            ],
            cwd=tmp_path,
            capture_output=True,
            text=True,
            check=False,
        )

        assert result.returncode == 0, result.stderr or result.stdout
        assert "Quality gates:" in result.stdout
        assert "FAIL" not in result.stdout
        generated_dir = tmp_path / "generated"
        assert list(generated_dir.glob("*_CV.pdf"))
        assert list(generated_dir.glob("*_CoverLetter.pdf"))

    def test_generate_application_dry_run_prints_redacted_apply_plan(self, tmp_path):
        roles_dir = tmp_path / "roles"
        roles_dir.mkdir()
        shutil.copy(
            ROOT / "tests/fixtures/non_pii/profile.synthetic.json", tmp_path / "profile.json"
        )
        role = json.loads(
            (ROOT / "tests/fixtures/non_pii/roles/synthetic_quality_gate_pass.json").read_text(
                encoding="utf-8"
            )
        )
        role["output_prefix"] = "Alex_Example_Private_Output"
        (roles_dir / "synthetic_quality_gate_pass.json").write_text(
            json.dumps(role), encoding="utf-8"
        )

        for script_path in [
            ROOT / "src" / "generate_application.py",
            ROOT / "plugins" / "career-agent" / "src" / "generate_application.py",
        ]:
            result = subprocess.run(
                [
                    sys.executable,
                    str(script_path),
                    "--role",
                    "synthetic_quality_gate_pass",
                    "--dry-run",
                ],
                cwd=tmp_path,
                capture_output=True,
                text=True,
                check=False,
            )

            assert result.returncode == 0, result.stderr or result.stdout
            assert "Apply dry run:" in result.stdout
            assert "Package version:" in result.stdout
            assert "Package version: unknown" not in result.stdout
            assert "Apply skill path:" in result.stdout
            assert "Planned safe fields (values redacted):" in result.stdout
            assert "Planned upload strategy:" in result.stdout
            assert (
                "Do not send one large inline base64 string through Runtime.evaluate."
                in result.stdout
            )
            assert "Handoff fields / stop boundaries:" in result.stdout
            assert (
                "Dry run only: no PDFs generated, browser opened, files uploaded, or tracker updated."
                in result.stdout
            )
            for leaked in [
                "Synthetic role used only to validate generated PDF quality gates.",
                "Alex_Example_Private_Output",
                "alex.example@example.com",
                "+15550100000",
                str(tmp_path),
                str(script_path),
            ]:
                assert leaked not in result.stdout

        assert not (tmp_path / "generated").exists()


class TestPdfQualityGates:
    @staticmethod
    def _load_fixture(name: str) -> dict[str, Any]:
        path = ROOT / name
        return json.loads(path.read_text(encoding="utf-8"))

    def _generate_fixture_packet(
        self, tmp_path: Path, role_fixture: str
    ) -> tuple[dict[str, Any], dict[str, Any], Path, Path]:
        pytest.importorskip("reportlab")
        pytest.importorskip("pypdf")
        sys.path.insert(0, str(ROOT / "src"))
        try:
            from cl_builder import build_cover_letter
            from cv_builder import build_cv
            from generate_application import prepare_generation_config

            profile = self._load_fixture("tests/fixtures/non_pii/profile.synthetic.json")
            role = self._load_fixture(f"tests/fixtures/non_pii/roles/{role_fixture}")
            config = prepare_generation_config(profile, role)
            cv_path = tmp_path / f"{config['output_prefix']}_CV.pdf"
            cl_path = tmp_path / f"{config['output_prefix']}_CoverLetter.pdf"

            build_cv(profile, config, str(cv_path))
            build_cover_letter(profile, config, str(cl_path))

            return profile, config, cv_path, cl_path
        finally:
            sys.path.pop(0)

    def test_quality_gates_pass_on_synthetic_fixture(self, tmp_path):
        pypdf = pytest.importorskip("pypdf")
        sys.path.insert(0, str(ROOT / "src"))
        try:
            from quality_gates import OK, run_quality_gates

            profile, config, cv_path, cl_path = self._generate_fixture_packet(
                tmp_path, "synthetic_quality_gate_pass.json"
            )
            report = run_quality_gates(profile, config, cv_path, cl_path)
            cv_text = "\n".join(
                page.extract_text() or "" for page in pypdf.PdfReader(str(cv_path)).pages
            )
        finally:
            sys.path.pop(0)

        assert not report.has_failures
        assert any(
            result.name == "cv_text_extractable" and result.status == OK
            for result in report.results
        )
        assert "+15550100000" in cv_text.replace(" ", "")
        assert "Designed Python APIs for fictional partner onboarding" in cv_text
        assert "Implemented fictional model-evaluation jobs" not in cv_text
        assert cv_text.index("Developer Productivity") < cv_text.index("Platform Reliability")

    def test_quality_gates_fail_on_placeholder_text(self, tmp_path):
        sys.path.insert(0, str(ROOT / "src"))
        try:
            from quality_gates import FAIL, run_quality_gates

            profile, config, cv_path, cl_path = self._generate_fixture_packet(
                tmp_path, "synthetic_quality_gate_fail.json"
            )
            report = run_quality_gates(profile, config, cv_path, cl_path)
        finally:
            sys.path.pop(0)

        assert report.has_failures
        assert any(
            result.name == "no_placeholder_text" and result.status == FAIL
            for result in report.results
        )

    def test_quality_gates_warn_on_duplicate_low_evidence_bullets(self, tmp_path):
        sys.path.insert(0, str(ROOT / "src"))
        try:
            from quality_gates import WARN, run_quality_gates

            profile, config, cv_path, cl_path = self._generate_fixture_packet(
                tmp_path, "synthetic_quality_gate_warn.json"
            )
            report = run_quality_gates(profile, config, cv_path, cl_path)
        finally:
            sys.path.pop(0)

        assert not report.has_failures
        warnings = {result.name for result in report.results if result.status == WARN}
        assert "bullet_repetition" in warnings
        assert "impact_evidence_density" in warnings

    def test_relevant_experience_prose_does_not_trigger_placeholder(self):
        sys.path.insert(0, str(ROOT / "src"))
        try:
            from quality_gates import _contains_placeholder
        finally:
            sys.path.pop(0)

        natural_prose = (
            "Brought relevant experience from fintech roles to architect the payment layer."
        )
        assert _contains_placeholder(natural_prose) == []

        section_header = "Additional Relevant Experience"
        assert _contains_placeholder(section_header) == []

    def test_template_boilerplate_still_triggers_placeholder(self):
        sys.path.insert(0, str(ROOT / "src"))
        try:
            from quality_gates import _contains_placeholder
        finally:
            sys.path.pop(0)

        # Pin the specific patterns each line is expected to trip so that a
        # future drop of one pattern doesn't degrade coverage silently while
        # this test stays green via incidental matches from broader patterns.
        template_line = "TODO: Paragraph 3: fit with the JD requirements / relevant experience..."
        template_hits = set(_contains_placeholder(template_line))
        assert r"\bTODO\b" in template_hits
        assert r"paragraph\s+\d+" in template_hits
        assert r"fit with this specific JD" not in template_hits  # sanity: substring only

        hook_line = "specific hook to the company and role..."
        hook_hits = set(_contains_placeholder(hook_line))
        assert r"specific hook" in hook_hits

        jd_line = "and how this maps to the fit with this specific JD requirements."
        assert r"fit with this specific JD" in set(_contains_placeholder(jd_line))


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
        assert "pypdf" in content, "Missing pypdf dependency"

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

    def test_codex_setup_docs_separate_npx_from_plugin_install(self):
        """Docs should present Codex install commands without making npx the installer."""
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        docs = (ROOT / "docs" / "index.html").read_text(encoding="utf-8")
        docs_text = docs.replace('<span class="text-safety-indigo">codex</span> ', "codex ")

        assert "### Codex setup" in readme
        assert "It does not install the Codex plugin." in readme
        assert "codex plugin marketplace add nextwebb/career-agent" in readme
        assert "codex plugin add career-agent@career-agent" in readme
        assert "Codex setup" in docs
        assert "does not install the Codex plugin" in docs
        assert "codex plugin marketplace add nextwebb/career-agent" in docs_text
        assert "codex plugin add career-agent@career-agent" in docs_text


if __name__ == "__main__":
    import pytest

    sys.exit(pytest.main([__file__, "-v"]))
