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
- Hacker News RSS 추가: hnrss.org 키워드 필터 활용
- Lemmy API 연동: RSS summary 본문 없을 때 API로 post.body 보완
- Lemmy embed_description: 외부 직접 크롤링 대신 Lemmy API의 embed_description 사용
  (JS 렌더링 사이트도 Lemmy 서버가 캐싱한 미리보기 그대로 가져옴)
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
# Lemmy 링크 포스트 미리보기
# - Lemmy API의 embed_description 사용
# - 외부 사이트 직접 크롤링 불필요
# - JS 렌더링 사이트도 Lemmy 서버가 캐싱한 값 그대로 가져옴
# - 응답 구조: post_view.post.embed_description
# ──────────────────────────────────────────

LEMMY_API_BASE = "https://lemmy.world/api/v3"


def _extract_lemmy_post_id(entry_link: str) -> str | None:
    """
    Lemmy 게시글 URL에서 post ID 추출.
    예: https://lemmy.world/post/46191199 → "46191199"
    """
    match = re.search(r'/post/(\d+)', entry_link)
    return match.group(1) if match else None


def fetch_lemmy_embed_description(post_id: str) -> str:
    """
    Lemmy API로 게시글의 embed_description 조회.
    Lemmy가 미리보기로 보여주는 텍스트와 동일한 내용.
    embed_description 없으면 body 폴백.
    """
    try:
        resp = requests.get(
            f"{LEMMY_API_BASE}/post",
            params={"id": post_id},
            timeout=5,
            headers={"User-Agent": "samsun-rss-crawler/1.0"},
        )
        resp.raise_for_status()
        post = resp.json()["post_view"]["post"]

        embed_desc = (post.get("embed_description") or "").strip()
        if embed_desc:
            return embed_desc

        # 텍스트 포스트인 경우 body 폴백
        body = (post.get("body") or "").strip()
        return body

    except Exception as e:
        logger.warning(f"[Lemmy API] embed_description 조회 실패 (post_id={post_id}): {e}")
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
# 최종 커뮤니티 수집 소스:
# - Lemmy Technology: RSS + Lemmy API post_view.post.embed_description
# - Hacker News AI/LLM/ML: hnrss.org 키워드 필터 RSS
# 초기에는 다른 커뮤니티 수집도 검토했지만, 공개 수집 안정성과 라이선싱 리스크를 고려해 제외했다.
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
        "use_lemmy_embed": True, # Lemmy API embed_description으로 본문 보완
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
    use_lemmy_embed = feed_info.get("use_lemmy_embed", False)
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

        # Lemmy 링크 포스트: Lemmy API embed_description으로 본문 보완
        # JS 렌더링 사이트도 Lemmy 서버 캐시에서 가져오므로 안정적
        if use_lemmy_embed:
            post_id = _extract_lemmy_post_id(link)
            if post_id:
                embed_desc = fetch_lemmy_embed_description(post_id)
                if embed_desc:
                    content = embed_desc
                else:
                    continue  # 미리보기 없음 → 저장 스킵
            else:
                continue  # post ID 추출 실패 → 저장 스킵

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
