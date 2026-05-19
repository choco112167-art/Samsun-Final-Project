"""
Mark incomplete articles hidden for demo, without deleting production data.

Requires optional columns from backend/sql/add_demo_readiness_fields.sql.
No rows are changed unless --run is provided.

Usage:
    python scripts/mark_incomplete_articles_hidden.py
    python scripts/mark_incomplete_articles_hidden.py --run --limit 50
"""

from __future__ import annotations

import argparse

from article_pipeline_common import configure_stdio, get_supabase_client, supported_article_columns
from demo_quality import is_demo_ready


FIELDS = [
    "url_hash",
    "title",
    "title_ko",
    "source",
    "url",
    "published_at",
    "summary_formal",
    "summary_casual",
    "translation",
    "fact_label",
]
OPTIONAL = ["fact_status", "slang_terms", "neologism_terms", "is_hidden", "demo_visible"]


def main() -> int:
    configure_stdio()
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--include-demo", action="store_true", help="Also evaluate source=DEMO rows.")
    args = parser.parse_args()

    sb = get_supabase_client()
    optional = supported_article_columns(sb, OPTIONAL)
    if "is_hidden" not in optional and "demo_visible" not in optional:
        print("[hide-incomplete] Missing visibility columns.")
        print("[hide-incomplete] Run SQL: backend/sql/add_demo_readiness_fields.sql")
        return 2

    query = (
        sb.table("articles")
        .select(",".join(FIELDS + sorted(optional)))
        .order("published_at", desc=True)
        .limit(max(args.limit, 0))
    )
    if not args.include_demo:
        query = query.neq("source", "DEMO")
    rows = query.execute().data or []
    targets = [row for row in rows if not is_demo_ready(row)]
    print(f"[hide-incomplete] scanned={len(rows)} incomplete_targets={len(targets)} run={args.run}")
    for row in targets[:20]:
        print(f"  target={row.get('url_hash')} title_ko={(row.get('title_ko') or row.get('title') or '')[:80]}")

    if not args.run:
        print("[hide-incomplete] preview only. Add --run to update visibility fields.")
        return 0

    payload = {}
    if "is_hidden" in optional:
        payload["is_hidden"] = True
    if "demo_visible" in optional:
        payload["demo_visible"] = False
    for row in targets:
        sb.table("articles").update(payload).eq("url_hash", row["url_hash"]).execute()
    print(f"[hide-incomplete] updated={len(targets)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
