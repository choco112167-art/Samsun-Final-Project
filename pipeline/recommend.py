"""
pipeline/recommend.py — LLM 기반 기사 추천

벡터 유사도로 추려진 top10 기사 중에서
유저 관심사를 바탕으로 qwen이 5개를 골라 추천 이유와 함께 반환합니다.
"""

from __future__ import annotations
import json
import re
import torch
from pipeline.translate_summarize import model, tokenizer


RECOMMEND_SYSTEM_PROMPT = """당신은 개인화 뉴스 추천 전문가입니다.

유저의 관심사와 최근 읽은 기사 패턴을 분석하여
제공된 기사 목록에서 가장 적합한 5개를 선별합니다.

판단 기준:
1. 유저 관심사/최근 키워드와 얼마나 관련 있는지
2. 기사 내용이 유저에게 실질적으로 유용한지
3. 다양성 (비슷한 주제 중복 배제)

출력 규칙:
- 반드시 유효한 JSON 배열만 반환. 마크다운 금지.
- 형식: [{"index": <번호>, "reason": "<추천 이유 1문장>"}]
- 추천 이유: "최근 AI 반도체 기사를 읽으셨고, 이 기사는 엔비디아 신규 칩을 다뤄요"
- 반드시 5개 선택."""


def _build_user_prompt(
    interest_tags: list[str],
    recent_keywords: list[str],
    articles: list[dict],
) -> str:
    tags_str = ", ".join(interest_tags) if interest_tags else "없음"
    keywords_str = ", ".join(recent_keywords[:10]) if recent_keywords else "없음"

    articles_str = ""
    for i, a in enumerate(articles):
        title = a.get("title", "")
        summary = a.get("summary_casual") or a.get("summary_formal") or a.get("translation", "")[:80]
        category = a.get("category", "")
        articles_str += f"[{i}] ({category}) {title}\n    요약: {summary}\n"

    return f"""유저 관심사: {tags_str}
최근 읽은 기사 키워드: {keywords_str}

기사 목록:
{articles_str}
위 기사 중 이 유저에게 가장 적합한 5개를 골라 JSON으로 반환하세요."""


def _extract_json_list(text: str) -> list:
    """응답에서 JSON 배열 추출"""
    # thinking 태그 제거
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL).strip()

    # ```json ... ``` 펜스 제거
    text = re.sub(r'```json\s*', '', text)
    text = re.sub(r'```\s*', '', text)

    # JSON 배열 찾기
    match = re.search(r'\[.*\]', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except Exception:
            pass
    return []


def recommend_articles(
    interest_tags: list[str],
    recent_keywords: list[str],
    articles: list[dict],
    temperature: float = 0.3,
) -> list[dict]:
    """
    Args:
        interest_tags: 유저 관심사 태그
        recent_keywords: 최근 클릭 기사 키워드
        articles: 벡터 추천 top10 기사 목록
    Returns:
        추천 기사 5개 (원본 article dict + reason 필드 추가)
    """
    if not articles:
        return []

    user_prompt = _build_user_prompt(interest_tags, recent_keywords, articles)

    messages_input = [
        {"role": "system", "content": RECOMMEND_SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]

    text_input = tokenizer.apply_chat_template(
        messages_input,
        tokenize=False,
        add_generation_prompt=True,
    )
    inputs = tokenizer(text_input, return_tensors="pt").to(model.device)
    input_ids = inputs["input_ids"]

    with torch.no_grad():
        output = model.generate(
            input_ids,
            max_new_tokens=512,
            temperature=temperature,
            do_sample=True,
        )

    response_text = tokenizer.decode(
        output[0][input_ids.shape[-1]:],
        skip_special_tokens=True
    )

    picks = _extract_json_list(response_text)

    # 추천 결과 조합
    result = []
    seen = set()
    for pick in picks:
        idx = pick.get("index")
        reason = pick.get("reason", "회원님의 취향을 분석해 추천했어요")
        if idx is None or idx >= len(articles) or idx in seen:
            continue
        seen.add(idx)
        article = dict(articles[idx])
        article["reason"] = reason
        result.append(article)
        if len(result) >= 5:
            break

    # LLM이 5개 못 골랐을 경우 앞에서 채우기
    if len(result) < min(5, len(articles)):
        for i, a in enumerate(articles):
            if i not in seen and len(result) < 5:
                article = dict(a)
                article["reason"] = "회원님의 취향을 분석해 추천했어요"
                result.append(article)

    return result
