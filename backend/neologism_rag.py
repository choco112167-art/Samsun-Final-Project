"""
backend/neologism_rag.py — 신조어 벡터 검색 + Term(음차, 설명) 포맷

feat/mingyu 브랜치 로직을 통합했습니다.

흐름:
  1) 후보 영문 용어 추출 (제목+본문)
  2) 각 후보에 대해 `make_embedding` (local: qwen3-embedding:0.6b / cloud: OpenRouter 동일 차원) → 1024차원
  3) Supabase RPC `match_neologisms` 로 유사도 ≥ threshold 인 행 조회
  4) 매칭된 항목을 \"Term(ko_suggestion, explanation)\" 형태로 묶어 번역 프롬프트 상단에 주입

미매칭 용어에 대한 Gemini 검색은 배치 번역 비용·지연을 막기 위해 기본 비활성.
  환경변수 NEOLOGISM_PIPELINE_GEMINI=1 일 때만 `explain_neologism()` 전체 파이프라인 사용 가능.

필수 DB 객체:
  - `neologisms.embedding` VECTOR(1024)
  - 함수 `match_neologisms(query_vector, match_threshold, top_k)`
  → `backend/sql/neologisms_pgvector.sql` 실행 후 사용.

환경변수:
  NEOLOGISM_RAG_ENABLED   기본 1 — 0 이면 용어집 블록 비생성
  NEOLOGISM_SIM_THRESHOLD 기본 0.85 — RPC 매칭 최소 코사인 유사도
  NEOLOGISM_PIPELINE_GEMINI 기본 0 — 파이프라인 중 Gemini 신규 생성 여부
"""

from __future__ import annotations

import logging
import os
import re
import time
from typing import Any

from dotenv import load_dotenv
from supabase import Client, create_client

from backend.embedder import make_embedding
from config import get_settings
from pipeline.utils import extract_loose_json_object

load_dotenv()

logger = logging.getLogger(__name__)

SIMILARITY_THRESHOLD = float(os.getenv("NEOLOGISM_SIM_THRESHOLD", "0.85"))
GEMINI_MODEL = os.getenv("NEOLOGISM_GEMINI_MODEL", "gemini-2.5-flash")
GEMINI_MAX_RETRY = int(os.getenv("NEOLOGISM_GEMINI_MAX_RETRY", "2"))
GEMINI_RATE_LIMIT_RETRY = int(os.getenv("NEOLOGISM_GEMINI_RL_RETRY", "3"))
GEMINI_RATE_LIMIT_MAX_WAIT = float(os.getenv("NEOLOGISM_GEMINI_RL_MAX_WAIT", "60"))
DEFAULT_SOURCE = "gemini-search-grounding"

_PROMPT_TEMPLATE = (
    "{term}은 AI/기술 분야 신조어입니다.\n"
    "1. 한국어 음차 표기 (예: Mamba → 맘바)\n"
    "2. 한 줄 설명 (30자 이내, 한국어)\n"
    '위 두 가지만 JSON으로 반환: {{"ko": ..., "explanation": ...}}'
)

try:
    from google import genai
    from google.genai import types

    _GENAI_AVAILABLE = True
except ImportError:
    _GENAI_AVAILABLE = False


_settings = get_settings()
_sb_key = os.getenv("SUPABASE_KEY") or os.getenv("SUPABASE_ANON_KEY") or _settings.effective_supabase_key
_sb: Client | None = (
    create_client((_settings.supabase_url or os.getenv("SUPABASE_URL", "")).rstrip("/"), _sb_key)
    if ((_settings.supabase_url or os.getenv("SUPABASE_URL", "")).strip() and _sb_key)
    else None
)

_gemini_client = None


def _get_gemini_client():
    global _gemini_client
    if _gemini_client is not None:
        return _gemini_client
    if not _GENAI_AVAILABLE:
        return None
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        return None
    _gemini_client = genai.Client(api_key=api_key)
    return _gemini_client


def _format(term: str, ko: str, explanation: str) -> str:
    ko = (ko or term).strip()
    explanation = (explanation or "").strip()
    if not explanation:
        return f"{term}({ko})"
    return f"{term}({ko}, {explanation})"


def _extract_candidate_terms(blob: str, max_terms: int = 18) -> list[str]:
    """영문 제목·본문에서 고유명사·약어 후보 추출 (중복 제거)."""
    if not blob:
        return []
    seen: set[str] = set()
    out: list[str] = []

    # Title Case 구절 (예: Blackwell Ultra, Open AI Tool)
    for m in re.finditer(
        r"\b(?:[A-Z][a-z0-9]+(?:\s+[A-Z][a-z0-9]+){0,3})\b",
        blob,
    ):
        t = m.group(0).strip()
        key = t.lower()
        if len(t) >= 3 and key not in seen:
            seen.add(key)
            out.append(t)

    # 약어·버전 (GPT-4, Llama-3.1, RLHF)
    for m in re.finditer(
        r"\b[A-Z]{2,}(?:-\d+(?:\.\d+)?)?[a-zA-Z0-9]*\b|\b[A-Za-z]+-\d+(?:\.\d+)?\b",
        blob,
    ):
        t = m.group(0).strip()
        key = t.lower()
        if len(t) >= 2 and key not in seen:
            seen.add(key)
            out.append(t)
        if len(out) >= max_terms:
            break

    return out[:max_terms]


def _rpc_match(embedding: list[float]) -> dict[str, Any] | None:
    if _sb is None:
        return None
    if len(embedding) != 1024:
        logger.warning("embedding 차원 불일치: %s (기대 1024)", len(embedding))
        return None
    try:
        res = _sb.rpc(
            "match_neologisms",
            {
                "query_vector": embedding,
                "match_threshold": SIMILARITY_THRESHOLD,
                "top_k": 1,
            },
        ).execute()
    except Exception as e:
        logger.debug("match_neologisms RPC 미구현 또는 오류 — 건너뜀: %s", e)
        return None
    if not res.data:
        return None
    return res.data[0]


def lookup_neologism_row(term: str) -> dict[str, Any] | None:
    """단일 용어 임베딩 후 벡터 검색."""
    term = (term or "").strip()
    if not term:
        return None
    try:
        vec = make_embedding(term)
    except Exception as e:
        logger.warning("임베딩 실패 (%s): %s", term, e)
        return None
    return _rpc_match(vec)


def _extract_sources(response) -> list[str]:
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
    s = str(err)
    return "429" in s or "RESOURCE_EXHAUSTED" in s


def _parse_retry_delay(err: Exception, default: float = 30.0) -> float:
    s = str(err)
    m = re.search(r"retryDelay['\"]?\s*:\s*['\"]?(\d+(?:\.\d+)?)s", s)
    wait = float(m.group(1)) if m else default
    return min(wait + 1.0, GEMINI_RATE_LIMIT_MAX_WAIT)


def _generate_via_gemini(term: str) -> tuple[str, str, list[str]]:
    if not _GENAI_AVAILABLE:
        return term, "", []
    client = _get_gemini_client()
    if client is None:
        return term, "", []

    prompt = _PROMPT_TEMPLATE.format(term=term)
    attempt = 0
    rate_limit_retries = 0

    while attempt < GEMINI_MAX_RETRY:
        try:
            cfg_kwargs = dict(
                temperature=0.2,
                max_output_tokens=256,
                tools=[types.Tool(google_search=types.GoogleSearch())],
            )
            try:
                gen_cfg = types.GenerateContentConfig(
                    **cfg_kwargs,
                    thinking_config=types.ThinkingConfig(thinking_budget=0),
                )
            except Exception:
                gen_cfg = types.GenerateContentConfig(**cfg_kwargs)
            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=prompt,
                config=gen_cfg,
            )
        except Exception as e:
            if _is_rate_limit_error(e) and rate_limit_retries < GEMINI_RATE_LIMIT_RETRY:
                wait = _parse_retry_delay(e)
                rate_limit_retries += 1
                logger.warning(
                    "Gemini 429 — %.0fs 대기 후 재시도 (%s)", wait, term[:40],
                )
                time.sleep(wait)
                continue
            logger.error("Gemini 호출 실패 (%s): %s", term, e)
            attempt += 1
            if attempt >= GEMINI_MAX_RETRY:
                return term, "", []
            continue

        obj = extract_loose_json_object(getattr(response, "text", "") or "")
        if not obj:
            attempt += 1
            if attempt >= GEMINI_MAX_RETRY:
                return term, "", _extract_sources(response)
            continue

        ko = str(obj.get("ko") or obj.get("ko_suggestion") or "").strip() or term
        expl = str(obj.get("explanation") or "").strip()
        sources = _extract_sources(response)
        return ko, expl, sources

    return term, "", []


def _upsert_neologism(
    term: str,
    ko_suggestion: str,
    explanation: str,
    embedding: list[float],
    source: str,
) -> None:
    if _sb is None:
        return
    payload: dict[str, Any] = {
        "term": term,
        "ko_suggestion": ko_suggestion or None,
        "explanation": explanation or None,
    }
    if len(embedding) == 1024:
        payload["embedding"] = embedding
    if source:
        payload["source"] = source
    try:
        _sb.table("neologisms").upsert(payload).execute()
    except Exception as e:
        logger.warning("neologisms upsert 실패 (%s): %s", term, e)


def explain_neologism(term: str) -> str:
    """
    신조어 → \"Term(음차, 설명)\" (캐시 → Gemini → upsert).
    CLI·단건 처리용. 파이프라인 배치에서는 비용 때문에 기본 미사용.
    """
    term = (term or "").strip()
    if not term:
        return ""

    try:
        embedding = make_embedding(term)
    except Exception as e:
        logger.error("임베딩 실패 (%s): %s", term, e)
        return term

    hit = _rpc_match(embedding)
    if hit:
        return _format(
            hit.get("term") or term,
            hit.get("ko_suggestion") or "",
            hit.get("explanation") or "",
        )

    ko, expl, urls = _generate_via_gemini(term)
    if expl:
        src = " | ".join(urls[:3]) if urls else DEFAULT_SOURCE
        _upsert_neologism(term, ko, expl, embedding, src)

    return _format(term, ko, expl)


def build_neologism_glossary_prompt_section(title: str, body: str) -> str:
    """
    번역 LLM 에 넣을 신조어 용어집 블록 (영문 원문 기준).

    DB 에 `match_neologisms` + embedding 컬럼이 없으면 빈 문자열 (프롬프트 불변).
    """
    if not _truthy(os.getenv("NEOLOGISM_RAG_ENABLED", "1")):
        return ""

    blob = f"{title or ''}\n{body or ''}"
    candidates = _extract_candidate_terms(blob)
    lines: list[str] = []
    seen_fmt: set[str] = set()

    allow_gemini = _truthy(os.getenv("NEOLOGISM_PIPELINE_GEMINI", "0"))

    for raw in candidates:
        hit = lookup_neologism_row(raw)
        if hit:
            line = _format(
                hit.get("term") or raw,
                hit.get("ko_suggestion") or "",
                hit.get("explanation") or "",
            )
            if line not in seen_fmt:
                seen_fmt.add(line)
                lines.append(line)
            continue

        if allow_gemini:
            line = explain_neologism(raw)
            if line and line not in seen_fmt:
                seen_fmt.add(line)
                lines.append(line)

    if not lines:
        return ""

    joined = "\n".join(f"- {ln}" for ln in lines)
    return (
        "━━━ NEOLOGISM DATABASE GLOSSARY (verified/cache hits only; "
        "on FIRST mention in Korean use exactly Term(음차, 설명); "
        "later mentions English term alone) ━━━\n"
        f"{joined}\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    )


def _truthy(raw: str) -> bool:
    return raw.strip().lower() not in ("0", "false", "no", "off", "")


if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    q = " ".join(sys.argv[1:]) or "Mamba"
    print(explain_neologism(q))
