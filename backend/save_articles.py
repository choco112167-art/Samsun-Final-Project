"""
backend/save_articles.py — Supabase DB 저장 함수 모음

파이프라인(이동우님)이 번역/요약을 완료한 기사 데이터를
Supabase에 저장하는 모든 함수를 담당한다.

담당 테이블:
  articles     — 기사 원본 + 번역/요약 + 임베딩 (메인)
  neologisms   — AI 신조어 캐시 + 파인튜닝 말뭉치
  fact_checks  — 팩트체크 세부 기록 (MVP 이후)
  eval_results — 파인튜닝 전/후 평가 지표 (4주차~)
"""

import os
import hashlib   # URL을 MD5 해시로 변환할 때 사용
from datetime import datetime, timezone   # 수집 시각 자동 기록에 사용
from dotenv import load_dotenv
from supabase import create_client

# 우리가 만든 임베딩 어댑터 — make_embedding 하나만 import
from backend.embedder import make_embedding

load_dotenv()

# Supabase 클라이언트 생성
sb = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY"),
)


# ── 유틸 함수들 ──────────────────────────────────────────────

def make_url_hash(url: str) -> str:
    """
    URL을 MD5 해시로 변환한다.
    이 값이 articles 테이블의 PK(고유 키)가 된다.

    왜 URL을 직접 PK로 안 쓰냐면:
    URL이 너무 길고 특수문자가 많아서 DB 성능이 나빠질 수 있기 때문.
    MD5는 어떤 문자열이든 32자 고정 길이 문자열로 변환해준다.

    예: "https://techcrunch.com/2026/..." → "a3f2c8d1e4b7..."
    """
    return hashlib.md5(url.encode()).hexdigest()


def infer_fact_label(credibility_score: float) -> str:
    """
    신뢰도 점수(0.0~1.0)를 3단계 라벨로 자동 분류한다.

    MVP 단계에서는 출처 신뢰도만으로 자동 분류.
    이후 fact_checks 테이블에 쌓인 데이터로 정교화할 예정.

    0.8 이상 → FACT     (신뢰할 수 있는 기사)
    0.4 미만 → RUMOR    (루머 가능성 있음)
    그 외    → UNVERIFIED (확인 필요)
    """
    if credibility_score >= 0.8:
        return "FACT"
    if credibility_score < 0.4:
        return "RUMOR"
    return "UNVERIFIED"


# ── articles 테이블 저장 ──────────────────────────────────────

def save_articles(articles: list[dict]) -> int:
    """
    파이프라인 결과물(번역+요약된 기사 리스트)을 articles 테이블에 저장한다.
    같은 기사가 다시 들어와도 url_hash 기준으로 중복 저장되지 않는다.

    Args:
        articles: 파이프라인에서 넘어온 기사 딕셔너리 리스트
                  각 항목에 필요한 키:
                  url, title, source, source_type, category, country,
                  keywords, published_at, content, credibility_score,
                  translation, summary_formal, summary_casual

    Returns:
        저장된 기사 건수
    """
    batch = []   # 한 번에 저장할 데이터를 모아두는 리스트

    for a in articles:
        url   = a.get("url", "")
        score = a.get("credibility_score") or 0.5   # 신뢰도가 없으면 기본값 0.5

        # 한국어 제목 + 한국어 번역 합산 임베딩
        title_en = a.get("title_en", "") or ""
        combined = f"{a.get('title', '')}\n{a.get('translation', '')}"
        embedding = make_embedding(combined)

        # DB에 저장할 한 기사의 데이터를 딕셔너리로 조립
        batch.append({
            "url_hash":          make_url_hash(url),     # PK: URL의 MD5 해시
            "url":               url,                    # 원문 URL
            "title":             a.get("title") or title_en,  # 한국어 제목, 없으면 영어 fallback
            "title_en":          title_en,
            "source":            a.get("source"),        # 언론사명
            "source_type":       a.get("source_type"),   # 'media' | 'community'
            "category":          a.get("category"),      # 카테고리
            "country":           a.get("country"),       # 발행 국가
            "keywords":          a.get("keywords") or [], # 키워드 배열
            "published_at":      a.get("published_at"),  # 기사 발행 시각 (ISO 8601)
            "collected_at":      datetime.now(timezone.utc).isoformat(),  # 수집 시각 자동 기록
            "content":           a.get("content"),       # 영문 원문 본문
            "credibility_score": score,                  # 신뢰도 점수
            "fact_label":        infer_fact_label(score),# 자동 분류된 팩트 라벨
            "translation":       a.get("translation"),   # 한국어 번역 전문
            "summary_formal":    a.get("summary_formal"),# 격식체 3줄 요약
            "summary_casual":    a.get("summary_casual"),# 일상체 3줄 요약
            "embedding":         embedding,              # 임베딩 벡터 (RAG에 사용)
        })

    # upsert: url_hash가 이미 있으면 업데이트, 없으면 새로 추가
    # on_conflict="url_hash": PK 충돌 시 기존 행을 덮어쓴다
    # 크론탭이 1시간마다 같은 기사를 수집해도 중복 저장되지 않음
    sb.table("articles").upsert(batch, on_conflict="url_hash").execute()
    print(f"[DB] articles {len(batch)}건 저장 완료")
    return len(batch)


# ── neologisms 테이블 저장 ────────────────────────────────────

def save_neologisms(terms: list[str], url_hash: str) -> None:
    """
    번역 결과에서 발견된 AI 신조어를 neologisms 테이블에 저장한다.
    두 가지 역할을 한다:
      1. 실시간 캐시: 같은 용어 재등장 시 검색엔진 재호출 없이 바로 사용
      2. 파인튜닝 말뭉치: confirmed=True 데이터를 학습 데이터로 활용

    Args:
        terms:    신조어 영문 원어 리스트 (예: ["Blackwell Ultra", "RLHF"])
        url_hash: 해당 기사의 url_hash (최초 등장 기록용)
    """
    for term in terms:
        # 이미 DB에 있는 신조어인지 확인
        existing = (
            sb.table("neologisms")
            .select("term, occurrence_count")
            .eq("term", term)
            .execute()
        )

        if existing.data:
            # 이미 있으면 등장 횟수만 1 증가
            sb.table("neologisms").update({
                "occurrence_count": existing.data[0]["occurrence_count"] + 1,
            }).eq("term", term).execute()
        else:
            # 처음 등장한 신조어면 새로 추가
            # explanation은 MVP에서 NULL — 나중에 수동 검수 후 채움
            sb.table("neologisms").insert({
                "term":                term,
                "first_seen_url_hash": url_hash,   # 최초 등장 기사 연결
                "occurrence_count":    1,
                "confirmed":           False,       # 수동 검수 전까지는 미확인
                "created_at":          datetime.now(timezone.utc).isoformat(),
            }).execute()

    if terms:
        print(f"[DB] neologisms {len(terms)}건 upsert 완료")


# ── fact_checks 테이블 저장 ───────────────────────────────────

def save_fact_checks(url_hash: str, claims: list[dict]) -> None:
    """
    팩트체크 세부 기록을 저장한다. (MVP 이후 활용)

    articles.fact_label은 기사 전체의 신뢰도를 나타내지만,
    어떤 주장이 왜 RUMOR인지 상세 내용은 이 테이블에 저장된다.
    기사 1개에 여러 주장이 있을 수 있어서 1:N 구조.

    Args:
        url_hash: 해당 기사의 url_hash
        claims:   팩트체크 결과 리스트
                  각 항목: {"claim": "...", "verdict": "FACT", "confidence": 0.92}
    """
    if not claims:
        return   # 검증할 주장이 없으면 바로 종료

    # 각 주장을 DB에 저장할 형식으로 변환
    rows = [
        {
            "article_url_hash": url_hash,                    # 어느 기사의 팩트체크인지
            "claim":            c.get("claim"),              # 검증 대상 주장 원문
            "verdict":          c.get("verdict", "UNVERIFIED"), # 팩트체크 결과
            "confidence":       c.get("confidence"),         # AI 확신도 (0.0~1.0)
            "evidence_url":     c.get("evidence_url"),       # 근거 URL (MVP: None)
            "checker_type":     "ai",                        # MVP에서는 항상 AI 검증
            "checked_at":       datetime.now(timezone.utc).isoformat(),
        }
        for c in claims
    ]
    sb.table("fact_checks").insert(rows).execute()
    print(f"[DB] fact_checks {len(rows)}건 저장 완료")


# ── eval_results 테이블 저장 ──────────────────────────────────

def save_eval_result(
    url_hash:      str,   # 평가 대상 기사
    model_version: str,   # 예: 'qwen3-4b-base', 'qwen3-4b-ft-v1', 'gpt-4o'
    eval_type:     str,   # 'translation' | 'summary_formal'
    **metrics,            # 평가 지표 (아래 참고)
) -> None:
    """
    파인튜닝 전/후 평가 지표를 저장한다. (4주차~)

    같은 기사를 여러 모델로 평가해서 성능을 비교할 수 있다.
    예: 베이스 모델 vs 파인튜닝 모델 vs GPT-4o

    eval_type별 metrics:
      'translation'    → bleu(번역 품질), comet(의미 보존), tpr(신조어 유지율)
      'summary_formal' → geval_faithfulness, geval_fluency,
                         geval_conciseness, geval_relevance (각 1~5점)
    """
    sb.table("eval_results").insert({
        "article_url_hash": url_hash,
        "model_version":    model_version,
        "eval_type":        eval_type,
        "evaluated_at":     datetime.now(timezone.utc).isoformat(),
        **metrics,   # bleu, comet 등 추가 지표를 딕셔너리로 풀어서 저장
    }).execute()
