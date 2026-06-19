#!/usr/bin/env node
"use strict";

const { spawnSync } = require("child_process");
const fs = require("fs");
const path = require("path");

const root = path.resolve(__dirname, "..");
const packageJson = JSON.parse(fs.readFileSync(path.join(root, "package.json"), "utf8"));
const packageName = packageJson.name;

function read(relativePath) {
  return fs.readFileSync(path.join(root, relativePath), "utf8");
}

function fail(message) {
  console.error(message);
  process.exit(1);
}

function assertIncludes(content, needle, label) {
  if (!content.includes(needle)) {
    fail(`${label} must include: ${needle}`);
  }
}

function stripHtml(content) {
  return content
    .replace(/<[^>]+>/g, "")
    .replace(/\s+/g, " ")
    .trim();
}

function parseRequirements() {
  return read("requirements.txt")
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter((line) => line && !line.startsWith("#"))
    .map((line) => line.split(/[<>=~!]/, 1)[0].trim().toLowerCase());
}

function readPackPaths() {
  const result = spawnSync("npm", ["pack", "--dry-run", "--json"], {
    cwd: root,
    encoding: "utf8",
    shell: false,
  });

  if (result.status !== 0) {
    process.stderr.write(result.stderr || result.stdout);
    process.exit(result.status || 1);
  }

  try {
    return new Set(JSON.parse(result.stdout)[0].files.map((file) => file.path));
  } catch (error) {
    console.error("Unable to parse npm pack --dry-run --json output.");
    console.error(error.message);
    process.exit(1);
  }
}

const readme = read("README.md");
const docsIndex = read("docs/index.html");
const docsIndexText = stripHtml(docsIndex);
const docsReadme = read("docs/README.md");
const publicDocs = `${readme}\n${docsIndex}\n${docsReadme}`;

assertIncludes(readme, `npx ${packageName}`, "README install docs");
assertIncludes(docsIndexText, `npx ${packageName}`, "GitHub Pages install docs");

assertIncludes(readme, "Public docs describe npm `latest`", "README");
assertIncludes(docsIndex, "Latest docs for npm", "GitHub Pages docs");
assertIncludes(docsReadme, "latest docs", "docs/README.md");

const dependencies = parseRequirements();
for (const dependency of dependencies) {
  assertIncludes(readme.toLowerCase(), dependency, "README dependency docs");
  assertIncludes(docsIndex.toLowerCase(), dependency, "GitHub Pages dependency docs");
}

if (publicDocs.includes("requirements.txt")) {
  const packPaths = readPackPaths();
  if (!packPaths.has("requirements.txt")) {
    fail("Docs reference requirements.txt, but npm pack does not include it.");
  }
}

if (docsIndex.includes("pip install reportlab")) {
  fail("GitHub Pages docs must point at requirements.txt or mention every runtime PDF dependency.");
}

console.log("docs consistency check passed.");
