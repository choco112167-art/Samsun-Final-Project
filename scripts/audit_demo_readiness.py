"""
Audit Supabase articles for final Samsun News presentation readiness.

Usage:
    python scripts/audit_demo_readiness.py
"""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Any

from article_pipeline_common import configure_stdio, get_supabase_client, supported_article_columns
from demo_quality import (
    has_fact,
    has_korean,
    has_neologism_terms,
    has_translation,
    has_valid_summary,
    is_blank,
    is_demo_ready,
    is_weak_summary,
)
from sangjun_sqlite_common import FINAL_CATEGORIES, normalize_final_category


MAY_START = datetime.fromisoformat("2026-05-01T00:00:00+00:00")
MAY_END = datetime.fromisoformat("2026-05-18T23:59:59+00:00")


BASE_FIELDS = [
    "url_hash",
    "title",
    "title_ko",
    "source",
    "url",
    "published_at",
    "category",
    "summary_formal",
    "summary_casual",
    "translation",
    "fact_label",
]
OPTIONAL_FIELDS = [
    "summary_ko",
    "keywords",
    "fact_status",
    "fact_confidence",
    "slang_terms",
    "neologism_terms",
    "is_demo",
    "is_hidden",
    "demo_visible",
    "demo_priority",
    "hitl_required",
    "content_source",
]


def fetch_all(sb, fields: list[str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
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


def is_demo_or_sample(row: dict[str, Any]) -> bool:
    title = f"{row.get('title') or ''} {row.get('title_ko') or ''}".upper()
    return (
        str(row.get("source") or "").strip().upper() == "DEMO"
        or bool(row.get("is_demo"))
        or "DEMO" in title
        or "시연용" in str(row.get("title") or "")
        or "시연용" in str(row.get("title_ko") or "")
        or "MOCK" in title
    )


def fallback_category(row: dict[str, Any]) -> str:
    return normalize_final_category(
        row.get("category"),
        row.get("source"),
        row.get("title") or row.get("title_ko"),
        row.get("translation") or "",
    )


def is_incomplete(row: dict[str, Any]) -> bool:
    return (
        not has_korean(row.get("title_ko"))
        or not has_translation(row)
        or not has_valid_summary(row)
        or not has_fact(row)
    )


def is_final_visible(row: dict[str, Any]) -> bool:
    if bool(row.get("is_hidden")) or row.get("demo_visible") is False:
        return False
    if is_demo_or_sample(row):
        return False
    return not is_incomplete(row)


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


def text_len(value: object) -> int:
    return len(str(value or "").strip())


def main() -> int:
    configure_stdio()
    sb = get_supabase_client()
    optional = sorted(supported_article_columns(sb, OPTIONAL_FIELDS))
    rows = fetch_all(sb, BASE_FIELDS + optional)

    total = len(rows)
    not_hidden = sum(1 for row in rows if not bool(row.get("is_hidden")))
    hidden = sum(1 for row in rows if bool(row.get("is_hidden")))
    korean_title = sum(1 for row in rows if has_korean(row.get("title_ko")))
    missing_title_ko = sum(1 for row in rows if is_blank(row.get("title_ko")))
    missing_summary_formal = sum(1 for row in rows if is_blank(row.get("summary_formal")))
    missing_summary_casual = sum(1 for row in rows if is_blank(row.get("summary_casual")))
    missing_summary_ko = sum(1 for row in rows if "summary_ko" in optional and is_blank(row.get("summary_ko")))
    weak_summaries = sum(1 for row in rows if not has_valid_summary(row))
    missing_translation = sum(1 for row in rows if not has_translation(row))
    with_fact = sum(1 for row in rows if has_fact(row))
    with_neologisms = sum(1 for row in rows if has_neologism_terms(row))
    demo_ready = sum(1 for row in rows if is_demo_ready(row))
    newest = max((str(row.get("published_at") or "") for row in rows), default="")
    may_rows = [
        row for row in rows
        if (dt := parse_dt(row.get("published_at"))) is not None and MAY_START <= dt <= MAY_END
    ]
    demo_rows = [row for row in rows if is_demo_or_sample(row)]
    incomplete_rows = [row for row in rows if is_incomplete(row)]
    final_visible_rows = [row for row in rows if is_final_visible(row)]
    final_visible_rows.sort(
        key=lambda row: (
            int(row.get("demo_priority") or 0),
            str(row.get("published_at") or ""),
        ),
        reverse=True,
    )
    fact_counts = Counter(normalize_fact(row.get("fact_status") or row.get("fact_label")) for row in rows)
    demo_fact_counts = Counter(normalize_fact(row.get("fact_status") or row.get("fact_label")) for row in demo_rows)
    with_translation = sum(1 for row in rows if has_translation(row))
    with_summary_formal = sum(1 for row in rows if not is_weak_summary(row.get("summary_formal")))
    with_summary_casual = sum(1 for row in rows if not is_weak_summary(row.get("summary_casual")))
    with_summary_ko = sum(1 for row in rows if "summary_ko" in optional and not is_weak_summary(row.get("summary_ko")))
    category_null = sum(1 for row in rows if is_blank(row.get("category")))

    visible_by_category = Counter(fallback_category(row) for row in final_visible_rows)
    all_by_final_category = Counter(fallback_category(row) for row in rows)
    visible_by_source = Counter(str(row.get("source") or "(none)") for row in final_visible_rows)
    sangjun_rows = [
        row for row in rows
        if row.get("content_source") == "sangjun_sqlite"
        or "sangjun" in [str(item).lower() for item in (row.get("keywords") or [])]
    ]
    demo_visible_violations = [row for row in final_visible_rows if is_demo_or_sample(row)]
    incomplete_visible_violations = [row for row in final_visible_rows if is_incomplete(row)]

    print("[demo-readiness]")
    print(f"total_articles: {total}")
    print(f"is_hidden_false_articles: {not_hidden}")
    print(f"is_hidden_true_articles: {hidden}")
    print(f"final_visible_real_complete_articles: {len(final_visible_rows)}")
    print(f"demo_or_sample_articles: {len(demo_rows)}")
    print(f"incomplete_articles: {len(incomplete_rows)}")
    print(f"category_null_articles: {category_null}")
    print(f"articles_with_korean_title: {korean_title}")
    print(f"articles_missing_title_ko: {missing_title_ko}")
    print(f"articles_missing_summary_formal: {missing_summary_formal}")
    print(f"articles_missing_summary_casual: {missing_summary_casual}")
    if "summary_ko" in optional:
        print(f"articles_missing_summary_ko: {missing_summary_ko}")
    print(f"articles_with_weak_or_missing_all_summaries: {weak_summaries}")
    print(f"articles_missing_or_short_translation: {missing_translation}")
    print(f"articles_with_valid_translation: {with_translation}")
    print(f"articles_with_valid_summary_formal: {with_summary_formal}")
    print(f"articles_with_valid_summary_casual: {with_summary_casual}")
    if "summary_ko" in optional:
        print(f"articles_with_valid_summary_ko: {with_summary_ko}")
    print(f"articles_with_fact_status_or_label: {with_fact}")
    print(f"articles_with_neologism_terms: {with_neologisms}")
    print(f"newest_article_published_at: {newest or '(none)'}")
    print(f"demo_ready_articles_legacy_strict: {demo_ready}")
    print(f"may_2026_05_01_to_05_18_articles: {len(may_rows)}")
    print(f"sangjun_imported_articles: {len(sangjun_rows)}")
    print(f"demo_or_sample_visible_violations: {len(demo_visible_violations)}")
    print(f"incomplete_visible_violations: {len(incomplete_visible_violations)}")
    print(f"demo_articles: {len(demo_rows)}")
    print(f"demo_rumor_articles: {demo_fact_counts.get('rumor', 0)}")
    print(f"hitl_required_articles: {fact_counts.get('hitl_required', 0)}")
    print("fact_status_counts:")
    for key in ("verified", "unverified", "rumor", "hitl_required", "missing"):
        print(f"  {key}: {fact_counts.get(key, 0)}")
    print("visible_by_category:")
    for key in FINAL_CATEGORIES:
        print(f"  {key}: {visible_by_category.get(key, 0)}")
    print("all_articles_by_final_7_category:")
    for key in FINAL_CATEGORIES:
        print(f"  {key}: {all_by_final_category.get(key, 0)}")
    print("visible_by_source:")
    for key, count in visible_by_source.most_common():
        print(f"  {key}: {count}")
    print(f"optional_columns_detected: {','.join(optional) or '(none)'}")
    print("final_feed_top50:")
    for idx, row in enumerate(final_visible_rows[:50], start=1):
        title = row.get("title_ko") or row.get("title") or "(untitled)"
        summary_len = max(text_len(row.get("summary_formal")), text_len(row.get("summary_casual")), text_len(row.get("summary_ko")))
        print(
            f"  {idx:02d}. {title} | category={fallback_category(row)} | "
            f"source={row.get('source')} | published_at={row.get('published_at')} | "
            f"translation_len={text_len(row.get('translation'))} | summary_len={summary_len}"
        )

    if len(final_visible_rows) < 100:
        print("[demo-readiness] WARNING: fewer than 100 final-visible complete real articles.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
