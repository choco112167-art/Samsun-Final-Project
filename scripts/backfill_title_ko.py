"""
Backfill missing articles.title_ko values in Supabase.

Safe to rerun: it only selects rows where title_ko is null/empty and updates
those rows by the existing unique `url_hash`.

Usage:
    python scripts/backfill_title_ko.py --limit 100
    python scripts/backfill_title_ko.py --limit 20 --dry-run
"""

from __future__ import annotations

import argparse
import sys
import time

from article_pipeline_common import (
    configure_stdio,
    generate_title_ko,
    get_supabase_client,
    title_model,
)


def _fetch_missing(sb, limit: int) -> list[dict]:
    result = (
        sb.table("articles")
        .select("url_hash,title,title_ko,published_at")
        .or_("title_ko.is.null,title_ko.eq.")
        .order("published_at", desc=True)
        .limit(limit)
        .execute()
    )
    return result.data or []


def backfill(limit: int, dry_run: bool, sleep_sec: float, model: str) -> int:
    sb = get_supabase_client()
    rows = _fetch_missing(sb, limit)
    print(f"[backfill] missing title_ko rows selected: {len(rows)}")

    updated = 0
    for index, row in enumerate(rows, 1):
        title = (row.get("title") or "").strip()
        url_hash = row.get("url_hash")
        if not title or not url_hash:
            continue

        try:
            title_ko = generate_title_ko(title, model=model)
            print(f"[{index}/{len(rows)}] {title[:80]} -> {title_ko[:80]}")
            if not dry_run:
                sb.table("articles").update({"title_ko": title_ko}).eq("url_hash", url_hash).execute()
            updated += 1
            if sleep_sec > 0:
                time.sleep(sleep_sec)
        except Exception as exc:
            print(f"[warn] failed url_hash={url_hash}: {exc}", file=sys.stderr)

    print(f"[backfill] {'would update' if dry_run else 'updated'}: {updated}")
    return updated


def main() -> int:
    configure_stdio()
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--sleep", type=float, default=0.2)
    parser.add_argument("--model", default=title_model())
    args = parser.parse_args()
    backfill(
        limit=max(args.limit, 0),
        dry_run=args.dry_run,
        sleep_sec=max(args.sleep, 0.0),
        model=args.model,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
