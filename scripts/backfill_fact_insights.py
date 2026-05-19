"""
Backfill short conservative fact insight text for final demo-visible articles.

Default is dry-run:
    python scripts/backfill_fact_insights.py --dry-run

Apply updates:
    python scripts/backfill_fact_insights.py --run
"""

from __future__ import annotations

import argparse
from collections import Counter
from typing import Any

from article_pipeline_common import configure_stdio, get_supabase_client, supported_article_columns
from demo_quality import has_korean, has_translation, has_valid_summary, is_blank


BASE_FIELDS = [
    "url_hash",
    "title",
    "title_ko",
    "source",
    "url",
    "published_at",
    "translation",
    "summary_formal",
    "summary_casual",
    "fact_label",
]

OPTIONAL_FIELDS = [
    "fact_status",
    "fact_reason",
    "fact_insight",
    "is_demo",
    "is_hidden",
    "demo_visible",
]

REASONS = {
    "UNVERIFIED": "출처는 확인되지만 독립 교차검증 정보가 부족해 미검증으로 표시했습니다.",
    "RUMOR": "공식 발표보다 추정성 표현이 많아 루머 주의가 필요합니다.",
    "HITL_REQUIRED": "자동 판정만으로는 판단이 어려워 수동 검토가 필요한 기사입니다.",
    "FACT": "신뢰도 높은 출처와 명확한 보도 형식으로 확인된 기사입니다.",
    "VERIFIED": "신뢰도 높은 출처와 명확한 보도 형식으로 확인된 기사입니다.",
    "INSIGHT": "분석/해설 성격의 기사로, 출처 신뢰도와 보도 맥락을 함께 참고해야 합니다.",
    "FACT_INSIGHT": "신뢰도 높은 출처의 분석 기사로, 사실 보도와 해설 맥락을 함께 제공합니다.",
}


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


def normalize_fact(row: dict[str, Any]) -> str:
    raw = str(row.get("fact_status") or row.get("fact_label") or "").strip().upper()
    if raw in {"HITL", "HUMAN_REVIEW_REQUIRED"}:
        return "HITL_REQUIRED"
    if raw in {"VERIFIED", "FACT", "INSIGHT", "FACT_INSIGHT", "RUMOR", "UNVERIFIED", "HITL_REQUIRED"}:
        return raw
    return "UNVERIFIED"


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


def is_visible_complete(row: dict[str, Any]) -> bool:
    if bool(row.get("is_hidden")) or row.get("demo_visible") is False:
        return False
    if is_demo_or_sample(row):
        return False
    return (
        has_korean(row.get("title_ko"))
        and has_translation(row)
        and has_valid_summary(row)
        and not is_blank(row.get("url"))
        and not is_blank(row.get("source"))
    )


def needs_insight(row: dict[str, Any]) -> bool:
    return is_blank(row.get("fact_reason")) and is_blank(row.get("fact_insight"))


def main() -> int:
    configure_stdio()
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", action="store_true", help="Apply updates. Default is dry-run.")
    parser.add_argument("--dry-run", action="store_true", help="Preview only. This is the default.")
    parser.add_argument("--limit", type=int, default=10)
    args = parser.parse_args()

    sb = get_supabase_client()
    optional = sorted(supported_article_columns(sb, OPTIONAL_FIELDS))
    rows = fetch_all(sb, BASE_FIELDS + optional)
    visible = [row for row in rows if is_visible_complete(row)]
    fact_counts = Counter(normalize_fact(row) for row in visible)
    priority_order = {"HITL_REQUIRED": 0, "RUMOR": 1, "UNVERIFIED": 2, "INSIGHT": 3, "FACT_INSIGHT": 4, "FACT": 5, "VERIFIED": 5}
    candidates = [row for row in visible if needs_insight(row)]
    candidates.sort(key=lambda row: (priority_order.get(normalize_fact(row), 9), str(row.get("published_at") or "")), reverse=False)
    selected = candidates[: max(args.limit, 0)]

    print("[fact-insight-backfill]")
    print(f"mode: {'run' if args.run else 'dry-run'}")
    print(f"visible_complete_articles: {len(visible)}")
    print("fact_label_distribution:")
    for key, count in fact_counts.most_common():
        print(f"  {key}: {count}")
    print(f"hitl_unverified_rumor_visible: {sum(fact_counts.get(key, 0) for key in ('HITL_REQUIRED', 'UNVERIFIED', 'RUMOR'))}")
    print(f"missing_fact_reason_or_insight_visible: {len(candidates)}")
    print(f"selected_for_update: {len(selected)}")

    if "fact_reason" not in optional and "fact_insight" not in optional:
        print("Missing columns: fact_reason/fact_insight. Run backend/sql/final_demo_supabase_patch.sql first.")
        return 2 if args.run else 0

    for idx, row in enumerate(selected, start=1):
        label = normalize_fact(row)
        reason = REASONS.get(label, REASONS["UNVERIFIED"])
        print(f"  {idx:02d}. {label} | {row.get('source')} | {row.get('title_ko') or row.get('title')}")
        print(f"      {reason}")
        if args.run:
            payload: dict[str, str] = {}
            if "fact_reason" in optional:
                payload["fact_reason"] = reason
            if "fact_insight" in optional:
                payload["fact_insight"] = reason
            sb.table("articles").update(payload).eq("url_hash", row["url_hash"]).execute()

    if not args.run:
        print("No updates applied. Re-run with --run to update Supabase.")
    else:
        print(f"updated_rows: {len(selected)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
