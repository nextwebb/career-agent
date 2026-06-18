#!/usr/bin/env node
/**
 * doctor.js — career-agent health check
 *
 * Run via: npx @nextwebb/career-agent doctor
 *      or: npm run doctor
 *
 * Checks:
 *   - Python 3.10+ available
 *   - reportlab installed
 *   - Claude Code CLI status
 *   - Codex CLI status
 *   - profile.json exists in cwd
 *   - Browser automation requirements (guidance only)
 */

"use strict";

const { spawnSync } = require("child_process");
const fs = require("fs");
const path = require("path");

const GREEN = "\x1b[32m";
const RED = "\x1b[31m";
const YELLOW = "\x1b[33m";
const DIM = "\x1b[2m";
const BOLD = "\x1b[1m";
const RESET = "\x1b[0m";

function run(cmd, args, opts = {}) {
  return spawnSync(cmd, args, { encoding: "utf8", shell: false, ...opts });
}

const PASS = `${GREEN}✓ PASS${RESET}`;
const FAIL = `${RED}✗ FAIL${RESET}`;
const WARN = `${YELLOW}⚠ WARN${RESET}`;

const results = [];

function check(label, status, detail = "") {
  const icon = status === "pass" ? PASS : status === "warn" ? WARN : FAIL;
  results.push({ label, status, detail });
  const detailStr = detail ? `  ${DIM}${detail}${RESET}` : "";
  console.log(`  ${icon}  ${label}${detailStr}`);
}

function commandVersion(command) {
  const result = run(command, ["--version"]);
  if (result.status !== 0) {
    return null;
  }
  return (result.stdout || result.stderr || "").trim() || "available";
}

function findPython() {
  for (const candidate of ["python3", "python3.12", "python3.11", "python3.10", "python"]) {
    const result = run(candidate, ["--version"]);
    if (result.status !== 0) {
      continue;
    }

    const versionLine = (result.stdout || result.stderr || "").trim();
    const match = versionLine.match(/Python (\d+)\.(\d+)/);
    const major = match ? parseInt(match[1], 10) : 0;
    const minor = match ? parseInt(match[2], 10) : 0;
    if (major > 3 || (major === 3 && minor >= 10)) {
      return { bin: candidate, version: versionLine };
    }
  }

  return null;
}

console.log(`\n${BOLD}career-agent health check${RESET}\n`);
console.log("─".repeat(55));

const python = findPython();
if (python) {
  check("Python 3.10+", "pass", python.version);
} else {
  check("Python 3.10+", "fail", "Not found — install from https://python.org/downloads");
}

if (python) {
  const rlCheck = run(python.bin, ["-c", "import reportlab; print(reportlab.Version)"]);
  if (rlCheck.status === 0) {
    check("reportlab", "pass", `version ${(rlCheck.stdout || "").trim()}`);
  } else {
    check("reportlab", "fail", `Not installed — run: ${python.bin} -m pip install reportlab`);
  }
} else {
  check("reportlab", "fail", "Skipped (Python 3.10+ not found)");
}

const claudeVersion = commandVersion("claude");
const codexVersion = commandVersion("codex");

if (claudeVersion) {
  check("Claude Code CLI", "pass", claudeVersion);
} else {
  check("Claude Code CLI", "warn", "Not found — required only for Claude Code plugin usage");
}

if (codexVersion) {
  check("Codex CLI", "pass", codexVersion);
} else {
  check("Codex CLI", "warn", "Not found — required only for Codex plugin usage");
}

if (!claudeVersion && !codexVersion) {
  check("Agent host", "fail", "Install Claude Code or Codex before using career-agent skills");
}

const profilePath = path.join(process.cwd(), "profile.json");
if (fs.existsSync(profilePath)) {
  try {
    const data = JSON.parse(fs.readFileSync(profilePath, "utf8"));
    const name = data.name || (data.contact && data.contact.name) || "(name not set)";
    check("profile.json", "pass", `Found — ${name}`);
  } catch {
    check("profile.json", "warn", "Exists but is not valid JSON");
  }
} else {
  check("profile.json", "fail", `Not found in ${process.cwd()} — run: npx @nextwebb/career-agent`);
}

check(
  "Claude browser automation",
  "warn",
  "For /apply in Claude Code, connect the Claude in Chrome extension before ATS form filling"
);

check(
  "Codex browser automation",
  "warn",
  "Use Browser for public pages and Chrome for signed-in state; Codex /apply remains experimental until issue #65"
);

console.log("─".repeat(55));

const failed = results.filter((r) => r.status === "fail").length;
const warned = results.filter((r) => r.status === "warn").length;

if (failed === 0) {
  console.log(
    `\n${GREEN}${BOLD}All required checks passed.${RESET}${warned > 0 ? ` (${warned} warning${warned > 1 ? "s" : ""})` : ""}`
  );
  console.log(`${DIM}Next: run /setup-profile in Claude Code or invoke $setup-profile in Codex.${RESET}\n`);
} else {
  console.log(
    `\n${RED}${BOLD}${failed} check${failed > 1 ? "s" : ""} failed.${RESET} Fix the issues above then re-run:\n`
  );
  console.log(`  ${DIM}npx @nextwebb/career-agent doctor${RESET}\n`);
  process.exit(1);
}
