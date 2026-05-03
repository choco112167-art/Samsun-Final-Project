"""
backend/save_articles.py — Supabase DB 저장 함수 모음

파이프라인(이동우님)이 번역/요약을 완료한 기사 데이터를
Supabase에 저장하는 모든 함수를 담당한다.

담당 테이블:
  articles     — 기사 원본 + 번역/요약 + 임베딩 (메인)
  neologisms   — AI 신조어 캐시 + 파인튜닝 말뭉치
  fact_checks  — 팩트체크 세부 기록 (MVP 이후)
  eval_results — 파인튜닝 전/후 평가 지표 (4주차~)

팩트체크 (feat/dongwoo `fact_checker/` 통합):
  - 저장 직전 `fact_checker.pipeline.run_fact_check` 로 라벨·신뢰도 산출
  - `pipeline.translate_summarize`(Ollama qwen3.5:4b)와 별도 경로 — 충돌 없음
  - 비활성: 환경변수 FACTCHECK_ENABLED=0
"""

import logging
import os
import hashlib   # URL을 MD5 해시로 변환할 때 사용
from datetime import datetime, timezone   # 수집 시각 자동 기록에 사용
from dotenv import load_dotenv
from supabase import create_client

# 우리가 만든 임베딩 어댑터 — make_embedding 하나만 import
from backend.embedder import make_embedding
from config import get_settings

load_dotenv()

logger = logging.getLogger(__name__)
_AI_META_COLUMNS: set[str] | None = None


def _truthy_env(name: str, default: str = "1") -> bool:
    return os.getenv(name, default).strip().lower() not in ("0", "false", "no", "off")


FACTCHECK_ENABLED = _truthy_env("FACTCHECK_ENABLED", "1")


def _factcheck_skip_flags() -> tuple[bool, bool]:
    """(skip_fc_api, skip_llm) — 키가 없으면 해당 단계 생략."""
    skip_fc = not (os.getenv("GOOGLE_FC_API_KEY") or "").strip()
    has_llm = bool(
        (os.getenv("GEMINI_API_KEY") or "").strip()
        or (os.getenv("GOOGLE_API_KEY") or "").strip()
        or (os.getenv("OPENROUTER_API_KEY") or "").strip(),
    )
    return skip_fc, not has_llm


def normalize_fact_label(label: str | None) -> str:
    """articles.fact_checks.verdict 및 articles.fact_label (FACT|RUMOR|INSIGHT|UNVERIFIED|DROP)."""
    u = (label or "").strip().upper().replace(" ", "_")
    if u == "FACT":
        return "FACT"
    if u == "RUMOR":
        return "RUMOR"
    if u == "INSIGHT":
        return "INSIGHT"
    if u in ("FACT_INSIGHT", "FACT+INSIGHT", "INSIGHT+FACT"):
        return "FACT_INSIGHT"
    if u == "DROP":
        return "DROP"
    # NEEDS_VERIFICATION 등 중간 상태 → DB 스키마에 맞춤
    return "UNVERIFIED"


def infer_fact_label_from_fc(score: float, fc_label: str) -> str:
    """팩트체크 파이프라인 라벨 우선, 없으면 점수 기반 infer_fact_label 과 동일 규칙."""
    normalized = normalize_fact_label(fc_label)
    if normalized in ("FACT", "RUMOR", "UNVERIFIED", "INSIGHT", "FACT_INSIGHT"):
        return normalized
    return infer_fact_label(score)


def _article_ai_meta_columns() -> set[str]:
    """Return optional AI worker columns that exist in the current Supabase schema."""
    global _AI_META_COLUMNS
    if _AI_META_COLUMNS is not None:
        return _AI_META_COLUMNS
    candidates = {
        "ai_status",
        "ai_provider",
        "ai_model",
        "ai_generated_at",
        "ai_error",
        "content_source",
        "content_chars",
        "translation_chars",
    }
    available: set[str] = set()
    for column in candidates:
        try:
            sb.table("articles").select(column).limit(1).execute()
            available.add(column)
        except Exception:
            pass
    _AI_META_COLUMNS = available
    return available


def _attach_ai_meta(payload: dict, article: dict) -> None:
    columns = _article_ai_meta_columns()
    if not columns:
        return
    has_outputs = all(
        str(article.get(field) or "").strip()
        for field in ("translation", "summary_formal", "summary_casual")
    )
    if "ai_status" in columns:
        payload["ai_status"] = "completed" if has_outputs else "pending"
    if "ai_provider" in columns:
        payload["ai_provider"] = article.get("ai_provider") if has_outputs else None
    if "ai_model" in columns:
        payload["ai_model"] = article.get("ai_model")
    if "ai_error" in columns:
        payload["ai_error"] = None
    if "content_source" in columns:
        payload["content_source"] = article.get("content_source") or ("rss_summary" if article.get("content") else None)
    if "content_chars" in columns:
        payload["content_chars"] = len(str(article.get("content") or ""))
    if "translation_chars" in columns:
        payload["translation_chars"] = len(str(article.get("translation") or ""))

# Supabase 클라이언트 생성
_settings = get_settings()
sb = create_client(
    (os.getenv("SUPABASE_URL") or _settings.supabase_url).rstrip("/"),
    os.getenv("SUPABASE_KEY") or os.getenv("SUPABASE_ANON_KEY") or _settings.effective_supabase_key,
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
        articles: 파이프라인에서 넘어온 기사 딕셔너리 리스트.
                  권장 키: url, title (RSS 원문 영어 제목), title_ko (한국어 번역 제목),
                  source, source_type, category, country,
                  keywords, published_at, content, credibility_score,
                  translation, summary_formal, summary_casual.
                  루트 main.py 파이프라인 사용 시 `_pipeline_fact_checked`, `fact_label`,
                  `claims_payload_rows` 가 포함되면 저장 단계에서 팩트체크를 재실행하지 않는다.

    Returns:
        저장된 기사 건수 (팩트체크 결과 DROP 인 기사는 건너뜀)

    팩트체크:
        FACTCHECK_ENABLED=1 (기본) 일 때 `fact_checker.pipeline.run_fact_check` 실행.
        번역 파이프라인(Ollama qwen3.5:4b)과는 별도 프로세스이며 모델 충돌 없음.
    """
    run_fact_check = None
    skip_fc: bool = True
    skip_llm: bool = True
    if FACTCHECK_ENABLED:
        skip_fc, skip_llm = _factcheck_skip_flags()
        try:
            from fact_checker.pipeline import run_fact_check as _rfc

            run_fact_check = _rfc
        except ImportError as err:
            logger.warning("FACTCHECK_ENABLED 이지만 fact_checker 로드 실패: %s", err)

    batch: list[dict] = []
    pending_fact_checks: list[tuple[str, list[dict]]] = []

    for a in articles:
        url = a.get("url", "") or ""
        title_rss = (a.get("title") or "").strip()
        title_ko = (a.get("title_ko") or "").strip()
        title_fc = (title_rss or title_ko).strip()
        content_fc = (a.get("content") or "")[:120000]
        source = a.get("source") or ""
        source_type = (a.get("source_type") or "media")

        score_out = float(a.get("credibility_score") or 0.5)
        label_out = infer_fact_label(score_out)
        claims_payload: list[dict] = []

        pipeline_done = bool(a.get("_pipeline_fact_checked"))

        if pipeline_done:
            score_out = float(a.get("credibility_score") or score_out)
            label_out = normalize_fact_label(a.get("fact_label"))
            for row in a.get("claims_payload_rows") or []:
                verdict = normalize_fact_label(row.get("verdict"))
                if verdict == "DROP":
                    continue
                claims_payload.append({
                    "claim": row.get("claim"),
                    "verdict": verdict,
                    "confidence": row.get("confidence"),
                    "evidence_url": row.get("evidence_url"),
                    "reasoning_trace": row.get("reasoning_trace"),
                    "verification_method": row.get("verification_method"),
                })
        elif FACTCHECK_ENABLED and run_fact_check is not None:
            try:
                fc = run_fact_check(
                    title_fc,
                    content_fc,
                    source,
                    source_type,
                    skip_fc_api=skip_fc,
                    skip_llm=skip_llm,
                )
                if fc.fact_label == "DROP":
                    logger.info("[FactCheck] DROP 스킵: source=%s title=%s...", source, title_fc[:72])
                    continue

                score_out = float(fc.confidence)
                label_out = infer_fact_label_from_fc(score_out, fc.fact_label)
                raw = fc.to_claim_dict(title_fc)
                claims_payload.append({
                    "claim": raw.get("claim"),
                    "verdict": normalize_fact_label(raw.get("verdict")),
                    "confidence": raw.get("confidence"),
                    "evidence_url": raw.get("evidence_url"),
                    "reasoning_trace": raw.get("reasoning_trace"),
                    "verification_method": raw.get("verification_method"),
                })
            except Exception:
                logger.exception("[FactCheck] 예외 — 크롤러 신뢰도(contradiction_score) 유지")

        combined = f"{title_ko}\n{a.get('translation', '')}"
        embedding = make_embedding(combined)

        uh = make_url_hash(url)

        payload = {
            "url_hash":          uh,
            "url":               url,
            "title":             title_rss or title_ko or "",
            "title_ko":          title_ko or None,
            "source":            a.get("source"),
            "source_type":       a.get("source_type"),
            "category":          a.get("category"),
            "country":           a.get("country"),
            "keywords":          a.get("keywords") or [],
            "published_at":      a.get("published_at"),
            "collected_at":      datetime.now(timezone.utc).isoformat(),
            "content":           a.get("content"),
            "credibility_score": score_out,
            "fact_label":        label_out,
            "translation":       a.get("translation"),
            "summary_formal":    a.get("summary_formal"),
            "summary_casual":    a.get("summary_casual"),
            "embedding":         embedding,
        }
        _attach_ai_meta(payload, a)
        batch.append(payload)

        if claims_payload:
            pending_fact_checks.append((uh, claims_payload))

    if not batch:
        print("[DB] articles 저장 0건 (전부 DROP 또는 입력 없음)")
        return 0

    sb.table("articles").upsert(batch, on_conflict="url_hash").execute()
    print(f"[DB] articles {len(batch)}건 저장 완료")

    for url_hash, claims in pending_fact_checks:
        save_fact_checks(url_hash, claims)

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

    동일 기사 재저장 시 기존 팩트체크 행을 삭제한 뒤 다시 삽입한다.

    Args:
        url_hash: 해당 기사의 url_hash
        claims:   팩트체크 결과 리스트
                  각 항목: {"claim": "...", "verdict": "FACT", "confidence": 0.92}
    """
    if not claims:
        return

    sb.table("fact_checks").delete().eq("article_url_hash", url_hash).execute()

    rows: list[dict] = []
    for c in claims:
        verdict = normalize_fact_label(c.get("verdict", "UNVERIFIED"))
        if verdict == "DROP":
            continue

        claim_body = (c.get("claim") or "").strip()
        rt = c.get("reasoning_trace")
        vm = c.get("verification_method")
        extras: list[str] = []
        if vm:
            extras.append(f"[{vm}]")
        if rt:
            extras.append(str(rt)[:2000])
        if extras:
            claim_body = (claim_body + "\n\n" + "\n".join(extras)).strip()[:14000]

        rows.append({
            "article_url_hash": url_hash,
            "claim":            claim_body,
            "verdict":          verdict,
            "confidence":       float(c.get("confidence") if c.get("confidence") is not None else 0.5),
            "evidence_url":     c.get("evidence_url"),
            "checker_type":     "ai",
            "checked_at":       datetime.now(timezone.utc).isoformat(),
        })

    if rows:
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
