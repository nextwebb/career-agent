#!/usr/bin/env node
"use strict";

const fs = require("fs");
const path = require("path");

const root = path.resolve(__dirname, "..");
const pluginRoot = path.join(root, "plugins", "career-agent");
const checkOnly = process.argv.includes("--check");

const copiedPaths = [
  ".codex-plugin",
  "AGENTS.md",
  "LICENSE",
  "README.md",
  "docs/apply-codex-chrome-verification.md",
  "docs/source-methodology.md",
  "profile.example.json",
  "requirements.txt",
  "roles.example",
  "skills",
  "src",
];

function normalize(filePath) {
  return filePath.split(path.sep).join("/");
}

function walkFiles(baseDir) {
  if (!fs.existsSync(baseDir)) {
    return [];
  }

  const entries = fs.readdirSync(baseDir, { withFileTypes: true });
  return entries.flatMap((entry) => {
    const entryPath = path.join(baseDir, entry.name);
    if (entry.name === "__pycache__" || entry.name === ".DS_Store") {
      return [];
    }
    if (entry.isDirectory()) {
      return walkFiles(entryPath);
    }
    if (entry.isFile() && !entry.name.endsWith(".pyc")) {
      return [entryPath];
    }
    return [];
  });
}

function expectedFiles() {
  return copiedPaths.flatMap((relativePath) => {
    const sourcePath = path.join(root, relativePath);
    if (!fs.existsSync(sourcePath)) {
      throw new Error(`Missing canonical marketplace source path: ${relativePath}`);
    }
    if (fs.statSync(sourcePath).isDirectory()) {
      return walkFiles(sourcePath).map((file) => normalize(path.relative(root, file)));
    }
    return [relativePath];
  });
}

function copyPath(relativePath) {
  const sourcePath = path.join(root, relativePath);
  const targetPath = path.join(pluginRoot, relativePath);
  fs.mkdirSync(path.dirname(targetPath), { recursive: true });
  fs.cpSync(sourcePath, targetPath, { recursive: true });
}

function sync() {
  fs.rmSync(pluginRoot, { recursive: true, force: true });
  for (const relativePath of copiedPaths) {
    copyPath(relativePath);
  }
}

function check() {
  const expected = expectedFiles().sort();
  const actual = walkFiles(pluginRoot)
    .map((file) => normalize(path.relative(pluginRoot, file)))
    .sort();

  const missing = expected.filter((file) => !actual.includes(file));
  const extra = actual.filter((file) => !expected.includes(file));
  const changed = expected.filter((file) => {
    const sourcePath = path.join(root, file);
    const targetPath = path.join(pluginRoot, file);
    return fs.existsSync(targetPath) && !fs.readFileSync(sourcePath).equals(fs.readFileSync(targetPath));
  });

  const failures = [];
  if (missing.length > 0) {
    failures.push(`missing: ${missing.join(", ")}`);
  }
  if (extra.length > 0) {
    failures.push(`extra: ${extra.join(", ")}`);
  }
  if (changed.length > 0) {
    failures.push(`changed: ${changed.join(", ")}`);
  }

  if (failures.length > 0) {
    console.error("Codex marketplace copy is out of sync.");
    console.error(failures.join("\n"));
    console.error("Run: npm run sync:codex-marketplace");
    process.exit(1);
  }

  console.log("Codex marketplace copy check passed.");
}

if (checkOnly) {
  check();
} else {
  sync();
  check();
}
