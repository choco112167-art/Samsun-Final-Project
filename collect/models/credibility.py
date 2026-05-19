"""
피드(ai_only=False) 및 파이프라인 프리플라이트용 AI 관련성 판별.

토큰 비용 절감: 단순 정규식·키워드 매칭만 사용 (LLM 호출 없음).
"""

from __future__ import annotations

import re

from models.article import Article

# 한 줄 요약형 피드(title_only)에서는 제목 위주로만 검사할 수 있음
_AI_TERMS_COMPILED = re.compile(
    r"|".join(
        [
            r"\bai\b",
            r"\bml\b",
            r"\bllm\b",
            r"\bl\.l\.m\b",
            r"\bnlp\b",
            r"\bchatgpt\b",
            r"\bgpt[- ]?[345]\b",
            r"\bgpt-4o\b",
            r"\bopenai\b",
            r"\bclaude\b",
            r"\banthropic\b",
            r"\bgemini\b",
            r"\bgoogle deepmind\b",
            r"\bdeepmind\b",
            r"\bmeta\s+ai\b",
            r"\bllama\b",
            r"\bmistral\b",
            r"\bmixtral\b",
            r"\bdeepseek\b",
            r"\bqwen\b",
            r"\bgemma\b",
            r"\bgrok\b",
            r"\bsora\b",
            r"\bdall[- ]?e\b",
            r"\brunway\b",
            r"\bflux\b",
            r"\bneural\b",
            r"\btransformer\b",
            r"\bdiffusion\b",
            r"\bStable\s+Diffusion\b",
            r"\bMidjourney\b",
            r"\bLLaVA\b",
            r"\bRAG\b",
            r"\bfine[- ]tun(e|ing)\b",
            r"\binference\b",
            r"\bparameter[s]?\b",
            r"\bgpu\b|\btpu\b|\bnpu\b",
            r"\bnvidia\b|\bradeon\b|\bcuda\b",
            r"\bhbm\b|\bsemiconductor\b|\bchip\b",
            r"\bdata\s+cent(er|re)\b|\bai\s+accelerator\b",
            r"\binference\s+chip\b",
            r"\bcopilot\b",
            r"\bassistant\b.{0,25}\b(model|AI)\b",
            r"\bmachine\s+learning\b",
            r"\bdeep\s+learning\b",
            r"\bfoundation\s+model\b",
            r"\blarge\s+language\b",
            r"\bmultimodal\b",
            r"\bembedding\b|\bvector\b.{0,15}\b(search|db)\b",
            r"\btokenizer\b|\bquantization\b",
            r"\brlhf\b|\balignment\b|\bhallucination\b",
            r"\bfederated\b.{0,15}\blearning\b",
            r"\bagi\b|\bagentic\b",
            r"\bautonomous\b|\brobot\b",
            r"\bdeepfake\b|\bsynthetic\s+data\b",
            r"\bai\s+safety\b|\bai\s+regulation\b|\bai\s+act\b",
            r"\bsuperintelligence\b",
            r"\bxai\b|\bperplexity\b|\bcohere\b",
            r"\bstability\s+ai\b|\bcharacter\s+ai\b|\bscale\s+ai\b",
            r"\bdatabricks\b",
        ]
    ),
    re.IGNORECASE,
)


def is_ai_related(article: Article, title_only: bool = False) -> bool:
    """
    제목(+ 선택적으로 본문 앞부분)에서 AI·ML 관련 용어 탐지.

    Lemmy 등 ai_only=False 피드에서 RSS 단계 및 파이프라인 프리플라이트에 사용한다.
    """
    blob = article.title.strip()
    if not title_only and article.content:
        blob = blob + "\n" + article.content[:12000]
    return bool(_AI_TERMS_COMPILED.search(blob))


def score_article(article: Article) -> Article:
    """출처 프로파일 기준 credibility 스코어 주입."""
    try:
        from fact_checker.channel_config import get_profile

        p = get_profile(article.source)
        article.credibility_score = float(p.credibility_score)
    except Exception:
        pass
    return article
