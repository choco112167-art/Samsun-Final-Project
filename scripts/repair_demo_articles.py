"""
Convenience wrapper for demo-readiness repair commands.

It does not delete data. Without --run, it prints the commands to run.

Usage:
    python scripts/repair_demo_articles.py
    python scripts/repair_demo_articles.py --run --limit 5 --provider openrouter
"""

from __future__ import annotations

import argparse
import subprocess
import sys

from article_pipeline_common import configure_stdio


def run_cmd(cmd: list[str], run: bool) -> int:
    print(" ".join(cmd))
    if not run:
        return 0
    completed = subprocess.run(cmd, check=False)
    return completed.returncode


def main() -> int:
    configure_stdio()
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--provider", choices=("openrouter", "gemini", "local", "mock"), default="openrouter")
    parser.add_argument("--model", default="google/gemini-2.5-flash")
    parser.add_argument("--title-contains", default="")
    args = parser.parse_args()

    py = sys.executable
    title_cmd = [
        py,
        "scripts/backfill_title_ko.py",
        "--limit",
        str(max(args.limit, 0)),
    ]
    if args.title_contains:
        title_cmd.extend(["--title-contains", args.title_contains])

    ai_cmd = [
        py,
        "scripts/backfill_article_ai_outputs.py",
        "--limit",
        str(max(args.limit, 0)),
        "--provider",
        args.provider,
        "--model",
        args.model,
        "--repair-short-translation",
        "--repair-weak-summary",
        "--repair-missing-fact-status",
        "--summary-sentences",
        "3",
    ]
    if args.title_contains:
        ai_cmd.extend(["--title-contains", args.title_contains])
    if args.run:
        ai_cmd.append("--run")

    print(f"[repair-demo] run={args.run}")
    rc = run_cmd(title_cmd, args.run)
    if rc:
        return rc
    return run_cmd(ai_cmd, args.run)


if __name__ == "__main__":
    raise SystemExit(main())
