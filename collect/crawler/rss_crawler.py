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
- 커뮤니티 피드: Lemmy / Hacker News(hnrss) / Product Hunt — Reddit 제거 (feat/leesangjun)
- Hacker News RSS: hnrss.org 키워드 필터 활용
- Lemmy 링크 포스트: 외부 URL의 og:description 으로 본문 보완 (feat/leesangjun)
"""

import feedparser
import html
import logging
import re
import time
from html.parser import HTMLParser
from datetime import datetime

import requests

from models.article import Article
from models.credibility import is_ai_related, score_article

logger = logging.getLogger(__name__)


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

    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


# ──────────────────────────────────────────
# Lemmy 링크 포스트 Open Graph 미리보기
# - Lemmy RSS summary 의 외부 URL 에서 og:description 추출
# ──────────────────────────────────────────


def _extract_lemmy_external_url(rss_summary: str) -> str | None:
    """
    Lemmy RSS summary 에서 외부 링크 URL 추출.
    Lemmy 도메인 / 유저 / 커뮤니티 URL 은 제외.
    """
    clean = clean_html(rss_summary)
    matches = re.findall(r"https?://\S+", clean)
    for url in matches:
        if not re.search(r"lemmy|/u/|/c/", url):
            return url.rstrip(").,]}\"'")
    return None


def fetch_og_description(external_url: str) -> str:
    """외부 URL 의 Open Graph og:description 추출."""
    try:
        resp = requests.get(
            external_url,
            timeout=5,
            headers={"User-Agent": "samsun-rss-crawler/1.0"},
        )
        resp.raise_for_status()

        og_match = re.search(
            r'<meta[^>]+property=["\']og:description["\'][^>]+content=["\'](.*?)["\']',
            resp.text,
            re.IGNORECASE | re.DOTALL,
        )
        if not og_match:
            og_match = re.search(
                r'<meta[^>]+content=["\'](.*?)["\'][^>]+property=["\']og:description["\']',
                resp.text,
                re.IGNORECASE | re.DOTALL,
            )

        if og_match:
            return html.unescape(og_match.group(1).strip())
        return ""
    except Exception as e:
        logger.warning("[OG] 미리보기 조회 실패 (%s): %s", external_url[:80], e)
        return ""


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
# - Lemmy: title_only + 선택 시 og:description 본문 보완 (use_og)
# - Hacker News: hnrss.org 키워드 필터 (ai_only=True)
# - Product Hunt: 공식 RSS
# ──────────────────────────────────────────
COMMUNITY_FEEDS = [
    {
        "source": "Lemmy Technology",
        "url": "https://lemmy.world/feeds/c/technology.xml",
        "country": "글로벌",
        "category": "AI 커뮤니티",
        "ai_only": False,
        "title_only": True,
        "source_type": "community",
        "use_og": True,
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
    {
        "source": "Product Hunt",
        "url": "https://www.producthunt.com/feed",
        "country": "글로벌",
        "category": "AI 제품",
        "ai_only": False,
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
    source = feed_info["source"]
    ai_only = feed_info.get("ai_only", False)
    use_og = feed_info.get("use_og", False)
    logger.info("[%s] 피드 수집 중...", source)

    try:
        feed = feedparser.parse(feed_info["url"])
    except Exception as e:
        logger.error("[%s] 피드 파싱 실패: %s", source, e)
        return []

    if feed.bozo and not feed.entries:
        logger.warning("[%s] 피드 이상 (bozo): %s", source, feed.bozo_exception)
        return []

    articles = []
    filtered_out = 0

    for entry in feed.entries:
        title = entry.get("title", "").strip()
        link = entry.get("link", "").strip()
        if not title or not link:
            continue

        raw_content = ""
        if hasattr(entry, "summary"):
            raw_content = entry.summary
        elif hasattr(entry, "content"):
            raw_content = entry.content[0].get("value", "")

        content = clean_html(raw_content)

        if use_og:
            external_url = _extract_lemmy_external_url(raw_content)
            if external_url:
                og_desc = fetch_og_description(external_url)
                if og_desc:
                    content = og_desc
                else:
                    filtered_out += 1
                    continue
            else:
                filtered_out += 1
                continue

        article = Article(
            title=title,
            url=link,
            source=source,
            category=feed_info["category"],
            country=feed_info["country"],
            published_at=parse_published_at(entry),
            content=content,
            source_type=feed_info.get("source_type", "media"),
            ai_only_feed=feed_info.get("ai_only", False),
            title_only_feed=feed_info.get("title_only", False),
        )

        title_only = feed_info.get("title_only", False)
        if not ai_only and not is_ai_related(article, title_only=title_only):
            filtered_out += 1
            continue

        article = score_article(article)
        articles.append(article)

    if filtered_out:
        logger.info("[%s] 필터링으로 제외 %s건", source, filtered_out)
    logger.info("[%s] %s건 수집 완료", source, len(articles))
    return articles


def fetch_all(delay: float = 1.0) -> list[Article]:
    """전체 RSS 피드 수집. delay로 서버 부하 방지."""
    all_articles = []
    for feed_info in RSS_FEEDS:
        articles = parse_feed(feed_info)
        all_articles.extend(articles)
        time.sleep(delay)
    return all_articles
