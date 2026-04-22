"""
backend/seed_neologisms.py — 신조어 테이블 시딩 스크립트

backend.neologism_rag.explain_neologism() 을 용어 목록에 대해 순차 호출하여
Supabase neologisms 테이블을 초기 데이터로 채웁니다.

동작:
  - 각 term 을 explain_neologism() 에 전달
      · 캐시 히트(pgvector 유사도 >= 0.85)면 Gemini 호출 없이 즉시 반환
      · 미스면 Gemini 2.5 Flash + Google Search Grounding 호출 후 upsert
  - 호출 간 sleep (CALL_INTERVAL_SEC, Gemini free-tier RPM 보호)
  - 진행률 / 성공·실패 / 누적 소요시간을 줄마다 표시
  - Ctrl+C 로 중단 시에도 지금까지의 결과 요약 출력

실행:
  python -m backend.seed_neologisms

사전 준비:
  1) .env 에 GEMINI_API_KEY, SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY 설정
  2) Ollama 로컬 서버 실행 (qwen3-embedding:0.6b 모델 pull)
  3) Supabase neologisms 테이블에 embedding VECTOR(1024), source TEXT 컬럼 +
     match_neologisms RPC 적용 (backend/neologism_rag.sql 참고)
"""

from __future__ import annotations

import logging
import sys
import time

from backend.neologism_rag import explain_neologism

# ── 시딩 대상 용어 (요구사항 명시 순서 그대로) ──────────────────────
SEED_TERMS: list[str] = [
    "LoRA",
    "RLHF",
    "RAG",
    "Transformer",
    "Diffusion Model",
    "Fine-tuning",
    "Prompt Engineering",
    "Vector Database",
    "Embedding",
    "Hallucination",
    "Chain of Thought",
    "Multimodal",
    "Quantization",
    "Inference",
    "Context Window",
    "Attention Mechanism",
    "Benchmark",
    "Agent",
    "LangChain",
    "Grounding",
]

# Gemini free-tier RPM 보호.
# gemini-2.5-flash 무료 티어는 실측 5 RPM (= 12초 간격) → 13초로 버퍼 1초.
# 그래도 429 가 발생하면 neologism_rag._generate_via_gemini 의
# retryDelay 파싱 재시도가 받아주므로 안전망 이중화.
CALL_INTERVAL_SEC: float = 13.0


def _is_success(result: str, term: str) -> bool:
    """
    explain_neologism 반환값으로 실질적 성공 여부 판정.

    - 성공:  "Term(ko, explanation)"  형태 (괄호 + 쉼표 포함, 설명 비어있지 않음)
    - 실패:  "Term"  또는  "Term(Term)"  형태 (설명 생성 실패 폴백)
    """
    if not result or "(" not in result or not result.endswith(")"):
        return False
    inside = result[result.index("(") + 1 : -1]
    if ", " not in inside:
        return False
    ko, explanation = inside.split(", ", 1)
    return bool(explanation.strip()) and ko.strip().lower() != term.strip().lower()


def seed(terms: list[str], interval: float = CALL_INTERVAL_SEC) -> dict:
    """
    용어 목록을 순차 시딩. 캐시 히트는 즉시 반환되므로 sleep 을 생략하여
    전체 소요시간을 최소화.

    Returns:
        {
            "success": [("LoRA", "LoRA(로라, ...)"), ...],
            "failure": [("X", "X(X)"), ...],
            "elapsed": 45.2,
        }
    """
    success: list[tuple[str, str]] = []
    failure: list[tuple[str, str]] = []
    cache_hits = 0
    total = len(terms)
    width = len(str(total))
    t_start = time.perf_counter()

    print(f"{'=' * 72}")
    print(f"신조어 시딩 시작 — 총 {total}개, Gemini 호출 간 간격 {interval:.1f}s")
    print(f"{'=' * 72}")

    try:
        for i, term in enumerate(terms, 1):
            t0 = time.perf_counter()
            try:
                result = explain_neologism(term)
            except Exception as e:  # pragma: no cover — explain_neologism 내부 폴백 존재, 방어적
                result = ""
                logging.exception("[%d/%d] 예외: %s", i, total, e)

            dt = time.perf_counter() - t0
            ok = _is_success(result, term)

            # 캐시 히트 추정: 성공 + 1.5초 이내 (Ollama+RPC 만으로 완료)
            # Gemini 호출은 보통 2.5s 이상 소요되므로 이 기준으로 구분
            is_cache_hit = ok and dt < 1.5

            if is_cache_hit:
                tag = "HIT "
                cache_hits += 1
            elif ok:
                tag = "OK  "
            else:
                tag = "FAIL"

            print(f"[{i:>{width}}/{total}] {tag} {term:<22} {dt:5.2f}s  → {result}")

            (success if ok else failure).append((term, result))

            # 마지막 항목 뒤에는 sleep 생략.
            # 캐시 히트면 Gemini 호출이 없으므로 RPM 보호 대기도 불필요.
            if i < total and interval > 0 and not is_cache_hit:
                time.sleep(interval)

    except KeyboardInterrupt:
        print("\n[중단] Ctrl+C 감지 — 지금까지의 결과로 요약을 출력합니다.")

    elapsed = time.perf_counter() - t_start

    print(f"{'=' * 72}")
    print(
        f"요약: 성공 {len(success)} (캐시 히트 {cache_hits}) / "
        f"실패 {len(failure)} / 시도 {len(success) + len(failure)}개, "
        f"누적 {elapsed:.1f}s"
    )
    if failure:
        print("실패 목록:")
        for term, result in failure:
            print(f"  - {term}: {result or '(빈 반환)'}")
    print(f"{'=' * 72}")

    return {"success": success, "failure": failure, "elapsed": elapsed}


def main() -> int:
    logging.basicConfig(
        level=logging.WARNING,  # INFO 는 너무 시끄러움 — 진행은 print 로 출력
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    result = seed(SEED_TERMS)
    return 0 if not result["failure"] else 1


if __name__ == "__main__":
    sys.exit(main())
