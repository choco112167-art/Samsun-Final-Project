import argparse
import logging
import os
import sys

from dotenv import load_dotenv

sys.stdout.reconfigure(encoding="utf-8")
load_dotenv()

# 이상준 RSS 모듈 경로 추가
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "collect"))

from crawler.rss_crawler import fetch_all
from pipeline.translate_summarize import translate_and_summarize, estimate_sentences

logger = logging.getLogger(__name__)


def _factcheck_skip_flags() -> tuple[bool, bool]:
    """save_articles와 동일 규칙 — Google FC / LLM 단계 생략 여부."""
    skip_fc = not (os.getenv("GOOGLE_FC_API_KEY") or "").strip()
    has_llm = bool(
        (os.getenv("GEMINI_API_KEY") or "").strip()
        or (os.getenv("GOOGLE_API_KEY") or "").strip()
        or (os.getenv("OPENROUTER_API_KEY") or "").strip(),
    )
    return skip_fc, not has_llm


def _provider() -> str:
    return (os.getenv("LLM_PROVIDER") or os.getenv("MODE") or "local").strip().lower()


def _embedding_provider() -> str:
    return (os.getenv("EMBEDDING_PROVIDER") or os.getenv("MODE") or "local").strip().lower()


def missing_required_env() -> list[str]:
    """Return env names required for a real RSS→AI→Supabase refresh."""
    missing: list[str] = []
    if not os.getenv("SUPABASE_URL", "").strip():
        missing.append("SUPABASE_URL")
    if not (
        os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
        or os.getenv("SUPABASE_KEY", "").strip()
        or os.getenv("SUPABASE_ANON_KEY", "").strip()
    ):
        missing.append("SUPABASE_SERVICE_ROLE_KEY or SUPABASE_KEY or SUPABASE_ANON_KEY")

    llm_provider = _provider()
    if llm_provider in ("openrouter", "cloud") and not os.getenv("OPENROUTER_API_KEY", "").strip():
        missing.append("OPENROUTER_API_KEY")
    if llm_provider == "gemini" and not (
        os.getenv("GEMINI_API_KEY", "").strip() or os.getenv("GOOGLE_API_KEY", "").strip()
    ):
        missing.append("GEMINI_API_KEY or GOOGLE_API_KEY")

    embedding_provider = _embedding_provider()
    if embedding_provider in ("openrouter", "cloud") and not os.getenv("OPENROUTER_API_KEY", "").strip():
        missing.append("OPENROUTER_API_KEY")

    return list(dict.fromkeys(missing))


def print_env_report() -> list[str]:
    missing = missing_required_env()
    print("== refresh env check ==")
    print(f"LLM_PROVIDER: {_provider()}")
    print(f"EMBEDDING_PROVIDER: {_embedding_provider()}")
    print("SUPABASE_URL: set" if os.getenv("SUPABASE_URL", "").strip() else "SUPABASE_URL: missing")
    print(
        "Supabase write key: set"
        if (
            os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
            or os.getenv("SUPABASE_KEY", "").strip()
            or os.getenv("SUPABASE_ANON_KEY", "").strip()
        )
        else "Supabase write key: missing"
    )
    print("GOOGLE_FC_API_KEY: set" if os.getenv("GOOGLE_FC_API_KEY", "").strip() else "GOOGLE_FC_API_KEY: missing (deep Google FC will be skipped)")
    if missing:
        print("\nMissing required variables:")
        for name in missing:
            print(f"- {name}")
        print("\nSet them in the repository root .env file copied from .env.example, or in the shell environment.")
    else:
        print("All required variables for the selected providers are present.")
    return missing


def run_pipeline(max_articles: int = 10, summary_sentences: int = 3, save_failed_rows: bool = False):
    """
    전체 파이프라인:
      1) RSS·Lemmy 등 수집
      2) AI 관련성 + 초경량 신호 탐지 (프리플라이트) — 통과하지 못하면 DROP (번역 생략)
      3) 번역·요약 (LLM)
      4) 심층 팩트체크 — FACT_AUTO·Insight 경로는 생략 (FACT / INSIGHT 라벨만)
      5) 결과 dict 리스트 반환 → save_articles.py 가 DB 저장
    """
    print("=" * 60)
    print("[ 1단계: RSS 수집 (이상준 파트) ]")
    print("=" * 60)
    articles = fetch_all()
    if max_articles:
        articles = articles[:max_articles]
    print(f"\n총 {len(articles)}건 수집 완료\n")

    from fact_checker.channel_config import get_profile
    from fact_checker.pipeline import FactCheckResult, run_fact_check
    from fact_checker.preflight import augmented_body_for_fact_check, run_preflight

    print("=" * 60)
    print("[ 2~4단계: 프리플라이트 → 번역·요약 → 팩트체크 ]")
    print("=" * 60)

    results: list[dict] = []
    skip_fc, skip_llm = _factcheck_skip_flags()

    for i, article in enumerate(articles, 1):
        print(f"\n[{i}/{len(articles)}] [{article.source}] {article.title[:60]}...")
        ai_only_feed = getattr(article, "ai_only_feed", True)

        try:
            pf = run_preflight(
                title=article.title,
                content=article.content or "",
                source=article.source,
                source_type=article.source_type,
                ai_only_feed=ai_only_feed,
                title_only_feed=getattr(article, "title_only_feed", False),
            )
            if pf.dropped:
                print(f"  [프리플라이트 DROP] {pf.reason}")
                continue

            text = article.content or article.title
            n = estimate_sentences(text, max_sentences=summary_sentences)
            processed = translate_and_summarize(
                text=text,
                title=article.title,
                summary_sentences=n,
            )

            fc_res: FactCheckResult | None = None

            if pf.tier1_fact_auto_only:
                prof = get_profile(article.source)
                fc_res = FactCheckResult(
                    fact_label="FACT",
                    confidence=float(prof.credibility_score),
                    tier=prof.default_tier,
                    step_reached=1,
                    verification_method="auto_preflight",
                    reasoning_trace=(
                        "TIER1 언론 · 루머 신호 없음 → FACT_AUTO (번역 후 심층 FC·LLM 생략)"
                    ),
                )
            elif pf.insight_analysis:
                prof = get_profile(article.source)
                base = float(prof.credibility_score)
                fc_res = FactCheckResult(
                    fact_label="INSIGHT",
                    confidence=min(0.82, base + 0.05),
                    tier=prof.default_tier,
                    step_reached=1,
                    verification_method="insight_signal",
                    reasoning_trace=(
                        "의견 표현 다수이나 전문 용어·수치 포함 — Insight 분석글 "
                        "(경량 라벨 · 심층 팩트체크 생략)"
                    ),
                )
            elif pf.needs_deep_fact_check:
                combined = augmented_body_for_fact_check(article.content or "", processed)
                fc_res = run_fact_check(
                    article.title,
                    combined,
                    article.source,
                    article.source_type,
                    skip_fc_api=skip_fc,
                    skip_llm=skip_llm,
                )
                if fc_res.fact_label == "DROP":
                    print("  [심층 팩트체크 DROP] — DB 제외")
                    continue
            else:
                prof = get_profile(article.source)
                fc_res = FactCheckResult(
                    fact_label="UNVERIFIED",
                    confidence=0.50,
                    tier=prof.default_tier,
                    step_reached=0,
                    verification_method="auto",
                    reasoning_trace="프리플라이트 분기 미정 — UNVERIFIED",
                )

            claim_rows: list[dict] = []
            if fc_res and fc_res.should_save():
                raw = fc_res.to_claim_dict(article.title)
                claim_rows.append(
                    {
                        "claim": raw.get("claim"),
                        "verdict": raw.get("verdict"),
                        "confidence": raw.get("confidence"),
                        "evidence_url": raw.get("evidence_url"),
                        "reasoning_trace": raw.get("reasoning_trace"),
                        "verification_method": raw.get("verification_method"),
                    }
                )

            result = {
                "source": article.source,
                "source_type": article.source_type,
                "category": article.category,
                "country": article.country,
                "title": article.title,
                "title_ko": processed.get("title") or "",
                "url": article.url,
                "credibility_score": float(fc_res.confidence) if fc_res else article.credibility_score,
                "published_at": article.published_at,
                "content": article.content,
                "keywords": getattr(article, "keywords", []),
                "translation": processed.get("translation", ""),
                "summary_formal": processed.get("summary_formal", ""),
                "summary_casual": processed.get("summary_casual", ""),
                "_pipeline_fact_checked": True,
                "fact_label": fc_res.fact_label if fc_res else "UNVERIFIED",
                "claims_payload_rows": claim_rows,
            }
            results.append(result)

            print(f"  [한국어 제목]  {(result['title_ko'] or '')[:50]}")
            print(f"  [라벨]        {result['fact_label']}  conf={result['credibility_score']:.2f}")
            print(f"  [번역]        {result['translation'][:50]}...")
        except Exception as e:
            print(f"  오류: {e}")
            logger.exception("파이프라인 항목 실패")
            if save_failed_rows:
                results.append({
                    "source": article.source,
                    "source_type": getattr(article, "source_type", "media"),
                    "category": getattr(article, "category", ""),
                    "country": getattr(article, "country", ""),
                    "title": article.title,
                    "title_ko": "",
                    "url": article.url,
                    "credibility_score": float(getattr(article, "credibility_score", 0.5) or 0.5),
                    "published_at": getattr(article, "published_at", ""),
                    "content": getattr(article, "content", ""),
                    "keywords": getattr(article, "keywords", []),
                    "translation": "",
                    "summary_formal": "",
                    "summary_casual": "",
                    "error": str(e),
                    "_pipeline_fact_checked": True,
                    "fact_label": "UNVERIFIED",
                    "claims_payload_rows": [],
                })

    return results


def main() -> int:
    parser = argparse.ArgumentParser(description="Run RSS → AI preprocessing → Supabase refresh.")
    parser.add_argument("--limit", type=int, default=10, help="Maximum RSS articles to process. Use a small number first.")
    parser.add_argument("--summary-sentences", type=int, default=3)
    parser.add_argument("--check-env", action="store_true", help="Print required env status and exit.")
    parser.add_argument("--dry-run", action="store_true", help="Run crawl/AI processing but do not write Supabase.")
    parser.add_argument(
        "--save-failed-rows",
        action="store_true",
        help="Legacy/debug mode: save failed rows with empty AI fields. Default is to skip failed rows.",
    )
    args = parser.parse_args()

    missing = print_env_report()
    if args.check_env:
        return 1 if missing else 0
    if missing:
        return 2

    from backend.save_articles import save_articles

    out = run_pipeline(
        max_articles=max(args.limit, 0),
        summary_sentences=max(args.summary_sentences, 1),
        save_failed_rows=args.save_failed_rows,
    )
    print(f"\n파이프라인 완료: {len(out)}건 처리")
    if args.dry_run:
        print("[dry-run] Supabase 저장 생략")
        return 0
    save_articles(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
