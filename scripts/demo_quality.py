"""Shared quality checks for Samsun News demo-readiness scripts."""

from __future__ import annotations

import re
from typing import Any


def has_korean(value: Any) -> bool:
    return bool(re.search(r"[가-힣]", str(value or "")))


def is_blank(value: Any) -> bool:
    return value is None or not str(value).strip()


def sentence_count(value: Any) -> int:
    text = re.sub(r"\s+", " ", str(value or "").strip())
    if not text:
        return 0
    numbered = len(re.findall(r"(?:^|\s)\d+\.\s+", text))
    punctuation = len([part for part in re.split(r"[.!?。！？]", text) if len(part.strip()) > 5])
    return max(numbered, punctuation)


def is_weak_summary(value: Any, min_chars: int = 55, min_sentences: int = 2) -> bool:
    text = str(value or "").strip()
    if not text:
        return True
    if "[MOCK" in text or "(파싱 실패)" in text:
        return True
    return len(text) < min_chars or sentence_count(text) < min_sentences


def has_valid_summary(row: dict[str, Any]) -> bool:
    return not is_weak_summary(row.get("summary_formal")) or not is_weak_summary(row.get("summary_casual"))


def has_translation(row: dict[str, Any], min_chars: int = 140) -> bool:
    text = str(row.get("translation") or "").strip()
    return len(text) >= min_chars and has_korean(text) and "[MOCK" not in text


def has_fact(row: dict[str, Any]) -> bool:
    return not is_blank(row.get("fact_status")) or not is_blank(row.get("fact_label"))


def has_neologism_terms(row: dict[str, Any]) -> bool:
    for field in ("neologism_terms", "slang_terms"):
        value = row.get(field)
        if isinstance(value, list) and len(value) > 0:
            return True
        if isinstance(value, str) and value.strip() not in {"", "{}", "[]"}:
            return True
    return False


def is_demo_ready(row: dict[str, Any]) -> bool:
    return (
        has_korean(row.get("title_ko"))
        and has_valid_summary(row)
        and has_translation(row)
        and has_fact(row)
        and not is_blank(row.get("source"))
        and not is_blank(row.get("url"))
    )
