"""
三鮮 (삼선) - DB 관리
담당: 강주찬 (백엔드)
- DB 초기화
- 기사 저장 / 조회
- FastAPI에서 import해서 사용
"""

import sqlite3
import logging
from typing import Optional

logger = logging.getLogger(__name__)

DB_PATH = "samsun.db"


def get_connection(db_path: str = DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: str = DB_PATH) -> sqlite3.Connection:
    conn = get_connection(db_path)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS articles (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            url_hash            TEXT UNIQUE,
            title               TEXT NOT NULL,
            url                 TEXT NOT NULL,
            source              TEXT,
            source_type         TEXT DEFAULT 'media',   -- 'media' | 'community'
            category            TEXT,
            country             TEXT,
            content             TEXT,
            published_at        TEXT,
            title_ko            TEXT,
            translation_ko      TEXT,
            summary_ko          TEXT,
            translation_formal  TEXT,
            translation_casual  TEXT,
            credibility_score   REAL DEFAULT 0.0,
            created_at          TEXT DEFAULT (datetime('now')),
            summary_en          TEXT,                           -- BART 영문 요약
            rouge_score         REAL DEFAULT NULL,              -- 요약 ROUGE-L 스코어
            bleu_score          REAL DEFAULT NULL,              -- 번역 BLEU 스코어
            eval_checked        INTEGER DEFAULT 0               -- 사람 검수 완료 (0/1)
        )
    """)

    # 기존 DB 마이그레이션
    existing = [row[1] for row in conn.execute("PRAGMA table_info(articles)").fetchall()]
    migrations = {
        "title_ko":       "ALTER TABLE articles ADD COLUMN title_ko TEXT",
        "translation_ko": "ALTER TABLE articles ADD COLUMN translation_ko TEXT",
        "source_type":    "ALTER TABLE articles ADD COLUMN source_type TEXT DEFAULT 'media'",
        "summary_en":     "ALTER TABLE articles ADD COLUMN summary_en TEXT",
        "rouge_score":    "ALTER TABLE articles ADD COLUMN rouge_score REAL DEFAULT NULL",
        "bleu_score":     "ALTER TABLE articles ADD COLUMN bleu_score REAL DEFAULT NULL",
        "eval_checked":   "ALTER TABLE articles ADD COLUMN eval_checked INTEGER DEFAULT 0",
    }
    for col, sql in migrations.items():
        if col not in existing:
            conn.execute(sql)
            logger.info(f"컬럼 추가: {col}")

    conn.execute("""
        CREATE TABLE IF NOT EXISTS crawl_logs (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            source     TEXT,
            status     TEXT,
            count      INTEGER DEFAULT 0,
            message    TEXT,
            logged_at  TEXT DEFAULT (datetime('now'))
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS user_logs (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            action      TEXT,
            article_id  INTEGER,
            query       TEXT,
            logged_at   TEXT DEFAULT (datetime('now'))
        )
    """)

    conn.commit()
    logger.info(f"DB 초기화 완료: {db_path}")
    return conn


def save_articles(conn: sqlite3.Connection, articles: list) -> int:
    """기사 저장 (중복 제거 포함). 저장된 건수 반환."""
    saved = 0
    for a in articles:
        try:
            conn.execute("""
                INSERT OR IGNORE INTO articles
                    (url_hash, title, url, source, source_type, category, country,
                     content, published_at, credibility_score)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                a.url_hash, a.title, a.url, a.source, a.source_type,
                a.category, a.country, a.content,
                a.published_at, a.credibility_score
            ))
            if conn.execute("SELECT changes()").fetchone()[0]:
                saved += 1
        except sqlite3.Error as e:
            logger.error(f"저장 실패 ({a.url}): {e}")
    conn.commit()
    return saved


def save_crawl_log(conn: sqlite3.Connection, source: str, status: str,
                   count: int = 0, message: str = ""):
    conn.execute("""
        INSERT INTO crawl_logs (source, status, count, message)
        VALUES (?, ?, ?, ?)
    """, (source, status, count, message))
    conn.commit()


def get_articles(conn: sqlite3.Connection, limit: int = 20,
                 category: Optional[str] = None,
                 source: Optional[str] = None,
                 source_type: Optional[str] = None) -> list:
    query = "SELECT * FROM articles WHERE 1=1"
    params = []
    if category:
        query += " AND category = ?"
        params.append(category)
    if source:
        query += " AND source = ?"
        params.append(source)
    if source_type:
        query += " AND source_type = ?"
        params.append(source_type)
    query += " ORDER BY published_at DESC LIMIT ?"
    params.append(limit)
    return conn.execute(query, params).fetchall()


def get_article_by_id(conn: sqlite3.Connection, article_id: int):
    return conn.execute(
        "SELECT * FROM articles WHERE id = ?", (article_id,)
    ).fetchone()


def update_translation(conn: sqlite3.Connection, article_id: int,
                       title_ko: str, translation_ko: str):
    conn.execute("""
        UPDATE articles
        SET title_ko = ?, translation_ko = ?
        WHERE id = ?
    """, (title_ko, translation_ko, article_id))
    conn.commit()


def get_untranslated_articles(conn: sqlite3.Connection, limit: int = 50) -> list:
    return conn.execute("""
        SELECT id, title, content FROM articles
        WHERE (title_ko IS NULL OR title_ko = '')
        AND (content IS NOT NULL AND content != '')
        ORDER BY published_at DESC
        LIMIT ?
    """, (limit,)).fetchall()

def get_unsummarized_articles(conn: sqlite3.Connection, limit: int = 50) -> list:
    """요약 안 된 기사 조회 (summarizer용)."""
    return conn.execute("""
        SELECT id, title, content FROM articles
        WHERE (summary_en IS NULL OR summary_en = '')
        AND (content IS NOT NULL AND content != '')
        ORDER BY published_at DESC
        LIMIT ?
    """, (limit,)).fetchall()


def update_summary(conn: sqlite3.Connection, article_id: int, summary_en: str):
    """영문 요약 결과 저장."""
    conn.execute("""
        UPDATE articles SET summary_en = ? WHERE id = ?
    """, (summary_en, article_id))
    conn.commit()


def get_untranslated_summaries(conn: sqlite3.Connection, limit: int = 50) -> list:
    """요약은 됐지만 번역 안 된 기사 조회 (translator용)."""
    return conn.execute("""
        SELECT id, title, summary_en FROM articles
        WHERE (summary_en IS NOT NULL AND summary_en != '')
        AND (translation_ko IS NULL OR translation_ko = '')
        ORDER BY published_at DESC
        LIMIT ?
    """, (limit,)).fetchall()


def update_translation_full(conn: sqlite3.Connection, article_id: int,
                             title_ko: str, translation_ko: str):
    """번역 결과 저장 (제목 + 한국어 번역)."""
    conn.execute("""
        UPDATE articles SET title_ko = ?, translation_ko = ? WHERE id = ?
    """, (title_ko, translation_ko, article_id))
    conn.commit()


def update_eval_scores(conn: sqlite3.Connection, article_id: int,
                       rouge_score: float = None, bleu_score: float = None):
    """ROUGE/BLEU 스코어 저장."""
    conn.execute("""
        UPDATE articles SET rouge_score = ?, bleu_score = ? WHERE id = ?
    """, (rouge_score, bleu_score, article_id))
    conn.commit()