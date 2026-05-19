"""
三鮮 (삼선) - 메인 실행 진입점
cron으로 1시간마다 실행: 0 * * * * python collect/main.py

실행 흐름:
  1. RSS 전체 수집 + AI 필터링 + 신뢰도 스코어
  2. 기사별 번역 + 요약 (Qwen3.5:4b via Ollama)
  3. Supabase 배치 upsert (팩트체크 + 임베딩 포함)
"""

import logging
import sys
import os

# collect/ 디렉토리 (crawler, models, classifier 임포트용)
sys.path.insert(0, os.path.dirname(__file__))
# 프로젝트 루트 (backend, pipeline 임포트용)
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from crawler.rss_crawler import fetch_all
from pipeline.translate_summarize import translate_and_summarize, estimate_sentences
from backend.save_articles import save_articles

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


def run():
    logger.info("=" * 50)
    logger.info("三鮮 RSS 크롤러 시작")
    logger.info("=" * 50)

    # 1. RSS 전체 수집
    articles = fetch_all()
    logger.info(f"수집 완료: {len(articles)}건")

    if not articles:
        logger.info("신규 기사 없음 — 종료")
        return

    # 2. 번역 + 요약 → 배치 딕셔너리 구성
    batch = []
    for i, article in enumerate(articles, 1):
        logger.info(f"[{i}/{len(articles)}] 번역·요약 중: {article.title[:60]}")
        try:
            # num_ctx=8192 초과 방지: 시스템 프롬프트(~375토큰) + 출력(~2000토큰) 감안
            # 10000자 ≈ 2500토큰 → 합계 ~4875토큰으로 8192 내 안전
            content = article.content[:10000] if len(article.content) > 10000 else article.content
            n = estimate_sentences(content)
            result = translate_and_summarize(
                text=content,
                title=article.title,
                summary_sentences=n,
            )
        except Exception as e:
            logger.error(f"번역·요약 실패 ({article.source}): {e}")
            result = {"title_ko": "", "translation": "", "summary_formal": "", "summary_casual": ""}

        batch.append({
            "url":               article.url,
            "title":             article.title,
            "title_ko":          result.get("title", ""),
            "source":            article.source,
            "source_type":       article.source_type,
            "category":          article.category or result.get("category"),
            "country":           article.country,
            "keywords":          article.keywords,
            "published_at":      article.published_at,
            "content":           article.content,
            "credibility_score": article.credibility_score,
            "translation":       result.get("translation", ""),
            "summary_formal":    result.get("summary_formal", ""),
            "summary_casual":    result.get("summary_casual", ""),
        })

    # 3. Supabase 저장 (팩트체크 + 임베딩 포함)
    saved = save_articles(batch)
    logger.info(f"저장 완료: {saved}건")


if __name__ == "__main__":
    run()
