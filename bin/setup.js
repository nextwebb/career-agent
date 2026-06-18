#!/usr/bin/env node
/**
 * setup.js — career-agent prerequisites check
 *
 * Run via: npx @nextwebb/career-agent
 *
 * Steps:
 *   1. Dispatch `career-agent doctor` to the doctor command
 *   2. Detect Python 3.10+
 *   3. Check/install PDF runtime dependencies
 *   4. Detect Claude Code and Codex independently
 *   5. Copy profile.example.json → ./profile.json (if missing)
 *   6. Print next steps
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

const ok = (msg) => console.log(`${GREEN}✓${RESET} ${msg}`);
const warn = (msg) => console.log(`${YELLOW}⚠${RESET} ${msg}`);
const fail = (msg) => console.error(`${RED}✗${RESET} ${msg}`);
const dim = (msg) => console.log(`${DIM}  ${msg}${RESET}`);
const header = (msg) => console.log(`\n${BOLD}${msg}${RESET}`);
const PYTHON_PACKAGES = [
  { importName: "reportlab", installName: "reportlab" },
  { importName: "pypdf", installName: "pypdf" },
];

function run(cmd, args, opts = {}) {
  return spawnSync(cmd, args, { encoding: "utf8", shell: false, ...opts });
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

if (process.argv[2] === "doctor") {
  const doctor = run(process.execPath, [path.join(__dirname, "doctor.js")], {
    stdio: "inherit",
  });
  process.exit(doctor.status || 0);
}

if (process.argv.length > 2) {
  fail(`Unknown command: ${process.argv.slice(2).join(" ")}`);
  dim("Supported commands: career-agent, career-agent doctor");
  process.exit(1);
}

let hasErrors = false;

header("Checking prerequisites…");

const python = findPython();
if (!python) {
  fail("Python 3.10+ not found.");
  dim("Install Python 3.10+ from https://python.org/downloads and re-run this setup.");
  process.exit(1);
}
ok(`Python found: ${python.version}`);

for (const pkg of PYTHON_PACKAGES) {
  const packageCheck = run(python.bin, ["-c", `import ${pkg.importName}`]);
  if (packageCheck.status === 0) {
    ok(`${pkg.installName} is installed`);
  } else {
    dim(`${pkg.installName} not found — installing…`);
    const packageInstall = run(python.bin, [
      "-m",
      "pip",
      "install",
      pkg.installName,
      "--quiet",
    ]);
    if (packageInstall.status === 0) {
      ok(`${pkg.installName} installed`);
    } else {
      fail(`Failed to install ${pkg.installName}.`);
      dim(`Run manually: ${python.bin} -m pip install ${pkg.installName}`);
      dim("Then re-run: npx @nextwebb/career-agent");
      hasErrors = true;
    }
  }
}

const claudeVersion = commandVersion("claude");
const codexVersion = commandVersion("codex");

if (claudeVersion) {
  ok(`Claude Code CLI found: ${claudeVersion}`);
} else {
  warn("Claude Code CLI not found. Claude plugin install commands will not work until it is installed.");
}

if (codexVersion) {
  ok(`Codex CLI found: ${codexVersion}`);
} else {
  warn("Codex CLI not found. Codex plugin install and verification commands require Codex.");
}

if (!claudeVersion && !codexVersion) {
  fail("Neither Claude Code nor Codex CLI was found.");
  dim("Install at least one supported agent host before continuing.");
  hasErrors = true;
}

if (hasErrors) {
  console.error(`\n${RED}Setup incomplete — fix the errors above and re-run.${RESET}`);
  process.exit(1);
}

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

console.log("");
console.log(`${GREEN}${BOLD}Prerequisites met.${RESET}`);
console.log(`
${BOLD}Next steps:${RESET}

  Claude Code:
     ${DIM}claude plugin marketplace add nextwebb/career-agent${RESET}
     ${DIM}claude plugin install career-agent${RESET}

  Codex:
     ${DIM}Install career-agent from a configured Codex marketplace or local plugin source.${RESET}
     ${DIM}This package includes .codex-plugin/plugin.json for Codex plugin discovery.${RESET}

  Then bootstrap your profile:
     ${DIM}/setup-profile       # Claude Code alias${RESET}
     ${DIM}$setup-profile       # Codex skill invocation${RESET}

  Find roles and generate application files:
     ${DIM}/source Germany backend${RESET}
     ${DIM}/new-role https://jobs.example.com/senior-engineer-123${RESET}
     ${DIM}/generate-cv <role_id>${RESET}

  Browser form filling:
     ${DIM}/apply <role_id>     # Claude Code supported flow${RESET}
     ${DIM}$apply <role_id>     # Codex experimental until issue #65 is verified${RESET}

${DIM}Docs & issues: https://github.com/nextwebb/career-agent${RESET}
`);
