#!/usr/bin/env node
"use strict";

const fs = require("fs");
const path = require("path");

const root = path.resolve(__dirname, "..");
const codeownersPath = path.join(root, ".github", "CODEOWNERS");
const content = fs.readFileSync(codeownersPath, "utf8");

const disallowedOwners = ["@copilot", "@chatgpt-codex-connector"];
const found = disallowedOwners.filter((owner) => content.includes(owner));

if (found.length > 0) {
  console.error(
    `CODEOWNERS contains unverified AI owner handle(s): ${found.join(", ")}`
  );
  console.error(
    "Route AI review through a verified integration/workflow instead of CODEOWNERS."
  );
  process.exit(1);
}

if (!content.includes("@nextwebb")) {
  console.error("CODEOWNERS must include the verified repository owner @nextwebb.");
  process.exit(1);
}

console.log("CODEOWNERS review routing check passed.");
