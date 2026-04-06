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
- 커뮤니티 피드 추가: Reddit, Product Hunt
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
    Reddit의 <div class="md">, <table> 등 모두 처리.
    외부 라이브러리 불필요 (표준 html.parser 사용).
    """
    if not text:
        return ""
    # HTML 태그 파싱으로 텍스트 추출
    stripper = _HTMLStripper()
    try:
        stripper.feed(text)
        text = stripper.get_data()
    except Exception:
        # 파싱 실패 시 정규식으로 폴백
        text = re.sub(r"<[^>]+>", " ", text)

    # HTML 엔티티 처리 (&#32; &amp; &lt; 등)
    import html
    text = html.unescape(text)

    # 연속 공백 / 줄바꿈 정리
    text = re.sub(r"\s+", " ", text).strip()
    return text


def clean_reddit_content(text: str) -> str:
    """
    Reddit RSS 메타 텍스트 / 이미지 URL 제거.
    - preview.redd.it 이미지 URL 제거 (앞/중간 모두)
    - 'submitted by /u/...' 이후 전부 제거
    - [link], [comments] 잔여 제거
    - 정리 후 50자 미만이면 본문 없는 게시글로 판단 → 빈 문자열
    """
    if not text:
        return ""
    # preview.redd.it 썸네일 URL만 제거 (Reddit 자동 생성 이미지, 본문과 무관)
    # 일반 URL은 본문 내용일 수 있으므로 유지
    cleaned = re.sub(r"https?://preview\.redd\.it/\S+", "", text).strip()
    # 'submitted by /u/...' 이후 전부 제거
    cleaned = re.sub(r"\s*submitted by\s+/u/\S+.*$", "", cleaned, flags=re.DOTALL).strip()
    # [link], [comments] 잔여 제거
    cleaned = re.sub(r"\[link\]|\[comments\]", "", cleaned).strip()
    # 연속 공백 정리
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    # 50자 미만이면 본문 없는 링크 공유 게시글 → 빈 문자열
    return cleaned if len(cleaned) >= 50 else ""


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
# Reddit: .rss 붙이면 RSS 제공
# Product Hunt: 공식 RSS 제공
# ──────────────────────────────────────────
COMMUNITY_FEEDS = [
    {
        "source": "Reddit r/artificial",
        "url": "https://www.reddit.com/r/artificial/.rss",
        "country": "글로벌",
        "category": "AI 커뮤니티",
        "ai_only": True,
        "source_type": "community",
    },
    {
        "source": "Reddit r/MachineLearning",
        "url": "https://www.reddit.com/r/MachineLearning/.rss",
        "country": "글로벌",
        "category": "AI 연구",
        "ai_only": True,
        "source_type": "community",
    },
    {
        "source": "Reddit r/LocalLLaMA",
        "url": "https://www.reddit.com/r/LocalLLaMA/.rss",
        "country": "글로벌",
        "category": "LLM 커뮤니티",
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
    source   = feed_info["source"]
    ai_only  = feed_info.get("ai_only", False)
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

        # 커뮤니티 소스별 후처리
        source_url = feed_info["url"].lower()
        if "reddit" in source_url:
            content = clean_reddit_content(content)
            # 본문 없는 링크 공유 게시글은 수집 제외
            if not content:
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
        )

        # AI 전용 피드가 아니면 키워드 필터 적용
        title_only = feed_info.get("title_only", False)
        if not ai_only and not is_ai_related(article, title_only=title_only):
            filtered_out += 1
            continue

        article = score_article(article)
        articles.append(article)

    if filtered_out:
        logger.info(f"[{source}] AI 무관 기사 {filtered_out}건 필터링됨")
    logger.info(f"[{source}] {len(articles)}건 수집 완료")
    return articles


def fetch_all(delay: float = 1.0) -> list[Article]:
    """전체 RSS 피드 수집. delay로 서버 부하 방지."""
    all_articles = []
    for feed_info in RSS_FEEDS:
        articles = parse_feed(feed_info)
        all_articles.extend(articles)
        time.sleep(delay)
    return all_articles
