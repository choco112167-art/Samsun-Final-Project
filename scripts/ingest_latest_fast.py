"""
Fast-ish RSS ingest for local demos.

This mode runs full translation/summarization but skips deep fact-check waits by
passing `_pipeline_fact_checked=True` with a conservative source-prior label.
For the fastest list refresh, use `ingest_latest_titles.py` instead.
"""

from __future__ import annotations

import argparse
import os

from article_pipeline_common import configure_stdio, fetch_rss_articles


def main() -> int:
    configure_stdio()
    parser = argparse.ArgumentParser()
    parser.add_argument("--max", type=int, default=10)
    parser.add_argument("--summary-sentences", type=int, default=3)
    parser.add_argument("--run", action="store_true", help="Actually write completed rows to Supabase. Default is dry-run.")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing. This is the default.")
    parser.add_argument("--provider", choices=["local", "openrouter", "gemini"], help="Override LLM_PROVIDER for this run.")
    parser.add_argument("--model", help="Override provider model for this run.")
    args = parser.parse_args()

    if args.provider:
        os.environ["LLM_PROVIDER"] = args.provider
        os.environ["MODE"] = args.provider
    if args.model:
        if args.provider == "openrouter" or os.getenv("LLM_PROVIDER", "").lower() in {"openrouter", "cloud"}:
            os.environ["OPENROUTER_TRANSLATION_MODEL"] = args.model
        elif args.provider == "gemini" or os.getenv("LLM_PROVIDER", "").lower() == "gemini":
            os.environ["GEMINI_TRANSLATION_MODEL"] = args.model
        else:
            os.environ["MODEL_NAME"] = args.model

    from backend.save_articles import save_articles
    from fact_checker.channel_config import get_profile
    from pipeline.translate_summarize import estimate_sentences, translate_and_summarize

    articles = fetch_rss_articles(limit=args.max)
    rows: list[dict] = []

    for index, article in enumerate(articles, 1):
        print(f"[{index}/{len(articles)}] {article.published_at} {article.source} - {article.title[:90]}")
        text = article.content or article.title
        n = estimate_sentences(text, max_sentences=args.summary_sentences)
        processed = translate_and_summarize(text, title=article.title, summary_sentences=n)

        profile = get_profile(article.source)
        score = float(profile.credibility_score)
        label = "FACT" if score >= 0.8 else "UNVERIFIED"
        rows.append(
            {
                "source": article.source,
                "source_type": article.source_type,
                "category": article.category,
                "country": article.country,
                "title": article.title,
                "title_ko": processed.get("title") or None,
                "url": article.url,
                "credibility_score": score,
                "published_at": article.published_at,
                "content": article.content,
                "keywords": getattr(article, "keywords", []) or [],
                "translation": processed.get("translation") or "",
                "summary_formal": processed.get("summary_formal") or "",
                "summary_casual": processed.get("summary_casual") or "",
                "_pipeline_fact_checked": True,
                "fact_label": label,
                "claims_payload_rows": [
                    {
                        "claim": article.title,
                        "verdict": label,
                        "confidence": score,
                        "verification_method": "fast_ingest_source_prior",
                        "reasoning_trace": "로컬 시연용 빠른 수집: 출처 신뢰도 기반 임시 라벨",
                    }
                ],
            }
        )

    print(f"[ingest_fast] prepared={len(rows)}")
    if not args.run:
        print("[ingest_fast] dry-run: Supabase 저장 생략. 실제 반영은 --run을 붙여 실행하세요.")
        return 0
    saved = save_articles(rows)
    print(f"[ingest_fast] saved={saved}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
