"""
RSS 이후 · 번역 직전 초경량 게이트.

목표:
  - ai_only=False 커뮤니티 피드에 대해 제목·본문 AI 관련성 재확인 (크롤 단계와 동일 규칙)
  - 번역 LLM 호출 전 DROP 으로 토큰 비용 절감
  - 언론사(TIER1 계열) FACT_AUTO 경로 여부 플래그 제공 (심층 FC 생략)
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass

_collect_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "collect"))
if _collect_root not in sys.path:
    sys.path.insert(0, _collect_root)

from models.article import Article  # noqa: E402
from models.credibility import is_ai_related  # noqa: E402

from fact_checker.channel_config import ChannelTier, get_profile, should_drop
from fact_checker.signal_detector import detect as detect_signals


@dataclass
class PreflightResult:
    dropped: bool
    reason: str = ""
    #: 번역 후 전체 팩트체크(run_fact_check) 실행 여부 — False 면 FACT 자동 배선만
    needs_deep_fact_check: bool = True
    #: 공식 미디어 + 루머 신호 없음 → FACT_AUTO (심층 FC 생략)
    tier1_fact_auto_only: bool = False
    #: 의견 다수이나 모델명·수치 등 Insight 신호 → 심층 FC 생략, fact_label=INSIGHT
    insight_analysis: bool = False


def run_preflight(
    *,
    title: str,
    content: str,
    source: str,
    source_type: str,
    ai_only_feed: bool,
    title_only_feed: bool = False,
) -> PreflightResult:
    profile = get_profile(source)
    tier: ChannelTier = profile.default_tier

    if not ai_only_feed:
        shim = Article(
            title=title or "",
            url="",
            source=source,
            category="",
            country="",
            published_at="",
            content=content or "",
            source_type=source_type,
            ai_only_feed=False,
        )
        if not is_ai_related(shim, title_only=title_only_feed):
            return PreflightResult(dropped=True, reason="AI 관련성 없음 (프리플라이트)")

    sig = detect_signals(
        title=title or "",
        content=content or "",
        source_type=source_type,
        current_tier=tier,
    )

    tier_eff: ChannelTier = sig.tier_override or tier  # type: ignore[assignment]

    if should_drop(tier_eff):
        return PreflightResult(dropped=True, reason=f"tier DROP ({tier_eff})")

    if sig.fact_label_hint == "DROP":
        return PreflightResult(dropped=True, reason="신호 DROP (의견·잡담 등)")

    tier1_fact_auto_only = (
        source_type == "media"
        and sig.fact_label_hint == "FACT_AUTO"
        and tier_eff not in ("MEDIA_CREDIBLE_LEAK", "COMMUNITY_HIGH_SIGNAL")
    )

    insight_analysis = sig.fact_label_hint == "INSIGHT"
    needs_deep_fact_check = not tier1_fact_auto_only and not insight_analysis

    return PreflightResult(
        dropped=False,
        needs_deep_fact_check=needs_deep_fact_check,
        tier1_fact_auto_only=tier1_fact_auto_only,
        insight_analysis=insight_analysis,
    )


def augmented_body_for_fact_check(base_content: str, processed: dict) -> str:
    """번역·요약 결과를 영문 팩트체크 단계에 맥락으로 덧붙인다."""
    parts: list[str] = [(base_content or "")[:120000]]
    sf = (processed.get("summary_formal") or "").strip()
    tr = (processed.get("translation") or "").strip()
    if sf:
        parts.append("\n\n--- KO summary_formal ---\n" + sf[:3000])
    if tr:
        parts.append("\n\n--- KO translation excerpt ---\n" + tr[:6000])
    return "".join(parts)
