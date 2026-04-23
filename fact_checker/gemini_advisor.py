"""
fact_checker/gemini_advisor.py — Step 3A: Gemini Advisor

설계 근거: DESIGN.md § 5 참고
  - Guo et al., AAAI 2024 (Bad Actor, Good Advisor) — LLM Advisor 구조
  - Google AI, Gemini API Docs 2025 — Google Search Grounding

흐름:
  signal_detector 결과(루머 강도/패턴)를 컨텍스트로 주입
  → Google Search Grounding + 상식 추론 → 최종 verdict 판단

  Pass A(문체 분석) 제거: signal_detector.py의 정규식 분석과 중복이므로 통합.
  signal_detector 결과를 그대로 Gemini 컨텍스트로 전달.

외부 연동:
  pipeline.py에서 호출:
    result = run(title, content, signal_strength, signal_patterns)  →  GeminiResult
"""

import json
import os
import re
import logging

logger = logging.getLogger(__name__)

# ── Gemini SDK 동적 임포트 (없으면 Mock 사용) ─────────────────────────────
try:
    from google import genai
    from google.genai import types
    _GENAI_AVAILABLE = True
except ImportError:
    _GENAI_AVAILABLE = False
    logger.warning("google-genai 미설치 — Mock 모드로 실행")

GEMINI_MODEL = "gemini-2.5-flash"


# ── 결과 데이터 클래스 ───────────────────────────────────────────────────

class GeminiResult:
    """Gemini Advisor 판단 결과."""

    def __init__(
        self,
        verdict: str,          # FACT | RUMOR | UNVERIFIED
        confidence: float,     # 0.0~1.0
        reasoning: str,        # 판단 근거 한 줄 요약
        grounded: bool = False,   # Google Search Grounding 적용 여부
        search_queries: list[str] | None = None,  # 실행된 검색 쿼리
    ):
        self.verdict = verdict
        self.confidence = confidence
        self.reasoning = reasoning
        self.grounded = grounded
        self.search_queries = search_queries or []

    def __repr__(self):
        return (
            f"GeminiResult(verdict={self.verdict}, confidence={self.confidence:.2f}, "
            f"grounded={self.grounded})"
        )


# ── 프롬프트 ─────────────────────────────────────────────────────────────
# 근거: Guo et al. (AAAI 2024) — Advisor 구조, signal_detector 결과를 컨텍스트로 주입
# Pass A(문체 분석) 제거 — signal_detector.py 정규식 분석으로 대체
PASS_B_SYSTEM = """You are an expert AI/technology news fact-checker with access to Google Search.

You will receive:
1. A news article claim (headline + body)
2. Pre-analysis results from a rule-based signal detector

Your job:
- Use Google Search to find evidence supporting or contradicting the key claims
- Cross-reference with the signal detector's findings
- Deliver a final fact-check verdict

Key claims to verify for AI tech news:
- Model names and capabilities (do they match official announcements?)
- Benchmark numbers (are they accurate per the original papers?)
- Company/institution claims (are attributions correct?)
- Timeline claims (is "first", "latest", "record" accurate?)

Return ONLY valid JSON:
{
  "verdict": "FACT" | "RUMOR" | "UNVERIFIED",
  "confidence": <0.0-1.0>,
  "key_claims_checked": ["<claim1>", "<claim2>"],
  "supporting_evidence": "<what search found that supports the claim>",
  "contradicting_evidence": "<what search found that contradicts the claim>",
  "reasoning": "<final reasoning in Korean, 2-3 sentences>",
  "search_queries_used": ["<query1>", "<query2>"]
}

Confidence calibration guide (from FEVER benchmark standards):
- 0.85~1.00: Strong evidence found, verdict is clear
- 0.65~0.84: Some evidence found, verdict is probable
- 0.50~0.64: Conflicting or insufficient evidence
- <0.50: Return UNVERIFIED, not enough to judge
"""

PASS_B_USER = """[ARTICLE TO FACT-CHECK]
Headline: {title}

Body (first 2000 chars):
{content}

[PRE-ANALYSIS (signal detector)]
Rumor signal strength: {signal_strength}
Detected patterns: {signal_patterns}

Use Google Search to verify the key factual claims. Return JSON verdict only."""


# ── JSON 파싱 헬퍼 ───────────────────────────────────────────────────────

def _extract_json(text: str) -> dict:
    """
    Gemini 응답에서 JSON 추출. 3단계 fallback:
    1. 마크다운 펜스 제거 후 전체 파싱
    2. 중괄호 기준 JSON 블록 추출
    3. 파싱 실패 시 JSONDecodeError raise

    Gemini는 Google Search Grounding 사용 시 JSON 앞뒤에
    자연어 설명을 붙이는 경우가 있어 이 헬퍼로 안정적으로 추출.
    """
    # 1차: 마크다운 펜스 제거
    cleaned = re.sub(r"```(?:json)?\s*|\s*```", "", text).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # 2차: 첫 번째 { ... } 블록 추출 (중첩 포함), 마지막 } 기준으로 greedy 재시도
    for pattern in (r"\{[\s\S]*\}", r"\{[^{}]*\}"):
        match = re.search(pattern, cleaned)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                continue

    # 3차: 실패
    raise json.JSONDecodeError(f"JSON 추출 실패: {text[:200]}", text, 0)


# ── 핵심 함수 ────────────────────────────────────────────────────────────

def _call_gemini_pass_b(
    title: str,
    content: str,
    signal_strength: str,
    signal_patterns: list,
    client,
) -> dict:
    """
    Google Search Grounding + 상식 추론.
    근거: Gemini API google_search tool — 실시간 검색 결과를 컨텍스트에 주입.
    signal_detector 결과를 컨텍스트로 주입 (Pass A 대체).
    최대 2회 retry.
    """
    prompt = PASS_B_USER.format(
        title=title,
        content=content[:2000],
        signal_strength=signal_strength,
        signal_patterns=signal_patterns,
    )

    for attempt in range(2):
        # Google Search Grounding 활성화 (google-genai SDK)
        # system_instruction 분리: Grounding 사용 시 역할 지시 명확화
        # thinking_budget=0: JSON 출력 토큰 확보 (Pass B는 Grounding 응답이 길어질 수 있음)
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=PASS_B_SYSTEM,
                temperature=0.2,
                max_output_tokens=1024,
                tools=[types.Tool(google_search=types.GoogleSearch())],
                thinking_config=types.ThinkingConfig(thinking_budget=0),
            ),
        )
        try:
            return _extract_json(response.text)
        except json.JSONDecodeError:
            if attempt == 1:
                raise
            logger.warning("[Pass B] JSON 파싱 실패, retry...")
    return {}


def _mock_run(title: str) -> GeminiResult:
    """Gemini API 미설치 시 Mock 결과 반환. 개발/테스트 환경 파이프라인 흐름 검증용."""
    logger.warning(f"[Mock] Gemini 미설치 — '{title[:40]}' UNVERIFIED 반환")
    return GeminiResult(
        verdict="UNVERIFIED",
        confidence=0.50,
        reasoning="Gemini API 미설치 — Mock 결과",
        grounded=False,
    )


def run(
    title: str,
    content: str,
    signal_strength: str = "NONE",
    signal_patterns: list[str] | None = None,
) -> GeminiResult:
    """
    Gemini Advisor 실행 진입점.

    Args:
        title:            영어 기사 제목
        content:          영어 기사 본문
        signal_strength:  signal_detector 루머 강도 (STRONG/WEAK/NONE)
        signal_patterns:  signal_detector 매칭 패턴 목록

    Returns:
        GeminiResult (verdict, confidence, reasoning 포함)

    실패 시: UNVERIFIED(0.50) 반환 (파이프라인 중단 방지)
    """
    if not _GENAI_AVAILABLE:
        return _mock_run(title)

    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        logger.warning("GEMINI_API_KEY 환경변수 없음 — Mock 반환")
        return _mock_run(title)

    try:
        client = genai.Client(api_key=api_key)

        # ── Google Search Grounding + 추론 ─────────────────
        # signal_detector 결과를 컨텍스트로 주입
        logger.info(f"[Gemini] '{title[:50]}' (signal={signal_strength}, with Google Search)")
        pass_b = _call_gemini_pass_b(title, content, signal_strength, signal_patterns or [], client)

        verdict = pass_b.get("verdict", "UNVERIFIED")
        confidence = float(pass_b.get("confidence", 0.50))
        reasoning = pass_b.get("reasoning", "")
        search_queries = pass_b.get("search_queries_used", [])

        # 강한 루머 신호 감지 시 confidence 하향 보정
        if signal_strength == "STRONG" and confidence > 0.70:
            confidence = max(confidence - 0.10, 0.60)
            reasoning += " (강한 루머 신호 감지 → confidence 보정: -0.10)"

        logger.info(
            f"[Gemini Done] verdict={verdict}, confidence={confidence:.2f}, "
            f"grounded={len(search_queries) > 0}"
        )

        return GeminiResult(
            verdict=verdict,
            confidence=confidence,
            reasoning=reasoning,
            grounded=len(search_queries) > 0,
            search_queries=search_queries,
        )

    except json.JSONDecodeError as e:
        logger.error(f"[Gemini] JSON 파싱 실패: {e}")
        return GeminiResult(
            verdict="UNVERIFIED", confidence=0.50,
            reasoning=f"JSON 파싱 오류: {e}"
        )
    except Exception as e:
        logger.error(f"[Gemini] 예외 발생: {e}")
        return GeminiResult(
            verdict="UNVERIFIED", confidence=0.50,
            reasoning=f"Gemini 호출 실패: {e}"
        )
