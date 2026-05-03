"""
Very fast RSS ingest for refreshing the home feed before a demo.

Fast mode fills list-critical fields only: title, title_ko, source, category,
published_at, original URL (`url`) and empty translation/summary fields.
It uses upsert on `url_hash`, so rerunning does not create duplicates.
"""

from __future__ import annotations

import argparse
import sys
import time

from article_pipeline_common import (
    article_hashes,
    configure_stdio,
    existing_article_hashes,
    fetch_rss_articles,
    generate_title_ko,
    get_supabase_client,
    quick_article_row,
    title_model,
    upsert_article_rows,
)


def main() -> int:
    configure_stdio()
    parser = argparse.ArgumentParser()
    parser.add_argument("--max", type=int, default=20)
    parser.add_argument("--sleep", type=float, default=0.1)
    parser.add_argument("--model", default=title_model())
    parser.add_argument("--skip-existing", action="store_true")
    args = parser.parse_args()

    sb = get_supabase_client()
    articles = fetch_rss_articles(limit=args.max)
    existing = existing_article_hashes(sb, article_hashes(articles))

    from fact_checker.channel_config import get_profile

    rows: list[dict] = []
    for index, article in enumerate(articles, 1):
        url_hash = article_hashes([article])[0]
        if args.skip_existing and url_hash in existing:
            print(f"[{index}/{len(articles)}] skip existing - {article.title[:80]}")
            continue

        title_ko = generate_title_ko(article.title, model=args.model)
        profile = get_profile(article.source)
        score = float(profile.credibility_score)
        label = "FACT" if score >= 0.8 else "UNVERIFIED"
        print(f"[{index}/{len(articles)}] {article.published_at} {article.title[:70]} -> {title_ko[:70]}")
        rows.append(quick_article_row(article, title_ko=title_ko, label=label, score=score))
        if args.sleep > 0:
            time.sleep(args.sleep)

    count = upsert_article_rows(sb, rows)
    print(f"[ingest_titles] upserted={count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
