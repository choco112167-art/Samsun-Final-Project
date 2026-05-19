"""RSS 크롤러용 기사 데이터 클래스."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Article:
    title: str
    url: str
    source: str
    category: str
    country: str
    published_at: str
    content: str
    source_type: str = "media"
    credibility_score: float = 0.5
    keywords: list[str] = field(default_factory=list)
    #: 해당 피드가 ai_only=True 면 True — 크롤 단계에서 AI 키워드 게이트 생략
    ai_only_feed: bool = True
    #: Lemmy 등 title_only 피드 — 관련성 검사 시 제목 위주
    title_only_feed: bool = False
