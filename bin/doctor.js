#!/usr/bin/env node
/**
 * doctor.js — career-agent health check
 *
 * Run via: npx @nextwebb/career-agent doctor
 *      or: npm run doctor
 *
 * Checks:
 *   - Python 3 available
 *   - reportlab installed
 *   - Claude Code CLI available
 *   - profile.json exists in cwd
 *   - Claude in Chrome (guidance only)
 */

"use strict";

const { spawnSync } = require("child_process");
const fs = require("fs");
const path = require("path");

// ANSI colour helpers
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

console.log(`\n${BOLD}career-agent health check${RESET}\n`);
console.log("─".repeat(55));

// ─── Python 3 ────────────────────────────────────────────────────────────────
let pythonBin = null;
let pythonVersion = null;
for (const candidate of ["python3", "python"]) {
  const result = run(candidate, ["--version"]);
  if (result.status === 0) {
    const versionLine = (result.stdout || result.stderr || "").trim();
    const match = versionLine.match(/Python (\d+)\.(\d+)/);
    if (match && parseInt(match[1], 10) >= 3) {
      pythonBin = candidate;
      pythonVersion = versionLine;
      break;
    }
  }
}

if (pythonBin) {
  check("Python 3", "pass", pythonVersion);
} else {
  check("Python 3", "fail", "Not found — install from https://python.org/downloads");
}

// ─── reportlab ───────────────────────────────────────────────────────────────
if (pythonBin) {
  const rlCheck = run(pythonBin, ["-c", "import reportlab; print(reportlab.Version)"]);
  if (rlCheck.status === 0) {
    check("reportlab", "pass", `version ${(rlCheck.stdout || "").trim()}`);
  } else {
    check(
      "reportlab",
      "fail",
      `Not installed — run: ${pythonBin} -m pip install reportlab`
    );
  }
} else {
  check("reportlab", "fail", "Skipped (Python not found)");
}

// ─── Claude Code CLI ─────────────────────────────────────────────────────────
const claudeCheck = run("claude", ["--version"]);
if (claudeCheck.status === 0) {
  check("Claude Code CLI", "pass", (claudeCheck.stdout || "").trim());
} else {
  check("Claude Code CLI", "fail", "Not found — install from https://claude.ai/code");
}

// ─── profile.json ────────────────────────────────────────────────────────────
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
  check(
    "profile.json",
    "fail",
    `Not found in ${process.cwd()} — run: npx @nextwebb/career-agent`
  );
}

// ─── Claude in Chrome (guidance only) ────────────────────────────────────────
check(
  "Claude in Chrome extension",
  "warn",
  "Cannot auto-detect — ensure it is enabled for ATS form filling"
);

// ─── Summary ─────────────────────────────────────────────────────────────────
console.log("─".repeat(55));

const failed = results.filter((r) => r.status === "fail").length;
const warned = results.filter((r) => r.status === "warn").length;

if (failed === 0) {
  console.log(
    `\n${GREEN}${BOLD}All checks passed!${RESET}${warned > 0 ? ` (${warned} warning${warned > 1 ? "s" : ""})` : ""}`
  );
  console.log(`${DIM}Run \`claude /generate-cv <role_id>\` to get started.${RESET}\n`);
} else {
  console.log(
    `\n${RED}${BOLD}${failed} check${failed > 1 ? "s" : ""} failed.${RESET} Fix the issues above then re-run:\n`
  );
  console.log(`  ${DIM}npx @nextwebb/career-agent${RESET}\n`);
  process.exit(1);
}
