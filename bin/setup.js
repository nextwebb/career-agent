#!/usr/bin/env node
/**
 * setup.js — career-agent prerequisites check
 *
 * Run via: npx @nextwebb/career-agent
 *
 * Steps:
 *   1. Detect Python 3.10+
 *   2. Check/install reportlab
 *   3. Check Claude Code CLI
 *   4. Copy profile.example.json → ./profile.json (if missing)
 *   5. Print next steps
 */

"use strict";

const { spawnSync } = require("child_process");
const fs = require("fs");
const path = require("path");

// ANSI colour helpers
const GREEN = "\x1b[32m";
const RED = "\x1b[31m";
const DIM = "\x1b[2m";
const BOLD = "\x1b[1m";
const RESET = "\x1b[0m";

const ok = (msg) => console.log(`${GREEN}✓${RESET} ${msg}`);
const fail = (msg) => console.error(`${RED}✗${RESET} ${msg}`);
const dim = (msg) => console.log(`${DIM}  ${msg}${RESET}`);
const header = (msg) => console.log(`\n${BOLD}${msg}${RESET}`);

let hasErrors = false;

function run(cmd, args, opts = {}) {
  return spawnSync(cmd, args, { encoding: "utf8", shell: false, ...opts });
}

// ─── Step 1: Detect Python 3.10+ ─────────────────────────────────────────────
header("Checking prerequisites…");

let pythonBin = null;
for (const candidate of ["python3", "python3.12", "python3.11", "python3.10", "python"]) {
  const result = run(candidate, ["--version"]);
  if (result.status === 0) {
    const versionLine = (result.stdout || result.stderr || "").trim();
    const match = versionLine.match(/Python (\d+)\.(\d+)/);
    const major = match ? parseInt(match[1], 10) : 0;
    const minor = match ? parseInt(match[2], 10) : 0;
    if (major > 3 || (major === 3 && minor >= 10)) {
      pythonBin = candidate;
      ok(`Python found: ${versionLine}`);
      break;
    }
  }
}

if (!pythonBin) {
  fail("Python 3.10+ not found.");
  dim("Install Python 3.10+ from https://python.org/downloads and re-run this setup.");
  process.exit(1);
}

// ─── Step 2: Check / install reportlab ───────────────────────────────────────
const rlCheck = run(pythonBin, ["-c", "import reportlab"]);
if (rlCheck.status === 0) {
  ok("reportlab is installed");
} else {
  dim("reportlab not found — installing…");
  const rlInstall = run(pythonBin, ["-m", "pip", "install", "reportlab", "--quiet"]);
  if (rlInstall.status === 0) {
    ok("reportlab installed");
  } else {
    fail("Failed to install reportlab.");
    dim(`Run manually: ${pythonBin} -m pip install reportlab`);
    dim("Then re-run: npx @nextwebb/career-agent");
    hasErrors = true;
  }
}

// ─── Step 3: Check Claude Code CLI ───────────────────────────────────────────
const claudeCheck = run("claude", ["--version"]);
if (claudeCheck.status === 0) {
  ok(`Claude Code CLI found: ${(claudeCheck.stdout || "").trim()}`);
} else {
  fail("Claude Code CLI not found.");
  dim("Install it from https://claude.ai/code");
  dim("Then re-run: npx @nextwebb/career-agent");
  process.exit(1);
}

if (hasErrors) {
  console.error(`\n${RED}Setup incomplete — fix the errors above and re-run.${RESET}`);
  process.exit(1);
}

// ─── Step 4: Copy profile.example.json ───────────────────────────────────────
header("Setting up profile…");

const profileDest = path.join(process.cwd(), "profile.json");
const profileSrc = path.join(__dirname, "..", "profile.example.json");

if (fs.existsSync(profileDest)) {
  ok("profile.json already exists — skipping copy");
} else if (fs.existsSync(profileSrc)) {
  fs.copyFileSync(profileSrc, profileDest);
  ok("profile.json created from profile.example.json");
} else {
  dim("profile.example.json not found in package — create profile.json manually.");
}

// ─── Step 5: Next steps ──────────────────────────────────────────────────────
console.log("");
if (hasErrors) {
  console.log(`${RED}Setup completed with errors. Fix the issues above before proceeding.${RESET}`);
} else {
  console.log(`${GREEN}${BOLD}Prerequisites met.${RESET}`);
}
console.log(`
${BOLD}Next steps:${RESET}

  1. Register and install the plugin:
     ${DIM}claude plugin marketplace add nextwebb/career-agent${RESET}
     ${DIM}claude plugin install career-agent${RESET}

  2. Bootstrap your profile from your CV or LinkedIn PDF:
     ${DIM}/setup-profile${RESET}

  3. Find matching roles:
     ${DIM}/source Germany backend${RESET}

  4. Create a role config:
     ${DIM}/new-role https://jobs.example.com/senior-engineer-123${RESET}

  5. Generate your CV:
     ${DIM}/generate-cv <role_id>${RESET}

  6. Fill the ATS form:
     ${DIM}/apply <role_id>${RESET}

${DIM}Docs & issues: https://github.com/nextwebb/career-agent${RESET}
`);
