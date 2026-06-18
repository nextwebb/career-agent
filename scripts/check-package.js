#!/usr/bin/env node
"use strict";

const { spawnSync } = require("child_process");
const fs = require("fs");
const path = require("path");

const required = [
  ".claude-plugin/plugin.json",
  ".codex-plugin/plugin.json",
  "AGENTS.md",
  "LICENSE",
  "docs/apply-codex-chrome-verification.md",
  "docs/source-methodology.md",
  "plugin.json",
  "profile.example.json",
  "roles.example/example_role.json",
  "skills/apply/SKILL.md",
  "skills/generate-cv/SKILL.md",
  "skills/new-role/SKILL.md",
  "skills/setup-profile/SKILL.md",
  "skills/source/SKILL.md",
  "skills/track/SKILL.md",
  "src/generate_application.py",
  "src/quality_gates.py",
  "src/tracker.py",
];

const publicRepositoryContactRoots = [".github", "docs"];
const contactScanExtensions = new Set([".html", ".json", ".md", ".txt", ".yaml", ".yml"]);
const ignoredContactScanDirectories = new Set([
  ".git",
  ".claude",
  ".mypy_cache",
  ".pytest_cache",
  ".ruff_cache",
  "__pycache__",
  "build",
  "dist",
  "generated",
  "node_modules",
  "roles",
  "sourced",
]);
const ignoredContactScanFiles = new Set([
  ".env",
  "base_profile.pdf",
  "package-lock.json",
  "profile.json",
  "tracker.json",
]);
const allowedPlaceholderEmailDomains = new Set(["example.com", "example.net", "example.org"]);

function normalizePath(file) {
  return file.split(path.sep).join("/");
}

function shouldScanPublicContactFile(file) {
  const normalized = normalizePath(file);
  const parts = normalized.split("/");
  const basename = parts[parts.length - 1];

  if (ignoredContactScanFiles.has(normalized) || ignoredContactScanFiles.has(basename)) {
    return false;
  }

  if (parts.some((part) => ignoredContactScanDirectories.has(part))) {
    return false;
  }

  return contactScanExtensions.has(path.extname(basename).toLowerCase());
}

function collectTextFiles(directory) {
  if (!fs.existsSync(directory)) {
    return [];
  }

  const entries = fs.readdirSync(directory, { withFileTypes: true });
  return entries.flatMap((entry) => {
    const entryPath = path.join(directory, entry.name);
    if (entry.isDirectory()) {
      if (ignoredContactScanDirectories.has(entry.name)) {
        return [];
      }
      return collectTextFiles(entryPath);
    }

    if (shouldScanPublicContactFile(entryPath)) {
      return [normalizePath(entryPath)];
    }

    return [];
  });
}

function collectRootContactFiles() {
  return fs
    .readdirSync(".", { withFileTypes: true })
    .filter((entry) => entry.isFile())
    .map((entry) => entry.name)
    .filter(shouldScanPublicContactFile);
}

const emailPattern = /\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b/gi;

function isAllowedPlaceholderEmail(email) {
  const domain = email.split("@").pop().toLowerCase();
  return allowedPlaceholderEmailDomains.has(domain);
}

function buildPublicContactScanFiles(packPaths) {
  return new Set([
    ...packPaths.filter(shouldScanPublicContactFile),
    ...collectRootContactFiles(),
    ...publicRepositoryContactRoots.flatMap(collectTextFiles),
  ]);
}

function findPublicContactEmails(files) {
  return [...files]
    .filter((file) => fs.existsSync(file) && shouldScanPublicContactFile(file))
    .flatMap((file) => {
      const content = fs.readFileSync(file, "utf8");
      return content.split(/\r?\n/).flatMap((line, index) => {
        emailPattern.lastIndex = 0;
        const emails = [...line.matchAll(emailPattern)]
          .map((match) => match[0])
          .filter((email) => !isAllowedPlaceholderEmail(email));
        return emails.length > 0 ? [`${file}:${index + 1}`] : [];
      });
    });
}

function main() {
  const result = spawnSync("npm", ["pack", "--dry-run", "--json"], {
    encoding: "utf8",
    shell: false,
  });

  if (result.status !== 0) {
    process.stderr.write(result.stderr || result.stdout);
    process.exit(result.status || 1);
  }

  let pack;
  try {
    pack = JSON.parse(result.stdout)[0];
  } catch (error) {
    console.error("Unable to parse npm pack --dry-run --json output.");
    console.error(error.message);
    process.exit(1);
  }

  const paths = new Set(pack.files.map((file) => file.path));

  const missing = required.filter((file) => !paths.has(file));
  if (missing.length > 0) {
    console.error(`npm pack is missing required file(s): ${missing.join(", ")}`);
    process.exit(1);
  }

  const forbidden = [...paths].filter(
    (file) =>
      file.includes("__pycache__") ||
      file.endsWith(".pyc") ||
      file.endsWith(".DS_Store") ||
      file === "profile.json" ||
      file === "tracker.json" ||
      file.startsWith("roles/") ||
      file.startsWith("generated/")
  );
  if (forbidden.length > 0) {
    console.error(`npm pack contains forbidden artifact(s): ${forbidden.join(", ")}`);
    process.exit(1);
  }

  const filesWithEmails = findPublicContactEmails(buildPublicContactScanFiles([...paths]));
  if (filesWithEmails.length > 0) {
    console.error(
      "Public metadata/docs contain direct email contact(s). Use a public URL or " +
        `private GitHub reporting path instead: ${filesWithEmails.join(", ")}`
    );
    process.exit(1);
  }

  console.log("npm package contents check passed.");
}

if (require.main === module) {
  main();
}

module.exports = {
  buildPublicContactScanFiles,
  collectTextFiles,
  findPublicContactEmails,
  isAllowedPlaceholderEmail,
  shouldScanPublicContactFile,
};
