"""Helpers for importing the local Sangjun SQLite article database."""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from collections import Counter
from datetime import datetime, time, timezone
from pathlib import Path
from typing import Any


DEFAULT_SINCE = "2026-05-01"
DEFAULT_UNTIL = "2026-05-18"

FIELD_CANDIDATES: dict[str, tuple[str, ...]] = {
    "id": ("id", "article_id", "idx", "rowid"),
    "title": ("title", "title_en", "headline", "original_title"),
    "title_ko": ("title_ko", "ko_title", "korean_title", "translated_title"),
    "url": ("url", "source_url", "link", "article_url"),
    "source_url": ("source_url", "url", "link", "article_url"),
    "source": ("source", "publisher", "site", "media", "feed_source"),
    "category": ("category", "section", "topic", "label"),
    "country": ("country", "region"),
    "published_at": ("published_at", "published", "pub_date", "date", "created_at"),
    "content": ("content", "body", "article_text", "text", "crawled_text", "description"),
    "translation": ("translation_ko", "translation", "translated_text", "ko_body"),
    "summary_ko": ("summary_ko", "summary", "ko_summary"),
    "summary_formal": ("summary_formal", "formal_summary"),
    "summary_casual": ("summary_casual", "casual_summary"),
    "fact_status": ("fact_status", "fact_label", "verdict"),
    "fact_label": ("fact_label", "fact_status", "verdict"),
    "fact_confidence": ("fact_confidence", "confidence", "credibility_score"),
    "hitl_required": ("hitl_required", "human_review_required"),
    "neologism_terms": ("neologism_terms", "slang_terms"),
}

WRITE_COLUMNS: dict[str, str] = {
    "title_ko": "TEXT",
    "translation_ko": "TEXT",
    "translation": "TEXT",
    "summary_ko": "TEXT",
    "summary_formal": "TEXT",
    "summary_casual": "TEXT",
    "fact_status": "TEXT",
    "fact_label": "TEXT",
    "fact_confidence": "REAL",
    "hitl_required": "INTEGER DEFAULT 0",
    "neologism_terms": "TEXT",
    "processed_at": "TEXT",
}


def resolve_db_path(value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return Path.cwd() / path


def quote_ident(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def list_tables(conn: sqlite3.Connection) -> list[str]:
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
    ).fetchall()
    return [str(row[0]) for row in rows]


def table_columns(conn: sqlite3.Connection, table: str) -> list[str]:
    rows = conn.execute(f"PRAGMA table_info({quote_ident(table)})").fetchall()
    return [str(row[1]) for row in rows]


def detect_article_table(conn: sqlite3.Connection) -> tuple[str, list[str]]:
    best: tuple[str, list[str], int] | None = None
    for table in list_tables(conn):
        columns = table_columns(conn, table)
        lower = {column.lower() for column in columns}
        score = 0
        for logical in ("title", "url", "published_at", "content"):
            if any(candidate.lower() in lower for candidate in FIELD_CANDIDATES[logical]):
                score += 1
        if best is None or score > best[2]:
            best = (table, columns, score)
    if best is None or best[2] < 2:
        raise RuntimeError("Could not detect an article-like table in the SQLite DB.")
    return best[0], best[1]


def column_map(columns: list[str]) -> dict[str, str]:
    by_lower = {column.lower(): column for column in columns}
    result: dict[str, str] = {}
    for logical, candidates in FIELD_CANDIDATES.items():
        for candidate in candidates:
            found = by_lower.get(candidate.lower())
            if found:
                result[logical] = found
                break
    return result


def parse_bound(value: str, end_of_day: bool = False) -> datetime:
    text = value.strip()
    if not text:
        raise ValueError("empty date bound")
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        day = datetime.fromisoformat(text).date()
        return datetime.combine(day, time.max if end_of_day else time.min).replace(tzinfo=timezone.utc)
    parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def parse_published_at(value: Any) -> datetime | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    for candidate in (text, text.replace("Z", "+00:00")):
        try:
            parsed = datetime.fromisoformat(candidate)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed.astimezone(timezone.utc)
        except ValueError:
            pass
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M:%S", "%Y-%m-%d"):
        try:
            parsed = datetime.strptime(text[:19], fmt)
            return parsed.replace(tzinfo=timezone.utc)
        except ValueError:
            pass
    return None


def fetch_all_rows(conn: sqlite3.Connection, table: str) -> list[dict[str, Any]]:
    conn.row_factory = sqlite3.Row
    return [dict(row) for row in conn.execute(f"SELECT rowid AS __rowid__, * FROM {quote_ident(table)}")]


def get_value(row: dict[str, Any], cmap: dict[str, str], logical: str, default: Any = "") -> Any:
    column = cmap.get(logical)
    if not column:
        return default
    return row.get(column, default)


def in_date_range(
    row: dict[str, Any],
    cmap: dict[str, str],
    since: datetime,
    until: datetime,
    include_missing_date: bool = False,
) -> bool:
    published = parse_published_at(get_value(row, cmap, "published_at"))
    if published is None:
        return include_missing_date
    return since <= published <= until


def filter_rows(
    rows: list[dict[str, Any]],
    cmap: dict[str, str],
    since_text: str,
    until_text: str,
    include_missing_date: bool = False,
    source: str = "",
    category: str = "",
) -> list[dict[str, Any]]:
    since = parse_bound(since_text)
    until = parse_bound(until_text, end_of_day=True)
    selected = [
        row for row in rows
        if in_date_range(row, cmap, since, until, include_missing_date=include_missing_date)
    ]
    if source:
        selected = [row for row in selected if str(get_value(row, cmap, "source")).strip() == source]
    if category:
        selected = [row for row in selected if str(get_value(row, cmap, "category")).strip() == category]
    selected.sort(
        key=lambda row: parse_published_at(get_value(row, cmap, "published_at")) or datetime.min.replace(tzinfo=timezone.utc),
        reverse=True,
    )
    return selected


def is_blank(value: Any) -> bool:
    return value is None or not str(value).strip()


def counter_for(rows: list[dict[str, Any]], cmap: dict[str, str], logical: str) -> Counter[str]:
    return Counter(str(get_value(row, cmap, logical, "(missing)") or "(blank)").strip() for row in rows)


def make_url_hash(url: str) -> str:
    return hashlib.md5(url.encode("utf-8")).hexdigest()


def detect_neologisms(text: str) -> list[str]:
    candidates = [
        "HITL",
        "프롬프트 주입",
        "가드레일",
        "RAG",
        "LLMOps",
        "파인튜닝",
        "멀티모달",
        "에이전트",
    ]
    lower = text.lower()
    return [term for term in candidates if term.lower() in lower]


def json_dumps_ko(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)
