"""
Audit Supabase articles for polished Samsun News demo readiness.

Usage:
    python scripts/audit_demo_readiness.py
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone

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


MAY_START = datetime.fromisoformat("2026-05-01T00:00:00+00:00")
MAY_END = datetime.fromisoformat("2026-05-18T23:59:59+00:00")


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


def normalize_fact(value: object) -> str:
    raw = str(value or "").strip().upper()
    if raw in {"FACT", "VERIFIED", "FACT_INSIGHT", "INSIGHT"}:
        return "verified"
    if raw in {"RUMOR"}:
        return "rumor"
    if raw in {"HITL", "HITL_REQUIRED", "HUMAN_REVIEW_REQUIRED"}:
        return "hitl_required"
    if raw in {"", "NONE", "NULL"}:
        return "missing"
    return "unverified"


def parse_dt(value: object) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except ValueError:
        return None


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
    may_rows = [
        row for row in rows
        if (dt := parse_dt(row.get("published_at"))) is not None and MAY_START <= dt <= MAY_END
    ]
    demo_rows = [
        row for row in rows
        if str(row.get("source") or "").strip().upper() == "DEMO"
        or bool(row.get("is_demo"))
        or "[시연용]" in str(row.get("title_ko") or "")
    ]
    fact_counts = Counter(normalize_fact(row.get("fact_status") or row.get("fact_label")) for row in rows)
    demo_fact_counts = Counter(normalize_fact(row.get("fact_status") or row.get("fact_label")) for row in demo_rows)

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
    print(f"may_2026_05_01_to_05_18_articles: {len(may_rows)}")
    print(f"demo_articles: {len(demo_rows)}")
    print(f"demo_rumor_articles: {demo_fact_counts.get('rumor', 0)}")
    print(f"hitl_required_articles: {fact_counts.get('hitl_required', 0)}")
    print("fact_status_counts:")
    for key in ("verified", "unverified", "rumor", "hitl_required", "missing"):
        print(f"  {key}: {fact_counts.get(key, 0)}")
    print(f"optional_columns_detected: {','.join(optional) or '(none)'}")

    if demo_ready < 5:
        print("[demo-readiness] WARNING: fewer than 5 demo-ready articles. Run repair/seed commands before demo.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
