"""
backend/main.py — 삼선뉴스 FastAPI 서버

관리/로컬 디버깅용 HTTP 요청을 받아서 Supabase DB 조회,
pgvector RAG 추천, 검색 결과를 돌려주는 보조 서버.
Apps in Toss `.ait` 런타임은 이 서버를 필요로 하지 않는다.

API 응답 형식 (안정성):
  프론트엔드·클라이언트가 필드별로 파싱하므로 엔드포인트마다 바디 형태가 다릅니다.
  (예: GET /articles → 배열 직접, GET /feed → {"feed": [...]}, POST 성공 → {"message": ...})
  호환성 유지를 위해 일괄 {"status","data"} 래핑은 하지 않습니다.
"""

import logging
import os
import re

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict
from supabase import create_client

from backend.embedder import make_embedding, expand_query
from backend.rag import build_personalized_feed, upsert_user_profile
from config import get_settings

_settings = get_settings()
logging.basicConfig(level=getattr(logging, _settings.log_level.upper(), logging.INFO))
logger = logging.getLogger(__name__)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=_settings.cors_origins_list(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_sb_key = (
    os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    or os.getenv("SUPABASE_KEY")
    or os.getenv("SUPABASE_ANON_KEY")
    or _settings.effective_supabase_key
)
_sb_url = (_settings.supabase_url or os.getenv("SUPABASE_URL", "")).rstrip("/")
if _sb_url and _sb_key:
    sb = create_client(_sb_url, _sb_key)
else:
    logger.warning("Supabase env is incomplete. Set SUPABASE_URL and SUPABASE_KEY in root .env.")
    sb = None


def require_supabase():
    if sb is None:
        raise HTTPException(
            status_code=503,
            detail="Supabase is not configured. Set SUPABASE_URL and SUPABASE_KEY.",
        )
    return sb


class OnboardingRequest(BaseModel):
    user_id: str
    interest_tags: list[str]


class ArticleRequest(BaseModel):
    articles: list[dict]


class LlmTextRequest(BaseModel):
    """번역·요약 API 공통 본문."""
    text: str
    summary_sentences: int | None = None


class ArticleResponse(BaseModel):
    """articles 테이블 단건 조회 응답 — 원문 영어는 `title`, 번역 한국어는 `title_ko`."""

    model_config = ConfigDict(extra="allow")

    url_hash: str
    url: str | None = None
    title: str | None = None
    title_ko: str | None = None


@app.post("/onboarding")
def onboarding(req: OnboardingRequest):
    """
    유저가 처음 앱을 열고 관심 주제를 선택했을 때 호출된다.
    관심 주제를 벡터로 변환해서 users 테이블에 저장한다.
    이 벡터가 나중에 /feed에서 기사 추천의 기준이 된다.
    """
    db = require_supabase()
    upsert_user_profile(db, req.user_id, req.interest_tags)
    return {"message": "온보딩 완료!"}


@app.get("/feed/{user_id}")
def get_feed(user_id: str, top_k: int = 10):
    """
    유저 맞춤 기사 피드를 돌려준다. RAG 추천의 핵심 엔드포인트.

    feat/leesangjun: user_logs 기반 최근 읽기 패턴으로 각 기사에 `reason`(추천 이유) 추가.
    """
    try:
        db = require_supabase()
        articles, _interest_tags = build_personalized_feed(db, user_id, top_k=top_k)
    except LookupError:
        raise HTTPException(status_code=404, detail="유저 없음") from None

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
    db = require_supabase()
    query = db.table("articles").select(
        "url_hash, url, title, title_ko, source, source_type, category, country, "
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


@app.get("/article/{url_hash}", response_model=ArticleResponse)
def get_article(url_hash: str):
    """
    DetailPage에서 기사 하나의 전체 내용을 가져올 때 호출된다.
    """
    db = require_supabase()
    result = db.table("articles").select("*").eq("url_hash", url_hash).execute()

    if not result.data:
        raise HTTPException(status_code=404, detail="기사 없음")

    return result.data[0]


SEARCH_ALIASES = {
    "엔비디아": ["nvidia", "gpu", "blackwell", "ai chip", "ai accelerator"],
    "nvidia": ["엔비디아", "gpu", "blackwell", "ai chip", "ai accelerator"],
    "앤트로픽": ["anthropic", "claude"],
    "안트로픽": ["anthropic", "claude"],
    "anthropic": ["앤트로픽", "claude", "클로드"],
    "오픈ai": ["openai", "chatgpt", "gpt"],
    "오픈에이아이": ["openai", "chatgpt", "gpt"],
    "openai": ["오픈AI", "챗GPT", "chatgpt", "gpt"],
    "제미나이": ["gemini", "google", "deepmind"],
    "gemini": ["제미나이", "구글", "deepmind"],
    "반도체": ["semiconductor", "chip", "gpu", "hbm", "nvidia"],
    "칩": ["chip", "semiconductor", "gpu", "ai accelerator"],
    "llm": ["대규모 언어 모델", "large language model", "오픈소스 LLM"],
    "rag": ["retrieval augmented generation", "검색 증강 생성", "vector search", "pgvector"],
    "스타트업": ["startup", "funding", "투자"],
    "투자": ["funding", "investment", "valuation", "startup"],
    "규제": ["regulation", "ai act", "policy", "법안"],
    "오타": ["typo", "misspelling"],
}


def _search_terms(q: str, expanded: str) -> list[str]:
    """Build Korean/English/alias terms for robust keyword fallback."""
    raw_terms: list[str] = [q, expanded]
    for token in re.findall(r"[\w가-힣.+#-]{2,}", f"{q} {expanded}".lower()):
        raw_terms.append(token)
        raw_terms.extend(SEARCH_ALIASES.get(token, []))

    terms: list[str] = []
    seen: set[str] = set()
    for term in raw_terms:
        normalized = re.sub(r"\s+", " ", str(term or "").strip())
        # PostgREST .or_ uses comma separators; skip unsafe fragments.
        if not normalized or "," in normalized or ")" in normalized or "(" in normalized:
            continue
        key = normalized.lower()
        if key not in seen:
            seen.add(key)
            terms.append(normalized)
    return terms[:12]


def _keyword_search_articles(db, cols: str, q: str, expanded: str, top_k: int) -> list[dict]:
    """Keyword fallback over Korean/English title, translation, summaries, and content."""
    rows: list[dict] = []
    for term in _search_terms(q, expanded):
        filters = ",".join(
            f"{field}.ilike.%{term}%"
            for field in (
                "title",
                "title_ko",
                "translation",
                "summary_formal",
                "summary_casual",
                "content",
                "source",
                "category",
            )
        )
        try:
            result = db.table("articles").select(cols).or_(filters).limit(top_k).execute()
            rows.extend(result.data or [])
        except Exception as err:
            logger.debug("keyword search fallback failed for term=%r: %s", term, err)
    return rows


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
      3. 키워드 폴백: 제목(영문·한국어) 또는 번역에 원본 검색어가 포함된 기사 추가
         → 벡터 점수가 낮아도 직접 언급되면 결과에 포함
      4. 중복 제거 후 유사도 내림차순 반환
    """
    if not q.strip():
        return {"results": []}

    COLS = (
        "url_hash, url, title, title_ko, source, source_type, category, country, "
        "keywords, published_at, credibility_score, fact_label, "
        "translation, summary_formal, summary_casual"
    )

    # 1. LLM 쿼리 확장. 실패해도 원본 쿼리로 검색한다.
    expanded = expand_query(q)

    # 2. 벡터 검색. local embedding/Ollama가 꺼져 있어도 키워드 fallback은 반드시 동작한다.
    db = require_supabase()
    seen: dict = {}
    try:
        query_vector = make_embedding(expanded)
        vec_result = db.rpc("match_articles", {
            "query_vector": query_vector,
            "top_k":        top_k * 2,
        }).execute()

        for r in (vec_result.data or []):
            if r.get("similarity", 0) >= threshold:
                seen[r["url_hash"]] = r
    except Exception as err:
        logger.warning("vector search failed; using keyword fallback only: %s", err)

    # 3. 키워드/별칭 폴백: 한국어·영어·흔한 표기 차이를 같이 검색한다.
    for r in _keyword_search_articles(db, COLS, q, expanded, top_k):
        h = r["url_hash"]
        if h not in seen:
            seen[h] = {**r, "similarity": 0.65}  # 키워드 직접 매칭 = 신뢰도 0.65

    results = sorted(seen.values(), key=lambda x: x.get("similarity", 0), reverse=True)
    return {
        "results":        results[:top_k],
        "expanded_query": expanded,
    }


@app.get("/health")
def health():
    """
    서버 생존 확인. 로컬/관리용 모니터링에 사용.
    """
    return {"status": "ok"}


@app.get("/debug")
def debug():
    """Supabase 연결 및 환경변수 확인용 (임시)"""
    import requests as _req
    supabase_url = (_settings.supabase_url or os.getenv("SUPABASE_URL", "")).rstrip("/")
    sb_key = (
        os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
        or os.getenv("SUPABASE_KEY", "")
        or os.getenv("SUPABASE_ANON_KEY", "")
        or _settings.effective_supabase_key
    )

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
        if sb is None:
            raise RuntimeError("Supabase client is not configured")
        sb.table("articles").select("url_hash").limit(1).execute()
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
    영문 원문을 한국어로 번역합니다 (`MODEL_NAME` 기본: Gemma 4 E4B fine-tuned, `pipeline.translate_summarize`).
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
    db = require_supabase()
    db.table("user_logs").insert({
        "user_id": user_id,
        "url_hash": url_hash,
        "action": "view",
    }).execute()
    return {"message": "조회 기록 완료"}


# ── 부재 기간 놓친 기사 요약 알림 (feat/soomin) ─────────────────
@app.get("/absence-summary/{user_id}")
@app.get("/api/users/{user_id}/absence-summary")
def absence_summary(user_id: str, top_k: int = 5):
    """마지막 접속 이후 맞춤 유사 기사 목록 (경로 두 종류 동일 처리)."""
    from backend.absence_summary import compute_absence_summary

    return compute_absence_summary(require_supabase(), user_id, top_k=top_k)


@app.post("/user-seen/{user_id}")
@app.post("/api/users/{user_id}/seen")
def user_seen(user_id: str):
    """부재 알림 확인 시 last_seen_at 갱신."""
    from backend.absence_summary import mark_user_seen

    mark_user_seen(require_supabase(), user_id)
    return {"message": "last_seen_at 업데이트 완료"}


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
        "url_hash, url, title, title_ko, source, source_type, category, country, "
        "keywords, published_at, credibility_score, fact_label, "
        "translation, summary_formal, summary_casual"
    )

    # 해당 날짜 조회 기록 집계
    db = require_supabase()
    logs = (
        db.table("user_logs")
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
            a = db.table("articles").select(cols).eq("url_hash", url_hash).execute()
            if a.data:
                result.append({**a.data[0], "view_count": counts[url_hash]})
        return result
    else:
        # 조회 기록 없으면 해당 날짜 발행 기사 반환
        result = (
            db.table("articles")
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
def log_view(
    user_id: str = Query(..., description="유저 ID"),
    url_hash: str = Query(..., description="기사 url_hash"),
):
    db = require_supabase()
    db.table("user_logs").insert({
        "user_id": user_id,
        "url_hash": url_hash,
        "action": "view",
    }).execute()
    return {"message": "기록 완료"}


# ── 프론트엔드 정적 파일 서빙 (SPA) ────────────────────────
# API 라우트 정의 후 맨 마지막에 마운트해야 API가 우선됨
_DIST = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "frontend", "dist")
_DIST_WEB = os.path.join(_DIST, "web")
_STATIC_ROOT = _DIST_WEB if os.path.isfile(os.path.join(_DIST_WEB, "index.html")) else _DIST
_ASSETS_DIR = os.path.join(_STATIC_ROOT, "assets")
if os.path.isfile(os.path.join(_STATIC_ROOT, "index.html")):
    if os.path.isdir(_ASSETS_DIR):
        app.mount("/assets", StaticFiles(directory=_ASSETS_DIR), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def serve_spa(full_path: str = ""):
        """React SPA — 모든 미매칭 경로를 index.html로 돌려줌"""
        return FileResponse(os.path.join(_STATIC_ROOT, "index.html"))
