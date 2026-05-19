"""
Clear test-only mock AI outputs from Supabase articles.

Rows are targeted only when at least one AI output field contains "[MOCK".
Only fields that contain "[MOCK" are reset so real model outputs are not
accidentally removed.
"""

from __future__ import annotations

import argparse
from typing import Any

from article_pipeline_common import configure_stdio, get_supabase_client, supported_article_columns

AI_FIELDS = ("translation", "summary_formal", "summary_casual")
MOCK_FILTER = "translation.ilike.%[MOCK%,summary_formal.ilike.%[MOCK%,summary_casual.ilike.%[MOCK%"


def fetch_mock_rows(sb, limit: int, url_hash: str | None, meta: set[str]) -> list[dict[str, Any]]:
    select_fields = [
        "url_hash",
        "title",
        "title_ko",
        "published_at",
        "translation",
        "summary_formal",
        "summary_casual",
    ]
    select_fields.extend(sorted(field for field in meta if field in {"ai_provider", "ai_model"}))
    query = (
        sb.table("articles")
        .select(",".join(select_fields))
        .or_(MOCK_FILTER)
        .order("published_at", desc=True)
        .limit(limit)
    )
    if url_hash:
        query = query.eq("url_hash", url_hash)
    return query.execute().data or []


def main() -> int:
    configure_stdio()
    parser = argparse.ArgumentParser(description="Clear [MOCK] AI outputs from articles.")
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--url-hash", type=str, default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--run", action="store_true", help="Actually update Supabase. Without this, preview only.")
    args = parser.parse_args()

    sb = get_supabase_client()
    meta = supported_article_columns(sb, ("ai_status", "ai_provider", "ai_model", "ai_error"))
    rows = fetch_mock_rows(sb, max(args.limit, 0), args.url_hash, meta)

    print(f"[clear_mock] targets={len(rows)} limit={args.limit} run={args.run}")
    cleared = 0
    for index, row in enumerate(rows, 1):
        title = (row.get("title_ko") or row.get("title") or "")[:90]
        mock_fields = [field for field in AI_FIELDS if "[MOCK" in str(row.get(field) or "")]
        print(f"\n[{index}/{len(rows)}] id={row.get('url_hash')} title={title}")
        print(f"  mock_fields={','.join(mock_fields)}")
        if not mock_fields:
            print("  update_ok=False reason=no [MOCK] marker")
            continue

        payload: dict[str, Any] = {field: "" for field in mock_fields}
        if "ai_status" in meta:
            payload["ai_status"] = "pending"
        if "ai_provider" in meta and str(row.get("ai_provider") or "").lower() == "mock":
            payload["ai_provider"] = None
        if "ai_model" in meta and str(row.get("ai_model") or "").lower().startswith("mock"):
            payload["ai_model"] = None
        if "ai_error" in meta:
            payload["ai_error"] = None

        if not args.run:
            print(f"  update_ok=False preview_only update_fields={','.join(payload.keys())}")
            continue

        sb.table("articles").update(payload).eq("url_hash", row["url_hash"]).execute()
        cleared += 1
        print("  update_ok=True")

    print(f"\n[clear_mock] cleared={cleared}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
