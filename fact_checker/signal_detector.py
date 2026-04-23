"""
fact_checker/signal_detector.py — 루머/의견 신호 탐지 (Step 0-1)

처리 흐름:
    1. Opinion 신호 탐지 → 채널 tier를 MEDIA_OPINION으로 조정 → DROP
    2. Credible Leak 신호 탐지 → tier를 MEDIA_CREDIBLE_LEAK으로 조정
    3. 루머 신호 강도 판별 → RUMOR / NEEDS_VERIFICATION / FACT_AUTO

루머 신호 강도:
    STRONG  → RUMOR 라벨 (FC API → Gemini Advisor → CoVe/DebateCV 파이프라인)
    WEAK    → NEEDS_VERIFICATION (FC API → Gemini Advisor 순서로 검증)
    NONE    → 언론사 Official이면 FACT_AUTO (LLM 호출 생략)
              커뮤니티면 NEEDS_VERIFICATION
"""

import re
from dataclasses import dataclass, field
from typing import Literal

SignalStrength = Literal["STRONG", "WEAK", "NONE"]


# ── 의견/사설 신호 (MEDIA_OPINION → DROP) ──────────────────
OPINION_PATTERNS: list[str] = [
    # 영문 — 기자 의견/주관 표현
    r"\bopinion\b", r"\beditorial\b", r"\bcommentary\b", r"\bcolumn\b",
    r"\bi think\b", r"\bi believe\b", r"\bin my view\b",
    r"\bshould\b.{0,20}\bai\b",   # "AI should ..."
    r"\bwhy\s+(we|i|you)\s+(need|must|should)\b",
    r"\bthe case for\b", r"\bthe case against\b",
    r"\blet's be honest\b", r"\bfrank(ly)?\b",
    # 한국어 — 의견/칼럼
    r"칼럼", r"사설", r"기고", r"오피니언",
    r"내 생각", r"필자는", r"필자의 견해",
    r"~해야 한다고 생각", r"개인적으로",
    r"아마도.{0,10}것이다",
]

# ── Credible Leak 신호 (MEDIA_CREDIBLE_LEAK) ───────────────
CREDIBLE_LEAK_PATTERNS: list[str] = [
    # 영문 — 소식통 인용
    r"\bsources?\s+(say|told|claim|familiar with)\b",
    r"\baccording to\s+(sources?|insiders?|people familiar)\b",
    r"\bexclusive(ly)?\b",
    r"\bbreaking\b",
    r"\bunconfirmed\b",
    r"\bleaked?\b",
    r"\binsider\b",
    r"\bexpected to (announce|reveal|launch|release)\b",
    # 한국어
    r"단독", r"특종",
    r"소식통에 따르면", r"관계자에 따르면", r"업계 관계자",
    r"복수의 소식통", r"내부 관계자",
    r"유출(된|됐|됩)", r"유출 문서",
    r"출시(될|될 것으로|예정)",
    r"발표(될|될 것으로|예정)",
]

# ── 강한 루머 신호 (RUMOR 즉시) ────────────────────────────
RUMOR_STRONG_PATTERNS: list[str] = [
    # 영문
    r"\ballegedly\b",
    r"\bpurportedly\b",
    r"\breportedly\b",
    r"\bunverified\b",
    r"\bsupposedly\b",
    r"\bso-called\b",
    r"\bclaims?\s+to\b",
    r"\bcontroversial\b",
    r"\bmisinformation\b", r"\bdisinformation\b",
    r"\bfake news\b",
    r"\bdebunked\b",
    # 한국어
    r"루머", r"소문",
    r"~라는 주장", r"주장에 따르면",
    r"사실 여부", r"사실 확인",
    r"가짜 뉴스", r"허위", r"허위 정보",
    r"논란",
    r"~로 알려졌(다|으나|지만)",
    r"~라는 후문",
    r"~일 것으로 추정",
    r"검증되지 않",
]

# ── 약한 루머 신호 (NEEDS_VERIFICATION) ────────────────────
RUMOR_WEAK_PATTERNS: list[str] = [
    # 영문
    r"\bsaid to\b",
    r"\bthought to\b",
    r"\bbelieved to\b",
    r"\bmay\s+(be|have)\b",
    r"\bmight\s+(be|have)\b",
    r"\bcould\s+(be|indicate)\b",
    r"\bis\s+expected\s+to\b",
    r"\blikely\s+to\b",
    r"\bpossibly\b",
    r"\bpotentially\b",
    r"\bspeculation\b",
    r"\bsuggests?\b",
    r"\bhints?\b",
    # 한국어
    r"~일 수 있", r"~일지도",
    r"~로 보인다", r"~로 예상",
    r"~할 것으로 보이", r"~할 가능성",
    r"추측", r"예측", r"관측",
    r"전해졌다", r"전해진다",
    r"~라는 이야기",
    r"업계에서는",
]


@dataclass
class SignalResult:
    tier_override: str | None          # None이면 tier 변경 없음
    rumor_strength: SignalStrength
    matched_patterns: list[str] = field(default_factory=list)
    fact_label_hint: str = ""          # FACT_AUTO | RUMOR | NEEDS_VERIFICATION


def _find_matches(text: str, patterns: list[str]) -> list[str]:
    """패턴 목록 중 매칭된 항목 반환 (최대 5개)."""
    matched = []
    for p in patterns:
        if re.search(p, text, re.IGNORECASE):
            matched.append(p)
        if len(matched) >= 5:
            break
    return matched


def detect(
    title: str,
    content: str,
    source_type: str,
    current_tier: str,
) -> SignalResult:
    """
    기사 제목 + 본문에서 신호 탐지.

    Args:
        title:        기사 제목 (영문)
        content:      기사 본문 (영문, 최대 2000자면 충분)
        source_type:  "media" | "community"
        current_tier: channel_config에서 얻은 기본 tier

    Returns:
        SignalResult
    """
    # 검색 대상: 제목 전체 + 본문 앞 1000자 (루머 신호는 대부분 초반에 등장)
    search_text = (title + " " + content[:1000]).lower()

    # ── 1. Opinion 탐지 (미디어만) ──────────────────────────
    if source_type == "media" and current_tier != "COMMUNITY_NOISE":
        opinion_hits = _find_matches(search_text, OPINION_PATTERNS)
        if len(opinion_hits) >= 2:   # 단일 패턴 오탐 방지 — 2개 이상일 때만 Opinion
            return SignalResult(
                tier_override="MEDIA_OPINION",
                rumor_strength="NONE",
                matched_patterns=opinion_hits,
                fact_label_hint="DROP",
            )

    # ── 2. Credible Leak 탐지 (미디어만) ───────────────────
    if source_type == "media":
        leak_hits = _find_matches(search_text, CREDIBLE_LEAK_PATTERNS)
        if leak_hits:
            tier_override = "MEDIA_CREDIBLE_LEAK"
        else:
            tier_override = None

        # ── 3. 루머 강도 탐지 ──────────────────────────────
        strong_hits = _find_matches(search_text, RUMOR_STRONG_PATTERNS)
        if strong_hits:
            return SignalResult(
                tier_override=tier_override,
                rumor_strength="STRONG",
                matched_patterns=strong_hits + leak_hits,
                fact_label_hint="RUMOR",
            )

        weak_hits = _find_matches(search_text, RUMOR_WEAK_PATTERNS)
        if weak_hits or leak_hits:
            return SignalResult(
                tier_override=tier_override,
                rumor_strength="WEAK",
                matched_patterns=weak_hits + leak_hits,
                fact_label_hint="NEEDS_VERIFICATION",
            )

        # 신호 없음 + Official 미디어 → FACT 자동 처리
        return SignalResult(
            tier_override=None,
            rumor_strength="NONE",
            matched_patterns=[],
            fact_label_hint="FACT_AUTO",
        )

    # ── 커뮤니티 채널 ───────────────────────────────────────
    # tier(HIGH_SIGNAL/NOISE)는 category_filter가 이미 결정.
    # 루머 신호만 추가로 체크.
    strong_hits = _find_matches(search_text, RUMOR_STRONG_PATTERNS)
    if strong_hits:
        return SignalResult(
            tier_override=None,
            rumor_strength="STRONG",
            matched_patterns=strong_hits,
            fact_label_hint="RUMOR",
        )

    return SignalResult(
        tier_override=None,
        rumor_strength="NONE",
        matched_patterns=[],
        fact_label_hint="NEEDS_VERIFICATION",   # 커뮤니티는 항상 검증 필요
    )
