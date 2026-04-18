"""
backend/embedder.py — 임베딩 어댑터

MODE=local  → Ollama 로컬 (개발 중)
MODE=cloud  → OpenRouter API (배포 시)

.env에서 MODE 한 줄만 바꾸면 전체 전환됩니다.
"""

import os
from dotenv import load_dotenv

load_dotenv()

MODE = os.getenv("MODE", "local")


# ════════════════════════════════════════════
# LOCAL — Ollama (개발 환경)
# 사용: MODE=local
# 준비: ollama pull qwen3-embedding:4b
# ════════════════════════════════════════════

def _embed_local(text: str) -> list[float]:
    # ollama 라이브러리로 직접 호출 (HTTP 요청보다 안정적)
    import ollama
    resp = ollama.embeddings(
        model="qwen3-embedding:4b",
        prompt=text,
    )
    return resp["embedding"][:1024]


# ════════════════════════════════════════════
# CLOUD — OpenRouter Embedding API (배포 환경)
# 사용: MODE=cloud
# 준비: .env에 OPENROUTER_API_KEY 설정
# ════════════════════════════════════════════

def _embed_cloud(text: str) -> list[float]:
    import requests
    api_key = os.getenv("OPENROUTER_API_KEY", "")
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
    resp.raise_for_status()
    return resp.json()["data"][0]["embedding"][:1024]


# ════════════════════════════════════════════
# 공개 인터페이스 — 이것만 import해서 쓰세요
# ════════════════════════════════════════════

def make_embedding(text: str) -> list[float]:
    """
    텍스트 → 임베딩 벡터 (1024차원)

    전환 방법:
      로컬 → 클라우드: 아래 return 줄을 주석 처리하고, 주석 처리된 줄을 활성화

    MODE=local  → Ollama qwen3-embedding:4b  (현재 활성)
    MODE=cloud  → OpenRouter qwen/qwen3-embedding-4b
    """
    # ── 로컬 (개발 중 — 기본값) ──────────────────────────────
    return _embed_local(text)

    # ── 클라우드 (배포 시 위 줄 주석, 아래 줄 활성화) ─────────
    # return _embed_cloud(text)
