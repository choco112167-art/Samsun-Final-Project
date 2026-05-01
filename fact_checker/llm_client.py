"""
fact_checker/llm_client.py — Gemini → OpenRouter 자동 fallback LLM 클라이언트

Gemini 무료 티어 RPD 소진 또는 429 에러 시 OpenRouter(gpt-4.1-mini)로 전환.
Google Search Grounding은 Gemini 전용 — fallback 시 grounding 없이 실행.

환경변수:
    GEMINI_API_KEY 또는 GOOGLE_API_KEY — Gemini
    OPENROUTER_API_KEY                 — fallback
"""

import os
import logging

logger = logging.getLogger(__name__)

GEMINI_MODEL       = "gemini-2.5-flash"
OPENROUTER_MODEL   = "openai/gpt-4.1-mini"
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


def _is_quota_error(e: Exception) -> bool:
    """Gemini 429 / quota 초과 에러 감지."""
    msg = str(e).lower()
    return any(k in msg for k in (
        "429", "resource_exhausted", "quota", "rate limit",
        "too many requests", "ratelimitexceeded",
    ))


def _call_gemini(
    system: str,
    user: str,
    client,
    temperature: float,
    max_tokens: int,
    use_grounding: bool,
) -> str:
    from google.genai import types

    config_kwargs = dict(
        system_instruction=system,
        temperature=temperature,
        max_output_tokens=max_tokens,
        thinking_config=types.ThinkingConfig(thinking_budget=0),
    )
    if use_grounding:
        config_kwargs["tools"] = [types.Tool(google_search=types.GoogleSearch())]

    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=user,
        config=types.GenerateContentConfig(**config_kwargs),
    )
    return response.text


def _call_openrouter(system: str, user: str, temperature: float, max_tokens: int) -> str:
    from openai import OpenAI

    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY 환경변수 없음 — fallback 불가")

    client = OpenAI(api_key=api_key, base_url=OPENROUTER_BASE_URL)
    response = client.chat.completions.create(
        model=OPENROUTER_MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user",   "content": user},
        ],
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return response.choices[0].message.content


def call_with_fallback(
    system: str,
    user: str,
    gemini_client=None,
    temperature: float = 0.1,
    max_tokens: int = 1024,
    use_grounding: bool = False,
) -> tuple[str, bool]:
    """
    LLM 호출 — Gemini 우선, quota 소진 시 OpenRouter fallback.

    Args:
        system:         시스템 프롬프트
        user:           유저 프롬프트
        gemini_client:  google.genai.Client 인스턴스 (None이면 즉시 fallback)
        temperature:    온도
        max_tokens:     최대 출력 토큰
        use_grounding:  Google Search Grounding 사용 여부 (Gemini 전용, fallback 시 무시)

    Returns:
        (response_text, used_fallback)
        used_fallback=True 이면 OpenRouter를 사용한 것
    """
    if gemini_client is not None:
        for attempt in range(2):
            try:
                text = _call_gemini(system, user, gemini_client, temperature, max_tokens, use_grounding)
                return text, False
            except Exception as e:
                if _is_quota_error(e):
                    logger.warning(
                        f"[LLMClient] Gemini quota/rate-limit 감지 → OpenRouter({OPENROUTER_MODEL}) fallback"
                    )
                    break
                if attempt == 1:
                    logger.error(f"[LLMClient] Gemini 2회 실패, fallback 시도: {e}")
                    break
                logger.warning(f"[LLMClient] Gemini retry (attempt {attempt + 1}): {e}")

    # OpenRouter fallback (grounding 미지원 — LLM 추론만)
    logger.info(f"[LLMClient] OpenRouter {OPENROUTER_MODEL} 호출")
    text = _call_openrouter(system, user, temperature, max_tokens)
    return text, True
