import sys
import os
sys.stdout.reconfigure(encoding='utf-8')

# 이상준 RSS 모듈 경로 추가
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'collect'))

from crawler.rss_crawler import fetch_all
from pipeline.translate_summarize import translate_and_summarize, estimate_sentences


def run_pipeline(max_articles: int = 10, summary_sentences: int = 3):
    """RSS 수집(이상준) → 번역+요약(이동우) 통합 파이프라인"""

    print("=" * 60)
    print("[ 1단계: RSS 수집 (이상준 파트) ]")
    print("=" * 60)
    articles = fetch_all()
    if max_articles:
        articles = articles[:max_articles]
    print(f"\n총 {len(articles)}건 수집 완료\n")

    print("=" * 60)
    print("[ 2단계: 번역 + 요약 (이동우 파트) ]")
    print("=" * 60)

    results = []
    for i, article in enumerate(articles, 1):
        print(f"\n[{i}/{len(articles)}] [{article.source}] {article.title[:60]}...")
        try:
            text = article.content or article.title
            n = estimate_sentences(text, max_sentences=summary_sentences)
            processed = translate_and_summarize(
                text=text,
                title=article.title,
                summary_sentences=n,
            )
            result = {
                "source":            article.source,
                "source_type":       article.source_type,
                "category":          article.category,
                "country":           article.country,
                "title":             processed.get("title", ""),   # 한국어 제목
                "title_en":          article.title,                # 영어 원제
                "url":               article.url,
                "credibility_score": article.credibility_score,
                "published_at":      article.published_at,
                "content":           article.content,
                "keywords":          getattr(article, "keywords", []),
                "translation":       processed.get("translation", ""),
                "summary_formal":    processed.get("summary_formal", ""),
                "summary_casual":    processed.get("summary_casual", ""),
            }
            results.append(result)

            print(f"  [한국어 제목]  {result['title'][:50]}")
            print(f"  [번역]        {result['translation'][:50]}...")
            print(f"  [격식체 요약]  {result['summary_formal'][:50]}...")
            print(f"  [일상체 요약]  {result['summary_casual'][:50]}...")
        except Exception as e:
            print(f"  오류: {e}")
            results.append({
                "source":         article.source,
                "title":          "",
                "title_en":       article.title,
                "url":            article.url,
                "translation":    "",
                "summary_formal": "",
                "summary_casual": "",
                "error":          str(e),
            })

    return results


if __name__ == "__main__":
    from backend.save_articles import save_articles
    results = run_pipeline(max_articles=10, summary_sentences=3)
    print(f"\n파이프라인 완료: {len(results)}건 처리")
    save_articles(results)
