#!/usr/bin/env node
"use strict";

const { spawnSync } = require("child_process");

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

const required = [
  ".claude-plugin/plugin.json",
  ".codex-plugin/plugin.json",
  "AGENTS.md",
  "LICENSE",
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
  "src/tracker.py",
];

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

console.log("npm package contents check passed.");
