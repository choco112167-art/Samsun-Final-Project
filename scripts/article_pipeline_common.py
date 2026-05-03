"""
Shared helpers for Samsun News article ingest/backfill scripts.

Important context:
The home-feed issue was not a sort bug. `/articles` already orders by
`published_at desc`; the visible problem came from missing Supabase data:
too few recent rows and many legacy rows with empty `title_ko`.
"""

from __future__ import annotations

import hashlib
import re
import os
import sys
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Iterable

import requests
from dotenv import load_dotenv
from supabase import create_client


ROOT = Path(__file__).resolve().parents[1]
COLLECT = ROOT / "collect"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
NAV_NOISE_TERMS = {
    "latest",
    "startups",
    "venture",
    "apple",
    "security",
    "apps",
    "events",
    "podcasts",
    "newsletters",
    "advertising",
    "careers",
    "privacy",
    "terms",
}

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(COLLECT) not in sys.path:
    sys.path.insert(0, str(COLLECT))


def configure_stdio() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")


def load_project_env() -> None:
    load_dotenv(ROOT / ".env")


def require_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required env: {name}")
    return value


def get_supabase_client():
    load_project_env()
    supabase_url = require_env("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY") or os.getenv("SUPABASE_ANON_KEY", "")
    if not supabase_key.strip():
        raise RuntimeError("Missing required env: SUPABASE_KEY or SUPABASE_ANON_KEY")
    return create_client(supabase_url, supabase_key)


def fetch_rss_articles(limit: int | None = None):
    from crawler.rss_crawler import fetch_all

    articles = fetch_all()
    if limit is not None:
        return articles[: max(limit, 0)]
    return articles


def make_url_hash(url: str) -> str:
    return hashlib.md5(url.encode("utf-8")).hexdigest()


def article_hashes(articles: Iterable[object]) -> list[str]:
    hashes: list[str] = []
    for article in articles:
        url = getattr(article, "url", "") or ""
        if url:
            hashes.append(make_url_hash(url))
    return hashes


def existing_article_hashes(sb, hashes: list[str]) -> set[str]:
    if not hashes:
        return set()
    result = sb.table("articles").select("url_hash").in_("url_hash", hashes).execute()
    return {row["url_hash"] for row in (result.data or []) if row.get("url_hash")}


def parse_published_at(value: str | None) -> str | None:
    """Normalize RSS/DB timestamps to ISO strings Supabase accepts."""
    if not value:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        normalized = text.replace("Z", "+00:00")
        return datetime.fromisoformat(normalized).isoformat()
    except ValueError:
        return text


def title_model(default: str = "google/gemini-2.5-flash-lite") -> str:
    return os.getenv("OPENROUTER_TITLE_MODEL") or os.getenv("OPENROUTER_MODEL", default)


def generate_title_ko(title: str, model: str | None = None) -> str:
    api_key = require_env("OPENROUTER_API_KEY")
    prompt = (
        "Translate the news headline into natural Korean. "
        "Return only the Korean headline. Preserve product names, company names, "
        "model names, and technical terms when appropriate.\n\n"
        f"Headline: {title}"
    )
    response = requests.post(
        OPENROUTER_URL,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost:5173",
            "X-Title": "Samsun News article pipeline",
        },
        json={
            "model": model or title_model(),
            "messages": [
                {
                    "role": "system",
                    "content": "You are a careful Korean technology news headline translator.",
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,
            "max_tokens": 120,
        },
        timeout=45,
    )
    response.raise_for_status()
    data = response.json()
    text = data["choices"][0]["message"]["content"].strip()
    return text.strip('"').strip()


def quick_article_row(article, title_ko: str, label: str, score: float) -> dict:
    return {
        "url_hash": make_url_hash(article.url),
        "url": article.url,
        "title": article.title,
        "title_ko": title_ko or None,
        "source": article.source,
        "source_type": article.source_type,
        "category": article.category,
        "country": article.country,
        "keywords": getattr(article, "keywords", []) or [],
        "published_at": parse_published_at(getattr(article, "published_at", None)),
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "content": getattr(article, "content", "") or "",
        "credibility_score": score,
        "fact_label": label,
        # Fast/demo ingest intentionally leaves body translation and summaries empty.
        # The frontend must show a prepared/hidden state, never the title as body fallback.
        "translation": "",
        "summary_formal": "",
        "summary_casual": "",
    }


def upsert_article_rows(sb, rows: list[dict]) -> int:
    if not rows:
        return 0
    add_ai_metadata_if_supported(sb, rows)
    sb.table("articles").upsert(rows, on_conflict="url_hash").execute()
    return len(rows)


def supported_article_columns(sb, candidates: Iterable[str]) -> set[str]:
    supported: set[str] = set()
    for column in candidates:
        try:
            sb.table("articles").select(column).limit(1).execute()
            supported.add(column)
        except Exception:
            pass
    return supported


def add_ai_metadata_if_supported(sb, rows: list[dict], provider: str = "pending") -> None:
    """Attach AI status metadata only when the DB migration exists."""
    columns = supported_article_columns(
        sb,
        (
            "ai_status",
            "ai_provider",
            "ai_model",
            "ai_error",
            "content_source",
            "content_chars",
            "translation_chars",
        ),
    )
    if not columns:
        return
    for row in rows:
        has_outputs = all(not is_blank(row.get(field)) for field in ("translation", "summary_formal", "summary_casual"))
        if "ai_status" in columns:
            row.setdefault("ai_status", "completed" if has_outputs else "pending")
        if "ai_provider" in columns:
            row.setdefault("ai_provider", provider if has_outputs else None)
        if "ai_model" in columns:
            row.setdefault("ai_model", None)
        if "ai_error" in columns:
            row.setdefault("ai_error", None)
        if "content_source" in columns:
            row.setdefault("content_source", "rss_summary" if row.get("content") else None)
        if "content_chars" in columns:
            row.setdefault("content_chars", len(str(row.get("content") or "")))
        if "translation_chars" in columns:
            row.setdefault("translation_chars", len(str(row.get("translation") or "")))


def is_blank(value: object) -> bool:
    return value is None or not str(value).strip()


def body_quality_warning(text: str) -> str:
    cleaned = " ".join((text or "").split())
    if not cleaned:
        return "empty"
    lower = cleaned.lower()
    first_words = re.findall(r"[a-zA-Z]+", lower[:500])
    if first_words:
        noise_hits = sum(1 for word in first_words if word in NAV_NOISE_TERMS)
        if noise_hits >= 6:
            return f"navigation-noise-heavy({noise_hits})"
    if len(cleaned) < 800:
        return f"too-short({len(cleaned)})"
    sentences = re.split(r"(?<=[.!?])\s+", cleaned)
    if len([s for s in sentences if len(s) > 40]) < 3:
        return "not-enough-article-sentences"
    return ""


class _ArticleHTMLParser(HTMLParser):
    """Tiny fallback article-body extractor for backfill jobs."""

    def __init__(self) -> None:
        super().__init__()
        self._capture = False
        self._skip_depth = 0
        self._chunks: list[str] = []

    def handle_starttag(self, tag: str, attrs):
        if tag in {"script", "style", "noscript", "svg"}:
            self._skip_depth += 1
            return
        if self._skip_depth:
            return
        if tag in {"p", "h1", "h2", "li"}:
            self._capture = True

    def handle_endtag(self, tag: str):
        if tag in {"script", "style", "noscript", "svg"} and self._skip_depth:
            self._skip_depth -= 1
            return
        if tag in {"p", "h1", "h2", "li"}:
            self._capture = False
            self._chunks.append("\n")

    def handle_data(self, data: str):
        if self._capture and not self._skip_depth:
            text = data.strip()
            if text:
                self._chunks.append(text)

    def text(self) -> str:
        joined = " ".join(self._chunks)
        joined = re.sub(r"\s+", " ", joined).strip()
        return joined


def fetch_article_body_from_url(url: str, timeout: int = 20) -> str:
    """Best-effort fallback when `articles.content` is empty.

    This intentionally avoids title fallback: if we cannot extract a real body,
    callers should skip the row and log the reason.
    """
    if is_blank(url):
        return ""
    response = requests.get(
        str(url),
        timeout=timeout,
        headers={
            "User-Agent": "SamsunNewsBot/1.0 (+https://github.com/choco112167-art/Samsun-Final-Project)",
            "Accept": "text/html,application/xhtml+xml",
        },
    )
    response.raise_for_status()
    html = response.text

    try:
        import trafilatura

        extracted = trafilatura.extract(
            html,
            url=str(url),
            include_comments=False,
            include_tables=False,
            favor_precision=True,
        )
        if extracted and not body_quality_warning(extracted):
            return extracted.strip()
    except Exception:
        pass

    try:
        from readability import Document

        article_html = Document(html).summary()
        parser = _ArticleHTMLParser()
        parser.feed(article_html)
        extracted = parser.text()
        if extracted and not body_quality_warning(extracted):
            return extracted
    except Exception:
        pass

    parser = _ArticleHTMLParser()
    parser.feed(html)
    return parser.text()
