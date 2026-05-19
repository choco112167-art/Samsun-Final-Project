# -*- coding: utf-8 -*-
"""
번역 후처리 — 고유명사 보존율(TPR) 보완

2단계 파이프라인:
    Step 1: restore_entities()     — 음역 패턴 복원 (기존 로직 재사용)
    Step 2: inject_missing_terms() — 소스 기반 누락 용어 주입 (신규)

사용법:
    from pipeline.post_process import post_process

    result = translate_and_summarize(en_text)
    result["translation"] = post_process(en_text, result["translation"])
"""

import re
import os
import sys

# 프로젝트 루트를 경로에 추가 (eval.metrics 임포트용)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from eval.metrics.term_preservation import (
    AI_TERMS,
    check_term_preservation,
    restore_entities,
)

# ── 영어 문장 분리 패턴 ──────────────────────────────────────────
# 약어(A.I., U.S.)·소수점·URL 속 마침표 오탐 최소화
_EN_SENT_PAT = re.compile(
    r'(?<!\b[A-Z])(?<!\b[A-Z][a-z])(?<!\d)'  # 약어·소수점 뒤 제외
    r'[.!?]'
    r'(?=\s+[A-Z"\'(\[]|\s*$)',               # 다음 문장 대문자 또는 끝
)

# 한국어 문장 분리 패턴
_KO_SENT_PAT = re.compile(r'(?<=[다요음죠])[.!?。]\s*|(?<=[.!?])\s+')

# 문장 종결부 (괄호 삽입 위치 탐색용)
_KO_ENDING_PAT = re.compile(r'([.!?。])\s*$')

# 한국어 조사 패턴 (용어 뒤 붙는 조사 검출)
_KO_JOSA = re.compile(r'[은는이가을를에서의로과와도만]')


def _split_sentences(text: str, lang: str = "en") -> list[str]:
    """텍스트를 문장 단위로 분리."""
    if lang == "en":
        parts = _EN_SENT_PAT.split(text.strip())
    else:
        parts = _KO_SENT_PAT.split(text.strip())
    return [p.strip() for p in parts if p.strip()]


def _term_present(term: str, text: str) -> bool:
    """번역문에 term이 영문으로 존재하는지 확인 (ASCII + 조사 허용)."""
    return bool(
        re.search(
            r'\b' + re.escape(term) + r'\b',
            text,
            re.ASCII | re.IGNORECASE,
        )
    )


def _append_term(sentence: str, term: str) -> str:
    """
    문장 종결부 직전에 '(Term)' 삽입.
    종결 부호 없으면 문장 끝에 추가.
    """
    m = _KO_ENDING_PAT.search(sentence)
    if m:
        pos = m.start()
        return sentence[:pos] + f"({term})" + sentence[pos:]
    return sentence + f"({term})"


def inject_missing_terms(en_text: str, ko_text: str, missing: list[str]) -> str:
    """
    원문(en_text)에 등장하지만 번역(ko_text)에 없는 용어를 주입.

    전략:
    1. 원문을 문장 단위로 분리해 각 용어가 등장하는 문장 인덱스를 확인.
    2. 한국어 번역에서 같은 인덱스(rough alignment)의 문장 말미에 (Term) 삽입.
    3. 이미 번역문에 있거나, 한국어 문장을 못 찾으면 스킵.
    """
    if not missing:
        return ko_text

    en_sents = _split_sentences(en_text, lang="en")
    ko_sents = _split_sentences(ko_text, lang="ko")

    if not ko_sents:
        return ko_text

    modified_ko = ko_text

    for term in missing:
        pat = re.compile(r'\b' + re.escape(term) + r'\b', re.IGNORECASE)

        for i, en_sent in enumerate(en_sents):
            if not pat.search(en_sent):
                continue

            # rough alignment: 같은 인덱스, 없으면 마지막 문장
            ko_idx = min(i, len(ko_sents) - 1)
            ko_sent_orig = ko_sents[ko_idx]

            # 이미 해당 한국어 문장에 term이 있으면 skip
            if _term_present(term, ko_sent_orig):
                break

            # 번역 전체에 이미 있으면 skip (다른 문장에 있는 경우)
            if _term_present(term, modified_ko):
                break

            ko_sent_new = _append_term(ko_sent_orig, term)
            # 첫 번째 발생만 교체 (동일 문장 중복 방지)
            modified_ko = modified_ko.replace(ko_sent_orig, ko_sent_new, 1)
            # ko_sents 동기화
            ko_sents[ko_idx] = ko_sent_new
            break

    return modified_ko


def post_process(en_text: str, ko_translation: str, verbose: bool = False) -> str:
    """
    번역 후처리 메인 함수.

    Args:
        en_text:        원본 영어 기사 본문
        ko_translation: 모델이 생성한 한국어 번역 결과
        verbose:        누락 용어 로그 출력 여부

    Returns:
        후처리된 한국어 번역 문자열
    """
    # ── Step 1: 음역 복원 ──────────────────────────────────────
    result = restore_entities(ko_translation)

    # ── Step 2: 소스 기반 누락 용어 주입 ──────────────────────
    tpr_check = check_term_preservation(result, source=en_text)
    missing = tpr_check.get("missing", [])

    if verbose and missing:
        print(f"  [post_process] 누락 용어 {len(missing)}개: {missing}")

    if missing:
        result = inject_missing_terms(en_text, result, missing)

    if verbose:
        tpr_after = check_term_preservation(result, source=en_text)
        print(f"  [post_process] TPR: {tpr_check['tpr']:.3f} → {tpr_after['tpr']:.3f}")

    return result
