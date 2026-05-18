"""
Audit Supabase articles for polished Samsun News demo readiness.

Usage:
    python scripts/audit_demo_readiness.py
"""

from __future__ import annotations

from article_pipeline_common import configure_stdio, get_supabase_client, supported_article_columns
from demo_quality import (
    has_fact,
    has_korean,
    has_neologism_terms,
    has_translation,
    is_blank,
    is_demo_ready,
    is_weak_summary,
)


BASE_FIELDS = [
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
OPTIONAL_FIELDS = [
    "fact_status",
    "fact_confidence",
    "slang_terms",
    "neologism_terms",
    "is_demo",
    "is_hidden",
    "demo_visible",
    "demo_priority",
    "hitl_required",
]


def fetch_all(sb, fields: list[str]) -> list[dict]:
    rows: list[dict] = []
    offset = 0
    page_size = 1000
    select_fields = ",".join(fields)
    while True:
        result = sb.table("articles").select(select_fields).range(offset, offset + page_size - 1).execute()
        page = result.data or []
        rows.extend(page)
        if len(page) < page_size:
            return rows
        offset += page_size


def main() -> int:
    configure_stdio()
    sb = get_supabase_client()
    optional = sorted(supported_article_columns(sb, OPTIONAL_FIELDS))
    rows = fetch_all(sb, BASE_FIELDS + optional)

    total = len(rows)
    korean_title = sum(1 for row in rows if has_korean(row.get("title_ko")))
    missing_title_ko = sum(1 for row in rows if is_blank(row.get("title_ko")))
    missing_summary_formal = sum(1 for row in rows if is_blank(row.get("summary_formal")))
    missing_summary_casual = sum(1 for row in rows if is_blank(row.get("summary_casual")))
    weak_summaries = sum(
        1 for row in rows
        if is_weak_summary(row.get("summary_formal")) or is_weak_summary(row.get("summary_casual"))
    )
    missing_translation = sum(1 for row in rows if not has_translation(row))
    with_fact = sum(1 for row in rows if has_fact(row))
    with_neologisms = sum(1 for row in rows if has_neologism_terms(row))
    demo_ready = sum(1 for row in rows if is_demo_ready(row))
    newest = max((str(row.get("published_at") or "") for row in rows), default="")

    print("[demo-readiness]")
    print(f"total_articles: {total}")
    print(f"articles_with_korean_title: {korean_title}")
    print(f"articles_missing_title_ko: {missing_title_ko}")
    print(f"articles_missing_summary_formal: {missing_summary_formal}")
    print(f"articles_missing_summary_casual: {missing_summary_casual}")
    print(f"articles_with_weak_summaries: {weak_summaries}")
    print(f"articles_missing_or_short_translation: {missing_translation}")
    print(f"articles_with_fact_status_or_label: {with_fact}")
    print(f"articles_with_neologism_terms: {with_neologisms}")
    print(f"newest_article_published_at: {newest or '(none)'}")
    print(f"demo_ready_articles: {demo_ready}")
    print(f"optional_columns_detected: {','.join(optional) or '(none)'}")

    if demo_ready < 5:
        print("[demo-readiness] WARNING: fewer than 5 demo-ready articles. Run repair/seed commands before demo.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
