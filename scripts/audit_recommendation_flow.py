"""
Audit the Samsun News personalized recommendation path.

Default is read-only:
    python scripts/audit_recommendation_flow.py --dry-run

Optional write smoke test:
    python scripts/audit_recommendation_flow.py --run
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from typing import Any

from article_pipeline_common import configure_stdio, get_supabase_client, supported_article_columns


TEST_USER_ID = "audit_recommendation_flow_test"
VECTOR_DIM = 1024


def coerce_vector(raw: Any) -> list[float] | None:
    if raw is None:
        return None
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except json.JSONDecodeError:
            raw = [part.strip() for part in raw.strip("[]").split(",") if part.strip()]
    if not isinstance(raw, list):
        return None
    vector: list[float] = []
    for value in raw[:VECTOR_DIM]:
        try:
            vector.append(float(value))
        except (TypeError, ValueError):
            return None
    if len(vector) < VECTOR_DIM:
        vector.extend([0.0] * (VECTOR_DIM - len(vector)))
    return vector


def serialize_vector(vector: list[float]) -> str:
    return "[" + ",".join(f"{value:.8f}" for value in vector[:VECTOR_DIM]) + "]"


def fetch_rows(sb, fields: str, limit: int = 1000) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    offset = 0
    while True:
        result = sb.table("articles").select(fields).range(offset, offset + limit - 1).execute()
        page = result.data or []
        rows.extend(page)
        if len(page) < limit:
            return rows
        offset += limit


def status(name: str, ok: bool, detail: str = "") -> None:
    mark = "OK" if ok else "WARN"
    print(f"[{mark}] {name}: {detail}")


def table_exists(sb, table: str) -> tuple[bool, str]:
    try:
        result = sb.table(table).select("*").limit(1).execute()
        return True, f"{len(result.data or [])} sample rows accessible"
    except Exception as exc:  # noqa: BLE001 - audit should keep going
        return False, str(exc)


def rpc_match_articles(sb, vector: list[float], top_k: int = 5) -> tuple[bool, list[dict[str, Any]], str]:
    try:
        result = sb.rpc("match_articles", {
            "query_vector": serialize_vector(vector),
            "top_k": top_k,
        }).execute()
        rows = result.data or []
        return True, rows, f"{len(rows)} rows"
    except Exception as exc:  # noqa: BLE001
        return False, [], str(exc)


def fallback_candidates(sb, interest_tags: list[str], top_k: int = 5) -> list[dict[str, Any]]:
    rows = fetch_rows(
        sb,
        "url_hash,title_ko,source,category,published_at,translation,summary_formal,summary_casual,fact_label,is_hidden,is_demo",
        limit=1000,
    )
    visible = [
        row for row in rows
        if not row.get("is_hidden")
        and not row.get("is_demo")
        and row.get("title_ko")
        and row.get("translation")
        and (row.get("summary_formal") or row.get("summary_casual"))
        and row.get("source") != "DEMO"
    ]

    def score(row: dict[str, Any]) -> tuple[int, str]:
        category = str(row.get("category") or "")
        matched = 1 if category in interest_tags else 0
        return matched, str(row.get("published_at") or "")

    return sorted(visible, key=score, reverse=True)[:top_k]


def run_write_smoke(sb, article: dict[str, Any], vector: list[float], keep_test_user: bool) -> None:
    now = datetime.now(timezone.utc).isoformat()
    url_hash = article["url_hash"]
    user_payload = {
        "user_id": TEST_USER_ID,
        "interest_tags": ["AI 비즈니스", "AI 연구"],
        "user_vector": serialize_vector(vector),
        "last_seen_at": now,
    }
    try:
        sb.table("users").upsert({**user_payload, "updated_at": now}, on_conflict="user_id").execute()
    except Exception as exc:  # noqa: BLE001
        if "updated_at" not in str(exc):
            raise
        sb.table("users").upsert(user_payload, on_conflict="user_id").execute()
    status("interest_tags 저장", True, TEST_USER_ID)

    sb.table("user_logs").insert({
        "user_id": TEST_USER_ID,
        "url_hash": url_hash,
        "action": "view",
        "created_at": now,
    }).execute()
    status("user_logs 저장", True, url_hash)

    user = sb.table("users").select("user_vector").eq("user_id", TEST_USER_ID).maybe_single().execute()
    current = coerce_vector((user.data or {}).get("user_vector")) or vector
    next_vector = [current[i] * 0.6 + vector[i] * 0.4 for i in range(VECTOR_DIM)]
    update_payload = {
        "user_vector": serialize_vector(next_vector),
    }
    try:
        sb.table("users").update({
            **update_payload,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }).eq("user_id", TEST_USER_ID).execute()
    except Exception as exc:  # noqa: BLE001
        if "updated_at" not in str(exc):
            raise
        sb.table("users").update(update_payload).eq("user_id", TEST_USER_ID).execute()
    status("user_vector 업데이트", True, "old*0.6 + article*0.4")

    if not keep_test_user:
        sb.table("user_logs").delete().eq("user_id", TEST_USER_ID).execute()
        sb.table("users").delete().eq("user_id", TEST_USER_ID).execute()
        status("테스트 데이터 정리", True, TEST_USER_ID)


def main() -> int:
    configure_stdio()
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="read-only audit; default")
    parser.add_argument("--run", action="store_true", help="perform a small write smoke test and clean it up")
    parser.add_argument("--keep-test-user", action="store_true", help="keep the audit test user/logs")
    args = parser.parse_args()
    dry_run = not args.run

    sb = get_supabase_client()
    columns = supported_article_columns(sb, ("embedding", "category", "is_hidden"))

    print("=== Personalized recommendation audit ===")
    print(f"mode: {'dry-run' if dry_run else 'run'}")

    for table in ("articles", "users", "user_logs"):
        ok, detail = table_exists(sb, table)
        status(f"{table} 테이블", ok, detail)

    required_article_cols = {"embedding", "category", "is_hidden"}
    status("articles 필수 컬럼", required_article_cols.issubset(columns), ", ".join(sorted(required_article_cols & columns)))

    rows = fetch_rows(sb, "url_hash,title_ko,category,embedding,is_hidden,is_demo,published_at", limit=500)
    embedded = [row for row in rows if coerce_vector(row.get("embedding"))]
    visible_embedded = [row for row in embedded if not row.get("is_hidden") and not row.get("is_demo")]
    status("articles.embedding non-null", bool(embedded), f"{len(embedded)} / {len(rows)}")
    status("visible embedded candidates", bool(visible_embedded), str(len(visible_embedded)))

    seed_article = visible_embedded[0] if visible_embedded else (embedded[0] if embedded else None)
    seed_vector = coerce_vector(seed_article.get("embedding")) if seed_article else None
    if seed_article and seed_vector:
        ok, recs, detail = rpc_match_articles(sb, seed_vector, 5)
        status("match_articles RPC", ok and len(recs) > 0, detail)
        if not ok:
            print("  fix: run backend/sql/final_demo_supabase_patch.sql in Supabase SQL Editor")
        for row in recs[:5]:
            print(f"  - {row.get('title_ko') or row.get('title')} | {row.get('category')} | sim={row.get('similarity')}")
    else:
        status("match_articles RPC", False, "No article embedding available for query_vector")

    fallback = fallback_candidates(sb, ["AI 비즈니스", "AI 연구"], 5)
    status("fallback 추천", bool(fallback), f"{len(fallback)} rows")
    for row in fallback[:5]:
        print(f"  fallback - {row.get('title_ko')} | {row.get('category')} | {row.get('published_at')}")

    if args.run:
        if not seed_article or not seed_vector:
            status("write smoke", False, "Skipped because no article embedding exists")
        else:
            run_write_smoke(sb, seed_article, seed_vector, keep_test_user=args.keep_test_user)

    print("=== Done ===")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
