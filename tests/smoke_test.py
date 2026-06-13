#!/usr/bin/env python3
"""
smoke_test.py — Smoke tests for career-agent

Validates project structure, configuration files, and basic functionality
without requiring external dependencies or PII data.

Run: pytest tests/smoke_test.py -v
"""

import json
import py_compile
import sys
from pathlib import Path

# Project root
ROOT = Path(__file__).parent.parent


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
        expected_skills = ["apply", "generate-cv", "new-role", "source", "track"]

        for skill in expected_skills:
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
        """Verify core modules can be imported."""
        sys.path.insert(0, str(ROOT / "src"))

        try:
            import cl_builder
            import cv_builder
            import generate_application
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

        # Validate required fields
        required_fields = ["name", "version", "description", "skills"]
        for field in required_fields:
            assert field in data, f"Missing required field in plugin.json: {field}"

        assert data["name"] == "career-agent", "Incorrect plugin name"
        assert data["skills"] == "skills", "Skills path should be 'skills'"

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
            assert "repository" in data, "Missing repository field in marketplace.json"


class TestSKILLMarkdown:
    """Validate SKILL.md files have proper structure."""

    def test_skill_md_files_have_titles(self):
        """Check that all SKILL.md files start with a markdown title."""
        skills_dir = ROOT / "skills"
        skill_files = list(skills_dir.glob("*/SKILL.md"))

        assert len(skill_files) >= 5, "Expected at least 5 skill files"

        for skill_file in skill_files:
            with open(skill_file, encoding="utf-8") as f:
                first_line = f.readline().strip()
            assert first_line.startswith("#"), f"{skill_file.name} missing markdown title"

    def test_skill_md_files_have_content(self):
        """Verify SKILL.md files are not empty."""
        skills_dir = ROOT / "skills"
        skill_files = list(skills_dir.glob("*/SKILL.md"))

        for skill_file in skill_files:
            content = skill_file.read_text(encoding="utf-8")
            assert len(content) > 100, f"{skill_file.name} appears to be incomplete"
            assert "##" in content, f"{skill_file.name} missing section headers"


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
            assert any(op in line for op in ["==", ">=", "~=", "<="]), (
                f"Requirement '{line}' should specify version constraint"
            )


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
