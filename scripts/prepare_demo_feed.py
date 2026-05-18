"""
Prepare Supabase articles for a polished live demo feed without deleting data.

The script uses optional visibility columns from
backend/sql/add_demo_readiness_fields.sql:
  - is_hidden
  - demo_visible
  - is_demo
  - demo_priority

Rows are only updated with --run. Production rows are never deleted.

Usage:
    python scripts/export_articles_backup.py
    python scripts/prepare_demo_feed.py --since 2026-05-01 --until 2026-05-18
    python scripts/prepare_demo_feed.py --since 2026-05-01 --until 2026-05-18 --run
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from typing import Any

from article_pipeline_common import configure_stdio, get_supabase_client, supported_article_columns
from demo_quality import has_fact, has_korean, has_valid_summary, is_demo_ready
from sangjun_sqlite_common import DEFAULT_SINCE, DEFAULT_UNTIL, parse_bound, parse_published_at


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
    "is_hidden",
    "is_demo",
    "demo_visible",
    "demo_priority",
    "hitl_required",
]
VISIBILITY_FIELDS = {"is_hidden", "demo_visible"}


def parse_dt(value: Any) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None


def age_days(row: dict[str, Any]) -> float:
    dt = parse_dt(row.get("published_at"))
    if dt is None:
        return 9999.0
    return (datetime.now(timezone.utc) - dt).total_seconds() / 86_400


def is_demo(row: dict[str, Any]) -> bool:
    return bool(row.get("is_demo")) or str(row.get("source") or "").strip().upper() == "DEMO"


def protected_by_priority(row: dict[str, Any]) -> bool:
    try:
        priority = int(row.get("demo_priority") or 0)
    except (TypeError, ValueError):
        priority = 0
    return is_demo(row) or 0 < priority <= 20


def hide_reason(row: dict[str, Any], since: datetime, until: datetime) -> str:
    if protected_by_priority(row):
        return ""
    published = parse_published_at(row.get("published_at"))
    if published is None:
        return "missing_published_at"
    if published < since:
        return f"before_{since.date().isoformat()}"
    if published > until:
        return f"after_{until.date().isoformat()}"
    if not has_korean(row.get("title_ko")):
        return "missing_title_ko"
    if not has_valid_summary(row):
        return "missing_or_weak_summary"
    if not has_fact(row):
        return "missing_fact_status"
    if not is_demo_ready(row):
        return "not_demo_ready"
    return ""


def fetch_rows(sb, fields: list[str], limit: int) -> list[dict[str, Any]]:
    return (
        sb.table("articles")
        .select(",".join(fields))
        .order("published_at", desc=True)
        .limit(max(limit, 0))
        .execute()
        .data
        or []
    )


def main() -> int:
    configure_stdio()
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", action="store_true", help="Actually update visibility fields.")
    parser.add_argument("--limit", type=int, default=1000)
    parser.add_argument("--since", default=DEFAULT_SINCE)
    parser.add_argument("--until", default=DEFAULT_UNTIL)
    parser.add_argument("--confirm-delete", action="store_true", help="Reserved for destructive modes; this script does not delete rows.")
    args = parser.parse_args()

    sb = get_supabase_client()
    optional = supported_article_columns(sb, OPTIONAL_FIELDS)
    missing_visibility = sorted(VISIBILITY_FIELDS - optional)
    if missing_visibility:
        print("[prepare-demo-feed] Missing visibility columns:", ",".join(missing_visibility))
        print("[prepare-demo-feed] Run SQL in Supabase SQL Editor: backend/sql/add_demo_readiness_fields.sql")
        return 2

    since = parse_bound(args.since)
    until = parse_bound(args.until, end_of_day=True)
    if args.confirm_delete:
        print("[prepare-demo-feed] --confirm-delete was provided, but this script never hard-deletes rows.")

    rows = fetch_rows(sb, BASE_FIELDS + sorted(optional), args.limit)
    targets: list[tuple[dict[str, Any], str]] = []
    ready = 0
    for row in rows:
        if is_demo_ready(row):
            ready += 1
        reason = hide_reason(row, since, until)
        if reason:
            targets.append((row, reason))

    print(
        f"[prepare-demo-feed] scanned={len(rows)} demo_ready={ready} "
        f"hide_targets={len(targets)} run={args.run}"
    )
    for row, reason in targets[:30]:
        title = (row.get("title_ko") or row.get("title") or "")[:90]
        print(f"  target={row.get('url_hash')} reason={reason} age_days={age_days(row):.1f} title={title}")

    if not args.run:
        print("[prepare-demo-feed] preview only. Back up first, then add --run to update visibility.")
        return 0

    payload: dict[str, Any] = {"is_hidden": True, "demo_visible": False}
    for row, _reason in targets:
        sb.table("articles").update(payload).eq("url_hash", row["url_hash"]).execute()
    print(f"[prepare-demo-feed] updated={len(targets)}")
    print("[prepare-demo-feed] no production rows were deleted.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
