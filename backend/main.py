"""
backend/main.py — 삼선뉴스 FastAPI 서버

프론트(토스 미니앱)에서 오는 모든 HTTP 요청을 받아서
Supabase DB 조회, pgvector RAG 추천, 검색 결과를 돌려주는 백엔드 서버.
Railway에 배포되어 24시간 돌아간다.
"""

import logging
import os
from datetime import datetime, timezone, timedelta

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from supabase import create_client

from backend.embedder import make_embedding
from config import get_settings

_settings = get_settings()
logging.basicConfig(level=getattr(logging, _settings.log_level.upper(), logging.INFO))

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=_settings.cors_origins_list(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_sb_key = os.getenv("SUPABASE_KEY") or _settings.supabase_anon_key
sb = create_client(_settings.supabase_url, _sb_key)
ARTICLES_TABLE = _settings.articles_table


class OnboardingRequest(BaseModel):
    user_id: str
    interest_tags: list[str]


class ArticleRequest(BaseModel):
    articles: list[dict]


class LlmTextRequest(BaseModel):
    """번역·요약 API 공통 본문."""
    text: str
    summary_sentences: int | None = None


@app.post("/onboarding")
def onboarding(req: OnboardingRequest):
    """
    유저가 처음 앱을 열고 관심 주제를 선택했을 때 호출된다.
    관심 주제를 벡터로 변환해서 users 테이블에 저장한다.
    이 벡터가 나중에 /feed에서 기사 추천의 기준이 된다.
    """
    combined = " ".join(req.interest_tags)
    user_vector = make_embedding(combined)

    sb.table("users").upsert({
        "user_id": req.user_id,
        "interest_tags": req.interest_tags,
        "user_vector": user_vector,
    }).execute()

    return {"message": "온보딩 완료!"}


@app.get("/feed/{user_id}")
def get_feed(user_id: str, top_k: int = 10):
    """
    유저 맞춤 기사 피드를 돌려준다. RAG 추천의 핵심 엔드포인트.
    """
    result = sb.table("users").select("user_vector").eq("user_id", user_id).execute()

    if not result.data:
        raise HTTPException(status_code=404, detail="유저 없음")

    user_vector = result.data[0]["user_vector"]

    result = sb.rpc("match_articles", {
        "query_vector": user_vector,
        "top_k": top_k,
    }).execute()

    return {"feed": result.data}


@app.get("/articles")
def get_articles(
    category: str | None = None,
    source: str | None = None,
    source_type: str | None = None,
    limit: int = 50,
    offset: int = 0,
    is_breaking: bool | None = None,
):
    """
    HomePage, CategoryPage 등에서 기사 목록을 가져올 때 호출된다.
    """
    query = sb.table(ARTICLES_TABLE).select(
        "url_hash, url, title, source, source_type, category, country, "
        "keywords, published_at, collected_at, content, "
        "credibility_score, fact_label, "
        "translation, summary_formal, summary_casual"
    )

    if category:
        query = query.eq("category", category)
    if source:
        query = query.eq("source", source)
    if source_type:
        query = query.eq("source_type", source_type)

    query = query.order("published_at", desc=True).range(offset, offset + limit - 1)
    result = query.execute()
    return result.data


@app.get("/article/{url_hash}")
def get_article(url_hash: str):
    """
    DetailPage에서 기사 하나의 전체 내용을 가져올 때 호출된다.
    """
    result = sb.table(ARTICLES_TABLE).select("*").eq("url_hash", url_hash).execute()

    if not result.data:
        raise HTTPException(status_code=404, detail="기사 없음")

    return result.data[0]


@app.post("/articles")
def save_articles_endpoint(req: ArticleRequest):
    """
    파이프라인(이동우님)이 번역/요약을 완료한 기사들을 DB에 저장할 때 호출된다.
    """
    from backend.save_articles import save_articles as db_save

    count = db_save(req.articles)
    return {"message": f"{count}개 기사 저장 완료!"}


@app.get("/search")
def search(q: str, top_k: int = 10):
    """
    SearchPage에서 자연어 검색을 할 때 호출된다.
    """
    query_vector = make_embedding(q)

    result = sb.rpc("match_articles", {
        "query_vector": query_vector,
        "top_k": top_k,
    }).execute()

    return {"results": result.data}


@app.get("/health")
def health():
    """
    서버 생존 확인. Railway 모니터링 등에 사용.
    """
    return {"status": "ok"}


@app.post("/translate")
def translate(req: LlmTextRequest):
    """
    영문 원문을 한국어로 번역합니다 (Ollama `qwen3.5:4b`, `pipeline.translate_summarize`).
    응답은 translation 필드만 채웁니다.
    """
    from backend.llm_dispatch import translate_and_summarize_dispatch

    out = translate_and_summarize_dispatch(req.text, req.summary_sentences)
    return {"translation": out.get("translation", "")}


@app.post("/summarize")
def summarize(req: LlmTextRequest):
    """
    원문에 대해 격식체·일상체 요약을 생성합니다 (동일 단일 LLM 호출의 요약 필드만 반환).
    """
    from backend.llm_dispatch import translate_and_summarize_dispatch

    out = translate_and_summarize_dispatch(req.text, req.summary_sentences)
    return {
        "summary_formal": out.get("summary_formal", ""),
        "summary_casual": out.get("summary_casual", ""),
    }

@app.post("/article-view/{user_id}/{url_hash}")
def record_article_view(user_id: str, url_hash: str):
    # 1. 클릭한 기사 임베딩 가져오기
    article_res = sb.table(ARTICLES_TABLE).select("embedding").eq("url_hash", url_hash).execute()
    if not article_res.data or not article_res.data[0].get("embedding"):
        return {"message": "embedding 없음 — 스킵"}
    article_vector = article_res.data[0]["embedding"]

    # 2. 유저 벡터 가져오기
    user_res = sb.table("users").select("user_vector").eq("user_id", user_id).execute()
    if not user_res.data or not user_res.data[0].get("user_vector"):
        return {"message": "유저 없음 — 스킵"}
    user_vector = user_res.data[0]["user_vector"]

    # 3. 유저 벡터 업데이트 (클릭 기사 임베딩 40% 반영)
    # 문자열로 저장된 경우 리스트로 변환
    import json
    if isinstance(article_vector, str):
        article_vector = json.loads(article_vector)
    if isinstance(user_vector, str):
        user_vector = json.loads(user_vector)
    new_vector = [u * 0.6 + a * 0.4 for u, a in zip(user_vector, article_vector)]

    # 4. users 테이블 업데이트
    sb.table("users").update({"user_vector": new_vector}).eq("user_id", user_id).execute()

    return {"message": "조회 기록 완료"}


@app.get("/absence-summary/{user_id}")
def absence_summary(user_id: str, top_k: int = 5):
    """
    유저가 오랫동안 접속하지 않았을 때 놓친 기사 요약을 반환한다.
    부재 기간에 따라 가져오는 기간과 메시지가 달라진다.
      - 1일   → 어제 놓친 기사
      - 2~6일 → 부재 기간 전체
      - 7일+  → 최근 7일치 (상한선)
    마지막으로 last_seen_at을 현재 시각으로 업데이트한다.
    """
    now = datetime.now(timezone.utc)

    # 1. 유저 정보 조회
    user_res = sb.table("users").select("user_vector, last_seen_at").eq("user_id", user_id).execute()
    if not user_res.data:
        return {"show": False}

    user_data   = user_res.data[0]
    user_vector = user_data.get("user_vector")
    last_seen   = user_data.get("last_seen_at")

    # last_seen_at 업데이트 (공통)
    def update_last_seen():
        sb.table("users").update({"last_seen_at": now.isoformat()}).eq("user_id", user_id).execute()

    # 처음 방문이거나 벡터 없으면 기록만 하고 종료
    if not user_vector or not last_seen:
        update_last_seen()
        return {"show": False}

    # 2. 부재 기간 계산
    try:
        last_seen_dt = datetime.fromisoformat(last_seen.replace("Z", "+00:00"))
    except ValueError:
        update_last_seen()
        return {"show": False}

    days_away = (now - last_seen_dt).days

    # 하루도 안 지났으면 표시 안 함
    if days_away < 1:
        update_last_seen()
        return {"show": False}

    # 3. 부재 기간별 fetch 범위 & 메시지 결정
    if days_away == 1:
        fetch_days = 1
        message    = "어제 놓친 기사예요!"
    elif days_away <= 6:
        fetch_days = days_away
        message    = f"{days_away}일간 놓친 기사예요!"
    elif days_away < 30:
        fetch_days = days_away #7(테스트용으로 수정함)
        message    = f"{days_away}일 만에 오셨네요! 최근 1주일 주요 기사예요"
    else:
        fetch_days = days_away #7(테스트용으로 수정함)
        message    = "오랫동안 안 오셨네요! 최근 주요 기사만 추려봤어요"

    since_date = (now - timedelta(days=fetch_days)).isoformat()

    # 4. RAG 검색
    articles_res = sb.rpc("match_articles_since", {
        "query_vector": user_vector,
        "since_date":   since_date,
        "top_k":        top_k,
    }).execute()

    if not articles_res.data:
        return {"show": False}

    return {
        "show":      True,
        "message":   message,
        "days_away": days_away,
        "articles":  articles_res.data,
    }


@app.post("/user-seen/{user_id}")
def user_seen(user_id: str):
    """
    유저가 부재중 알림을 확인('확인했어요' 버튼)했을 때 호출.
    last_seen_at을 현재 시각으로 업데이트한다.
    """
    now = datetime.now(timezone.utc)
    sb.table("users").update({"last_seen_at": now.isoformat()}).eq("user_id", user_id).execute()
    return {"message": "last_seen_at 업데이트 완료"}