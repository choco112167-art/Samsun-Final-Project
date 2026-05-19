"""Audit Samsun News article freshness for the Apps in Toss feed.

This script reads the same Supabase `public.articles` table that the `.ait`
frontend uses. It does not crawl, generate, or mutate data.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any

from article_pipeline_common import configure_stdio, get_supabase_client, supported_article_columns
from demo_quality import has_fact, has_korean, has_translation, has_valid_summary, is_blank
from sangjun_sqlite_common import normalize_final_category


BASE_FIELDS = [
    "url_hash",
    "url",
    "title",
    "title_ko",
    "source",
    "source_type",
    "category",
    "published_at",
    "translation",
    "summary_formal",
    "summary_casual",
    "fact_label",
]

OPTIONAL_FIELDS = [
    "source_url",
    "original_url",
    "summary_ko",
    "created_at",
    "updated_at",
    "collected_at",
    "fact_status",
    "is_demo",
    "is_hidden",
    "demo_visible",
    "demo_priority",
]

COMMUNITY_SOURCES = {"Lemmy Technology", "Hacker News AI", "Hacker News LLM", "Hacker News ML"}


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


def source_url(row: dict[str, Any]) -> str:
    return str(row.get("url") or row.get("source_url") or row.get("original_url") or "").strip()


def is_valid_http_url(value: object) -> bool:
    text = str(value or "").strip().lower()
    return text.startswith("http://") or text.startswith("https://")


def is_demo_or_sample(row: dict[str, Any]) -> bool:
    title = f"{row.get('title') or ''} {row.get('title_ko') or ''}".upper()
    return (
        str(row.get("source") or "").strip().upper() == "DEMO"
        or bool(row.get("is_demo"))
        or "DEMO" in title
        or "MOCK" in title
        or "시연용" in str(row.get("title") or "")
        or "시연용" in str(row.get("title_ko") or "")
    )


def category_for(row: dict[str, Any]) -> str:
    return normalize_final_category(
        row.get("category"),
        row.get("source"),
        row.get("title") or row.get("title_ko"),
        row.get("translation") or "",
    )


def is_complete_visible(row: dict[str, Any]) -> bool:
    if bool(row.get("is_hidden")) or row.get("demo_visible") is False:
        return False
    if is_demo_or_sample(row):
        return False
    return (
        has_korean(row.get("title_ko"))
        and has_translation(row)
        and has_valid_summary(row)
        and has_fact(row)
        and bool(source_url(row))
        and is_valid_http_url(source_url(row))
    )


def missing_ai(row: dict[str, Any]) -> bool:
    return not (
        has_korean(row.get("title_ko"))
        and has_translation(row)
        and has_valid_summary(row)
    )


def newest(rows: list[dict[str, Any]], field: str = "published_at") -> datetime | None:
    values = [dt for row in rows if (dt := parse_dt(row.get(field))) is not None]
    return max(values, default=None)


def fmt_dt(value: datetime | None) -> str:
    return value.isoformat() if value else "(none)"


def main() -> int:
    configure_stdio()
    sb = get_supabase_client()
    optional = sorted(supported_article_columns(sb, OPTIONAL_FIELDS))
    rows = fetch_all(sb, BASE_FIELDS + optional)
    visible = [row for row in rows if is_complete_visible(row)]
    visible.sort(
        key=lambda row: (
            parse_dt(row.get("published_at")) or datetime.min.replace(tzinfo=timezone.utc),
            parse_dt(row.get("updated_at")) or parse_dt(row.get("created_at")) or datetime.min.replace(tzinfo=timezone.utc),
        ),
        reverse=True,
    )

    now = datetime.now(timezone.utc)
    windows = {
        "6h": now - timedelta(hours=6),
        "24h": now - timedelta(hours=24),
        "3d": now - timedelta(days=3),
        "7d": now - timedelta(days=7),
    }
    complete_by_window = {
        name: sum(1 for row in visible if (dt := parse_dt(row.get("published_at"))) is not None and dt >= start)
        for name, start in windows.items()
    }
    all_by_window = {
        name: sum(1 for row in rows if (dt := parse_dt(row.get("published_at"))) is not None and dt >= start)
        for name, start in windows.items()
    }
    recent_24_missing_or_hidden = sum(
        1
        for row in rows
        if (dt := parse_dt(row.get("published_at"))) is not None
        and dt >= windows["24h"]
        and (bool(row.get("is_hidden")) or missing_ai(row))
    )
    collected_recent_hidden = {
        name: sum(
            1
            for row in rows
            if (dt := parse_dt(row.get("published_at"))) is not None
            and dt >= start
            and bool(row.get("is_hidden"))
        )
        for name, start in windows.items()
    }
    collected_recent_missing_ai = {
        name: sum(
            1
            for row in rows
            if (dt := parse_dt(row.get("published_at"))) is not None
            and dt >= start
            and missing_ai(row)
        )
        for name, start in windows.items()
    }
    hidden_latest = [
        row for row in rows
        if bool(row.get("is_hidden")) and parse_dt(row.get("published_at")) is not None
    ]
    hidden_latest.sort(
        key=lambda row: parse_dt(row.get("published_at")) or datetime.min.replace(tzinfo=timezone.utc),
        reverse=True,
    )

    latest_by_source: dict[str, datetime | None] = defaultdict(lambda: None)
    for row in rows:
        source = str(row.get("source") or "(none)")
        dt = parse_dt(row.get("published_at"))
        if dt is not None and (latest_by_source[source] is None or dt > latest_by_source[source]):
            latest_by_source[source] = dt

    print("[freshness]")
    print(f"total_articles: {len(rows)}")
    print(f"visible_complete_articles: {len(visible)}")
    print(f"newest_visible_published_at: {fmt_dt(newest(visible))}")
    print(f"newest_any_published_at: {fmt_dt(newest(rows))}")
    print(f"recent_all_articles: 6h={all_by_window['6h']} 24h={all_by_window['24h']} 3d={all_by_window['3d']} 7d={all_by_window['7d']}")
    print(f"recent_complete_visible_articles: 6h={complete_by_window['6h']} 24h={complete_by_window['24h']} 3d={complete_by_window['3d']} 7d={complete_by_window['7d']}")
    print(f"recent_24h_hidden_or_missing_ai: {recent_24_missing_or_hidden}")
    print(
        "collected_but_hidden_articles: "
        f"6h={collected_recent_hidden['6h']} 24h={collected_recent_hidden['24h']} "
        f"3d={collected_recent_hidden['3d']} 7d={collected_recent_hidden['7d']}"
    )
    print(
        "collected_but_missing_ai_outputs: "
        f"6h={collected_recent_missing_ai['6h']} 24h={collected_recent_missing_ai['24h']} "
        f"3d={collected_recent_missing_ai['3d']} 7d={collected_recent_missing_ai['7d']}"
    )
    print("visible_by_category:")
    for category, count in Counter(category_for(row) for row in visible).most_common():
        print(f"  {category}: {count}")
    print("source_latest_published_at:")
    for source, dt in sorted(latest_by_source.items(), key=lambda item: item[0].lower()):
        print(f"  {source}: {fmt_dt(dt)}")
    print("community_latest:")
    for source in sorted(COMMUNITY_SOURCES):
        print(f"  {source}: {fmt_dt(latest_by_source.get(source))}")
    print("app_top_20:")
    for index, row in enumerate(visible[:20], 1):
        summary_text = str(row.get("summary_formal") or row.get("summary_casual") or row.get("summary_ko") or "")
        print(
            f"  {index:02d}. {row.get('published_at')} | {category_for(row)} | "
            f"{row.get('source')} | hidden={bool(row.get('is_hidden'))} | "
            f"translation_len={len(str(row.get('translation') or ''))} | "
            f"summary_len={len(summary_text)} | "
            f"{row.get('title_ko') or row.get('title')}"
        )
    print("latest_hidden_or_pending_top_10:")
    for index, row in enumerate(hidden_latest[:10], 1):
        print(
            f"  {index:02d}. {row.get('published_at')} | {category_for(row)} | "
            f"{row.get('source')} | missing_ai={missing_ai(row)} | "
            f"{row.get('title_ko') or row.get('title')}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
