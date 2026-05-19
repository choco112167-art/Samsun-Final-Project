"""
Backfill short conservative fact insight text for final demo-visible articles.

Default is dry-run:
    python scripts/backfill_fact_insights.py --dry-run

Apply updates:
    python scripts/backfill_fact_insights.py --run

If the visible feed has no HITL examples, promote up to 1-3 existing
UNVERIFIED real articles to HITL_REQUIRED for the final demo:
    python scripts/backfill_fact_insights.py --run --promote-hitl-samples 2
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
    "hitl_required",
    "is_demo",
    "is_hidden",
    "demo_visible",
]

REASONS = {
    "UNVERIFIED": "출처는 확인되지만 독립 교차검증 정보가 부족해 추가 확인이 필요한 기사입니다.",
    "RUMOR": "공식 발표보다 추정성 표현이 많아 주의가 필요한 기사입니다.",
    "HITL_REQUIRED": "자동 판정만으로는 판단이 어려워 사람이 추가로 확인해야 하는 기사입니다.",
    "FACT": "신뢰도 높은 출처와 명확한 보도 형식으로 확인된 기사입니다.",
    "VERIFIED": "신뢰도 높은 출처와 명확한 보도 형식으로 확인된 기사입니다.",
    "INSIGHT": "사실 보도보다 전문가 해설·관점이 중심인 기사입니다.",
    "FACT_INSIGHT": "사실 보도보다 전문가 해설·관점이 중심인 기사입니다.",
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
    if bool(row.get("hitl_required")):
        return "HITL_REQUIRED"
    raw = str(row.get("fact_status") or row.get("fact_label") or "").strip().upper()
    if raw in {"HITL", "HUMAN_REVIEW", "HUMAN_REVIEW_REQUIRED"}:
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
    text = f"{row.get('fact_reason') or ''}\n{row.get('fact_insight') or ''}"
    stale = (
        "미검증으로 표시했습니다" in text
        or "루머 주의가 필요합니다" in text
        or "수동 검토가 필요한 기사입니다" in text
    )
    return (is_blank(row.get("fact_reason")) and is_blank(row.get("fact_insight"))) or stale


def insight_payload(optional: list[str], label: str, *, promote_hitl: bool = False) -> dict[str, Any]:
    reason = REASONS.get(label, REASONS["UNVERIFIED"])
    payload: dict[str, Any] = {}
    if "fact_reason" in optional:
        payload["fact_reason"] = reason
    if "fact_insight" in optional:
        payload["fact_insight"] = reason
    if promote_hitl:
        payload["fact_label"] = "HITL_REQUIRED"
        if "fact_status" in optional:
            payload["fact_status"] = "HITL_REQUIRED"
        if "hitl_required" in optional:
            payload["hitl_required"] = True
    return payload


def print_row(prefix: str, row: dict[str, Any], label: str, reason: str) -> None:
    print(f"{prefix} {label} | {row.get('source')} | {row.get('title_ko') or row.get('title')}")
    print(f"      {reason}")


def main() -> int:
    configure_stdio()
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", action="store_true", help="Apply updates. Default is dry-run.")
    parser.add_argument("--dry-run", action="store_true", help="Preview only. This is the default.")
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument(
        "--promote-hitl-samples",
        type=int,
        default=0,
        help="With --run, promote up to this many visible UNVERIFIED real articles to HITL_REQUIRED. Max 3.",
    )
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
    promote_count = min(max(args.promote_hitl_samples, 0), 3)
    hitl_promote_candidates = [
        row for row in visible
        if normalize_fact(row) == "UNVERIFIED"
    ]
    hitl_promote_candidates.sort(
        key=lambda row: (0 if needs_insight(row) else 1, str(row.get("published_at") or "")),
        reverse=False,
    )
    selected_hitl_promotions: list[dict[str, Any]] = []
    if fact_counts.get("HITL_REQUIRED", 0) == 0 and promote_count > 0:
        selected_hitl_promotions = hitl_promote_candidates[:promote_count]
        promotion_hashes = {str(row.get("url_hash") or "") for row in selected_hitl_promotions}
        selected = [row for row in candidates if str(row.get("url_hash") or "") not in promotion_hashes][: max(args.limit, 0)]

    print("[fact-insight-backfill]")
    print(f"mode: {'run' if args.run else 'dry-run'}")
    print(f"visible_complete_articles: {len(visible)}")
    print("fact_label_distribution:")
    for key, count in fact_counts.most_common():
        print(f"  {key}: {count}")
    print(f"visible_hitl_required: {fact_counts.get('HITL_REQUIRED', 0)}")
    print(f"visible_unverified: {fact_counts.get('UNVERIFIED', 0)}")
    print(f"visible_rumor: {fact_counts.get('RUMOR', 0)}")
    print(f"visible_fact_or_verified: {fact_counts.get('FACT', 0) + fact_counts.get('VERIFIED', 0)}")
    print(f"hitl_unverified_rumor_visible: {sum(fact_counts.get(key, 0) for key in ('HITL_REQUIRED', 'UNVERIFIED', 'RUMOR'))}")
    print(f"missing_fact_reason_or_insight_visible: {len(candidates)}")
    print(f"selected_for_update: {len(selected)}")
    if fact_counts.get("HITL_REQUIRED", 0) == 0:
        print(f"hitl_promotion_candidates: {len(hitl_promote_candidates)}")
        for idx, row in enumerate(hitl_promote_candidates[:10], start=1):
            print(f"  candidate {idx:02d}. {row.get('source')} | {row.get('title_ko') or row.get('title')}")
    print(f"selected_for_hitl_promotion: {len(selected_hitl_promotions)}")

    if "fact_reason" not in optional and "fact_insight" not in optional:
        print("Missing columns: fact_reason/fact_insight. Run backend/sql/final_demo_supabase_patch.sql first.")
        return 2 if args.run else 0

    updated_rows = 0
    fact_reason_backfilled = 0
    fact_insight_backfilled = 0
    for idx, row in enumerate(selected, start=1):
        label = normalize_fact(row)
        reason = REASONS.get(label, REASONS["UNVERIFIED"])
        print_row(f"  {idx:02d}.", row, label, reason)
        if args.run:
            payload = insight_payload(optional, label)
            sb.table("articles").update(payload).eq("url_hash", row["url_hash"]).execute()
            updated_rows += 1
            fact_reason_backfilled += int("fact_reason" in payload)
            fact_insight_backfilled += int("fact_insight" in payload)

    promoted_rows = 0
    if selected_hitl_promotions:
        print("hitl_promotions:")
    for idx, row in enumerate(selected_hitl_promotions, start=1):
        reason = REASONS["HITL_REQUIRED"]
        print_row(f"  promote {idx:02d}.", row, "HITL_REQUIRED", reason)
        if args.run:
            payload = insight_payload(optional, "HITL_REQUIRED", promote_hitl=True)
            sb.table("articles").update(payload).eq("url_hash", row["url_hash"]).execute()
            updated_rows += 1
            promoted_rows += 1
            fact_reason_backfilled += int("fact_reason" in payload and is_blank(row.get("fact_reason")))
            fact_insight_backfilled += int("fact_insight" in payload and is_blank(row.get("fact_insight")))

    if not args.run:
        print("No updates applied. Re-run with --run to update Supabase.")
    else:
        print(f"updated_rows: {updated_rows}")
        print(f"fact_reason_backfilled: {fact_reason_backfilled}")
        print(f"fact_insight_backfilled: {fact_insight_backfilled}")
        print(f"promoted_hitl_rows: {promoted_rows}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
