#!/usr/bin/env python3
"""Render a JSONL run log as a markdown report.

Usage:
    python3 eval/report.py --run-id demo-2026-07-02
    python3 eval/report.py --run-id demo-2026-07-02 --out eval/runs/demo-2026-07-02.md
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from harness import (  # type: ignore[import-not-found]
    aggregate,
    iter_cases,
    load_cases,
    load_run_log,
    run_log_path,
)


def render_markdown(data: dict, run_id: str) -> str:
    entries = load_run_log(run_id)
    lines: list[str] = []
    lines.append(f"# Eval report: `{run_id}`")
    lines.append("")
    lines.append(f"Log: `{run_log_path(run_id)}`")
    lines.append(f"Total entries: {len(entries)}")
    lines.append("")
    if not entries:
        lines.append("_No entries recorded._")
        return "\n".join(lines) + "\n"

    agg = aggregate(entries)

    lines.append("## Results")
    lines.append("")
    lines.append("| ID | Tier | Name | Runs | Pass % | Threshold | Verdict |")
    lines.append("|----|------|------|-----:|-------:|----------:|---------|")
    for tier, case in iter_cases(data):
        cid = case["id"]
        if cid not in agg:
            continue
        a = agg[cid]
        meets = a["pass_pct"] >= case["pass_threshold_pct"]
        verdict = "PASS" if meets else "FAIL"
        lines.append(
            f"| {cid} | {tier} | {case['name']} | {a['total']} | "
            f"{a['pass_pct']:.1f}% | {case['pass_threshold_pct']}% | {verdict} |"
        )

    lines.append("")
    lines.append("## Expected verdicts (from cases.json)")
    lines.append("")
    lines.append("| ID | Expected | Notes |")
    lines.append("|----|----------|-------|")
    for _, case in iter_cases(data):
        cid = case["id"]
        if cid not in agg:
            continue
        note = case.get("notes", "").replace("|", "\\|").replace("\n", " ")
        lines.append(f"| {cid} | {case['expected_verdict']} | {note} |")

    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Render a run log as a markdown report.")
    p.add_argument("--run-id", required=True, help="Run identifier to report on.")
    p.add_argument("--out", help="Write to this file instead of stdout.")
    args = p.parse_args(argv)

    data = load_cases()
    md = render_markdown(data, args.run_id)
    if args.out:
        Path(args.out).write_text(md)
        print(f"wrote {args.out}")
    else:
        sys.stdout.write(md)
    return 0


if __name__ == "__main__":
    sys.exit(main())
