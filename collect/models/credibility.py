"""
三鮮 (삼선) - 신뢰도 스코어링
담당: 이상준 (데이터 수집) / 강주찬 (백엔드)
- 출처별 기본 신뢰도
- AI 관련성 키워드 필터 (일반 / 제목 전용 엄격 모드)
- 루머/팩트 구분 (향후 Claude API 연동 예정)
"""

from models.article import Article

# ──────────────────────────────────────────
# 출처별 기본 신뢰도 (어드민에서 조정 가능)
# ──────────────────────────────────────────
SOURCE_CREDIBILITY: dict[str, float] = {
    "MIT Technology Review": 0.95,
    "IEEE Spectrum":         0.93,
    "BBC Technology":        0.90,
    "The Guardian Tech":     0.88,
    "TechCrunch":            0.82,
    "The Verge":             0.80,

    "VentureBeat AI":        0.75,
}

# ──────────────────────────────────────────
# AI 관련성 필터 키워드 (제목 + 본문 검색용)
# ──────────────────────────────────────────
AI_KEYWORDS: list[str] = [
    "AI", "artificial intelligence", "machine learning", "deep learning",
    "LLM", "GPT", "ChatGPT", "neural", "transformer", "diffusion",
    "semiconductor", "chip", "NVIDIA", "robot", "autonomous",
    "OpenAI", "Anthropic", "Google DeepMind", "Meta AI",
    "generative", "foundation model", "large language", "inference",
    "Gemini", "Claude", "Copilot", "DeepSeek", "Mistral",
]

# ──────────────────────────────────────────
# # 더 명확한 AI/반도체 용어만 포함
# ──────────────────────────────────────────
AI_TITLE_KEYWORDS: list[str] = [
    "AI", "artificial intelligence", "machine learning",
    "LLM", "GPT", "ChatGPT", "neural", "semiconductor", "chip",
    "NVIDIA", "robot", "OpenAI", "Anthropic", "DeepMind",
    "Gemini", "Claude", "DeepSeek", "Mistral",
    "generative", "foundation model", "inference",
]


def get_credibility_score(source: str) -> float:
    """출처 기반 신뢰도 점수 반환. 미등록 출처는 0.5."""
    return SOURCE_CREDIBILITY.get(source, 0.5)


def is_ai_related(article: Article, title_only: bool = False) -> bool:
    """
    AI 관련 기사 여부 판별.
    title_only=True → 제목만 엄격하게 검사 (본문이 없는 피드용)
    title_only=False → 제목 + 본문 모두 검사
    """
    if title_only:
        text = article.title.lower()
        return any(kw.lower() in text for kw in AI_TITLE_KEYWORDS)
    else:
        text = (article.title + " " + article.content).lower()
        return any(kw.lower() in text for kw in AI_KEYWORDS)


def score_article(article: Article) -> Article:
    """
    기사 신뢰도 점수 계산 후 article에 반영.
    향후 Claude API로 루머/팩트 분류 추가 예정.
    """
    article.credibility_score = get_credibility_score(article.source)
    return article
