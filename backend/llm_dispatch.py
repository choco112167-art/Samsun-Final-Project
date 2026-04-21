"""
백엔드용 번역·요약 디스패처.

FastAPI `/translate`, `/summarize`는 여기를 통해
`pipeline.translate_summarize.translate_and_summarize`를 호출합니다.
단일 LLM 호출로 한국어 번역, 격식체 요약, 일상체 요약을 함께 받습니다.
"""

from __future__ import annotations

from pipeline.translate_summarize import translate_and_summarize


def translate_and_summarize_dispatch(
    text: str,
    summary_sentences: int | None = None,
) -> dict:
    """
    Args:
        text: 영어 본문
        summary_sentences: 요약 문장 수 (None이면 3)

    Returns:
        title, translation, summary_formal, summary_casual 키를 가진 dict
    """
    n = summary_sentences if summary_sentences is not None else 3
    return translate_and_summarize(text=text, summary_sentences=n)
