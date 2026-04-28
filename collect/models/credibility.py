"""
三鮮 (삼선) - 신뢰도 스코어링
담당: 이상준 (데이터 수집) / 강주찬 (백엔드)
- 출처별 기본 신뢰도
- AI 관련성 키워드 필터 (일반 / 제목 전용 엄격 모드)
- 루머/팩트 구분 (향후 Claude API 연동 예정)
"""

from models.article import Article
import logging
import re

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
    "Nikkei Asia Tech":      0.78,
    "VentureBeat AI":        0.75,
}

# ──────────────────────────────────────────
# AI 관련성 필터 키워드 (제목 + 본문 검색용)
# ──────────────────────────────────────────

#AI_KEYWORDS → title_only: False일 때 제목 + 본문 합쳐서 검색
#AI_TITLE_KEYWORDS → title_only: True일 때 제목만 검색

AI_KEYWORDS: list[str] = [
    # 기본 AI 용어
    "AI", "artificial intelligence", "machine learning", "deep learning",
    "LLM", "GPT", "ChatGPT", "neural", "transformer", "diffusion",
    "semiconductor", "chip", "NVIDIA", "robot", "autonomous",
    "OpenAI", "Anthropic", "Google DeepMind", "Meta AI",
    "generative", "foundation model", "large language", "inference",
    "Gemini", "Claude", "Copilot", "DeepSeek", "Mistral",

    # AI 모델 / 제품
    "Grok", "Llama", "Stable Diffusion", "Midjourney", "DALL-E",
    "Sora", "Runway", "Flux", "Qwen", "Phi", "Gemma",

    # AI 기업
    "xAI", "Perplexity", "Cohere",
    "Stability AI", "Character AI", "Scale AI", "Databricks",
    "Huawei AI", "Huawei chip",
    "AMD AI", "AMD GPU", "AMD Instinct",
    "Intel AI", "Intel Gaudi",
    "TSMC AI", "TSMC chip",

    # AI 기술 용어
    "fine-tuning", "RAG", "agentic", "agent", "multimodal",
    "embedding", "vector", "prompt", "tokenizer", "quantization",
    "reinforcement learning", "RLHF", "alignment", "hallucination",
    "context window", "reasoning model",

    # AI 인프라 / 하드웨어
    "GPU", "TPU", "NPU", "HBM", "data center",
    "inference chip", "AI accelerator",

    # AI 트렌드 / 이슈
    "automation", "deepfake", "synthetic data", "AI safety",
    "AI regulation", "AI Act", "AGI", "superintelligence",
]

# ──────────────────────────────────────────
# 더 명확한 AI/반도체 용어만 포함 (제목 전용)
# ──────────────────────────────────────────
AI_TITLE_KEYWORDS: list[str] = [
    # 기본 AI 용어
    "AI", "artificial intelligence", "machine learning", "deep learning",
    "LLM", "GPT", "ChatGPT", "neural", "semiconductor", "chip",
    "NVIDIA", "robot", "autonomous",
    "OpenAI", "Anthropic", "DeepMind", "Meta AI",
    "generative", "foundation model", "inference",
    "Gemini", "Claude", "Copilot", "DeepSeek", "Mistral",

    # AI 모델 / 제품
    "Grok", "Llama", "Stable Diffusion", "Midjourney", "DALL-E",
    "Sora", "Runway", "Flux", "Qwen", "Phi", "Gemma",

    # AI 기업
    "xAI", "Perplexity", "Cohere",
    "Stability AI", "Character AI", "Scale AI", "Databricks",
    "Huawei AI", "Huawei chip",
    "AMD AI", "AMD GPU", "AMD Instinct",
    "Intel AI", "Intel Gaudi",
    "TSMC AI", "TSMC chip",

    # AI 기술 용어
    "fine-tuning", "RAG", "agentic", "agent", "multimodal",
    "embedding", "quantization", "RLHF", "alignment", "hallucination",
    "context window", "reasoning model",

    # AI 인프라 / 하드웨어
    "GPU", "TPU", "NPU", "HBM", "data center",
    "inference chip", "AI accelerator",

    # AI 트렌드 / 이슈
    "deepfake", "AGI", "superintelligence", "AI safety",
    "AI regulation", "AI Act", "automation",
]


def get_credibility_score(source: str) -> float:
    """출처 기반 신뢰도 점수 반환. 미등록 출처는 0.5."""
    return SOURCE_CREDIBILITY.get(source, 0.5)


def is_ai_related(article: Article, title_only: bool = False) -> bool:
    if title_only:
        text = article.title.lower()
        return any(re.search(r'\b' + re.escape(kw.lower()) + r'\b', text)
                   for kw in AI_TITLE_KEYWORDS)
    else:
        text = (article.title + " " + article.content).lower()
        return any(re.search(r'\b' + re.escape(kw.lower()) + r'\b', text)
                   for kw in AI_KEYWORDS)


def score_article(article: Article) -> Article:
    """
    기사 신뢰도 점수 계산 후 article에 반영.
    향후 Claude API로 루머/팩트 분류 추가 예정.
    """
    article.credibility_score = get_credibility_score(article.source)
    return article
