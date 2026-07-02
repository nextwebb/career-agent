#!/usr/bin/env python3
"""Eval harness for the 3-tier automation matrix.

Manages the case registry, records run results to JSONL, and reports pass/fail
against per-case thresholds. Does NOT drive a browser - that is the caller's
job (e.g. claude-in-chrome, playwright). This harness only handles:

  1. Loading cases.json.
  2. Listing / filtering cases by tier or id.
  3. Recording an outcome for a single run (pass/fail + optional notes).
  4. Aggregating a JSONL run log into pass-rate per case.
  5. Comparing observed pass rate to the case's pass_threshold_pct.

Usage:
    python3 eval/harness.py --list
    python3 eval/harness.py --tier tier1_login --dry-run
    python3 eval/harness.py --record L1 --outcome pass --run-id demo-2026-07-02
    python3 eval/harness.py --summary --run-id demo-2026-07-02
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

EVAL_DIR = Path(__file__).resolve().parent
CASES_PATH = EVAL_DIR / "cases.json"
RUNS_DIR = EVAL_DIR / "runs"
TIERS = ("tier1_login", "tier2_captcha", "tier3_forms")


def load_cases() -> dict:
    with CASES_PATH.open() as f:
        return json.load(f)


def iter_cases(data: dict, tier: str | None = None):
    tiers = [tier] if tier else list(TIERS)
    for t in tiers:
        for case in data.get(t, []):
            yield t, case


def find_case(data: dict, case_id: str) -> tuple[str, dict] | None:
    for tier, case in iter_cases(data):
        if case["id"] == case_id:
            return tier, case
    return None


def cmd_list(data: dict, tier: str | None) -> int:
    header = f"{'ID':<5} {'TIER':<16} {'EXPECTED':<24} {'NAME'}"
    print(header)
    print("-" * len(header))
    for t, case in iter_cases(data, tier):
        print(f"{case['id']:<5} {t:<16} {case['expected_verdict']:<24} {case['name']}")
    return 0


def cmd_dry_run(data: dict, tier: str) -> int:
    print(f"Dry run: {tier}")
    for _, case in iter_cases(data, tier):
        print(f"  [{case['id']}] {case['name']}")
        print(f"       url:      {case.get('url', '(none)')}")
        print(
            f"       expected: {case['expected_verdict']} "
            f"(>= {case['pass_threshold_pct']}% over {case['runs']} runs)"
        )
    return 0


def run_log_path(run_id: str) -> Path:
    safe = "".join(c if c.isalnum() or c in "-_." else "_" for c in run_id)
    return RUNS_DIR / f"{safe}.jsonl"


def cmd_record(data: dict, case_id: str, outcome: str, run_id: str, note: str) -> int:
    if outcome not in {"pass", "fail"}:
        print(f"error: --outcome must be 'pass' or 'fail', got {outcome!r}", file=sys.stderr)
        return 2
    found = find_case(data, case_id)
    if not found:
        print(f"error: unknown case id {case_id!r}", file=sys.stderr)
        return 2
    tier, case = found
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "run_id": run_id,
        "case_id": case_id,
        "tier": tier,
        "expected_verdict": case["expected_verdict"],
        "outcome": outcome,
        "note": note,
    }
    path = run_log_path(run_id)
    with path.open("a") as f:
        f.write(json.dumps(entry) + "\n")
    print(f"recorded: {case_id} {outcome} -> {path}")
    return 0


def load_run_log(run_id: str) -> list[dict]:
    path = run_log_path(run_id)
    if not path.exists():
        return []
    entries = []
    with path.open() as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    return entries


def aggregate(entries: list[dict]) -> dict[str, dict]:
    """Group entries by case_id and compute pass rate."""
    by_case: dict[str, dict] = {}
    for e in entries:
        cid = e["case_id"]
        agg = by_case.setdefault(
            cid,
            {"passes": 0, "fails": 0, "tier": e["tier"], "expected_verdict": e["expected_verdict"]},
        )
        if e["outcome"] == "pass":
            agg["passes"] += 1
        else:
            agg["fails"] += 1
    for agg in by_case.values():
        total = agg["passes"] + agg["fails"]
        agg["total"] = total
        agg["pass_pct"] = (agg["passes"] / total * 100.0) if total else 0.0
    return by_case


def verdict_for(case: dict, agg_entry: dict) -> str:
    """PASS only if we have the required N runs AND pass_pct >= threshold.

    Under-sampled cases return INCOMPLETE so an in-flight eval log cannot
    silently satisfy CI by recording one lucky pass.
    """
    if agg_entry["total"] < case["runs"]:
        return "INCOMPLETE"
    if agg_entry["pass_pct"] >= case["pass_threshold_pct"]:
        return "PASS"
    return "FAIL"


def cmd_summary(data: dict, run_id: str) -> int:
    entries = load_run_log(run_id)
    if not entries:
        print(f"no entries found for run_id={run_id!r} at {run_log_path(run_id)}")
        return 1
    agg = aggregate(entries)
    header = f"{'ID':<5} {'TIER':<16} {'RUNS':>7} {'PASS%':>7} {'THRESHOLD':>10} {'VERDICT':<10}"
    print(header)
    print("-" * len(header))
    exit_code = 0
    for tier, case in iter_cases(data):
        cid = case["id"]
        if cid not in agg:
            continue
        a = agg[cid]
        verdict = verdict_for(case, a)
        if verdict != "PASS":
            exit_code = 1
        runs_col = f"{a['total']}/{case['runs']}"
        print(
            f"{cid:<5} {tier:<16} {runs_col:>7} {a['pass_pct']:>6.1f}% "
            f"{case['pass_threshold_pct']:>9}% {verdict:<10}"
        )
    return exit_code


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Eval harness for the 3-tier automation matrix.")
    p.add_argument(
        "--list", action="store_true", help="List all cases (optionally filter by --tier)."
    )
    p.add_argument("--tier", choices=TIERS, help="Restrict to a single tier.")
    p.add_argument(
        "--dry-run", action="store_true", help="Print planned run for --tier without executing."
    )
    p.add_argument("--record", metavar="CASE_ID", help="Record an outcome for a case.")
    p.add_argument("--outcome", choices=("pass", "fail"), help="Outcome for --record.")
    p.add_argument("--run-id", default="default", help="Run identifier (namespaces the JSONL log).")
    p.add_argument("--note", default="", help="Free-text note for --record.")
    p.add_argument("--summary", action="store_true", help="Print pass/fail summary for --run-id.")
    args = p.parse_args(argv)

    data = load_cases()

    if args.list:
        return cmd_list(data, args.tier)
    if args.dry_run:
        if not args.tier:
            print("error: --dry-run requires --tier", file=sys.stderr)
            return 2
        return cmd_dry_run(data, args.tier)
    if args.record:
        if not args.outcome:
            print("error: --record requires --outcome", file=sys.stderr)
            return 2
        return cmd_record(data, args.record, args.outcome, args.run_id, args.note)
    if args.summary:
        return cmd_summary(data, args.run_id)

    p.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
