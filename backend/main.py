"""
backend/main.py — 삼선뉴스 FastAPI 서버

프론트(토스 미니앱)에서 오는 모든 HTTP 요청을 받아서
Supabase DB 조회, pgvector RAG 추천, 검색 결과를 돌려주는 백엔드 서버.
Railway에 배포되어 24시간 돌아간다.
"""

import logging
import os

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
    유저 맞춤 기사 피드를 돌려준다. 추천 이유도 함께 생성.
    """
    # 유저 벡터 조회
    result = sb.table("users").select("user_vector, interest_tags").eq("user_id", user_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="유저 없음")

    user_vector = result.data[0]["user_vector"]
    interest_tags = result.data[0].get("interest_tags", [])

    # 유저 최근 클릭 기사 카테고리/키워드 조회 (최근 10개)
    logs = sb.table("user_logs").select("url_hash").eq("user_id", user_id).order("created_at", desc=True).limit(10).execute()
    recent_keywords = []
    if logs.data:
        recent_hashes = [l["url_hash"] for l in logs.data]
        recent_articles = sb.table("articles").select("category, keywords").in_("url_hash", recent_hashes).execute()
        for a in recent_articles.data:
            recent_keywords.append(a.get("category", ""))
            recent_keywords.extend(a.get("keywords", []) or [])
    recent_keywords = list(set(filter(None, recent_keywords)))[:10]

    # 벡터 유사도 기반 추천
    result = sb.rpc("match_articles", {
        "query_vector": user_vector,
        "top_k": top_k,
    }).execute()

    articles = result.data

    # 추천 이유 생성 (LLM)
    def make_reason(article: dict) -> str:
        try:
            from backend.embedder import make_embedding  # embedder 재사용 또는 별도 llm 호출
            # 간단한 룰 기반 이유 생성 (LLM 호출 없이 빠르게)
            category = article.get("category", "")
            keywords = article.get("keywords", []) or []
            
            matched = [k for k in keywords if k in recent_keywords]
            if matched:
                return f"최근 관심 키워드 '{matched[0]}'와 관련된 기사예요"
            if category in recent_keywords:
                return f"최근 '{category}' 기사를 많이 읽으셨어요"
            if interest_tags:
                return f"관심 주제 '{interest_tags[0]}'와 연관된 기사예요"
            return "회원님의 읽기 패턴을 분석해 추천했어요"
        except Exception:
            return "회원님의 읽기 패턴을 분석해 추천했어요"

    for article in articles:
        article["reason"] = make_reason(article)

    return {"feed": articles}


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
    query = sb.table("articles").select(
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
    result = sb.table("articles").select("*").eq("url_hash", url_hash).execute()

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


# ── /feed-llm 엔드포인트 ──
# 코랩에서 LLM 실행 시 사용 (코랩 colab_feed_llm.py에서 별도 서버로 운영)
# 로컬에서는 주석 해제하여 사용 가능하나, 모델 로드로 인해 시작이 느려질 수 있음
#
# @app.get("/feed-llm/{user_id}")
# def get_feed_llm(user_id: str):
#     user_res = sb.table("users").select("user_vector, interest_tags").eq("user_id", user_id).execute()
#     if not user_res.data:
#         raise HTTPException(status_code=404, detail="유저 없음")
#     user_vector = user_res.data[0]["user_vector"]
#     interest_tags = user_res.data[0].get("interest_tags", [])
#
#     logs = sb.table("user_logs").select("url_hash").eq("user_id", user_id).order("created_at", desc=True).limit(10).execute()
#     recent_keywords = []
#     if logs.data:
#         recent_hashes = [l["url_hash"] for l in logs.data]
#         recent_articles = sb.table("articles").select("category, keywords").in_("url_hash", recent_hashes).execute()
#         for a in recent_articles.data:
#             recent_keywords.append(a.get("category", ""))
#             recent_keywords.extend(a.get("keywords", []) or [])
#     recent_keywords = list(set(filter(None, recent_keywords)))[:10]
#
#     vec_result = sb.rpc("match_articles", {"query_vector": user_vector, "top_k": 20}).execute()
#     top_articles = vec_result.data
#
#     try:
#         from pipeline.recommend import recommend_articles
#         recommended = recommend_articles(
#             interest_tags=interest_tags,
#             recent_keywords=recent_keywords,
#             articles=top_articles,
#         )
#     except Exception as e:
#         import traceback
#         logging.error(f"LLM 추천 오류: {e}")
#         logging.error(traceback.format_exc())
#         raise HTTPException(status_code=500, detail=str(e))
#
#     return {"feed": recommended}


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
    # 1. user_logs에 클릭 기록 저장
    sb.table("user_logs").insert({
        "user_id": user_id,
        "url_hash": url_hash,
        "action": "view",
    }).execute()

    # 2. 클릭한 기사 임베딩 가져오기
    article_res = sb.table("articles").select("embedding").eq("url_hash", url_hash).execute()
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
