"""
backend/neologism_rag.py — Gemini Search Grounding 기반 신조어 RAG

흐름:
  1) term 임베딩(qwen3-embedding:0.6b, Ollama 로컬) 생성
  2) Supabase pgvector 에서 유사도 검색 (cosine, threshold=0.85)
     → 히트 시 캐시된 음차/설명 반환
  3) 미스 시 Gemini 2.5 Flash + Google Search Grounding 단일 호출로
     한국어 음차 + 한 줄 설명(JSON) 생성 (fact_checker/gemini_advisor.py 패턴)
     - 429 RESOURCE_EXHAUSTED 응답 시 retryDelay 파싱 → 자동 대기 후 재시도
  4) neologisms 테이블에 upsert (term, ko_suggestion, explanation,
     embedding, source=grounding 메타데이터 URL)
  5) "Term(음차, 설명)" 형식 문자열 반환

사용 예:
    from backend.neologism_rag import explain_neologism
    print(explain_neologism("Mamba"))
    # → "Mamba(맘바, 선형 복잡도 상태공간 언어모델)"

환경 변수:
  OLLAMA_BASE_URL, OLLAMA_EMBED_MODEL      (backend.embedder 가 사용)
  GEMINI_API_KEY (또는 GOOGLE_API_KEY)     (Gemini 호출)
  SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY  (벡터 DB)

의존 패키지(requirements.txt 참고): google-genai, supabase, ollama

Supabase 스키마 보강: backend/neologism_rag.sql 참고
  - ALTER TABLE neologisms ADD COLUMN embedding VECTOR(1024), source TEXT
  - CREATE FUNCTION match_neologisms(query_vector, match_threshold, top_k)
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from typing import Optional

from dotenv import load_dotenv
from supabase import create_client

from backend.embedder import make_embedding

load_dotenv()

logger = logging.getLogger(__name__)

# ── 튜닝 파라미터 ──────────────────────────────────────────────
SIMILARITY_THRESHOLD:    float = 0.85
GEMINI_MODEL:            str   = "gemini-2.5-flash"
GEMINI_MAX_RETRY:        int   = 2      # JSON 파싱/일반 에러 재시도 예산
GEMINI_RATE_LIMIT_RETRY: int   = 3      # 429 RESOURCE_EXHAUSTED 재시도 횟수
GEMINI_RATE_LIMIT_MAX_WAIT: float = 60.0  # retryDelay 상한 (초) — 무한 대기 방지
DEFAULT_SOURCE:          str   = "gemini-search-grounding"


# ════════════════════════════════════════════════════════════════
# Gemini SDK 동적 임포트 (미설치 시 저장/호출 불가 — explain() 에서 폴백)
# 패턴: fact_checker/gemini_advisor.py 참조
# ════════════════════════════════════════════════════════════════
try:
    from google import genai
    from google.genai import types
    _GENAI_AVAILABLE = True
except ImportError:
    _GENAI_AVAILABLE = False
    logger.warning("google-genai 미설치 — Gemini 호출 시 term 원본만 반환")


# ════════════════════════════════════════════════════════════════
# Supabase 클라이언트 (service role 우선, RLS 우회)
# ════════════════════════════════════════════════════════════════
_SB_URL = os.getenv("SUPABASE_URL", "")
_SB_KEY = (
    os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    or os.getenv("SUPABASE_KEY")
    or os.getenv("SUPABASE_ANON_KEY", "")
)
_sb = create_client(_SB_URL, _SB_KEY) if (_SB_URL and _SB_KEY) else None


# ════════════════════════════════════════════════════════════════
# Gemini 클라이언트 (지연 초기화, 싱글톤)
# ════════════════════════════════════════════════════════════════
_gemini_client = None  # type: ignore[var-annotated]


def _get_gemini_client():
    global _gemini_client
    if _gemini_client is not None:
        return _gemini_client
    if not _GENAI_AVAILABLE:
        return None
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        logger.warning("GEMINI_API_KEY 환경변수 없음 — Gemini 호출 불가")
        return None
    _gemini_client = genai.Client(api_key=api_key)
    return _gemini_client


# ════════════════════════════════════════════════════════════════
# 프롬프트 (요구사항 4번)
# ════════════════════════════════════════════════════════════════
_PROMPT_TEMPLATE = (
    "{term}은 AI/기술 분야 신조어입니다.\n"
    "1. 한국어 음차 표기 (예: Mamba → 맘바)\n"
    "2. 한 줄 설명 (30자 이내, 한국어)\n"
    '위 두 가지만 JSON으로 반환: {{"ko": ..., "explanation": ...}}'
)


# ════════════════════════════════════════════════════════════════
# 1. pgvector 캐시 조회
# ════════════════════════════════════════════════════════════════
def _search_cached(embedding: list[float]) -> Optional[dict]:
    """match_neologisms RPC 로 threshold 이상 캐시 조회."""
    if _sb is None:
        logger.warning("Supabase 미설정 — 캐시 검색 건너뜀")
        return None
    try:
        res = _sb.rpc("match_neologisms", {
            "query_vector":    embedding,
            "match_threshold": SIMILARITY_THRESHOLD,
            "top_k":           1,
        }).execute()
    except Exception as e:
        logger.warning("match_neologisms RPC 실패: %s", e)
        return None

    if not res.data:
        return None
    hit = res.data[0]
    logger.info("캐시 히트 → %s (sim=%.3f)", hit.get("term"), hit.get("similarity", 0))
    return hit


# ════════════════════════════════════════════════════════════════
# 2. Gemini Search Grounding 호출 → (ko, explanation, source)
# ════════════════════════════════════════════════════════════════
def _extract_json(text: str) -> dict:
    """
    Gemini 응답에서 JSON 추출 (gemini_advisor._extract_json 과 동일 정책).
    Grounding 사용 시 JSON 앞뒤 자연어가 붙는 경우가 있어 3단계 폴백.
    """
    cleaned = re.sub(r"```(?:json)?\s*|\s*```", "", text or "").strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    for pattern in (r"\{[\s\S]*\}", r"\{[^{}]*\}"):
        m = re.search(pattern, cleaned)
        if m:
            try:
                return json.loads(m.group())
            except json.JSONDecodeError:
                continue
    return {}


def _extract_sources(response) -> list[str]:
    """Gemini grounding_metadata 에서 근거 URL 목록 추출 (best-effort)."""
    try:
        cand = response.candidates[0]
        gm = getattr(cand, "grounding_metadata", None)
        if gm is None:
            return []
        urls: list[str] = []
        for chunk in getattr(gm, "grounding_chunks", None) or []:
            web = getattr(chunk, "web", None)
            uri = getattr(web, "uri", None) if web else None
            if uri:
                urls.append(uri)
        return urls
    except Exception:
        return []


def _is_rate_limit_error(err: Exception) -> bool:
    """429 RESOURCE_EXHAUSTED 여부."""
    s = str(err)
    return "429" in s or "RESOURCE_EXHAUSTED" in s


def _parse_retry_delay(err: Exception, default: float = 30.0) -> float:
    """
    Gemini 429 에러 메시지에서 retryDelay(초) 추출.
    SDK 가 원본 JSON 을 str() 에 포함하므로 정규식으로 뽑아낸다.
    실패 시 default 반환. 상한은 GEMINI_RATE_LIMIT_MAX_WAIT.
    """
    s = str(err)
    # 패턴 예: "'retryDelay': '29s'" 또는 '"retryDelay":"29s"'
    m = re.search(r"retryDelay['\"]?\s*:\s*['\"]?(\d+(?:\.\d+)?)s", s)
    wait = float(m.group(1)) if m else default
    # +1s 버퍼, 상한 적용
    return min(wait + 1.0, GEMINI_RATE_LIMIT_MAX_WAIT)


def _generate_via_gemini(term: str) -> tuple[str, str, list[str]]:
    """
    Gemini 2.5 Flash + Google Search Grounding 단일 호출.

    재시도 정책:
      - 429 RESOURCE_EXHAUSTED → retryDelay 만큼 sleep 후 재시도
        (GEMINI_RATE_LIMIT_RETRY 회까지, 재시도 예산 별도)
      - 그 외 에러/JSON 파싱 실패 → 즉시 재시도
        (GEMINI_MAX_RETRY 회까지)

    Returns:
        (ko_suggestion, explanation, source_urls)
        모든 재시도 실패 시 (term, "", []) 반환 (파이프라인 중단 방지).
    """
    client = _get_gemini_client()
    if client is None:
        return term, "", []

    prompt = _PROMPT_TEMPLATE.format(term=term)

    attempt = 0
    rate_limit_retries = 0

    while attempt < GEMINI_MAX_RETRY:
        # ── 1) API 호출 ────────────────────────────────────────
        try:
            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.2,
                    max_output_tokens=256,
                    tools=[types.Tool(google_search=types.GoogleSearch())],
                    thinking_config=types.ThinkingConfig(thinking_budget=0),
                ),
            )
        except Exception as e:
            # 429: retryDelay 만큼 sleep 후 attempt 예산 소모 없이 재시도
            if _is_rate_limit_error(e) and rate_limit_retries < GEMINI_RATE_LIMIT_RETRY:
                wait = _parse_retry_delay(e)
                rate_limit_retries += 1
                logger.warning(
                    "Gemini 429 rate limit (term=%s, %d/%d) — %.0fs 대기 후 재시도",
                    term, rate_limit_retries, GEMINI_RATE_LIMIT_RETRY, wait,
                )
                time.sleep(wait)
                continue

            logger.error("Gemini 호출 실패 (term=%s, attempt=%d): %s", term, attempt, e)
            attempt += 1
            if attempt >= GEMINI_MAX_RETRY:
                return term, "", []
            continue

        # ── 2) JSON 파싱 ───────────────────────────────────────
        obj = _extract_json(getattr(response, "text", "") or "")
        if not obj:
            logger.warning("Gemini JSON 파싱 실패 (term=%s, attempt=%d)", term, attempt)
            attempt += 1
            if attempt >= GEMINI_MAX_RETRY:
                return term, "", _extract_sources(response)
            continue

        # ── 3) 성공 ────────────────────────────────────────────
        ko = str(obj.get("ko") or obj.get("ko_suggestion") or "").strip() or term
        expl = str(obj.get("explanation") or "").strip()
        sources = _extract_sources(response)
        return ko, expl, sources

    return term, "", []


# ════════════════════════════════════════════════════════════════
# 3. pgvector 저장 (upsert)
# ════════════════════════════════════════════════════════════════
def _upsert_neologism(
    term: str,
    ko_suggestion: str,
    explanation: str,
    embedding: list[float],
    source: str,
) -> None:
    if _sb is None:
        logger.warning("Supabase 미설정 — upsert 건너뜀: %s", term)
        return
    try:
        _sb.table("neologisms").upsert({
            "term":          term,
            "ko_suggestion": ko_suggestion,
            "explanation":   explanation,
            "embedding":     embedding,
            "source":        source,
        }).execute()
        logger.info("neologisms upsert 완료: %s", term)
    except Exception as e:
        logger.warning("neologisms upsert 실패 (term=%s): %s", term, e)


# ════════════════════════════════════════════════════════════════
# 4. 공개 API
# ════════════════════════════════════════════════════════════════
def explain_neologism(term: str) -> str:
    """
    신조어 → "Term(음차, 설명)" 문자열.

    Args:
        term: 영문 고유명사/신조어 (예: 'Mamba', 'Blackwell Ultra')

    Returns:
        "Mamba(맘바, 선형 복잡도 상태공간 언어모델)" 형태.
        빈 입력이면 빈 문자열 반환.
    """
    term = (term or "").strip()
    if not term:
        return ""

    # 1) 임베딩 (qwen3-embedding:0.6b, 1024차원)
    try:
        embedding = make_embedding(term)
    except Exception as e:
        logger.error("임베딩 실패 (term=%s): %s", term, e)
        return term

    # 2) pgvector 캐시 검색
    cached = _search_cached(embedding)
    if cached:
        return _format(
            cached.get("term", term),
            cached.get("ko_suggestion", ""),
            cached.get("explanation", ""),
        )

    # 3) Gemini + Google Search Grounding 으로 생성
    ko, expl, urls = _generate_via_gemini(term)

    # 4) pgvector 저장 (실패해도 사용자에겐 결과 반환)
    #    단, explanation 이 비어있으면 쓸모없는 캐시 row 가 되므로 저장 스킵
    if expl:
        source = " | ".join(urls[:3]) if urls else DEFAULT_SOURCE
        _upsert_neologism(term, ko, expl, embedding, source)
    else:
        logger.warning("explanation 비어있음 — 캐시 저장 스킵 (term=%s)", term)

    return _format(term, ko, expl)


def _format(term: str, ko: str, explanation: str) -> str:
    ko = (ko or term).strip()
    explanation = (explanation or "").strip()
    if not explanation:
        return f"{term}({ko})"
    return f"{term}({ko}, {explanation})"


# ════════════════════════════════════════════════════════════════
# CLI 테스트: python -m backend.neologism_rag "Mamba"
# ════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    import sys
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )
    query = " ".join(sys.argv[1:]) or "Mamba"
    print(explain_neologism(query))
