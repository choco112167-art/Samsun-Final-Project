"""
Qwen3.5 4B - 격식체·일상체 번역 + 요약 단일 호출 파이프라인
한 번의 LLM 호출로 격식체 번역, 일상체 번역, 요약을 동시에 처리.

Setup:
  1. ollama pull qwen3.5:4b
  2. pip install ollama python-dotenv

Usage:
  python pipeline/translate_summarize.py

Note:
  번역 프롬프트 생성 직전에 backend.neologism_rag.explain_neologism 으로
  신조어 용어집(glossary)을 만들어 user_content 앞에 주입합니다.
  신조어 조회 실패 시에도 파이프라인은 중단되지 않고 기존 프롬프트로 진행.
"""

import logging
import os
import re
import sys

import ollama
from dotenv import load_dotenv

from backend.neologism_rag import explain_neologism
from pipeline.utils import preprocess_text, extract_json as _extract_json_util

if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

load_dotenv()

logger = logging.getLogger(__name__)

MODEL = os.getenv("MODEL_NAME", "qwen3.5:4b")

# ────────────────────────────────────────────────
# 신조어 감지용 상수
# ────────────────────────────────────────────────
# 우선적으로 감지할 AI/기술 용어 (요구사항에서 지정한 큐레이션 목록).
# Fine-tuning 처럼 하이픈 포함 토큰도 \b(word boundary) 기반으로 잡힘.
AI_TERMS: tuple[str, ...] = (
    "LoRA", "RLHF", "RAG", "Transformer", "Diffusion",
    "Fine-tuning", "Quantization", "Hallucination", "Multimodal",
    "Benchmark", "Grounding", "Embedding", "Inference", "Agent",
)

# 대문자로 시작하는 단어 중 제외할 일반 영어 (문장 시작 관사/대명사/조동사 등).
# 이 목록에 없는 모든 Capitalized Word 는 후보로 간주하고 최대 5개까지 처리.
STOPWORDS: frozenset[str] = frozenset({
    "The", "This", "That", "These", "Those", "An",
    "In", "On", "At", "For", "With", "But", "And", "Or", "If",
    "When", "Where", "Why", "How", "What", "Who", "Which",
    "It", "Its", "They", "We", "Our", "Their", "His", "Her",
    "Have", "Has", "Had", "Will", "Would", "Could", "Should",
    "Can", "May", "Must",
    "Is", "Are", "Was", "Were", "Be", "Been", "Being",
    "Do", "Does", "Did", "Not", "As", "Of", "To", "By", "From",
    "About", "After", "Before", "While", "Since", "Until",
    "However", "Meanwhile", "Also", "Only",
})

# 용어 감지·조회 상한 (API 비용 절감).
MAX_GLOSSARY_TERMS: int = 5


SYSTEM_PROMPT = """You are a professional Korean translator and summarizer.

━━━ RULE 0: OUTPUT LANGUAGE (ABSOLUTE PRIORITY) ━━━
Output MUST contain ONLY Korean (한글) + Latin (A-Z/a-z) + digits + punctuation.
ZERO TOLERANCE — even one character from the following scripts causes failure:
  • Chinese/Hanzi (漢字): including 去, 年, 的, 在 etc.
  • Cyrillic/Russian: А, Б, В … я etc.
  • Thai, Arabic, Hebrew, Japanese kana
If the source contains these scripts, translate or romanize them into Korean. NEVER copy them.

━━━ OUTPUT FORMAT ━━━
Return ONLY valid JSON. No markdown fences, no explanation outside JSON.
{{
  "title_ko": "<한국어 제목>",
  "translation": "<전체 한국어 번역>",
  "summary_formal": "<격식체 요약>",
  "summary_casual": "<일상체 요약>"
}}
All four fields are REQUIRED. Never leave any field empty.
If no title is provided, set "title_ko" to "".

━━━ TRANSLATION RULES ━━━
1. Translate the ENTIRE article into Korean.
   Use journalistic body style (~했다 / ~밝혔다 / ~에 따르면). Prefer active voice: '발표했다' over '발표됐다'.
2. Keep these abbreviations in English exactly as-is: RAG, LLM, GPU, NPU, API, RLHF, SFT, LoRA, QLoRA, P2P, B2B, SNS.
3. AI/tech terms must stay in English — do NOT transliterate:
   Fine-tuning, Embedding, Prompt, Transformer, Benchmark, Inference, Token, Dataset, Checkpoint
   General loanwords already standard in Korean are fine: Startup→스타트업, Platform→플랫폼, Algorithm→알고리즘

4. PROPER NOUNS — company names, product names, brand names must stay in English. No Korean transliteration.
   • Rule: English name ONLY — do NOT add Korean phonetic transcription in parentheses.
   • e.g., Anthropic (NOT 앤트로픽), OpenAI (NOT 오픈에이아이), Nvidia (NOT 엔비디아),
     Google (NOT 구글), Meta (NOT 메타), Microsoft (NOT 마이크로소프트),
     Gemini (NOT 제미나이), Llama (NOT 라마), Claude (NOT 클로드), ChatGPT (NOT 챗GPT)
   • Model version numbers always stay in English: e.g., GPT-4o, Claude 3.5 Sonnet, Llama 3.1 70B

5. PERSON NAMES — use English name only. Do NOT add Korean transliteration.
   • e.g., Sam Altman (NOT 샘 올트먼), Jensen Huang (NOT 젠슨 황), Elon Musk (NOT 일론 머스크)
   • Job titles are translated into Korean: professor→교수, researcher→연구원, founder→창업자

6. NUMBERS AND UNITS
   • Currency symbols: $ → 달러 / € → 유로 / £ → 파운드 / ¥ → 엔 (중국 화폐는 위안)
     Exact figures may include original: 25억 달러($2.5B)
   • T / trillion → 조: $1T → 1조 달러
   • B / billion  → 억: $2.5B → 25억 달러
   • M / million  → 만: $500M → 5억 달러
   • K / thousand → 천: 5K → 5천 (context permitting)
   • Unit context — always specify the unit: parameters→개, people→명, tokens→개
     e.g., 70B parameters → 700억 개 파라미터
   • Multipliers: 2x → 2배 / 3x → 3배
   • Technical units (GB, TB, ms, TFLOPS, %) — keep as-is

7. Korean-origin names: write in Korean only, no parenthetical annotation.
   • Korean person names: 홍길동, 이재용 etc.
   • Korean company/institution names: 삼성전자, 국가정보원 etc.

8. Brand-new English coinages with no established Korean equivalent: EnglishTerm(한 줄 설명) on first mention.
   Example: Blackwell Ultra(Nvidia 차세대 GPU 아키텍처) — explanation in Korean, but NO Korean phonetic transcription.

━━━ TITLE TRANSLATION RULES ━━━
- title_ko: translate the English title into Korean headline style.
- Use noun-final endings: ~함 / ~됨 / ~발표 / ~출시 / ~공개
- Keep it concise — omit articles (a/the) and filler words.
- Apply all proper noun, person name, and number rules above.
- If no title is given in the input, set title_ko to "".

━━━ SUMMARY RULES ━━━
- summary_formal: exactly {n} Korean sentence(s), 격식체 (~습니다/~됩니다). Must be complete.
- summary_casual: exactly {n} Korean sentence(s), 일상체 (~해요/~예요/~거예요). Must be complete.
- Summaries must NOT copy translation sentences verbatim — paraphrase with different expressions.
- Use journalistic style (~했다/~밝혔다). Prefer active voice: '발표했다' over '발표됐다'.
- Apply all language, proper noun, and number rules above."""


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
# Neologism Glossary (신조어 용어집 주입)
# ────────────────────────────────────────────────
def _extract_candidate_terms(text: str, max_terms: int = MAX_GLOSSARY_TERMS) -> list[str]:
    """
    영문 본문에서 신조어 후보를 최대 max_terms 개까지 추출.

    우선순위:
      1) AI_TERMS 목록 매치 (대소문자 무시, 표기는 정규 형태로 통일)
      2) 대문자로 시작하는 3자+ 단어 (STOPWORDS 제외, 출현 순서)

    중복 제거. 원문의 첫 출현 순서를 최대한 보존.
    """
    found: list[str] = []
    seen: set[str] = set()

    # (1) AI_TERMS 우선 — 등장하기만 하면 canonical 표기로 수집
    for term in AI_TERMS:
        if len(found) >= max_terms:
            return found
        pattern = re.compile(rf"\b{re.escape(term)}\b", re.IGNORECASE)
        if pattern.search(text) and term not in seen:
            found.append(term)
            seen.add(term)

    # (2) Capitalized 단어 — 출현 순서대로
    cap_pattern = re.compile(r"\b[A-Z][A-Za-z][A-Za-z0-9\-]+\b")
    for m in cap_pattern.finditer(text):
        if len(found) >= max_terms:
            break
        word = m.group()
        if word in STOPWORDS or word in seen:
            continue
        # ALL CAPS 약어(GPU, API 등)는 SYSTEM_PROMPT 규칙 2번에서 이미 처리됨 — skip
        if word.isupper() and len(word) <= 4:
            continue
        found.append(word)
        seen.add(word)

    return found[:max_terms]


def _build_glossary(text: str, title: str = "") -> str:
    """
    본문 + 제목에서 신조어 추출 → explain_neologism 호출 → 용어집 문자열 반환.

    반환 형식:
        "다음 용어를 참고하세요:\n<Term1(음차, 설명)>\n<Term2(음차, 설명)>\n..."

    조회 결과가 없거나 모두 실패하면 빈 문자열 반환 → 기존 프롬프트 그대로 사용.
    개별 용어 조회 실패는 silent skip (파이프라인 중단 방지).
    """
    combined = f"{title}\n{text}" if title else text
    terms = _extract_candidate_terms(combined)
    if not terms:
        return ""

    entries: list[str] = []
    for term in terms:
        try:
            explanation = explain_neologism(term)
        except Exception as e:
            logger.warning("explain_neologism 실패 (term=%s): %s", term, e)
            continue
        if not explanation:
            continue
        # 설명이 비어있는 폴백 응답("Term" 또는 "Term(Term)")은 주입 가치 없음 — skip
        inside = explanation[explanation.find("(") + 1 : -1] if "(" in explanation else ""
        if ", " not in inside:
            continue
        entries.append(explanation)

    if not entries:
        return ""

    logger.info("glossary 주입: %d개 용어 (%s)", len(entries), ", ".join(terms[:len(entries)]))
    return "다음 용어를 참고하세요:\n" + "\n".join(entries)


# ────────────────────────────────────────────────
# Core Function
# ────────────────────────────────────────────────
def translate_and_summarize(
    text: str,
    title: str = "",
    summary_sentences: int = 3,
    temperature: float = 0.1,
) -> dict:
    """
    영어 뉴스 기사를 격식체·일상체로 번역하고 요약합니다 (단일 LLM 호출).

    Args:
        text: 원본 영어 본문
        title: 영어 기사 제목 (선택). 제공 시 title_ko 번역 포함.
        summary_sentences: 요약 문장 수 (기본: 3)
        temperature: 생성 다양성 (0.0~1.0)

    Returns:
        {
            "title_ko":      str,  # 한국어 제목 (title 미제공 시 "")
            "translation":   str,  # 번역 전문
            "summary_formal": str, # 격식체 요약
            "summary_casual": str, # 일상체 요약
        }
    """
    system = SYSTEM_PROMPT.format(n=summary_sentences)
    user_content = f"[TITLE]\n{title}\n\n[BODY]\n{text}" if title else text

    # 번역 프롬프트 생성 직전 — 신조어 용어집 주입 (실패해도 파이프라인 계속)
    try:
        glossary = _build_glossary(text, title)
    except Exception as e:
        logger.warning("glossary 생성 실패 (건너뜀): %s", e)
        glossary = ""

    if glossary:
        user_content = f"{glossary}\n\n{user_content}"

    for attempt in range(3):   # 최대 3회 시도
        response = ollama.chat(
            model=MODEL,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_content},
            ],
            options={
                "temperature": 0.1,
                "num_predict": -1,   # 무제한 — EOS 토큰까지 생성
                "num_gpu": 0,        # 0 = Ollama가 VRAM에 맞게 자동 분할 (이전 99는 VRAM 부족 시 실패)
            },
            think=False,  # thinking 모드 비활성화 (qwen3.5:4b 전용)
        )
        result = _extract_json(response.message.content)
        if "(파싱 실패)" not in result.get("summary_formal", ""):
            return result

    return result  # 3회 실패 시 마지막 결과 반환


def _extract_json(text: str) -> dict:
    """pipeline.utils.extract_json 위임 (하위 호환용 래퍼)"""
    return _extract_json_util(text)


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
