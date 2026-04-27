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
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from supabase import create_client

from backend.embedder import make_embedding, expand_query
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
    query = sb.table("articles").select(
        "url_hash, url, title, title_en, source, source_type, category, country, "
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
def search(q: str, top_k: int = 10, threshold: float = 0.4):
    """
    하이브리드 검색: LLM 쿼리 확장 벡터 검색 + 키워드 폴백.

    흐름:
      1. LLM으로 쿼리를 한/영 키워드로 확장 (예: "엔비디아" → "엔비디아 NVIDIA GPU ...")
      2. 확장 쿼리 임베딩 → pgvector 유사도 검색 (threshold 0.4 이상만)
      3. 키워드 폴백: 제목(영문) 또는 번역(한국어)에 원본 검색어가 포함된 기사 추가
         → 벡터 점수가 낮아도 직접 언급되면 결과에 포함
      4. 중복 제거 후 유사도 내림차순 반환
    """
    if not q.strip():
        return {"results": []}

    COLS = (
        "url_hash, url, title, source, source_type, category, country, "
        "keywords, published_at, credibility_score, fact_label, "
        "translation, summary_formal, summary_casual"
    )

    # 1. LLM 쿼리 확장
    expanded = expand_query(q)

    # 2. 벡터 검색
    query_vector = make_embedding(expanded)
    vec_result = sb.rpc("match_articles", {
        "query_vector": query_vector,
        "top_k":        top_k * 2,
    }).execute()

    seen: dict = {}
    for r in (vec_result.data or []):
        if r.get("similarity", 0) >= threshold:
            seen[r["url_hash"]] = r

    # 3. 키워드 폴백: 제목(영문) 또는 한국어 번역에 검색어 포함 여부
    try:
        kw_result = sb.table("articles").select(COLS).or_(
            f"title.ilike.%{q}%,translation.ilike.%{q}%"
        ).limit(top_k).execute()
        for r in (kw_result.data or []):
            h = r["url_hash"]
            if h not in seen:
                seen[h] = {**r, "similarity": 0.65}  # 키워드 직접 매칭 = 신뢰도 0.65
    except Exception:
        pass  # 키워드 검색 실패해도 벡터 결과는 반환

    results = sorted(seen.values(), key=lambda x: x.get("similarity", 0), reverse=True)
    return {
        "results":        results[:top_k],
        "expanded_query": expanded,
    }


@app.get("/health")
def health():
    """
    서버 생존 확인. Railway 모니터링 등에 사용.
    """
    return {"status": "ok"}


@app.get("/debug")
def debug():
    """Supabase 연결 및 환경변수 확인용 (임시)"""
    import requests as _req
    supabase_url = (_settings.supabase_url or os.getenv("SUPABASE_URL", "")).rstrip("/")
    sb_key = os.getenv("SUPABASE_KEY", "") or _settings.supabase_anon_key

    # URL 형식 진단
    url_issues = []
    if "/rest/v1" in supabase_url:
        url_issues.append("URL에 /rest/v1 포함됨 — 제거 필요")
    if supabase_url.count("supabase.co") == 0 and supabase_url:
        url_issues.append("supabase.co 도메인 아님")

    # supabase-py 없이 직접 REST 호출 테스트
    direct_ok = False
    direct_error = ""
    try:
        r = _req.get(
            f"{supabase_url}/rest/v1/articles?select=url_hash&limit=1",
            headers={"apikey": sb_key, "Authorization": f"Bearer {sb_key}"},
            timeout=5,
        )
        direct_ok = r.status_code == 200
        direct_error = "" if direct_ok else f"HTTP {r.status_code}: {r.text[:200]}"
    except Exception as e:
        direct_error = str(e)

    # supabase-py 테스트
    sdk_ok = False
    sdk_error = ""
    try:
        result = sb.table("articles").select("url_hash").limit(1).execute()
        sdk_ok = True
    except Exception as e:
        sdk_error = str(e)[:300]

    dist_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "frontend", "dist")
    dist_abs = os.path.abspath(dist_path)
    index_exists = os.path.isfile(os.path.join(dist_abs, "index.html"))

    return {
        "supabase_url": supabase_url[:60],
        "url_issues": url_issues,
        "key_prefix": sb_key[:15] if sb_key else "",
        "key_length": len(sb_key),
        "direct_rest_ok": direct_ok,
        "direct_rest_error": direct_error,
        "sdk_ok": sdk_ok,
        "sdk_error": sdk_error,
        "dist_path": dist_abs,
        "dist_exists": os.path.isdir(dist_abs),
        "index_html_exists": index_exists,
        "app_dir": os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")),
    }


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
    """프론트에서 기사 카드 조회 시 호출 — user_logs에 적재."""
    sb.table("user_logs").insert({
        "user_id": user_id,
        "url_hash": url_hash,
        "action": "view",
    }).execute()
    return {"message": "조회 기록 완료"}


# ── 날짜별 핫이슈 ─────────────────────────────────────────────
@app.get("/hot/{date}")
def get_hot(date: str, top_k: int = 5):
    """
    date: YYYY-MM-DD 형식
    해당 날짜의 조회수 TOP5 기사 반환.
    조회 기록 없으면 해당 날짜 발행 기사 반환.
    """
    from collections import Counter
    start = f"{date}T00:00:00+00:00"
    end   = f"{date}T23:59:59+00:00"

    cols = (
        "url_hash, url, title, source, source_type, category, country, "
        "keywords, published_at, credibility_score, fact_label, "
        "translation, summary_formal, summary_casual"
    )

    # 해당 날짜 조회 기록 집계
    logs = (
        sb.table("user_logs")
        .select("url_hash")
        .eq("action", "view")
        .gte("created_at", start)
        .lte("created_at", end)
        .execute()
    )

    if logs.data:
        counts = Counter(r["url_hash"] for r in logs.data)
        top_hashes = [h for h, _ in counts.most_common(top_k)]
        result = []
        for url_hash in top_hashes:
            a = sb.table("articles").select(cols).eq("url_hash", url_hash).execute()
            if a.data:
                result.append({**a.data[0], "view_count": counts[url_hash]})
        return result
    else:
        # 조회 기록 없으면 해당 날짜 발행 기사 반환
        result = (
            sb.table("articles")
            .select(cols)
            .gte("published_at", start)
            .lte("published_at", end)
            .order("credibility_score", desc=True)
            .limit(top_k)
            .execute()
        )
        return [{**a, "view_count": 0} for a in result.data]


# ── 로그 직접 기록 (대안 엔드포인트) ────────────────────────
@app.post("/logs/view")
def log_view(user_id: str, url_hash: str):
    sb.table("user_logs").insert({
        "user_id": user_id,
        "url_hash": url_hash,
        "action": "view",
    }).execute()
    return {"message": "기록 완료"}


# ── 프론트엔드 정적 파일 서빙 (SPA) ────────────────────────
# API 라우트 정의 후 맨 마지막에 마운트해야 API가 우선됨
_DIST = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "frontend", "dist")
if os.path.isdir(_DIST):
    app.mount("/assets", StaticFiles(directory=os.path.join(_DIST, "assets")), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def serve_spa(full_path: str = ""):
        """React SPA — 모든 미매칭 경로를 index.html로 돌려줌"""
        return FileResponse(os.path.join(_DIST, "index.html"))
