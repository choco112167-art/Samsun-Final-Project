"""
backend/embedder.py — 임베딩 어댑터

MODE=local  → Ollama 로컬 (개발 중)
MODE=cloud  → OpenRouter API (배포 시)

.env에서 MODE 한 줄만 바꾸면 전체 전환됩니다.
"""

import logging
import os
from pathlib import Path

from dotenv import load_dotenv

_repo_root = Path(__file__).resolve().parents[1]
# README 기준 backend/.env + 루트 .env (중복 키는 먼저 로드된 값 유지)
load_dotenv(_repo_root / "backend" / ".env")
load_dotenv(_repo_root / ".env")

logger = logging.getLogger(__name__)

EMBEDDING_PROVIDER = os.getenv("EMBEDDING_PROVIDER") or os.getenv("MODE", "local")


# ════════════════════════════════════════════
# LOCAL — Ollama (개발 환경)
# 사용: MODE=local
# 준비: ollama pull qwen3-embedding:0.6b
# ════════════════════════════════════════════

def _embed_local(text: str) -> list[float]:
    # ollama 라이브러리로 직접 호출 (HTTP 요청보다 안정적)
    import ollama
    resp = ollama.embeddings(
        model="qwen3-embedding:0.6b",
        prompt=text,
    )
    return resp["embedding"][:1024]


# ════════════════════════════════════════════
# CLOUD — OpenRouter Embedding API (배포 환경)
# 사용: MODE=cloud
# 준비: .env에 OPENROUTER_API_KEY 설정
# ════════════════════════════════════════════

def _embed_cloud(text: str) -> list[float]:
    import requests, time
    api_key = os.getenv("OPENROUTER_API_KEY", "")
    for attempt in range(3):
        resp = requests.post(
            "https://openrouter.ai/api/v1/embeddings",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type":  "application/json",
            },
            json={
                "model": "qwen/qwen3-embedding-4b",
                "input": text,
            },
            timeout=30,
        )
        body = resp.json()
        if "data" in body:
            logger.info(
                "OpenRouter embedding ok (attempt %s, dim=%s)",
                attempt + 1,
                len(body["data"][0]["embedding"]),
            )
            return body["data"][0]["embedding"][:1024]
        # 429 rate limit 또는 일시 오류 → 재시도
        if attempt < 2:
            time.sleep(2 ** attempt)
    logger.warning("OpenRouter embedding failed after retries: %s", body)
    raise RuntimeError(f"OpenRouter 임베딩 실패: {body}")


# ════════════════════════════════════════════
# QUERY EXPANSION — LLM으로 검색어 확장
# 한국어 짧은 쿼리 → 한/영 풍부한 키워드로 변환
# ════════════════════════════════════════════

def expand_query(q: str) -> str:
    """
    LLM(OpenRouter)을 이용해 검색어를 확장한다.
    예: "엔비디아" → "엔비디아 NVIDIA GPU 반도체 AI가속기 블랙웰 H100 데이터센터"

    EMBEDDING_PROVIDER/MODE=local이거나 실패하면 원본 쿼리를 그대로 반환.
    """
    if EMBEDDING_PROVIDER not in ("cloud", "openrouter"):
        logger.debug(
            "expand_query skipped (EMBEDDING_PROVIDER=%r not cloud)",
            EMBEDDING_PROVIDER,
        )
        return q

    import requests
    api_key = os.getenv("OPENROUTER_API_KEY", "")
    if not api_key:
        logger.warning("expand_query skipped: OPENROUTER_API_KEY is empty")
        return q

    system = (
        "You expand user search queries into indexing keywords. "
        "Output NOTHING except one single line of keywords. "
        "No greetings, no explanations, no labels (e.g. do not write 'Keywords:', 'Here:', 'Output:'). "
        "No bullet points, numbering, quotes, or markdown. "
        "8-12 unique Korean and/or English terms, space-separated only."
    )
    user_prompt = (
        "Turn the following user query into keywords for an AI/tech news search.\n\n"
        f"Query: {q}\n\n"
        "Respond with exactly one line: space-separated keywords only."
    )

    try:
        resp = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type":  "application/json",
            },
            json={
                "model":      "meta-llama/llama-3.1-8b-instruct",
                "messages":   [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user_prompt},
                ],
                "max_tokens": 120,
                "temperature": 0.1,
            },
            timeout=10,
        )
        body = resp.json()
        raw = (body["choices"][0]["message"]["content"] or "").strip()
        # 한 줄만 사용 (모델이 여러 줄 안내를 붙인 경우)
        expanded = raw.splitlines()[0].strip() if raw else ""

        prefixes = (
            "keywords:",
            "keyword:",
            "출력:",
            "결과:",
            "expanded:",
            "expanded query:",
            "검색어:",
            "키워드:",
            "here are the keywords:",
            "here are keywords:",
            "here are",
            "here is",
            "output:",
            "sure!",
            "okay!",
        )
        changed = True
        while expanded and changed:
            changed = False
            expanded = expanded.strip()
            el = expanded.lower()
            for p in prefixes:
                pl = p.lower()
                if el.startswith(pl):
                    expanded = expanded[len(pl) :].strip().strip(":\"'-, ")
                    changed = True
                    break
        out = f"{q} {expanded}".strip()
        logger.info(
            "expand_query: LLM ok (chars in=%s out=%s preview=%s)",
            len(q),
            len(out),
            (out[:120] + "…") if len(out) > 120 else out,
        )
        return out
    except Exception as exc:
        logger.warning("expand_query: LLM failed, using raw query: %s", exc)
        return q


# ════════════════════════════════════════════
# 공개 인터페이스 — 이것만 import해서 쓰세요
# ════════════════════════════════════════════

def make_embedding(text: str) -> list[float]:
    """
    텍스트 → 임베딩 벡터 (1024차원)

    .env의 EMBEDDING_PROVIDER 값으로 전환:
      local      → Ollama qwen3-embedding:0.6b
      openrouter → OpenRouter qwen/qwen3-embedding-4b
    """
    if EMBEDDING_PROVIDER in ("cloud", "openrouter"):
        return _embed_cloud(text)
    return _embed_local(text)
