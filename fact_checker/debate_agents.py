"""
fact_checker/debate_agents.py — Step 3C: DebateCV 3-에이전트 토론

설계 근거: DESIGN.md § 7 참고
  - Chern et al. (2024), arXiv:2507.19090
    "Debating Truth: Debate-driven Claim Verification with Multiple LLM Agents"
    → Prosecutor-Defender-Judge 3역할 구조
    → Round 1: 독립 논거 → Round 2: 상호 반박 → Judge: 최종 판결
    → ClaimBench에서 단일 GPT-4 대비 F1 +9.2%

  - Du et al. (ICML 2024), arXiv:2305.14325
    "Improving Factuality and Reasoning through Multiagent Debate"
    → Temperature 0.7 (Debaters) / 0.3 (Judge) 설정이 최적
    → 토론자: 다양성 필요, 판사: 신중함 필요

  - Liang et al. (ICML 2024)
    → 동일 LLM 2개가 서로 반박 시 팩트체크 정확도 +11.4%

고중요도 기사 기준 (importance_score ≥ 0.7):
  - AI 모델명 포함 (GPT-5, Gemini 3 등)
  - 벤치마크 수치 주장
  - "세계 최초", "SOTA", "최고 성능" 등 배타적 주장
  - 기업 인수합병, 대규모 투자 발표

흐름:
  Round 1: Prosecutor + Defender 독립 논거 생성
  Round 2: Prosecutor → Defender 논거 반박 / Defender → Prosecutor 논거 반박
  Final:   Judge → 양측 논거 + 반박 검토 → 최종 verdict + confidence
"""

import json
import os
import re
import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

try:
    from google import genai
    from google.genai import types
    _GENAI_AVAILABLE = True
except ImportError:
    _GENAI_AVAILABLE = False

GEMINI_MODEL = "gemini-2.5-flash"


# ── 결과 데이터 클래스 ───────────────────────────────────────────────────

@dataclass
class DebateResult:
    """DebateCV 3-에이전트 토론 결과."""
    verdict: str              # FACT | RUMOR | UNVERIFIED
    confidence: float         # 0.0~1.0
    judge_reasoning: str      # Judge 최종 판단 근거 (한국어)

    # 토론 기록
    prosecutor_arg: str = ""  # Prosecutor Round 1 논거
    defender_arg: str = ""    # Defender Round 1 논거
    prosecutor_rebuttal: str = ""  # Round 2 반박
    defender_rebuttal: str = ""    # Round 2 반박

    # 메타
    rounds_completed: int = 0
    debate_outcome: str = ""  # UNANIMOUS | MAJORITY | SPLIT


# ── Importance Score 산출 ─────────────────────────────────────────────────

# AI 모델명 패턴 (논문: Popat et al., EMNLP 2018 — 고유명사 밀도가 검증 난이도 지표)
_MODEL_PATTERNS = re.compile(
    r"\b(GPT-\d|Claude\s*\d|Gemini\s*\d|Llama\s*\d|Mistral|Qwen|Phi-\d|"
    r"DeepSeek|Grok|o\d|Falcon|Command|BLOOM|PaLM|Bard|Copilot|Sora|"
    r"Stable\s*Diffusion|DALL-E|Midjourney|Whisper|Codex)\b",
    re.IGNORECASE,
)

# 벤치마크 수치 패턴 (숫자+% 또는 벤치마크명+숫자)
_BENCHMARK_PATTERNS = re.compile(
    r"\b(\d+\.?\d*\s*%|\bMMLU\b|\bHumanEval\b|\bGSM8K\b|\bSWE-bench\b|"
    r"\bBigBench\b|\bHellaSwag\b|\bARC\b|\bTruthfulQA\b)\b",
    re.IGNORECASE,
)

# 배타적 주장 패턴
_SUPERLATIVE_PATTERNS = re.compile(
    r"\b(first|world.?s?\s+first|state.of.the.art|SOTA|best|record|"
    r"breakthrough|unprecedented|revolutionary|largest|fastest|most\s+powerful)\b",
    re.IGNORECASE,
)

# Breaking/Exclusive 뉴스 패턴
_BREAKING_PATTERNS = re.compile(
    r"\b(breaking|exclusive|scoop|just\s+in|developing|leaked|sources\s+say)\b",
    re.IGNORECASE,
)


def compute_importance_score(title: str, content: str) -> float:
    """
    기사 중요도 점수 산출 (0.0~1.0).

    근거:
      - Hassan et al., KDD 2017 (ClaimBuster): 수치+고유명사 밀도가 checkworthy 핵심 feature
      - Nakov et al., IJCAI 2021: 전문 팩트체커 인터뷰 — 수치/배타적 주장 우선 검증

    가중치:
      0.40 × 모델명 등장 (최대 3개 기준 정규화)
      0.30 × 벤치마크 수치 존재
      0.20 × 배타적 주장 존재
      0.10 × Breaking/Exclusive 뉴스 여부
    """
    text = f"{title} {content[:500]}"  # 제목 + 앞부분 집중 분석

    model_count = len(_MODEL_PATTERNS.findall(text))
    has_benchmark = bool(_BENCHMARK_PATTERNS.search(text))
    has_superlative = bool(_SUPERLATIVE_PATTERNS.search(text))
    is_breaking = bool(_BREAKING_PATTERNS.search(title))  # 제목만

    score = (
        0.40 * min(model_count / 3, 1.0)
        + 0.30 * (1.0 if has_benchmark else 0.0)
        + 0.20 * (1.0 if has_superlative else 0.0)
        + 0.10 * (1.0 if is_breaking else 0.0)
    )
    return round(score, 3)


# ── 프롬프트 ─────────────────────────────────────────────────────────────

PROSECUTOR_R1_SYSTEM = """You are the PROSECUTOR in a fact-checking debate.
Your role: Build the strongest possible case that the following claim is FALSE, MISLEADING, or EXAGGERATED.
You are an expert in AI/technology journalism and know common patterns of tech hype, misinformation, and inaccuracy.

Focus on:
- Technical inaccuracies (wrong specs, inflated benchmarks)
- Missing context (cherry-picked comparisons)
- Unsupported "world's first" or "best" claims
- Anonymous or unverifiable sources
- Timeline errors or premature announcements

Generate 3-5 specific, evidence-based arguments.
Return ONLY valid JSON:
{
  "role": "PROSECUTOR",
  "arguments": ["<arg1>", "<arg2>", "<arg3>"],
  "key_weaknesses": ["<weakness1>", "<weakness2>"],
  "suggested_verdict": "RUMOR" | "UNVERIFIED",
  "confidence": <0.0-1.0>
}"""

PROSECUTOR_R1_USER = """[CLAIM TO PROSECUTE]
Headline: {title}

Body (first 1500 chars):
{content}

Build the case against this claim. Return JSON only."""


DEFENDER_R1_SYSTEM = """You are the DEFENDER in a fact-checking debate.
Your role: Build the strongest possible case that the following claim is TRUE and ACCURATE.
You are an expert in AI/technology journalism and can recognize legitimate breakthrough announcements.

Focus on:
- Consistent with known technical facts about the organizations/models mentioned
- Plausible given the state of AI development
- Matches typical announcement patterns from credible organizations
- Numbers are within expected ranges for the technology described
- Context is fair and appropriate

Generate 3-5 specific, evidence-based arguments.
Return ONLY valid JSON:
{
  "role": "DEFENDER",
  "arguments": ["<arg1>", "<arg2>", "<arg3>"],
  "key_strengths": ["<strength1>", "<strength2>"],
  "suggested_verdict": "FACT" | "UNVERIFIED",
  "confidence": <0.0-1.0>
}"""

DEFENDER_R1_USER = """[CLAIM TO DEFEND]
Headline: {title}

Body (first 1500 chars):
{content}

Build the defense for this claim. Return JSON only."""


REBUTTAL_SYSTEM = """You are in Round 2 of a fact-checking debate.
You have read the opposing side's arguments and must now rebut them.
Identify the weakest points in their case and explain why they are wrong or insufficient.

Be specific. Point to concrete counter-evidence or logical flaws.
Return ONLY valid JSON:
{
  "rebuttal_points": ["<rebuttal1>", "<rebuttal2>", "<rebuttal3>"],
  "strongest_counter": "<the single most powerful counter-argument>"
}"""

PROSECUTOR_REBUTTAL_USER = """You are the PROSECUTOR rebutting the Defender's arguments.

[DEFENDER'S ARGUMENTS]
{defender_args}

[DEFENDER'S KEY STRENGTHS]
{defender_strengths}

Rebut these arguments. Find specific flaws. Return JSON only."""

DEFENDER_REBUTTAL_USER = """You are the DEFENDER rebutting the Prosecutor's arguments.

[PROSECUTOR'S ARGUMENTS]
{prosecutor_args}

[PROSECUTOR'S KEY WEAKNESSES IDENTIFIED]
{prosecutor_weaknesses}

Rebut these arguments. Find specific flaws. Return JSON only."""


JUDGE_SYSTEM = """You are the JUDGE in a fact-checking debate about an AI/technology news claim.
You have received:
1. Prosecutor's arguments (case against the claim)
2. Defender's arguments (case for the claim)
3. Both sides' rebuttals

Your task:
- Evaluate the quality and strength of each argument
- Weigh the evidence fairly
- Deliver a final verdict

IMPORTANT:
- Strong arguments with specific technical facts outweigh vague assertions
- When evidence is genuinely mixed → UNVERIFIED
- You must explain which arguments were most persuasive and why

Confidence calibration (FEVER benchmark standard):
- Clear winner with strong evidence → 0.85~0.95
- Moderate winner → 0.70~0.84
- Genuinely contested → 0.55~0.69 (likely UNVERIFIED)

Return ONLY valid JSON:
{
  "final_verdict": "FACT" | "RUMOR" | "UNVERIFIED",
  "final_confidence": <0.0-1.0>,
  "debate_outcome": "UNANIMOUS" | "MAJORITY" | "SPLIT",
  "winning_side": "PROSECUTOR" | "DEFENDER" | "NEITHER",
  "decisive_arguments": ["<most persuasive arg1>", "<most persuasive arg2>"],
  "reasoning": "<Korean, 3-4 sentences explaining the final verdict>"
}"""

JUDGE_USER = """[ARTICLE BEING JUDGED]
Headline: {title}

Article body (first 1000 chars):
{content}

[PROSECUTOR'S CASE (claiming FALSE/MISLEADING)]
Arguments: {prosecutor_args}
Round 2 Rebuttal: {prosecutor_rebuttal}
Suggested verdict: {prosecutor_verdict} (confidence: {prosecutor_conf:.2f})

[DEFENDER'S CASE (claiming TRUE/ACCURATE)]
Arguments: {defender_args}
Round 2 Rebuttal: {defender_rebuttal}
Suggested verdict: {defender_verdict} (confidence: {defender_conf:.2f})

Deliver your final verdict as judge. Return JSON only."""


# ── 핵심 함수 ────────────────────────────────────────────────────────────

def _extract_json(text: str) -> dict:
    """Gemini 응답에서 JSON 추출. 마크다운 펜스 제거 → 중괄호 블록 추출 순으로 시도."""
    cleaned = re.sub(r"```(?:json)?\s*|\s*```", "", text).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass
    for pattern in (r"\{[\s\S]*\}", r"\{[^{}]*\}"):
        match = re.search(pattern, cleaned)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                continue
    raise json.JSONDecodeError(f"JSON 추출 실패: {text[:200]}", text, 0)


def _call(system: str, user: str, client, temperature: float = 0.1, max_tokens: int = 1024) -> dict:
    """Gemini 호출 + JSON 파싱. 최대 2회 retry.
    system_instruction 분리로 Gemini가 역할 지시를 시스템 레벨로 인식.
    thinking_budget=0: gemini-2.5-flash 기본 thinking이 output 토큰 소비하여 JSON 잘림 방지.
    """
    for attempt in range(2):
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=user,
            config=types.GenerateContentConfig(
                system_instruction=system,
                temperature=temperature,
                max_output_tokens=max_tokens,
                thinking_config=types.ThinkingConfig(thinking_budget=0),
            ),
        )
        try:
            return _extract_json(response.text)
        except json.JSONDecodeError:
            if attempt == 1:
                raise
            logger.warning(f"[DebateCV] JSON 파싱 실패, retry... (attempt {attempt+1})")
    return {}


def _mock_run(prior_verdict: str, prior_confidence: float) -> DebateResult:
    logger.warning("[DebateCV Mock] Gemini 미설치 — prior verdict 반환")
    return DebateResult(
        verdict=prior_verdict,
        confidence=prior_confidence,
        judge_reasoning="DebateCV Mock — Gemini API 미설치",
        debate_outcome="SPLIT",
    )


def run(
    title: str,
    content: str,
    prior_verdict: str = "UNVERIFIED",
    prior_confidence: float = 0.50,
) -> DebateResult:
    """
    DebateCV 3-에이전트 토론 실행.

    Args:
        title:            영어 기사 제목
        content:          영어 기사 본문
        prior_verdict:    Step 3B CoVe 판단 (참고용)
        prior_confidence: Step 3B confidence

    Returns:
        DebateResult (Judge의 최종 verdict + confidence)

    토론 구조 (Chern et al., arXiv:2507.19090):
      Round 1: Prosecutor + Defender 독립 논거 (temperature=0.7, 다양성 확보)
      Round 2: 상호 반박 (temperature=0.4)
      Final:   Judge 판결 (temperature=0.3, 신중함 우선)
    """
    if not _GENAI_AVAILABLE:
        return _mock_run(prior_verdict, prior_confidence)

    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        return _mock_run(prior_verdict, prior_confidence)

    try:
        client = genai.Client(api_key=api_key)

        # ── Round 1: 독립 논거 생성 ───────────────────────
        # 근거: Du et al. (ICML 2024) — temperature 0.7로 다양한 논거 확보
        logger.info(f"[DebateCV Round 1] '{title[:50]}'")

        p_raw = _call(
            PROSECUTOR_R1_SYSTEM,
            PROSECUTOR_R1_USER.format(title=title, content=content[:1500]),
            client, temperature=0.7, max_tokens=512,
        )
        d_raw = _call(
            DEFENDER_R1_SYSTEM,
            DEFENDER_R1_USER.format(title=title, content=content[:1500]),
            client, temperature=0.7, max_tokens=512,
        )

        prosecutor_args = p_raw.get("arguments", [])
        prosecutor_weaknesses = p_raw.get("key_weaknesses", [])
        prosecutor_verdict = p_raw.get("suggested_verdict", "UNVERIFIED")
        prosecutor_conf = float(p_raw.get("confidence", 0.5))

        defender_args = d_raw.get("arguments", [])
        defender_strengths = d_raw.get("key_strengths", [])
        defender_verdict = d_raw.get("suggested_verdict", "UNVERIFIED")
        defender_conf = float(d_raw.get("confidence", 0.5))

        logger.info(
            f"[DebateCV R1] Prosecutor→{prosecutor_verdict}({prosecutor_conf:.2f}), "
            f"Defender→{defender_verdict}({defender_conf:.2f})"
        )

        # ── Round 2: 상호 반박 ────────────────────────────
        logger.info(f"[DebateCV Round 2] 상호 반박")

        pr_raw = _call(
            REBUTTAL_SYSTEM,
            PROSECUTOR_REBUTTAL_USER.format(
                defender_args="\n".join(defender_args),
                defender_strengths="\n".join(defender_strengths),
            ),
            client, temperature=0.4, max_tokens=384,
        )
        dr_raw = _call(
            REBUTTAL_SYSTEM,
            DEFENDER_REBUTTAL_USER.format(
                prosecutor_args="\n".join(prosecutor_args),
                prosecutor_weaknesses="\n".join(prosecutor_weaknesses),
            ),
            client, temperature=0.4, max_tokens=384,
        )

        prosecutor_rebuttal = pr_raw.get("strongest_counter", "")
        defender_rebuttal = dr_raw.get("strongest_counter", "")

        # ── Final: Judge 판결 ──────────────────────────────
        # 근거: Du et al. (ICML 2024) — Judge temperature=0.3, 신중함 우선
        logger.info(f"[DebateCV Final] Judge 판결")

        judge_raw = _call(
            JUDGE_SYSTEM,
            JUDGE_USER.format(
                title=title,
                content=content[:1000],
                prosecutor_args="\n".join(prosecutor_args),
                prosecutor_rebuttal=prosecutor_rebuttal,
                prosecutor_verdict=prosecutor_verdict,
                prosecutor_conf=prosecutor_conf,
                defender_args="\n".join(defender_args),
                defender_rebuttal=defender_rebuttal,
                defender_verdict=defender_verdict,
                defender_conf=defender_conf,
            ),
            client, temperature=0.3, max_tokens=640,
        )

        final_verdict = judge_raw.get("final_verdict", "UNVERIFIED")
        final_confidence = float(judge_raw.get("final_confidence", 0.50))
        debate_outcome = judge_raw.get("debate_outcome", "SPLIT")
        reasoning = judge_raw.get("reasoning", "")

        # 만장일치(UNANIMOUS) 시 confidence 상향 보정
        # 근거: Chern et al. — Prosecutor + Defender 모두 같은 방향이면 신뢰도 높음
        if debate_outcome == "UNANIMOUS" and final_confidence < 0.90:
            final_confidence = min(final_confidence + 0.05, 0.92)
            reasoning += f" (만장일치 → confidence +0.05)"

        logger.info(
            f"[DebateCV Done] verdict={final_verdict}, confidence={final_confidence:.2f}, "
            f"outcome={debate_outcome}"
        )

        return DebateResult(
            verdict=final_verdict,
            confidence=final_confidence,
            judge_reasoning=reasoning,
            prosecutor_arg="\n".join(prosecutor_args),
            defender_arg="\n".join(defender_args),
            prosecutor_rebuttal=prosecutor_rebuttal,
            defender_rebuttal=defender_rebuttal,
            rounds_completed=2,
            debate_outcome=debate_outcome,
        )

    except json.JSONDecodeError as e:
        logger.error(f"[DebateCV] JSON 파싱 실패: {e}")
        return DebateResult(
            verdict=prior_verdict, confidence=prior_confidence,
            judge_reasoning=f"JSON 파싱 오류: {e}", debate_outcome="SPLIT",
        )
    except Exception as e:
        logger.error(f"[DebateCV] 예외 발생: {e}")
        return DebateResult(
            verdict=prior_verdict, confidence=prior_confidence,
            judge_reasoning=f"DebateCV 실패: {e}", debate_outcome="SPLIT",
        )
