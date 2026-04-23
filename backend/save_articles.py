"""
backend/save_articles.py — Supabase DB 연동 함수 모음

테이블: articles / fact_checks / neologisms / eval_results
실행 전제:
    - supabase_schema.sql 을 Supabase SQL Editor에서 먼저 실행
    - .env 에 SUPABASE_URL, SUPABASE_KEY, OLLAMA_BASE_URL 설정
"""

import os
import hashlib
import requests
from datetime import datetime, timezone
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

# ── Supabase 클라이언트 ──────────────────────────────────────
sb = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY"),
)

# ── Ollama 임베딩 설정 ───────────────────────────────────────
OLLAMA_URL  = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1").replace("/v1", "")
EMBED_MODEL = "mxbai-embed-large"


# ── 유틸 ────────────────────────────────────────────────────

def make_url_hash(url: str) -> str:
    """URL → MD5 해시 (articles PK)"""
    return hashlib.md5(url.encode()).hexdigest()


def make_embedding(text: str) -> list[float]:
    """텍스트 → 1024차원 벡터 (mxbai-embed-large via Ollama)"""
    resp = requests.post(
        f"{OLLAMA_URL}/api/embeddings",
        json={"model": EMBED_MODEL, "prompt": text},
    )
    resp.raise_for_status()
    return resp.json()["embedding"]


def infer_fact_label(credibility_score: float) -> str:
    """
    credibility_score 기반 자동 분류 (MVP).
    MVP 이후 fact_checks 집계로 대체 예정.
    """
    if credibility_score >= 0.8:
        return "FACT"
    if credibility_score < 0.4:
        return "RUMOR"
    return "UNVERIFIED"


# ── articles ─────────────────────────────────────────────────

def save_articles(articles: list[dict]) -> int:
    """
    파이프라인 결과를 articles 테이블에 배치 upsert.

    articles 리스트 각 항목에 필요한 키:
        url, title, source, source_type, category, country,
        keywords (list), published_at (ISO 8601 str),
        content, credibility_score,
        translation, summary_formal, summary_casual

    Returns: 저장된 건수
    """
    batch = []
    for a in articles:
        url       = a.get("url", "")
        url_hash  = make_url_hash(url)
        score     = a.get("credibility_score") or 0.5
        embedding = make_embedding(a.get("translation", ""))

        batch.append({
            "url_hash":          url_hash,
            "url":               url,
            "title":             a.get("title"),
            "source":            a.get("source"),
            "source_type":       a.get("source_type"),
            "category":          a.get("category"),
            "country":           a.get("country"),
            "keywords":          a.get("keywords") or [],
            "published_at":      a.get("published_at"),
            "collected_at":      datetime.now(timezone.utc).isoformat(),
            "content":           a.get("content"),
            "credibility_score": score,
            "fact_label":        infer_fact_label(score),
            "translation":       a.get("translation"),
            "summary_formal":    a.get("summary_formal"),
            "summary_casual":    a.get("summary_casual"),
            "embedding":         embedding,
        })

    sb.table("articles").upsert(batch, on_conflict="url_hash").execute()
    print(f"[DB] articles {len(batch)}건 저장 완료")
    return len(batch)


# ── neologisms ────────────────────────────────────────────────

def save_neologisms(terms: list[str], url_hash: str) -> None:
    """
    번역 결과에서 추출된 신조어 목록 일괄 upsert.
    - 처음 등장: INSERT
    - 재등장:    occurrence_count +1
    explanation은 MVP에서 NULL 허용 (수동 검수 후 채움).

    Args:
        terms:    신조어 영문 원어 리스트 (예: ['Blackwell Ultra', 'RLHF'])
        url_hash: 해당 기사의 url_hash
    """
    for term in terms:
        existing = (
            sb.table("neologisms")
            .select("term, occurrence_count")
            .eq("term", term)
            .execute()
        )
        if existing.data:
            sb.table("neologisms").update({
                "occurrence_count": existing.data[0]["occurrence_count"] + 1,
            }).eq("term", term).execute()
        else:
            sb.table("neologisms").insert({
                "term":                term,
                "first_seen_url_hash": url_hash,
                "occurrence_count":    1,
                "confirmed":           False,
                "created_at":          datetime.now(timezone.utc).isoformat(),
            }).execute()

    if terms:
        print(f"[DB] neologisms {len(terms)}건 upsert 완료")


# ── fact_checks ───────────────────────────────────────────────

def save_fact_checks(url_hash: str, claims: list[dict]) -> None:
    """
    팩트체크 결과 저장 (MVP 이후 활용).

    claims 리스트 각 항목:
        {
            "claim":        "엔비디아 시총 3조 달러 돌파",
            "verdict":      "FACT",   # FACT | RUMOR | UNVERIFIED
            "confidence":   0.92,
            "evidence_url": None,     # MVP에서는 None
        }
    """
    if not claims:
        return

    rows = [
        {
            "article_url_hash": url_hash,
            "claim":            c.get("claim"),
            "verdict":          c.get("verdict", "UNVERIFIED"),
            "confidence":       c.get("confidence"),
            "evidence_url":     c.get("evidence_url"),
            "checker_type":     "ai",
            "checked_at":       datetime.now(timezone.utc).isoformat(),
        }
        for c in claims
    ]
    sb.table("fact_checks").insert(rows).execute()
    print(f"[DB] fact_checks {len(rows)}건 저장 완료")


# ── eval_results ──────────────────────────────────────────────

def save_eval_result(
    url_hash:      str,
    model_version: str,
    eval_type:     str,
    **metrics,
) -> None:
    """
    평가 결과 1건 저장 (파인튜닝 전/후 비교용, MVP 이후).

    eval_type = 'translation'    → metrics: bleu, comet, tpr
    eval_type = 'summary_formal' → metrics: geval_consistency, geval_fluency,
                                             geval_coherence, geval_relevance
    예시:
        save_eval_result(hash, 'qwen3-4b-base', 'translation', bleu=12.3, comet=0.71, tpr=0.88)
    """
    sb.table("eval_results").insert({
        "article_url_hash": url_hash,
        "model_version":    model_version,
        "eval_type":        eval_type,
        "evaluated_at":     datetime.now(timezone.utc).isoformat(),
        **metrics,
    }).execute()
