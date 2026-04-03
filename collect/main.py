"""
三鮮 (삼선) - 메인 실행 진입점
cron으로 1시간마다 실행: 0 * * * * python main.py

실행 흐름:
  1. DB 초기화
  2. RSS 전체 수집 + AI 필터링
  3. 신뢰도 스코어 반영 후 저장
  4. 크롤링 로그 기록
  5. 어드민 통계 출력
"""

import logging
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from db.database import init_db, save_articles, save_crawl_log
from crawler.rss_crawler import RSS_FEEDS, parse_feed
from admin.stats import show_collection_stats

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


def run(db_path: str = "samsun.db"):
    logger.info("=" * 50)
    logger.info("三鮮 RSS 크롤러 시작")
    logger.info("=" * 50)

    # 1. DB 초기화
    conn = init_db(db_path)
    total_saved = 0

    # 2. 피드별 수집 + 저장
    for feed_info in RSS_FEEDS:
        source = feed_info["source"]
        try:
            articles = parse_feed(feed_info)
            saved = save_articles(conn, articles)
            total_saved += saved
            save_crawl_log(conn, source, "success", saved)
            logger.info(f"[{source}] 신규 저장: {saved}건")
        except Exception as e:
            save_crawl_log(conn, source, "error", 0, str(e))
            logger.error(f"[{source}] 오류: {e}")

    logger.info(f"\n✅ 수집 완료 — 총 신규 기사: {total_saved}건") 
    conn.close()

    # 5. 어드민 통계 출력
    show_collection_stats(db_path)


if __name__ == "__main__":
    run()