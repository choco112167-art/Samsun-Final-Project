"""
三鮮 (삼선) - 어드민 통계
담당: 강주찬 (백엔드)
- 수집 현황 대시보드 (언론사 / 커뮤니티 분리 출력)
- 크롤링 로그 조회
- FastAPI 어드민 엔드포인트에서 import
"""

import sqlite3
from db.database import get_connection, DB_PATH


def _print_source_stats(conn: sqlite3.Connection, source_type: str):
    """source_type별 통계 출력 내부 함수."""
    rows = conn.execute("""
        SELECT source, COUNT(*) as cnt, MAX(published_at) as latest
        FROM articles
        WHERE source_type = ?
        GROUP BY source
        ORDER BY cnt DESC
    """, (source_type,)).fetchall()

    for row in rows:
        print(f"{row['source']:<28} {row['cnt']:>6}건   {row['latest'] or 'N/A'}")


def show_collection_stats(db_path: str = DB_PATH):
    """언론사 / 커뮤니티 분리 수집 현황 출력."""
    conn = get_connection(db_path)

    # 언론사
    print(f"\n{'[언론사]'}")
    print(f"{'출처':<28} {'기사 수':>6}   {'최신 기사'}")
    print("-" * 62)
    _print_source_stats(conn, "media")

    # 커뮤니티
    print(f"\n{'[커뮤니티]'}")
    print(f"{'출처':<28} {'기사 수':>6}   {'최신 기사'}")
    print("-" * 62)
    _print_source_stats(conn, "community")

    conn.close()


def show_crawl_logs(db_path: str = DB_PATH, limit: int = 20):
    """최근 크롤링 로그 조회."""
    conn = get_connection(db_path)
    rows = conn.execute("""
        SELECT source, status, count, message, logged_at
        FROM crawl_logs
        ORDER BY logged_at DESC
        LIMIT ?
    """, (limit,)).fetchall()
    conn.close()

    print(f"\n{'출처':<28} {'상태':>8}   {'건수':>6}   {'시각'}")
    print("-" * 68)
    for row in rows:
        print(f"{row['source']:<28} {row['status']:>8}   {row['count']:>6}건   {row['logged_at']}")


def get_credibility_distribution(db_path: str = DB_PATH) -> list:
    """신뢰도 점수 분포 조회."""
    conn = get_connection(db_path)
    rows = conn.execute("""
        SELECT source, source_type,
               ROUND(AVG(credibility_score), 2) as avg_score,
               COUNT(*) as cnt
        FROM articles
        GROUP BY source
        ORDER BY avg_score DESC
    """).fetchall()
    conn.close()
    return rows