"""
Audit Supabase neologisms for final demo-safe highlighting.

Usage:
    python scripts/audit_neologisms.py
"""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

from article_pipeline_common import configure_stdio, get_supabase_client


STOPWORDS = {
    "the",
    "a",
    "an",
    "and",
    "or",
    "of",
    "for",
    "to",
    "in",
    "on",
    "with",
    "by",
    "from",
    "tech",
    "technology",
    "news",
    "guardian",
    "verge",
    "decoder",
    "spectrum",
    "venturebeat",
    "meta",
    "google",
    "openai",
    "ai",
    "ml",
}

DEMO_ALLOWLIST = {
    "rag",
    "llm",
    "fine-tuning",
    "prompt injection",
    "guardrail",
    "hallucination",
    "inference",
    "token",
    "transformer",
    "embedding",
    "hitl",
    "cove",
    "re-ranking",
    "pgvector",
    "lora",
}


def norm(value: Any) -> str:
    return " ".join(str(value or "").strip().lower().split())


def explanation(row: dict[str, Any]) -> str:
    return str(row.get("explanation") or row.get("description") or "").strip()


def fetch_all_neologisms() -> list[dict[str, Any]]:
    sb = get_supabase_client()
    rows: list[dict[str, Any]] = []
    offset = 0
    page_size = 1000
    while True:
        result = sb.table("neologisms").select("*").range(offset, offset + page_size - 1).execute()
        page = result.data or []
        rows.extend(page)
        if len(page) < page_size:
            return rows
        offset += page_size


def main() -> int:
    configure_stdio()
    rows = fetch_all_neologisms()
    terms = [str(row.get("term") or "").strip() for row in rows]
    by_norm: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        key = norm(row.get("term"))
        if key:
            by_norm[key].append(row)

    missing_explanation = [term for term, row in zip(terms, rows) if term and not explanation(row)]
    short_terms = sorted(term for term in terms if 0 < len(term) <= 2)
    stopword_terms = sorted(term for term in terms if norm(term) in STOPWORDS)
    duplicate_terms = {key: len(group) for key, group in by_norm.items() if len(group) > 1}
    allowlist_missing = sorted(term for term in DEMO_ALLOWLIST if term not in by_norm)
    hidden_in_demo = sorted(
        term
        for term in terms
        if term and norm(term) not in DEMO_ALLOWLIST
    )

    ai_like_explanation = [
        row.get("term")
        for row in rows
        if norm(row.get("term")) != "ai"
        and "인간의 지적 능력을 모방하는 컴퓨터 시스템 기술" in explanation(row)
    ]

    print("[neologism-audit]")
    print(f"total_neologisms: {len(rows)}")
    print(f"missing_description_or_explanation: {len(missing_explanation)}")
    if missing_explanation:
        print("  " + ", ".join(missing_explanation[:30]))
    print(f"short_terms_len_1_to_2: {len(short_terms)}")
    if short_terms:
        print("  " + ", ".join(short_terms[:50]))
    print(f"stopword_terms: {len(stopword_terms)}")
    if stopword_terms:
        print("  " + ", ".join(stopword_terms[:50]))
    print(f"duplicate_terms: {len(duplicate_terms)}")
    for term, count in sorted(duplicate_terms.items())[:30]:
        print(f"  {term}: {count}")
    print(f"suspicious_ai_description_on_other_terms: {len(ai_like_explanation)}")
    if ai_like_explanation:
        print("  " + ", ".join(str(term) for term in ai_like_explanation[:50]))
    print(f"demo_allowlist_missing_in_db: {len(allowlist_missing)}")
    if allowlist_missing:
        print("  " + ", ".join(allowlist_missing))
    print(f"db_terms_hidden_in_demo_mode: {len(hidden_in_demo)}")
    if hidden_in_demo:
        print("  " + ", ".join(hidden_in_demo[:80]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
