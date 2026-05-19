"""
backend/rag.py — pgvector 기반 맞춤 피드(RAG) 헬퍼

feat/leesangjun 브랜치에서 도입된 로직을 통합하면서 다음 원칙을 지킨다.

1. Supabase 연결은 FastAPI(main.py)와 동일하게 `config.Settings` + 환경변수
   `SUPABASE_URL`, `SUPABASE_KEY`(또는 `SUPABASE_ANON_KEY`)를 사용한다.
2. 유저 임베딩은 기사 임베딩과 **차원이 반드시 같아야** 하므로
   `sentence_transformers`/`mxbai` 등 별도 클라이언트가 아니라
   `backend.embedder.make_embedding` 단일 진입점만 사용한다.
3. user_logs 테이블 기반 최근 읽기 패턴을 활용해 피드 항목마다 `reason` 문자열을 붙인다.

CLI 스모크 테스트:
    cd 프로젝트 루트 && PYTHONPATH=. python -m backend.rag
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any

from dotenv import load_dotenv
from supabase import Client, create_client

from backend.embedder import make_embedding
from config import get_settings

load_dotenv()

_settings = get_settings()
VECTOR_DIM = 1024


def supabase_client() -> Client:
    """main.py 의 `sb` 생성 규칙과 동일."""
    key = (
        os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        or os.getenv("SUPABASE_KEY")
        or os.getenv("SUPABASE_ANON_KEY")
        or _settings.effective_supabase_key
    )
    return create_client(_settings.supabase_url, key)


def upsert_user_profile(sb: Client, user_id: str, interest_tags: list[str]) -> None:
    """온보딩: 관심 태그 → 벡터 → users 테이블 upsert."""
    combined = " ".join(interest_tags)
    user_vector = make_embedding(combined)
    now = datetime.now(timezone.utc).isoformat()
    sb.table("users").upsert({
        "user_id": user_id,
        "interest_tags": interest_tags,
        "user_vector": user_vector,
        "last_seen_at": now,
    }).execute()


def _coerce_vector(raw: Any) -> list[float]:
    if isinstance(raw, str):
        raw = json.loads(raw)
    if not isinstance(raw, list):
        return [0.0] * VECTOR_DIM
    out = [float(v) for v in raw[:VECTOR_DIM]]
    if len(out) < VECTOR_DIM:
        out.extend([0.0] * (VECTOR_DIM - len(out)))
    return out


def blend_vectors(base: list[float], clicked: list[float], click_weight: float = 0.4) -> list[float]:
    """Blend a user's existing interest vector with a clicked article vector."""
    alpha = max(0.0, min(1.0, click_weight))
    base_v = _coerce_vector(base)
    clicked_v = _coerce_vector(clicked)
    return [(1.0 - alpha) * b + alpha * c for b, c in zip(base_v, clicked_v)]


def record_article_click_and_update_vector(sb: Client, user_id: str, url_hash: str) -> None:
    """
    POC for click-based recommendation learning.

    - Records the click in `user_logs`.
    - Fetches `articles.embedding`.
    - Blends it into `users.user_vector`.
    """
    now = datetime.now(timezone.utc).isoformat()
    sb.table("user_logs").insert({
        "user_id": user_id,
        "url_hash": url_hash,
        "action": "view",
        "created_at": now,
    }).execute()

    article = sb.table("articles").select("embedding").eq("url_hash", url_hash).maybe_single().execute()
    article_vector = (article.data or {}).get("embedding")
    if not article_vector:
        return

    user = sb.table("users").select("user_vector, interest_tags").eq("user_id", user_id).maybe_single().execute()
    if not user.data:
        sb.table("users").upsert({
            "user_id": user_id,
            "interest_tags": [],
            "user_vector": _coerce_vector(article_vector),
            "last_seen_at": now,
        }).execute()
        return

    current_vector = _coerce_vector(user.data.get("user_vector"))
    next_vector = blend_vectors(current_vector, _coerce_vector(article_vector))
    sb.table("users").update({
        "user_vector": next_vector,
        "last_seen_at": now,
    }).eq("user_id", user_id).execute()


def rpc_match_feed(sb: Client, user_vector: list[float], top_k: int) -> list[dict[str, Any]]:
    """Supabase RPC `match_articles` — 유저 벡터와 유사한 기사 목록."""
    res = sb.rpc("match_articles", {
        "query_vector": user_vector,
        "top_k": top_k,
    }).execute()
    return list(res.data or [])


def fetch_recommendation_candidates(sb: Client, user_vector: list[float], candidate_k: int = 20) -> list[dict[str, Any]]:
    """Return top-N pgvector candidates before optional reranking."""
    return rpc_match_feed(sb, user_vector, candidate_k)


def recent_keywords_from_logs(
    sb: Client,
    user_id: str,
    log_limit: int = 10,
    kw_limit: int = 10,
) -> list[str]:
    """
    user_logs 에서 최근 본 기사들의 category / keywords 를 모아 추천 이유 생성용으로 반환.
    """
    logs = sb.table("user_logs").select("url_hash").eq(
        "user_id", user_id,
    ).order("created_at", desc=True).limit(log_limit).execute()

    if not logs.data:
        return []

    recent_hashes = [l["url_hash"] for l in logs.data]
    arts = sb.table("articles").select("category, keywords").in_(
        "url_hash", recent_hashes,
    ).execute()

    merged: list[str] = []
    for a in arts.data or []:
        c = a.get("category")
        if c:
            merged.append(c)
        merged.extend(a.get("keywords") or [])

    seen: set[str] = set()
    out: list[str] = []
    for x in merged:
        if x and x not in seen:
            seen.add(x)
            out.append(x)
        if len(out) >= kw_limit:
            break
    return out


def attach_feed_reasons(
    articles: list[dict[str, Any]],
    interest_tags: list[str],
    recent_keywords: list[str],
) -> None:
    """각 기사 dict 에 `reason` 키를 in-place 로 추가한다."""
    tags = interest_tags or []
    recent_keywords = recent_keywords or []

    def make_reason(article: dict[str, Any]) -> str:
        category = article.get("category") or ""
        keywords = article.get("keywords") or []

        matched = [k for k in keywords if k and k in recent_keywords]
        if matched:
            return f"최근 관심 키워드 '{matched[0]}'와 관련된 기사예요"
        if category and category in recent_keywords:
            return f"최근 '{category}' 기사를 많이 읽으셨어요"
        if tags:
            return f"관심 주제 '{tags[0]}'와 연관된 기사예요"
        return "회원님의 읽기 패턴을 분석해 추천했어요"

    for art in articles:
        art["reason"] = make_reason(art)


def rerank_candidates(
    candidates: list[dict[str, Any]],
    interest_tags: list[str],
    recent_keywords: list[str],
    top_k: int,
) -> list[dict[str, Any]]:
    """
    Optional LLM reranking hook.

    Production/demo default is deterministic because the Apps in Toss frontend reads Supabase
    directly. Set RAG_LLM_RERANK_ENABLED=1 with OPENROUTER_API_KEY to use this in the
    local/admin FastAPI server.
    """
    if not candidates:
        return []
    if os.getenv("RAG_LLM_RERANK_ENABLED", "0").strip().lower() not in ("1", "true", "yes", "on"):
        return candidates[:top_k]

    api_key = os.getenv("OPENROUTER_API_KEY", "").strip()
    if not api_key:
        return candidates[:top_k]

    try:
        import requests

        compact = [
            {
                "url_hash": row.get("url_hash"),
                "title_ko": row.get("title_ko") or row.get("title"),
                "category": row.get("category"),
                "summary": row.get("summary_formal"),
                "similarity": row.get("similarity"),
            }
            for row in candidates[:20]
        ]
        prompt = (
            "Rerank these Korean AI news candidates for a user's personalized feed.\n"
            "Return JSON only: {\"url_hashes\": [..]}.\n"
            f"Interest tags: {interest_tags}\n"
            f"Recent keywords: {recent_keywords}\n"
            f"Candidates: {json.dumps(compact, ensure_ascii=False)}"
        )
        resp = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": os.getenv("RAG_RERANK_MODEL", "google/gemini-2.5-flash-lite"),
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.1,
                "max_tokens": 256,
            },
            timeout=12,
        )
        content = resp.json()["choices"][0]["message"]["content"]
        payload = json.loads(content[content.find("{"):content.rfind("}") + 1])
        order = [str(item) for item in payload.get("url_hashes", [])]
        by_hash = {str(row.get("url_hash")): row for row in candidates}
        reranked = [by_hash[h] for h in order if h in by_hash]
        leftovers = [row for row in candidates if str(row.get("url_hash")) not in set(order)]
        return [*reranked, *leftovers][:top_k]
    except Exception:
        return candidates[:top_k]


# 하위 호환: 과거 스크립트에서 `save_user(...)` 호출명 사용
def save_user(sb: Client, user_id: str, interest_tags: list[str]) -> None:
    upsert_user_profile(sb, user_id, interest_tags)


def build_personalized_feed(
    sb: Client,
    user_id: str,
    top_k: int = 10,
) -> tuple[list[dict[str, Any]], list[str]]:
    """
    Returns (articles_with_reason, interest_tags).

    Raises LookupError 유저 레코드가 없을 때 (호출측에서 HTTP 404 로 매핑).
    """
    row = sb.table("users").select(
        "user_vector, interest_tags",
    ).eq("user_id", user_id).execute()

    if not row.data:
        raise LookupError(user_id)

    user_vector = row.data[0]["user_vector"]
    interest_tags = row.data[0].get("interest_tags") or []

    candidates = fetch_recommendation_candidates(sb, user_vector, candidate_k=max(20, top_k))
    recent_kw = recent_keywords_from_logs(sb, user_id)
    articles = rerank_candidates(candidates, interest_tags, recent_kw, top_k)
    attach_feed_reasons(articles, interest_tags, recent_kw)

    return articles, interest_tags


if __name__ == "__main__":
    print(__doc__)
    print("\n스모크: 모듈 임포트 및 클라이언트 생성만 검증합니다.")
    sb = supabase_client()
    print("Supabase URL:", (_settings.supabase_url or "")[:48] + "...")
    print("Client OK:", type(sb).__name__)
