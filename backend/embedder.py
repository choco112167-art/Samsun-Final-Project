"""
backend/embedder.py — 임베딩 어댑터 (local 전용)

모델: Ollama qwen3-embedding:0.6b (1024차원, 32K context)
호출: POST {OLLAMA_URL}/api/embeddings

공개 함수 `make_embedding(text) -> list[float]` 시그니처는 유지.
호출하는 쪽(backend/save_articles.py 등)은 수정할 필요 없음.

2026-04-21: mxbai-embed-large / qwen3-embedding:4b → qwen3-embedding:0.6b 통일.
  (qwen3:0.6b는 채팅 전용 모델로 /api/embeddings 미지원이므로 임베딩 전용 모델 사용)
"""

import os
from dotenv import load_dotenv
import requests

load_dotenv()

OLLAMA_URL  = os.getenv("OLLAMA_URL") or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "qwen3-embedding:0.6b")
EMBED_DIM   = 1024


def _embed_local(text: str) -> list[float]:
    """Ollama /api/embeddings 호출 → 1024차원 벡터."""
    resp = requests.post(
        f"{OLLAMA_URL}/api/embeddings",
        json={"model": EMBED_MODEL, "prompt": text},
        timeout=30,
    )
    resp.raise_for_status()
    vec = resp.json()["embedding"]
    if len(vec) < EMBED_DIM:
        raise ValueError(
            f"임베딩 차원 불일치: {len(vec)} < {EMBED_DIM} (model={EMBED_MODEL})"
        )
    return vec[:EMBED_DIM]


def make_embedding(text: str) -> list[float]:
    """텍스트 → 1024차원 임베딩 벡터 (Ollama qwen3-embedding:0.6b)."""
    return _embed_local(text)
