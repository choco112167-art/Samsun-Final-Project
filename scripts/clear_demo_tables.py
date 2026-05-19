"""
Clear only Samsun News DEMO rows from Supabase.

This script does not delete production articles. It requires --confirm-delete
and only targets articles where source == "DEMO", plus related fact_checks.

Usage:
    python scripts/clear_demo_tables.py --dry-run
    python scripts/clear_demo_tables.py --confirm-delete
"""

from __future__ import annotations

import argparse

from article_pipeline_common import configure_stdio, get_supabase_client


def demo_hashes(sb) -> list[str]:
    result = sb.table("articles").select("url_hash,title_ko").eq("source", "DEMO").execute()
    rows = result.data or []
    for row in rows:
        print(f"[demo] {row.get('url_hash')} {row.get('title_ko')}")
    return [row["url_hash"] for row in rows if row.get("url_hash")]


def main() -> int:
    configure_stdio()
    parser = argparse.ArgumentParser()
    parser.add_argument("--confirm-delete", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    sb = get_supabase_client()
    hashes = demo_hashes(sb)
    print(f"[clear-demo] demo article rows found: {len(hashes)}")

    if args.dry_run or not args.confirm_delete:
        print("[clear-demo] preview only. Add --confirm-delete to delete source=DEMO rows.")
        return 0

    if hashes:
        try:
            sb.table("fact_checks").delete().in_("article_url_hash", hashes).execute()
            print("[clear-demo] related fact_checks deleted")
        except Exception as exc:
            print(f"[clear-demo] fact_checks delete skipped: {exc}")
    sb.table("articles").delete().eq("source", "DEMO").execute()
    print("[clear-demo] source=DEMO articles deleted")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
