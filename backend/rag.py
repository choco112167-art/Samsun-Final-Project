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

import os
from datetime import datetime, timezone
from typing import Any

from dotenv import load_dotenv
from supabase import Client, create_client

from backend.embedder import make_embedding
from config import get_settings

load_dotenv()

_settings = get_settings()


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


def rpc_match_feed(sb: Client, user_vector: list[float], top_k: int) -> list[dict[str, Any]]:
    """Supabase RPC `match_articles` — 유저 벡터와 유사한 기사 목록."""
    res = sb.rpc("match_articles", {
        "query_vector": user_vector,
        "top_k": top_k,
    }).execute()
    return list(res.data or [])


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

    articles = rpc_match_feed(sb, user_vector, top_k)
    recent_kw = recent_keywords_from_logs(sb, user_id)
    attach_feed_reasons(articles, interest_tags, recent_kw)

    return articles, interest_tags


if __name__ == "__main__":
    print(__doc__)
    print("\n스모크: 모듈 임포트 및 클라이언트 생성만 검증합니다.")
    sb = supabase_client()
    print("Supabase URL:", (_settings.supabase_url or "")[:48] + "...")
    print("Client OK:", type(sb).__name__)
