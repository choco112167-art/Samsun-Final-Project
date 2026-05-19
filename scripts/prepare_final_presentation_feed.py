"""
Prepare Supabase articles for the final live presentation feed.

Default is dry-run. Use --run to update Supabase.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Any

from article_pipeline_common import configure_stdio, get_supabase_client, supported_article_columns
from demo_quality import has_korean, has_translation, has_valid_summary, is_blank
from sangjun_sqlite_common import normalize_final_category, parse_bound


BASE_FIELDS = [
    "url_hash",
    "title",
    "title_ko",
    "source",
    "url",
    "published_at",
    "category",
    "translation",
    "summary_formal",
    "summary_casual",
    "fact_label",
]

OPTIONAL_FIELDS = [
    "source_url",
    "original_url",
    "summary_ko",
    "fact_status",
    "slang_terms",
    "neologism_terms",
    "is_demo",
    "is_hidden",
    "demo_visible",
    "demo_priority",
]

REQUIRED_UPDATE_COLUMNS = {"is_hidden", "demo_visible", "demo_priority"}
OPTIONAL_CATEGORY_UPDATE = "category"

FINAL_CATEGORIES = ("AI 연구", "AI 심층", "AI 스타트업", "AI 윤리", "AI 비즈니스", "AI 커뮤니티", "테크 전반")


def parse_dt(value: object) -> datetime:
    text = str(value or "").strip()
    if not text:
        return datetime.min.replace(tzinfo=timezone.utc)
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except ValueError:
        return datetime.min.replace(tzinfo=timezone.utc)


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


def is_demo_row(row: dict[str, Any]) -> bool:
    title = f"{row.get('title') or ''} {row.get('title_ko') or ''}".upper()
    return (
        str(row.get("source") or "").strip().upper() == "DEMO"
        or bool(row.get("is_demo"))
        or "DEMO" in title
        or "MOCK" in title
        or "시연용" in str(row.get("title") or "")
        or "시연용" in str(row.get("title_ko") or "")
    )


def fallback_category(row: dict[str, Any]) -> str:
    return normalize_final_category(
        row.get("category"),
        row.get("source"),
        row.get("title") or row.get("title_ko"),
        row.get("translation") or "",
    )


def is_complete_real(row: dict[str, Any]) -> bool:
    url = str(row.get("url") or row.get("source_url") or row.get("original_url") or "").strip()
    return (
        not is_demo_row(row)
        and has_korean(row.get("title_ko"))
        and has_translation(row)
        and has_valid_summary(row)
        and not is_blank(url)
        and not is_blank(row.get("source"))
    )


def in_range(row: dict[str, Any], since: datetime, until: datetime | None) -> bool:
    published = parse_dt(row.get("published_at"))
    if published < since:
        return False
    if until is not None and published > until:
        return False
    return True


def missing_fields(row: dict[str, Any]) -> list[str]:
    missing: list[str] = []
    if not has_korean(row.get("title_ko")):
        missing.append("title_ko")
    if not has_translation(row):
        missing.append("translation")
    if is_blank(row.get("summary_formal")):
        missing.append("summary_formal")
    if is_blank(row.get("summary_casual")):
        missing.append("summary_casual")
    if "summary_ko" in row and is_blank(row.get("summary_ko")):
        missing.append("summary_ko")
    return missing


def batch(items: list[str], size: int = 100) -> list[list[str]]:
    return [items[i:i + size] for i in range(0, len(items), size)]


def update_rows(sb, hashes: list[str], payload: dict[str, Any]) -> None:
    for part in batch(hashes):
        sb.table("articles").update(payload).in_("url_hash", part).execute()


def print_backfill_candidates(rows: list[dict[str, Any]], min_per_category: int, visible_counts: Counter[str]) -> None:
    by_category: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_category[fallback_category(row)].append(row)

    print("backfill_needed_by_category:")
    for category, candidates in sorted(by_category.items()):
        shortage = max(0, min_per_category - visible_counts.get(category, 0))
        if shortage <= 0 and len(candidates) == 0:
            continue
        print(f"  {category}: shortage={shortage}, candidates={len(candidates)}")
        for row in sorted(candidates, key=lambda item: parse_dt(item.get("published_at")), reverse=True)[:10]:
            print(
                "    - "
                f"url_hash={row.get('url_hash')} | "
                f"title={row.get('title')} | "
                f"title_ko={row.get('title_ko')} | "
                f"source={row.get('source')} | "
                f"category={fallback_category(row)} | "
                f"published_at={row.get('published_at')} | "
                f"missing={','.join(missing_fields(row)) or '(none)'}"
            )


def main() -> int:
    configure_stdio()
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", action="store_true", help="Apply updates. Default is dry-run.")
    parser.add_argument("--dry-run", action="store_true", help="Preview only. This is the default.")
    parser.add_argument("--target-visible", type=int, default=100)
    parser.add_argument("--min-per-category", type=int, default=5)
    parser.add_argument("--since", default="2026-05-01")
    parser.add_argument("--until", default="", help="Optional upper bound. Leave empty to keep newly refreshed articles visible.")
    parser.add_argument("--normalize-categories", action="store_true")
    args = parser.parse_args()

    sb = get_supabase_client()
    optional = sorted(supported_article_columns(sb, OPTIONAL_FIELDS))
    rows = fetch_all(sb, BASE_FIELDS + optional)

    supported = set(optional)
    missing_update_cols = sorted(REQUIRED_UPDATE_COLUMNS - supported)

    since = parse_bound(args.since)
    until = parse_bound(args.until, end_of_day=True) if str(args.until or "").strip() else None

    demo_rows = [row for row in rows if is_demo_row(row)]
    out_of_range_rows = [row for row in rows if not is_demo_row(row) and not in_range(row, since, until)]
    complete_real = [
        row for row in rows
        if is_complete_real(row) and in_range(row, since, until)
    ]
    incomplete_real = [
        row for row in rows
        if not is_demo_row(row) and in_range(row, since, until) and not is_complete_real(row)
    ]
    complete_real.sort(key=lambda row: parse_dt(row.get("published_at")), reverse=True)

    visible_counts = Counter(fallback_category(row) for row in complete_real)
    visible_source_counts = Counter(str(row.get("source") or "(none)") for row in complete_real)
    category_updates = [
        row for row in rows
        if args.normalize_categories
        and not is_blank(row.get("url_hash"))
        and str(row.get("category") or "").strip() != fallback_category(row)
    ]

    hide_hashes = sorted({
        str(row.get("url_hash"))
        for row in [*demo_rows, *incomplete_real, *out_of_range_rows]
        if row.get("url_hash")
    })
    restore_hashes = [str(row.get("url_hash")) for row in complete_real if row.get("url_hash")]
    promoted = complete_real[: max(args.target_visible, 0)]

    shortage_total = max(0, args.target_visible - len(complete_real))

    print("[prepare-final-presentation-feed]")
    print(f"mode: {'run' if args.run else 'dry-run'}")
    print(f"target_visible: {args.target_visible}")
    print(f"min_per_category: {args.min_per_category}")
    print(f"date_range: {since.date()} to {until.date() if until else 'latest'}")
    print(f"total_articles: {len(rows)}")
    print(f"demo_or_sample_articles_to_hide: {len(demo_rows)}")
    print(f"out_of_range_articles_to_hide: {len(out_of_range_rows)}")
    print(f"incomplete_real_articles_to_hide: {len(incomplete_real)}")
    print(f"unique_articles_to_hide: {len(hide_hashes)}")
    print(f"complete_real_articles_to_restore_visible: {len(restore_hashes)}")
    print(f"complete_real_articles: {len(complete_real)}")
    print(f"target_visible_shortage: {shortage_total}")
    print(f"category_updates_to_final_7: {len(category_updates)}")
    print(f"optional_columns_detected: {','.join(optional) or '(none)'}")
    print("visible_by_category:")
    for key in FINAL_CATEGORIES:
        print(f"  {key}: {visible_counts.get(key, 0)}")
    print("visible_by_source:")
    for key, count in visible_source_counts.most_common():
        print(f"  {key}: {count}")
    print("shortage_categories:")
    shortage_all = {key: max(0, args.min_per_category - visible_counts.get(key, 0)) for key in FINAL_CATEGORIES}
    shortage_all = {key: value for key, value in shortage_all.items() if value > 0}
    if shortage_all:
        for key, count in shortage_all.items():
            print(f"  {key}: {count}")
    else:
        print("  (none)")
    print("top_promoted_preview:")
    for idx, row in enumerate(promoted[:50], start=1):
        print(
            f"  {idx:02d}. {row.get('published_at')} | {fallback_category(row)} | "
            f"{row.get('source')} | {row.get('title_ko') or row.get('title')}"
        )

    if shortage_total or shortage_all:
        print_backfill_candidates(incomplete_real, args.min_per_category, visible_counts)

    if missing_update_cols:
        print(
            "[prepare-final-presentation-feed] missing update columns: "
            + ", ".join(missing_update_cols)
        )
        print("Run backend/sql/add_demo_readiness_fields.sql in Supabase SQL Editor before --run.")
        return 2 if args.run else 0

    if not args.run:
        print("No updates applied. Re-run with --run to update Supabase.")
        return 0

    if hide_hashes:
        update_rows(sb, hide_hashes, {"is_hidden": True, "demo_visible": False})
    if restore_hashes:
        update_rows(sb, restore_hashes, {"is_hidden": False, "demo_visible": True})
    for rank, part in enumerate(batch([str(row.get("url_hash")) for row in promoted if row.get("url_hash")], 100), start=0):
        sb.table("articles").update({"demo_priority": 1000 - rank}).in_("url_hash", part).execute()
    for row in category_updates:
        sb.table("articles").update({"category": fallback_category(row)}).eq("url_hash", row["url_hash"]).execute()

    print(f"hidden_articles_updated: {len(hide_hashes)}")
    print(f"restored_complete_real_articles: {len(restore_hashes)}")
    print(f"promoted_articles_updated: {len(promoted)}")
    print(f"category_updates: {len(category_updates)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
