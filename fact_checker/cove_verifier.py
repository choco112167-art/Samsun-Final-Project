"""
fact_checker/cove_verifier.py — Step 3B: Chain-of-Verification (CoVe)

설계 근거: DESIGN.md § 6 참고
  - Dhuliawala et al., Meta AI 2023 (arXiv:2309.11495)
    "Chain-of-Verification Reduces Hallucination in Large Language Models"
    → List-based CoVe: 병렬 검증 질문 생성 후 독립 순차 답변
    → 검증 단계에서 Draft 답변을 절대 노출하지 않음 (핵심 원칙)
    → 할루시네이션 38~40% 감소 효과

흐름:
  1. Draft verdict 생성 (Gemini 또는 OpenRouter LLM)
  2. 5개 독립 검증 질문 생성 (Draft 비공개)
  3. 각 질문 독립 답변 (Draft 여전히 비공개)
  4. 최종 종합 verdict + confidence 보정

AI 테크 뉴스 도메인 검증 질문 카테고리 (논문 Appendix B 커스터마이징):
  Q1: 존재 검증 — 언급된 모델/기관/논문이 실제 존재하는가?
  Q2: 수치 검증 — 벤치마크/파라미터 수치가 정확한가?
  Q3: 출처 검증 — 인용된 출처가 실제로 그 내용을 발표했는가?
  Q4: 맥락 검증 — 비교 대상이 공정하게 제시되었는가?
  Q5: 신규성 검증 — "최초", "SOTA" 등 주장이 현재 기준으로 사실인가?
"""

import json
import os
import re
import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

try:
    from google import genai
    _GENAI_AVAILABLE = True
except ImportError:
    _GENAI_AVAILABLE = False


# ── 결과 데이터 클래스 ───────────────────────────────────────────────────

@dataclass
class CoVeResult:
    """Chain-of-Verification 결과."""
    verdict: str            # FACT | RUMOR | UNVERIFIED
    confidence: float       # 0.0~1.0 (보정된 최종값)
    draft_verdict: str      # 1단계 Draft 판단
    draft_confidence: float
    verification_answers: list[dict] = field(default_factory=list)
    # [{"question": str, "answer": str, "consistent": bool}]
    agreement_ratio: float = 0.0   # 검증 질문 일치율 (0.0~1.0)
    reasoning: str = ""


# ── 프롬프트 ─────────────────────────────────────────────────────────────

QUESTION_GEN_SYSTEM = """You are designing a fact-checking verification plan for an AI/tech news article.
Generate exactly 5 verification questions — one per category.
The questions must be independently answerable WITHOUT seeing any verdict.

Categories (MUST cover all 5):
1. EXISTENCE: Does the model/organization/paper mentioned actually exist?
2. NUMBERS: Are the benchmark scores/parameters/dates accurate?
3. SOURCE: Did the cited organization/person actually make this statement?
4. CONTEXT: Is the comparison or framing fair and not misleading?
5. NOVELTY: Is the "first", "best", "record" claim accurate as of now?

CRITICAL: Questions must NOT reference or hint at any verdict. They must be purely factual inquiries.

Return ONLY valid JSON:
{
  "questions": [
    {"category": "EXISTENCE", "question": "<specific verifiable question>"},
    {"category": "NUMBERS",   "question": "<specific verifiable question>"},
    {"category": "SOURCE",    "question": "<specific verifiable question>"},
    {"category": "CONTEXT",   "question": "<specific verifiable question>"},
    {"category": "NOVELTY",   "question": "<specific verifiable question>"}
  ]
}"""

QUESTION_GEN_USER = """[ARTICLE]
Headline: {title}

Body (first 1500 chars):
{content}

Generate 5 independent verification questions. DO NOT include or reference any verdict.
Return JSON only."""


VERIFICATION_SYSTEM = """You are an independent fact-checker verifying a single specific question about an AI/tech news article.
You have NOT seen any verdict for this article. Answer ONLY the question asked.

Rules:
- Answer based on your knowledge and reasoning
- Be specific: cite model names, paper titles, organizations when relevant
- State clearly if you cannot verify (insufficient information)
- Do NOT guess or speculate beyond what you know

Return ONLY valid JSON:
{
  "question": "<the question>",
  "answer": "<detailed answer>",
  "verifiable": true | false,
  "supports_claim": true | false | null,
  "confidence": <0.0-1.0>
}
(supports_claim=null when cannot determine)"""

VERIFICATION_USER = """[ARTICLE CONTEXT]
Headline: {title}

[VERIFICATION QUESTION]
Category: {category}
Question: {question}

Answer this specific question independently. Return JSON only."""


SYNTHESIS_SYSTEM = """You are synthesizing fact-checking results from Chain-of-Verification.
You have:
1. A DRAFT verdict (generated before verification)
2. 5 INDEPENDENT verification answers (generated without seeing the draft)

Your task:
- Compare draft verdict with verification evidence
- Where they agree → increase confidence
- Where they conflict → decrease confidence, flag uncertainty
- Final verdict should reflect the VERIFICATION ANSWERS more than the draft
  (verification is more reliable because it was done independently)

Confidence calibration (per FEVER benchmark):
- All 5 verifications consistent + support verdict → 0.85~0.95
- 4/5 consistent → 0.70~0.84
- 3/5 consistent → 0.55~0.69
- ≤2/5 consistent → mark UNVERIFIED, confidence ≤ 0.55

Return ONLY valid JSON:
{
  "final_verdict": "FACT" | "RUMOR" | "UNVERIFIED",
  "final_confidence": <0.0-1.0>,
  "agreement_ratio": <0.0-1.0>,
  "draft_vs_verification": "AGREE" | "PARTIAL" | "CONFLICT",
  "reasoning": "<Korean, 2-3 sentences explaining the final verdict>"
}"""

SYNTHESIS_USER = """[DRAFT VERDICT]
Verdict: {draft_verdict}
Confidence: {draft_confidence}
Main concerns: {main_concerns}

[VERIFICATION RESULTS (5 independent answers)]
{verification_results}

Synthesize and return the final verdict. Return JSON only."""


# ── LLM 호출 헬퍼 ────────────────────────────────────────────────────────

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
    """LLM 호출 + JSON 파싱. Gemini quota 소진 시 OpenRouter fallback. 최대 2회 retry."""
    from .llm_client import call_with_fallback

    for attempt in range(2):
        text, used_fallback = call_with_fallback(
            system=system,
            user=user,
            gemini_client=client,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        if used_fallback:
            logger.info("[CoVe] OpenRouter fallback 사용")
        try:
            return _extract_json(text)
        except json.JSONDecodeError:
            if attempt == 1:
                raise
            logger.warning(f"[CoVe] JSON 파싱 실패, retry... (attempt {attempt+1})")
    return {}


# ── 핵심 함수 ────────────────────────────────────────────────────────────

def _mock_run(prior_verdict: str, prior_confidence: float) -> CoVeResult:
    """API 미설치 시 Mock — prior verdict 그대로 반환."""
    logger.warning("[CoVe Mock] Gemini 미설치 — prior verdict 반환")
    return CoVeResult(
        verdict=prior_verdict,
        confidence=prior_confidence,
        draft_verdict=prior_verdict,
        draft_confidence=prior_confidence,
        reasoning="CoVe Mock — Gemini API 미설치",
    )


def run(
    title: str,
    content: str,
    prior_verdict: str = "UNVERIFIED",
    prior_confidence: float = 0.50,
) -> CoVeResult:
    """
    Chain-of-Verification 실행.

    Args:
        title:             영어 기사 제목
        content:           영어 기사 본문
        prior_verdict:     Step 3A Gemini 판단 (참고용)
        prior_confidence:  Step 3A confidence

    Returns:
        CoVeResult (보정된 verdict + confidence)

    논문 핵심 원칙 준수:
      - Step 1(Draft)과 Step 2(질문 생성)는 서로 독립
      - Step 3(검증 답변)은 Draft를 절대 보지 않음
      - Step 4(종합)에서만 Draft와 검증 결과 비교
    """
    if not _GENAI_AVAILABLE:
        return _mock_run(prior_verdict, prior_confidence)

    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        return _mock_run(prior_verdict, prior_confidence)

    try:
        client = genai.Client(api_key=api_key)

        # ── Step 1: Draft — 3A Gemini 결과 재사용 (중복 API 호출 제거) ──
        # 3A에서 이미 동일 기사를 Google Search Grounding 기반으로 판단했으므로 추가 호출 생략.
        # CoVe 핵심 원칙(검증 질문 생성 시 Draft 비공개)은 Step 2에서 그대로 유지됨.
        draft_verdict = prior_verdict
        draft_confidence = prior_confidence
        main_concerns: list[str] = []

        # ── Step 2: 검증 질문 생성 (Draft 비공개) ─────────
        # 핵심: QUESTION_GEN 프롬프트에 Draft 결과 포함 안 함
        logger.info(f"[CoVe Step 2] 검증 질문 생성")
        q_raw = _call(
            QUESTION_GEN_SYSTEM,
            QUESTION_GEN_USER.format(title=title, content=content[:1500]),
            client,
            temperature=0.2,
        )
        questions = q_raw.get("questions", [])

        if not questions:
            logger.warning("[CoVe] 질문 생성 실패 — Draft 결과 반환")
            return CoVeResult(
                verdict=draft_verdict,
                confidence=draft_confidence,
                draft_verdict=draft_verdict,
                draft_confidence=draft_confidence,
                reasoning="검증 질문 생성 실패",
            )

        # ── Step 3: 각 질문 독립 답변 (Draft 절대 비공개) ─
        # 논문 핵심: "factored" 방식 — 각 질문을 격리된 컨텍스트에서 독립 답변
        logger.info(f"[CoVe Step 3] {len(questions)}개 질문 독립 검증")
        verification_answers = []
        for q in questions:
            ans_raw = _call(
                VERIFICATION_SYSTEM,
                VERIFICATION_USER.format(
                    title=title,
                    category=q.get("category", ""),
                    question=q.get("question", ""),
                ),
                client,
                temperature=0.1,
                max_tokens=384,
            )
            verification_answers.append({
                "category": q.get("category"),
                "question": q.get("question"),
                "answer": ans_raw.get("answer", ""),
                "supports_claim": ans_raw.get("supports_claim"),
                "verifiable": ans_raw.get("verifiable", True),
                "confidence": float(ans_raw.get("confidence", 0.5)),
            })

        # ── Step 4: 종합 (Draft + 검증 결과 비교) ─────────
        logger.info(f"[CoVe Step 4] 종합 판단")
        vr_text = "\n".join([
            f"Q{i+1} [{a['category']}]: {a['question']}\n"
            f"  → {a['answer']} (supports_claim={a['supports_claim']}, confidence={a['confidence']:.2f})"
            for i, a in enumerate(verification_answers)
        ])

        synth_raw = _call(
            SYNTHESIS_SYSTEM,
            SYNTHESIS_USER.format(
                draft_verdict=draft_verdict,
                draft_confidence=draft_confidence,
                main_concerns=main_concerns,
                verification_results=vr_text,
            ),
            client,
            temperature=0.1,
            max_tokens=512,
        )

        final_verdict = synth_raw.get("final_verdict", "UNVERIFIED")
        final_confidence = float(synth_raw.get("final_confidence", 0.50))
        agreement_ratio = float(synth_raw.get("agreement_ratio", 0.0))
        reasoning = synth_raw.get("reasoning", "")

        # CoVe 통과 시 confidence 소폭 상향 보정 (+0.05)
        # 근거: 독립 검증을 통과한 결과는 단일 판단보다 신뢰도 높음 (CoVe 논문 Table 3)
        if agreement_ratio >= 0.8 and final_confidence < 0.90:
            final_confidence = min(final_confidence + 0.05, 0.90)
            reasoning += f" (CoVe 독립검증 일치율 {agreement_ratio:.0%} → confidence +0.05 보정)"

        logger.info(
            f"[CoVe Done] verdict={final_verdict}, confidence={final_confidence:.2f}, "
            f"agreement={agreement_ratio:.2f}"
        )

        return CoVeResult(
            verdict=final_verdict,
            confidence=final_confidence,
            draft_verdict=draft_verdict,
            draft_confidence=draft_confidence,
            verification_answers=verification_answers,
            agreement_ratio=agreement_ratio,
            reasoning=reasoning,
        )

    except json.JSONDecodeError as e:
        logger.error(f"[CoVe] JSON 파싱 실패: {e}")
        return CoVeResult(
            verdict=prior_verdict, confidence=prior_confidence,
            draft_verdict=prior_verdict, draft_confidence=prior_confidence,
            reasoning=f"JSON 파싱 오류: {e}",
        )
    except Exception as e:
        logger.error(f"[CoVe] 예외 발생: {e}")
        return CoVeResult(
            verdict=prior_verdict, confidence=prior_confidence,
            draft_verdict=prior_verdict, draft_confidence=prior_confidence,
            reasoning=f"CoVe 실패: {e}",
        )
