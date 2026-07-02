# Eval harness — 3-tier automation matrix

Scaffolded on 2026-07-02 after a live experiment probing the claim:

> "Logging in with a password, solving a CAPTCHA, or filing a return is fully automatable today."

The live run confirmed the nuance: **L1 (simple login) passed**, **C2 (reCAPTCHA v2)
hard-blocked**. This directory keeps the matrix in the repo so future changes to the
automation stack can be measured against it instead of re-argued.

## What it tests

Three tiers of automation difficulty:

| Tier | ID range | Question |
|------|----------|----------|
| 1. Login | L1–L5 | Can we complete a password login end-to-end? |
| 2. CAPTCHA | C1–C6 | Can we clear a bot-detection challenge without paid solvers? |
| 3. Forms | F1–F5 | Can we fill and submit a non-trivial form (up to and including a tax return)? |

Each case in `cases.json` declares an `expected_verdict`
(`fully_automatable` / `partially_automatable` / `not_automatable`) and a
`pass_threshold_pct` the harness compares real runs against. Verdicts are
intentionally conservative — see `_meta.verdicts` in `cases.json` for definitions.

## Layout

```
eval/
  README.md      this file
  cases.json     source of truth for the case registry
  harness.py    load / list / record / summarise (CLI, no browser)
  report.py     render a JSONL run log as markdown
  runs/         JSONL run logs, one file per --run-id
```

The harness deliberately does **not** drive a browser. Browser automation is the
caller's job (claude-in-chrome, Playwright, etc.). The harness manages the case
registry, records outcomes, and reports pass rates. This keeps `eval/` a
standalone module — it does not import from `src/` and no test in `tests/`
imports from `eval/`.

## How to run

List every case:

```bash
python3 eval/harness.py --list
```

Dry-run a single tier (prints what would be executed):

```bash
python3 eval/harness.py --tier tier1_login --dry-run
```

Record an outcome for a case (call this once per browser run):

```bash
python3 eval/harness.py --record L1 --outcome pass \
  --run-id demo-2026-07-02 --note "single-run smoke, live demo"
```

Summarise a run:

```bash
python3 eval/harness.py --summary --run-id demo-2026-07-02
```

Render the run log as markdown:

```bash
python3 eval/report.py --run-id demo-2026-07-02 --out eval/runs/demo-2026-07-02.md
```

`--summary` exits non-zero if any case falls below its `pass_threshold_pct`, so it
plugs into CI as-is once real runs start being recorded.

## Known state (as of 2026-07-02)

- **L1** — executed live, passed. Baseline for the "logins are automatable" half of the claim.
- **C2** — executed live, hard-blocked by cross-origin iframe. Baseline for the "CAPTCHAs
  are automatable" half being false without ToS-violating solver services.
- All other cases are stubs with `notes` explaining why the expected verdict was chosen.
  They have no recorded runs yet.
