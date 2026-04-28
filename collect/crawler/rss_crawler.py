"""
三鮮 (삼선) - RSS 크롤러
담당: 이상준 (데이터 수집)
- 언론사 / 커뮤니티 RSS 피드 수집
- AI 관련성 필터링 (ai_only 플래그로 피드별 필터 강도 조절)
- 날짜 형식 통일 (마이크로초 제거)
- cron으로 1시간마다 독립 실행

[수정 이력]
- Nikkei RSS URL → AI/반도체 전용 카테고리로 교체
- ai_only 플래그 추가: AI 전용 피드는 필터 건너뜀 (속도 향상)
- 날짜 형식: strftime으로 마이크로초 제거
- 필터링된 기사 수 로그 출력
- source_type 필드 추가: 'media' | 'community'
- 커뮤니티 피드 추가: Product Hunt
- Reddit 제거: 2026-03-26 정책 변경으로 앱 등록 및 수집 불가
- Hacker News RSS 추가: hnrss.org 키워드 필터 활용
"""

import feedparser
import time
import logging
import re
from html.parser import HTMLParser
from datetime import datetime

from models.article import Article
from models.credibility import is_ai_related, score_article

logger = logging.getLogger(__name__)
import requests

class _HTMLStripper(HTMLParser):
    """HTML 태그 제거용 파서."""
    def __init__(self):
        super().__init__()
        self.reset()
        self.fed = []

    def handle_data(self, d):
        self.fed.append(d)

    def get_data(self):
        return " ".join(self.fed)


def clean_html(text: str) -> str:
    """
    HTML 태그 / 엔티티 제거 후 순수 텍스트 반환.
    외부 라이브러리 불필요 (표준 html.parser 사용).
    """
    if not text:
        return ""
    stripper = _HTMLStripper()
    try:
        stripper.feed(text)
        text = stripper.get_data()
    except Exception:
        text = re.sub(r"<[^>]+>", " ", text)

    import html
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


# ──────────────────────────────────────────
# 언론사 RSS 피드
# ──────────────────────────────────────────
MEDIA_FEEDS = [
    {
        "source": "TechCrunch",
        "url": "https://techcrunch.com/category/artificial-intelligence/feed/",
        "country": "미국",
        "category": "AI/스타트업",
        "ai_only": True,
        "source_type": "media",
    },
    {
        "source": "MIT Technology Review",
        "url": "https://www.technologyreview.com/feed/",
        "country": "미국",
        "category": "AI 심층",
        "ai_only": False,
        "source_type": "media",
    },
    {
        "source": "The Verge",
        "url": "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml",
        "country": "미국",
        "category": "테크 전반",
        "ai_only": True,
        "source_type": "media",
    },
    {
        "source": "VentureBeat AI",
        "url": "https://venturebeat.com/feed",
        "country": "미국",
        "category": "AI 비즈니스",
        "ai_only": False,
        "source_type": "media",
    },
    {
        "source": "The Guardian Tech",
        "url": "https://www.theguardian.com/technology/artificialintelligenceai/rss",
        "country": "영국",
        "category": "AI 윤리",
        "ai_only": True,
        "source_type": "media",
    },
    {
        "source": "IEEE Spectrum",
        "url": "https://spectrum.ieee.org/feeds/topic/artificial-intelligence.rss",
        "country": "글로벌",
        "category": "AI/반도체",
        "ai_only": True,
        "source_type": "media",
    },
    {
        "source": "The Decoder",
        "url": "https://the-decoder.com/feed/",
        "country": "독일/글로벌",
        "category": "AI 심층/기술",
        "ai_only": True,
        "source_type": "media",
    },
]

# ──────────────────────────────────────────
# 커뮤니티 RSS 피드
# hnrss.org: Hacker News 공식 서드파티 RSS
# - q= 파라미터로 키워드 필터링
# - ai_only=True로 추가 필터 스킵 (URL 자체가 이미 필터됨)
# ──────────────────────────────────────────
COMMUNITY_FEEDS = [
    {
        "source": "Lemmy Technology",
        "url": "https://lemmy.world/feeds/c/technology.xml",
        "country": "글로벌",
        "category": "AI 커뮤니티",
        "ai_only": False,        # 전체 글 수집 후 필터링
        "title_only": True,      # 제목만 보고 AI 관련 여부 판단
        "source_type": "community",
    },
    {
        "source": "Hacker News AI",
        "url": "https://hnrss.org/newest?q=artificial+intelligence",
        "country": "글로벌",
        "category": "AI 커뮤니티",
        "ai_only": True,
        "source_type": "community",
    },
    {
        "source": "Hacker News LLM",
        "url": "https://hnrss.org/newest?q=LLM",
        "country": "글로벌",
        "category": "LLM 커뮤니티",
        "ai_only": True,
        "source_type": "community",
    },
    {
        "source": "Hacker News ML",
        "url": "https://hnrss.org/newest?q=machine+learning",
        "country": "글로벌",
        "category": "AI 연구",
        "ai_only": True,
        "source_type": "community",
    },
]

# 전체 피드 (main.py에서 사용)
RSS_FEEDS = MEDIA_FEEDS + COMMUNITY_FEEDS


def parse_published_at(entry) -> str:
    """발행일 파싱. 마이크로초 없는 ISO 형식으로 통일."""
    fmt = "%Y-%m-%dT%H:%M:%S"
    if hasattr(entry, "published_parsed") and entry.published_parsed:
        return datetime(*entry.published_parsed[:6]).strftime(fmt)
    elif hasattr(entry, "updated_parsed") and entry.updated_parsed:
        return datetime(*entry.updated_parsed[:6]).strftime(fmt)
    else:
        return datetime.utcnow().strftime(fmt)


def parse_feed(feed_info: dict) -> list[Article]:
    """RSS 피드 파싱 → AI 관련 기사만 필터링하여 반환."""
    source  = feed_info["source"]
    ai_only = feed_info.get("ai_only", False)
    logger.info(f"[{source}] 피드 수집 중...")

    try:
        feed = feedparser.parse(feed_info["url"])
    except Exception as e:
        logger.error(f"[{source}] 피드 파싱 실패: {e}")
        return []

    if feed.bozo and not feed.entries:
        logger.warning(f"[{source}] 피드 이상 (bozo): {feed.bozo_exception}")
        return []

    articles = []
    filtered_out = 0

    for entry in feed.entries:
        title = entry.get("title", "").strip()
        link  = entry.get("link", "").strip()
        if not title or not link:
            continue

        raw_content = ""
        if hasattr(entry, "summary"):
            raw_content = entry.summary
        elif hasattr(entry, "content"):
            raw_content = entry.content[0].get("value", "")

        content = clean_html(raw_content)

        article = Article(
            title=title,
            url=link,
            source=source,
            category=feed_info["category"],
            country=feed_info["country"],
            published_at=parse_published_at(entry),
            content=content,
            source_type=feed_info.get("source_type", "media"),
        )
      
        title_only = feed_info.get("title_only", False)
        if not ai_only and not is_ai_related(article, title_only=title_only):
            filtered_out += 1
            continue

        article = score_article(article)
        articles.append(article)


    return articles


def fetch_all(delay: float = 1.0) -> list[Article]:
    """전체 RSS 피드 수집. delay로 서버 부하 방지."""
    all_articles = []
    for feed_info in RSS_FEEDS:
        articles = parse_feed(feed_info)
        all_articles.extend(articles)
        time.sleep(delay)
    return all_articles
