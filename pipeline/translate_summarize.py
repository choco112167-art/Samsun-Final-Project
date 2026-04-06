"""
Qwen3.5 4B - 격식체·일상체 번역 + 요약 단일 호출 파이프라인
한 번의 LLM 호출로 격식체 번역, 일상체 번역, 요약을 동시에 처리.

Setup:
  1. ollama pull qwen3.5:4b
  2. pip install ollama python-dotenv

Usage:
  python pipeline/translate_summarize.py
"""

import json
import re
import sys
import ollama
from dotenv import load_dotenv
import os

if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

load_dotenv()

MODEL = os.getenv("MODEL_NAME", "qwen3.5:4b")

SYSTEM_PROMPT = """You are a professional AI news translator and summarizer.
Given a news article, produce ALL three outputs at once:

1. **translation**: Translate the ENTIRE text into natural Korean.
2. **summary_formal**: Summarize in exactly {n} sentence(s) in formal Korean (격식체, ~습니다/~됩니다). Key points only.
3. **summary_casual**: Summarize in exactly {n} sentence(s) in casual Korean (일상체, ~해요/~예요/~거예요). Key points only.

Rules:
- Keep abbreviations like RAG, LLM, GPU, API, NPU in English only (no Korean).
- CRITICAL: For ALL proper nouns (company names, product names, people), use the format: English(한국어 음차) — English FIRST, Korean in parentheses. Apply on first mention only, English only after that.
  # 고유명사 병기 규칙: 반드시 영문을 앞에, 한국어 음차를 괄호 안에. 첫 등장 시에만 병기, 이후에는 영문만.
  Examples: Anthropic(앤트로픽), OpenAI(오픈에이아이), Google(구글), Meta(메타), Nvidia(엔비디아), Slack(슬랙), Alexa(알렉사), ChatGPT(챗지피티), Gemini(제미나이), Llama(라마).
- CRITICAL: Output Korean text only. Do NOT use any Chinese characters (漢字) in the output.
- Transliterate technical terms: Fine-tuning→파인튜닝, Embedding→임베딩, Prompt→프롬프트.
- For NEW coinages not yet widely known, use: OriginalTerm(한국어 음차, brief explanation) on first mention.
  # 신조어 처리: 첫 등장 시 영문(한국어 음차, 설명) 형식. 예) Blackwell Ultra(블랙웰 울트라, Nvidia 차세대 GPU)
- Summaries must NOT copy translation word-for-word.
- Output ONLY valid JSON. No explanation, no preamble."""


# ────────────────────────────────────────────────
# Sentence Estimator
# ────────────────────────────────────────────────
def estimate_sentences(text: str, max_sentences: int = 3) -> int:
    """
    원문 문장 수를 추정해 summary_sentences 상한을 반환합니다.

    약어(A.I., G.P.T.) · URL · 소수점의 마침표 오탐을 줄이기 위해
    '2글자 이상 단어 뒤의 문장 종결 부호(.!?) + 공백' 패턴만 카운트합니다.

    Returns:
        min(추정 문장 수, max_sentences)
        — 원문보다 많은 줄을 요약하도록 강제하지 않기 위해 상한을 둠.
    """
    parts = re.split(r'(?<=[a-zA-Z]{2})[.!?]\s+', text.strip())
    return min(max(1, len(parts)), max_sentences)


# ────────────────────────────────────────────────
# Core Function
# ────────────────────────────────────────────────
def translate_and_summarize(
    text: str,
    summary_sentences: int = 3,
    temperature: float = 0.1,
) -> dict:
    """
    영어 뉴스 기사를 격식체·일상체로 번역하고 요약합니다 (단일 LLM 호출).

    Args:
        text: 원본 영어 텍스트
        summary_sentences: 요약 문장 수 (기본: 3)
        temperature: 생성 다양성 (0.0~1.0)

    Returns:
        {
            "translation": str,     # 번역 전문
            "summary_formal": str,  # 격식체 3줄 요약
            "summary_casual": str,  # 일상체 3줄 요약
        }
    """
    system = SYSTEM_PROMPT.format(n=summary_sentences)

    for attempt in range(3):   # 최대 3회 시도
        response = ollama.chat(
            model=MODEL,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": text},
            ],
            options={
                "temperature": 0.1,
                "num_predict": 3000,
                "num_gpu": 99,
            },
            think=False,  # thinking 모드 비활성화 (qwen3.5:4b 전용)
        )
        result = _extract_json(response.message.content)
        if "(파싱 실패)" not in result.get("summary_formal", ""):
            return result

    return result  # 3회 실패 시 마지막 결과 반환


def _extract_json(text: str) -> dict:
    """LLM 응답에서 첫 번째 완전한 JSON 객체를 추출합니다."""
    text = text.strip()

    if "</think>" in text:
        text = text.split("</think>")[-1].strip()

    # 1차: { 위치 순차 탐색으로 완전한 JSON 파싱 시도
    pos = 0
    while True:
        start = text.find("{", pos)
        if start == -1:
            break
        try:
            obj, _ = json.JSONDecoder().raw_decode(text, start)
            if "translation" in obj:
                return obj
        except json.JSONDecodeError:
            pass
        pos = start + 1

    # 2차: regex로 각 필드 개별 추출 (JSON 구조 손상 시 최후 수단)
    def extract_field(key: str) -> str:
        pattern = rf'"{key}"\s*:\s*"((?:[^"\\]|\\.)*)"'
        m = re.search(pattern, text, re.DOTALL)
        return m.group(1).replace("\\n", "\n").replace('\\"', '"') if m else ""

    translation    = extract_field("translation")
    summary_formal = extract_field("summary_formal")
    summary_casual = extract_field("summary_casual")

    if translation:
        return {
            "translation":    translation,
            "summary_formal": summary_formal or "(파싱 실패)",
            "summary_casual": summary_casual or "(파싱 실패)",
        }

    return {
        "translation":    text,
        "summary_formal": "(파싱 실패)",
        "summary_casual": "(파싱 실패)",
    }


# ────────────────────────────────────────────────
# Batch Processing
# ────────────────────────────────────────────────
def batch_translate_summarize(
    texts: list,
    summary_sentences: int = 3,
) -> list:
    """여러 텍스트를 순서대로 번역+요약 처리합니다."""
    results = []
    for i, text in enumerate(texts, 1):
        print(f"[{i}/{len(texts)}] 처리 중...")
        try:
            result = translate_and_summarize(text, summary_sentences)
            results.append({"index": i, "status": "ok", **result})
        except Exception as e:
            results.append({"index": i, "status": "error", "error": str(e)})
    return results


# ────────────────────────────────────────────────
# CLI Demo
# ────────────────────────────────────────────────
def print_result(result: dict, label: str = "") -> None:
    sep = "=" * 60
    div = "-" * 60
    print(f"\n{sep}")
    if label:
        print(f"  {label}")
        print(sep)
    print("[원문 번역본]")
    print(result.get("translation", "(없음)"))
    print(div)
    print("[격식체 요약]")
    print(result.get("summary_formal", "(없음)"))
    print(div)
    print("[일상체 요약]")
    print(result.get("summary_casual", "(없음)"))
    print(sep)


if __name__ == "__main__":
    sample = """
    OpenAI has released GPT-4.1, its latest flagship model, featuring significant improvements
    in coding, instruction following, and long-context understanding. The model supports a
    1 million token context window and shows a 21% improvement on coding benchmarks compared
    to GPT-4o. OpenAI claims GPT-4.1 is particularly effective for agentic tasks, where AI
    systems autonomously complete multi-step workflows.
    """

    result = translate_and_summarize(text=sample, summary_sentences=3)
    print_result(result, "번역 + 요약 결과")
