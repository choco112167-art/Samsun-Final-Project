"""
OpenRouter — OpenAI 호환 chat completions
https://openrouter.ai/docs (Authorization + HTTP-Referer)
"""

from __future__ import annotations

import os
from dotenv import load_dotenv
from openai import OpenAI, OpenAIError

load_dotenv()

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_REFERER = "https://samsun-production.up.railway.app"


def _referer() -> str:
    return (os.getenv("OPENROUTER_HTTP_REFERER") or DEFAULT_REFERER).strip()


def _api_key() -> str:
    return (os.getenv("OPENROUTER_API_KEY") or "").strip()


def openrouter_chat_completion(
    messages: list[dict[str, str]],
    *,
    model: str | None = None,
    temperature: float = 0.1,
    max_tokens: int = 8192,
    timeout: float = 120.0,
) -> str:
    """
    returns assistant message content or "" on missing key / error.
    """
    key = _api_key()
    if not key:
        return ""
    m = model or os.getenv("OPENROUTER_MODEL", "qwen/qwen3-4b")
    client = OpenAI(
        base_url=OPENROUTER_BASE_URL,
        api_key=key,
        default_headers={"HTTP-Referer": _referer()},
        timeout=timeout,
    )
    try:
        r = client.chat.completions.create(
            model=m,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
    except OpenAIError:
        return ""
    if not r.choices:
        return ""
    return (r.choices[0].message.content or "").strip()
