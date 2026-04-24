"""
backend/embedder.py — 임베딩 어댑터

MODE=local  → Ollama HTTP (OLLAMA_BASE_URL, 기본: qwen3-embedding:0.6b)
MODE=cloud  → OpenRouter Embeddings API

- 로컬 Ollama 실패 시: OPENROUTER_API_KEY가 있으면 OpenRouter 임베딩으로 재시도
- 전부 실패 시: 1024차원 0-벡터 (검색/피드·RPC는 동작, 유사도는 품질 저하)
"""

from __future__ import annotations

import logging
import os
import time
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

MODE = os.getenv("MODE", "local")
EMBED_DIM = 1024
OLLAMA_EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "qwen3-embedding:0.6b")
OPENROUTER_EMBED_MODEL = os.getenv("OPENROUTER_EMBEDDING_MODEL", "qwen/qwen3-embedding-4b")
DEFAULT_OLLAMA_BASE = "http://127.0.0.1:11434"
REF = os.getenv("OPENROUTER_HTTP_REFERER", "https://samsun-production.up.railway.app").strip()


def _ollama_base() -> str:
    return (os.getenv("OLLAMA_BASE_URL") or DEFAULT_OLLAMA_BASE).rstrip("/")


def _openrouter_embed_headers() -> dict[str, str]:
    key = os.getenv("OPENROUTER_API_KEY", "")
    return {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "HTTP-Referer": REF,
    }


def _zero_embedding() -> list[float]:
    return [0.0] * EMBED_DIM


# ════════════════════════════════════════════
# LOCAL — Ollama HTTP (OLLAMA_BASE_URL)
# ════════════════════════════════════════════


def _embed_ollama_http(text: str) -> list[float]:
    import requests

    base = _ollama_base()
    last_err: str | None = None
    for payload in (
        {"model": OLLAMA_EMBED_MODEL, "input": text},
        {"model": OLLAMA_EMBED_MODEL, "prompt": text},
    ):
        r = requests.post(f"{base}/api/embeddings", json=payload, timeout=30)
        if r.status_code != 200:
            last_err = f"HTTP {r.status_code} {r.text[:200]}"
            continue
        data = r.json()
        emb = data.get("embedding")
        if emb and isinstance(emb, list):
            return [float(x) for x in emb[:EMBED_DIM]]
        last_err = "no embedding in body"
    raise RuntimeError(f"Ollama /api/embeddings 실패: {last_err}")


# ════════════════════════════════════════════
# CLOUD — OpenRouter Embeddings
# ════════════════════════════════════════════


def _embed_cloud(text: str) -> list[float]:
    import requests

    api_key = os.getenv("OPENROUTER_API_KEY", "")
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY 없음")
    for attempt in range(3):
        resp = requests.post(
            "https://openrouter.ai/api/v1/embeddings",
            headers=_openrouter_embed_headers(),
            json={
                "model": OPENROUTER_EMBED_MODEL,
                "input": text,
            },
            timeout=30,
        )
        body = resp.json()
        if "data" in body and body["data"]:
            emb = body["data"][0].get("embedding", [])
            return [float(x) for x in emb[:EMBED_DIM]]
        if attempt < 2:
            time.sleep(2**attempt)
    raise RuntimeError(f"OpenRouter 임베딩 실패: {body if isinstance(body, dict) else ''}")


# ════════════════════════════════════════════
# QUERY EXPANSION — OpenRouter chat
# ════════════════════════════════════════════


def expand_query(q: str) -> str:
    """
    LLM(OpenRouter)을 이용해 검색어를 확장한다.
    MODE=local이거나 실패하면 원본 쿼리를 그대로 반환.
    """
    if MODE != "cloud":
        return q

    import requests

    api_key = os.getenv("OPENROUTER_API_KEY", "")
    if not api_key:
        return q

    prompt = (
        "You are a search query expander for an AI/tech news search engine.\n"
        "Expand the user's Korean search query into a rich set of relevant keywords.\n"
        "Include both Korean and English terms, related concepts, tech names, and company names.\n"
        "Output ONLY the expanded keywords on a single line, space-separated. No explanation.\n\n"
        f"Query: {q}"
    )

    try:
        resp = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=_openrouter_embed_headers(),
            json={
                "model": "meta-llama/llama-3.1-8b-instruct",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 120,
                "temperature": 0.2,
            },
            timeout=10,
        )
        body = resp.json()
        expanded = body["choices"][0]["message"]["content"].strip()
        return f"{q} {expanded}"
    except Exception:
        return q


# ════════════════════════════════════════════
# 공개 인터페이스
# ════════════════════════════════════════════


def make_embedding(text: str) -> list[float]:
    """
    텍스트 → 임베딩 벡터 (최대 1024차원).

    - MODE=cloud: OpenRouter 임베딩 (실패 시 0-벡터)
    - MODE=local: Ollama HTTP (실패 시 OpenRouter 키가 있으면 클라우드, 끝도 실패면 0-벡터)
    """
    text = (text or "").strip() or " "

    if MODE == "cloud":
        try:
            return _embed_cloud(text)
        except Exception as e:
            logger.warning("OpenRouter 임베딩 실패, 0-벡터 폴백: %s", e)
        return _zero_embedding()

    # MODE=local — Ollama
    try:
        return _embed_ollama_http(text)
    except Exception as e:
        logger.warning("Ollama 임베딩 실패 (%s), OpenRouter/폴백 시도: %s", _ollama_base(), e)
    if os.getenv("OPENROUTER_API_KEY"):
        try:
            return _embed_cloud(text)
        except Exception as e2:
            logger.warning("OpenRouter 임베딩(폴백)도 실패: %s", e2)
    logger.warning("임베딩 전부 실패, 0-벡터로 진행(검색/피드는 계속됨)")
    return _zero_embedding()
