"""
fact_checker/pipeline.py — 팩트체크 파이프라인 오케스트레이터 (Step 0~3C)

설계 근거: DESIGN.md 전체 참고
  § 1: 3레벨 라우팅 — Vlachos & Riedel 2014, Thorne et al. 2018 (FEVER)
  § 5: Step 3A Gemini 2-Pass — Guo et al. AAAI 2024
  § 6: Step 3B CoVe — Dhuliawala et al. Meta AI 2023
  § 7: Step 3C DebateCV — Chern et al. arXiv:2507.19090
  § 8: Importance Score — Hassan et al. KDD 2017 (ClaimBuster)
  § 9: Confidence 집계 — Guo et al. TACL 2022

파이프라인 흐름:
  Step 0: 채널 신뢰도 기반 DROP 분류
  Step 1: 루머 신호 패턴 탐지 → FACT_AUTO or RUMOR
  Step 2: Google Fact Check API (~15.8% 매칭)
  Step 3A: Gemini Advisor + Google Search Grounding (전체 미매칭, signal_detector 결과 활용)
  Step 3B: Chain-of-Verification (confidence 0.50~0.79 구간)
  Step 3C: DebateCV 3-에이전트 (importance_score ≥ 0.7 AND 불확실)

외부 진입점:
  run_fact_check(title, content, source, source_type) → FactCheckResult
  save_articles.py에서 save_fact_checks() 호출 전에 실행
"""

import logging
from dataclasses import dataclass, field

from .channel_config import get_profile, should_drop, ChannelTier
from .signal_detector import detect as detect_signals, SignalResult
from . import google_fc_api
from .debate_agents import compute_importance_score

logger = logging.getLogger(__name__)


# ── 라우팅 임계값 (DESIGN.md § 9 기반) ──────────────────────────────────
CONFIDENCE_COVE_THRESHOLD = 0.80       # 3A 이후 이 미만이면 3B 진입
CONFIDENCE_UNVERIFIED_FLOOR = 0.50     # 최소 confidence (결정 불가 시)
IMPORTANCE_DEBATE_THRESHOLD = 0.70     # 이 이상이면 3C DebateCV 발동


# ── 결과 데이터 클래스 ───────────────────────────────────────────────────

@dataclass
class FactCheckResult:
    # 최종 라벨
    fact_label: str        # FACT | RUMOR | UNVERIFIED | DROP
    confidence: float      # 0.0~1.0

    # 처리 경로 (디버깅·로깅용)
    tier: ChannelTier
    step_reached: int      # 마지막으로 실행된 Step 번호 (0~3)
    signal: SignalResult | None = None
    fc_result: "google_fc_api.FCResult | None" = None

    # fact_checks 테이블 저장용
    evidence_url: str = ""
    evidence_publisher: str = ""
    matched_patterns: list[str] = field(default_factory=list)

    # Step 3 추가 메타 (검증 추적용)
    verification_method: str = ""     # gemini | cove | debate | auto | google_fc
    importance_score: float = 0.0
    reasoning_trace: str = ""         # 최종 판단 근거 요약 (한국어)

    def to_claim_dict(self, title: str) -> dict:
        """save_fact_checks()의 claims 리스트 형식으로 변환."""
        return {
            "claim":               title[:200],
            "verdict":             self.fact_label,
            "confidence":          self.confidence,
            "evidence_url":        self.evidence_url or None,
            "verification_method": self.verification_method or None,
            "importance_score":    self.importance_score or None,
            "reasoning_trace":     self.reasoning_trace[:500] if self.reasoning_trace else None,
        }

    def should_save(self) -> bool:
        """DROP이 아니면 DB 저장 대상."""
        return self.fact_label != "DROP"


# ── 파이프라인 실행 ───────────────────────────────────────────────────────

def run_fact_check(
    title: str,
    content: str,
    source: str,
    source_type: str,
    skip_fc_api: bool = False,
    skip_llm: bool = False,
) -> FactCheckResult:
    """
    팩트체크 파이프라인 실행.

    Args:
        title:        기사 제목 (영문)
        content:      기사 본문 (영문)
        source:       출처 이름 (RSS_FEEDS의 source 필드)
        source_type:  "media" | "community"
        skip_fc_api:  True이면 Step 2 Google FC API 건너뜀 (테스트용)
        skip_llm:     True이면 Step 3 전체 건너뜀 (테스트용)

    Returns:
        FactCheckResult
    """

    # ── Step 0: 채널 등급 분류 ──────────────────────────────────────────
    # 근거: Baly et al. EMNLP 2018 — 소스 신뢰도가 팩트체크 강력한 prior
    profile = get_profile(source)
    tier    = profile.default_tier

    if should_drop(tier):
        return FactCheckResult(
            fact_label="DROP", confidence=1.0,
            tier=tier, step_reached=0,
            verification_method="auto",
            reasoning_trace=f"채널 등급 DROP: {tier.value}",
        )

    # ── Step 1: 루머/의견 신호 탐지 ─────────────────────────────────────
    # 근거: Wang ACL 2017 (LIAR) — 헤징 표현이 PANTS-ON-FIRE와 유의미한 상관
    signal = detect_signals(
        title=title,
        content=content,
        source_type=source_type,
        current_tier=tier,
    )

    if signal.tier_override:
        tier = signal.tier_override

    if should_drop(tier):
        return FactCheckResult(
            fact_label="DROP", confidence=0.90,
            tier=tier, step_reached=1,
            signal=signal, matched_patterns=signal.matched_patterns,
            verification_method="auto",
            reasoning_trace=f"Opinion 패턴 탐지 → DROP: {signal.matched_patterns[:3]}",
        )

    if signal.fact_label_hint == "FACT_AUTO":
        return FactCheckResult(
            fact_label="FACT", confidence=profile.credibility_score,
            tier=tier, step_reached=1,
            signal=signal,
            verification_method="auto",
            reasoning_trace=f"공식 미디어 + 루머 신호 없음 → FACT_AUTO (신뢰도 {profile.credibility_score})",
        )

    if signal.fact_label_hint == "RUMOR" and skip_fc_api:
        return FactCheckResult(
            fact_label="RUMOR", confidence=0.80,
            tier=tier, step_reached=1,
            signal=signal, matched_patterns=signal.matched_patterns,
            verification_method="auto",
            reasoning_trace=f"강한 루머 신호 탐지: {signal.matched_patterns[:3]}",
        )

    # ── Step 2: Google Fact Check API ───────────────────────────────────
    # 근거: ClaimReview Schema — 200+ 팩트체킹 기관 DB, AI 뉴스 ~15.8% 매칭
    fc = None
    if not skip_fc_api:
        fc = google_fc_api.query(title)
        if fc.matched and fc.verdict != "NO_MATCH":
            return FactCheckResult(
                fact_label=fc.verdict, confidence=fc.confidence,
                tier=tier, step_reached=2,
                signal=signal, fc_result=fc,
                evidence_url=fc.evidence_url,
                evidence_publisher=fc.publisher,
                matched_patterns=signal.matched_patterns,
                verification_method="google_fc",
                reasoning_trace=f"Google FC API 매칭: {fc.publisher} → {fc.verdict}",
            )

    if skip_llm:
        return FactCheckResult(
            fact_label="UNVERIFIED", confidence=0.50,
            tier=tier, step_reached=2,
            signal=signal, fc_result=fc,
            matched_patterns=signal.matched_patterns if signal else [],
            verification_method="skip",
            reasoning_trace="LLM 단계 건너뜀 (skip_llm=True)",
        )

    # ── importance_score 산출 ─────────────────────────────────────────────
    # 근거: Hassan et al. KDD 2017 (ClaimBuster) — 수치+고유명사 밀도
    importance = compute_importance_score(title, content)
    logger.info(f"[Pipeline] importance_score={importance:.3f} for '{title[:50]}'")

    # ── Step 3A: Gemini 2-Pass Advisor ──────────────────────────────────
    # 근거: Guo et al. AAAI 2024 — Pass A 문체 분석 + Pass B Google Search Grounding
    try:
        from .gemini_advisor import run as gemini_run
        logger.info(f"[Pipeline] Step 3A: Gemini Advisor (signal={signal.rumor_strength if signal else 'NONE'})")
        gemini_result = gemini_run(
            title, content,
            signal_strength=signal.rumor_strength if signal else "NONE",
            signal_patterns=signal.matched_patterns if signal else [],
        )

        # 3A에서 충분히 확신하면 종료
        if gemini_result.confidence >= CONFIDENCE_COVE_THRESHOLD:
            return FactCheckResult(
                fact_label=gemini_result.verdict,
                confidence=gemini_result.confidence,
                tier=tier, step_reached=3,
                signal=signal, fc_result=fc,
                matched_patterns=signal.matched_patterns if signal else [],
                verification_method="gemini",
                importance_score=importance,
                reasoning_trace=gemini_result.reasoning,
            )

        # 3A confidence 불충분 → 3B 진입
        prior_verdict = gemini_result.verdict
        prior_confidence = gemini_result.confidence
        prior_reasoning = gemini_result.reasoning

    except Exception as e:
        logger.error(f"[Pipeline] Step 3A 실패: {e}")
        prior_verdict = "UNVERIFIED"
        prior_confidence = 0.50
        prior_reasoning = f"Gemini 2-Pass 실패: {e}"

    # ── Step 3B: Chain-of-Verification ──────────────────────────────────
    # 근거: Dhuliawala et al. Meta AI 2023 — 독립 검증으로 할루시네이션 38~40% 감소
    try:
        from .cove_verifier import run as cove_run
        logger.info(f"[Pipeline] Step 3B: CoVe (prior={prior_verdict}, conf={prior_confidence:.2f})")
        cove_result = cove_run(title, content, prior_verdict, prior_confidence)

        # CoVe에서 confidence 충분하고 importance 낮으면 종료
        if cove_result.confidence >= CONFIDENCE_COVE_THRESHOLD or importance < IMPORTANCE_DEBATE_THRESHOLD:
            return FactCheckResult(
                fact_label=cove_result.verdict,
                confidence=cove_result.confidence,
                tier=tier, step_reached=3,
                signal=signal, fc_result=fc,
                matched_patterns=signal.matched_patterns if signal else [],
                verification_method="cove",
                importance_score=importance,
                reasoning_trace=cove_result.reasoning,
            )

        prior_verdict = cove_result.verdict
        prior_confidence = cove_result.confidence
        prior_reasoning = cove_result.reasoning

    except Exception as e:
        logger.error(f"[Pipeline] Step 3B 실패: {e}")
        # 3B 실패해도 3C 진입 조건 충족이면 계속
        if importance < IMPORTANCE_DEBATE_THRESHOLD:
            return FactCheckResult(
                fact_label=prior_verdict, confidence=prior_confidence,
                tier=tier, step_reached=3,
                signal=signal, fc_result=fc,
                matched_patterns=signal.matched_patterns if signal else [],
                verification_method="gemini",
                importance_score=importance,
                reasoning_trace=prior_reasoning,
            )

    # ── Step 3C: DebateCV 3-에이전트 토론 ───────────────────────────────
    # 근거: Chern et al. arXiv:2507.19090 — 고중요도 기사 전용, F1 +9.2%
    # 조건: importance_score ≥ 0.7 AND 여전히 불확실
    try:
        from .debate_agents import run as debate_run
        logger.info(
            f"[Pipeline] Step 3C: DebateCV "
            f"(importance={importance:.3f}, prior={prior_verdict}, conf={prior_confidence:.2f})"
        )
        debate_result = debate_run(title, content, prior_verdict, prior_confidence)

        return FactCheckResult(
            fact_label=debate_result.verdict,
            confidence=debate_result.confidence,
            tier=tier, step_reached=3,
            signal=signal, fc_result=fc,
            matched_patterns=signal.matched_patterns if signal else [],
            verification_method="debate",
            importance_score=importance,
            reasoning_trace=(
                f"[DebateCV {debate_result.debate_outcome}] {debate_result.judge_reasoning}"
            ),
        )

    except Exception as e:
        logger.error(f"[Pipeline] Step 3C 실패: {e}")
        return FactCheckResult(
            fact_label=prior_verdict, confidence=prior_confidence,
            tier=tier, step_reached=3,
            signal=signal, fc_result=fc,
            matched_patterns=signal.matched_patterns if signal else [],
            verification_method="cove",
            importance_score=importance,
            reasoning_trace=f"DebateCV 실패 → CoVe 결과 사용: {prior_reasoning}",
        )
