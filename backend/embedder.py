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
            return body["data"][0]["embedding"][:1024]
        # 429 rate limit 또는 일시 오류 → 재시도
        if attempt < 2:
            time.sleep(2 ** attempt)
    raise RuntimeError(f"OpenRouter 임베딩 실패: {body}")


# ════════════════════════════════════════════
# QUERY EXPANSION — LLM으로 검색어 확장
# 한국어 짧은 쿼리 → 한/영 풍부한 키워드로 변환
# ════════════════════════════════════════════

def expand_query(q: str) -> str:
    """
    LLM(OpenRouter)을 이용해 검색어를 확장한다.
    예: "엔비디아" → "엔비디아 NVIDIA GPU 반도체 AI가속기 블랙웰 H100 데이터센터"

    MODE=local이거나 실패하면 원본 쿼리를 그대로 반환.
    """
    if MODE != "cloud":
        return q

    import requests
    api_key = os.getenv("OPENROUTER_API_KEY", "")
    if not api_key:
        return q

    prompt = (
        "Expand this search query for an AI/tech news engine.\n"
        "Output ONLY 8-12 unique keywords (Korean + English), space-separated, one line, no repetition.\n\n"
        f"Query: {q}"
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
                "messages":   [{"role": "user", "content": prompt}],
                "max_tokens": 120,
                "temperature": 0.2,
            },
            timeout=10,
        )
        body = resp.json()
        expanded = body["choices"][0]["message"]["content"].strip()
        # LLM이 원본 쿼리도 포함하도록 앞에 붙여줌
        return f"{q} {expanded}"
    except Exception:
        # 실패하면 원본 쿼리 그대로 사용 (검색은 항상 동작해야 함)
        return q


# ════════════════════════════════════════════
# 공개 인터페이스 — 이것만 import해서 쓰세요
# ════════════════════════════════════════════

def make_embedding(text: str) -> list[float]:
    """
    텍스트 → 임베딩 벡터 (1024차원)

    .env의 MODE 값으로 전환:
      MODE=local  → Ollama qwen3-embedding:0.6b  (개발용, 기본값)
      MODE=cloud  → OpenRouter qwen/qwen3-embedding-4b (Railway 배포용)
    """
    if MODE == "cloud":
        return _embed_cloud(text)
    return _embed_local(text)
