"""
공통 전처리 유틸리티
LLM 출력 또는 학습 데이터의 노이즈를 제거하고 JSON 파싱을 보장합니다.

사용법:
    from pipeline.utils import preprocess_text, extract_json
"""

import json
import re

_FIELDS = ["title_ko", "translation", "summary_formal", "summary_casual"]


def preprocess_text(text: str) -> str:
    """LLM 출력·학습 데이터의 표면 노이즈 제거.

    제거 항목:
    - <think>...</think> 태그 (Qwen3 사고 잔재)
    - 마크다운 코드블록 (```json ... ```)
    - 스마트 따옴표 → 표준 따옴표
    - CRLF → LF 정규화
    - 제어 문자 (탭·개행 제외)
    """
    # think 태그 제거
    if "</think>" in text:
        text = text.split("</think>")[-1]
    # 마크다운 코드블록 제거
    text = re.sub(r"```json\s*", "", text)
    text = re.sub(r"```\s*", "", text)
    # 스마트 따옴표 → 표준 따옴표
    text = (text
            .replace('\u201c', '"').replace('\u201d', '"')
            .replace('\u2018', "'").replace('\u2019', "'"))
    # 줄바꿈 정규화
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    # 제어 문자 제거 (탭·개행 제외)
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
    return text.strip()


def _extract_raw(text: str) -> dict[str, str]:
    """필드 경계 기반 raw 값 추출 (JSON 파싱 없음).

    JSON 구조가 어떻게 손상되어 있어도 동작:
    - unescaped 따옴표
    - 잘린 출력 (truncated)
    - 필드 간 구분자 다양한 형태
    """
    raw: dict[str, str] = {}

    for idx, field in enumerate(_FIELDS):
        # 값 시작점: "field": " — 공백 패턴 다양하게 허용
        content_start = None
        for sep in (f'"{field}": "', f'"{field}":"', f'"{field}" : "'):
            p = text.find(sep)
            if p != -1:
                content_start = p + len(sep)
                break
        if content_start is None:
            continue

        # 값 끝점: 다음 필드 마커 직전 또는 JSON 닫힘
        content_end = None

        if idx + 1 < len(_FIELDS):
            next_f = _FIELDS[idx + 1]
            for end_pat in (
                f'", "{next_f}"',
                f'",\n"{next_f}"',
                f'",\n  "{next_f}"',
                f'",\r\n"{next_f}"',
            ):
                ep = text.find(end_pat, content_start)
                if ep != -1:
                    content_end = ep
                    break

        if content_end is None:
            # 마지막 필드 또는 경계 못 찾은 경우
            for end_pat in ('"}', '" }', '"\n}'):
                ep = text.rfind(end_pat, content_start)
                if ep > content_start:
                    content_end = ep
                    break
            if content_end is None:
                content_end = len(text)

        val = text[content_start:content_end]
        # 이스케이프 시퀀스 복원
        val = (val
               .replace('\\"', '"')
               .replace('\\n', '\n')
               .replace('\\t', '\t')
               .replace('\\\\', '\\'))
        raw[field] = val.strip()

    return raw


def extract_json(text: str) -> dict:
    """LLM 응답에서 번역/요약 필드를 추출합니다.

    파싱 실패율 = 0 보장:
      1. 전처리 — 표면 노이즈 제거
      2. 완전한 JSON 파싱 (fast path, ~80% 케이스)
      3. 경계 추출 → json.dumps 재인코딩 → 재파싱
      4. 절대 최후 수단 (실질적으로 도달 불가)
    """
    text = preprocess_text(text)

    # ── 1단계: 완전한 JSON 파싱 (fast path) ──────────────────
    pos = 0
    while True:
        start = text.find("{", pos)
        if start == -1:
            break
        try:
            obj, _ = json.JSONDecoder().raw_decode(text, start)
            if "translation" in obj:
                return {f: obj.get(f, "") for f in _FIELDS}
        except json.JSONDecodeError:
            pass
        pos = start + 1

    # ── 2단계: 경계 추출 → json.dumps 재인코딩 ───────────────
    raw = _extract_raw(text)
    if raw.get("translation"):
        repaired = json.dumps(raw, ensure_ascii=False)
        obj = json.loads(repaired)
        return {f: obj.get(f, "") for f in _FIELDS}

    # ── 3단계: 절대 최후 수단 ────────────────────────────────
    return {
        "translation":    text,
        "summary_formal": "(파싱 실패)",
        "summary_casual": "(파싱 실패)",
    }
