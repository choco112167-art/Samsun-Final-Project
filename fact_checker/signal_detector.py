"""
fact_checker/signal_detector.py — 루머/의견 신호 탐지 (Step 0-1)

처리 흐름:
    1. 루머 신호 (미디어 우선) → RUMOR / NEEDS_VERIFICATION
    2. 의견 신호 다수 + 전문 용어·수치 없음 → DROP (잡담)
    2b. 의견 신호 다수 + Insight 신호 있음 → INSIGHT (분석·통찰 — 파이프라인 통과)
    3. Credible Leak 신호 → tier 조정
    4. 그 외 미디어 → FACT_AUTO / 커뮤니티 → NEEDS_VERIFICATION

루머 신호 강도:
    STRONG  → RUMOR 라벨
    WEAK    → NEEDS_VERIFICATION
    NONE    → 언론사 Official이면 FACT_AUTO

fact_label_hint:
    FACT_AUTO | RUMOR | NEEDS_VERIFICATION | INSIGHT | DROP
"""

import re
from dataclasses import dataclass, field
from typing import Literal

SignalStrength = Literal["STRONG", "WEAK", "NONE"]


# ── 의견/사설 신호 (다수 시 잡담 후보 — Insight 신호와 함께 판별) ──────────────────
OPINION_PATTERNS: list[str] = [
    r"\bopinion\b", r"\beditorial\b", r"\bcommentary\b", r"\bcolumn\b",
    r"\bi think\b", r"\bi believe\b", r"\bin my view\b", r"\bin my opinion\b",
    r"\bshould\b.{0,20}\bai\b",
    r"\bwhy\s+(we|i|you)\s+(need|must|should)\b",
    r"\bthe case for\b", r"\bthe case against\b",
    r"\blet's be honest\b", r"\bfrankly\b",
    r"칼럼", r"사설", r"기고", r"오피니언",
    r"내 생각", r"필자는", r"필자의 견해",
    r"~해야 한다고 생각", r"개인적으로",
    r"아마도.{0,10}것이다",
]

# ── Insight: 의견형 글이어도 살릴 만한 정보 밀도 (모델명·수치·기술·일정 등) ────────────
SURVIVAL_INFO_PATTERNS: list[str] = [
    r"\b(GPT-[345]|GPT-4o|ChatGPT|OpenAI|Claude|Anthropic|Gemini|Llama|Mistral|Mixtral|DeepSeek)\b",
    r"\b\d+(?:\.\d+)?\s*(?:billion|million)\b",
    r"\b\d+\s*(?:tokens?|parameters?)\b",
    r"\b\d+(?:\.\d+)?\s*%",
]

INSIGHT_EXTRA_PATTERNS: list[str] = [
    r"\b(transformer|attention|embedding|fine[- ]?tun|LoRA|QLoRA|RLHF|SFT|inference|throughput)\b",
    r"\b(RAG|vector\s+store|context\s+window|KV\s+cache|speculative\s+decode)\b",
    r"\b(MMLU|BLEU|GSM8K|HumanEval|GPQA|SWE-bench|Big.?Bench)\b",
    r"\barxiv\b|\bNeurIPS\b|\bICML\b|\bICLR\b|\bACL\b",
    r"\b20[2-3]\d-\d{2}-\d{2}\b",
    r"\b(Q[1-4]\s+20[2-3]\d)\b",
    r"\b20[2-3]\d\b",  # 연도 단독 (2024~2039 대략)
    r"\b(compared to|vs\.?|versus)\b.{0,40}\b(model|baseline|GPT|LLM)\b",
    r"\b\d{1,3}\.\d+\s*(?:fps|tokens/s|tok/s)\b",
]

# ── Credible Leak 신호 (MEDIA_CREDIBLE_LEAK) ───────────────
CREDIBLE_LEAK_PATTERNS: list[str] = [
    r"\bsources?\s+(say|told|claim|familiar with)\b",
    r"\baccording to\s+(sources?|insiders?|people familiar)\b",
    r"\bexclusive(ly)?\b",
    r"\bbreaking\b",
    r"\bunconfirmed\b",
    r"\bleaked?\b",
    r"\binsider\b",
    r"\bexpected to (announce|reveal|launch|release)\b",
    r"단독", r"특종",
    r"소식통에 따르면", r"관계자에 따르면", r"업계 관계자",
    r"복수의 소식통", r"내부 관계자",
    r"유출(된|됐|됩)", r"유출 문서",
    r"출시(될|될 것으로|예정)",
    r"발표(될|될 것으로|예정)",
]

# ── 강한 루머 신호 (RUMOR 즉시) ────────────────────────────
RUMOR_STRONG_PATTERNS: list[str] = [
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
    r"~일 수 있", r"~일지도",
    r"~로 보인다", r"~로 예상",
    r"~할 것으로 보이", r"~할 가능성",
    r"추측", r"예측", r"관측",
    r"전해졌다", r"전해진다",
    r"~라는 이야기",
    r"업계에서는",
]

# 커뮤니티 잡담 후보 전용 (다수 시 DROP 후보 — Insight 신호와 병행 판별)
COMMUNITY_CHATTER_PATTERNS: list[str] = [
    r"\bi think\b",
    r"\bin my view\b",
    r"\bfrankly\b",
]


@dataclass
class SignalResult:
    tier_override: str | None
    rumor_strength: SignalStrength
    matched_patterns: list[str] = field(default_factory=list)
    fact_label_hint: str = ""


def _find_matches(text: str, patterns: list[str]) -> list[str]:
    matched = []
    for p in patterns:
        if re.search(p, text, re.IGNORECASE):
            matched.append(p)
        if len(matched) >= 5:
            break
    return matched


def _has_insight_content(search_text: str) -> bool:
    """
    전문 용어·모델명·정보성 수치·일정 등이 있으면 True.
    의견 패턴만 많고 이런 신호가 없으면 순수 잡담으로 본다.
    """
    st = search_text.lower()
    all_pats = SURVIVAL_INFO_PATTERNS + INSIGHT_EXTRA_PATTERNS
    for p in all_pats:
        if re.search(p, st, re.IGNORECASE):
            return True
    return False


def detect(
    title: str,
    content: str,
    source_type: str,
    current_tier: str,
) -> SignalResult:
    search_text = (title + " " + content[:1000]).lower()

    # ══════════════════════════════════════════════════════
    # 미디어: 루머 → (취약) 누설/약한 루머 → 의견 다수(Insight vs DROP) → FACT_AUTO
    # ══════════════════════════════════════════════════════
    if source_type == "media" and current_tier != "COMMUNITY_NOISE":
        leak_hits = _find_matches(search_text, CREDIBLE_LEAK_PATTERNS)
        tier_override: str | None = "MEDIA_CREDIBLE_LEAK" if leak_hits else None

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

        opinion_hits = _find_matches(search_text, OPINION_PATTERNS)
        if len(opinion_hits) >= 2:
            if _has_insight_content(search_text):
                return SignalResult(
                    tier_override=None,
                    rumor_strength="NONE",
                    matched_patterns=opinion_hits,
                    fact_label_hint="INSIGHT",
                )
            return SignalResult(
                tier_override="MEDIA_OPINION",
                rumor_strength="NONE",
                matched_patterns=opinion_hits,
                fact_label_hint="DROP",
            )

        return SignalResult(
            tier_override=None,
            rumor_strength="NONE",
            matched_patterns=[],
            fact_label_hint="FACT_AUTO",
        )

    # ══════════════════════════════════════════════════════
    # 커뮤니티: 잡담 후보(I think 등) vs Insight → 루머 → 기본 NEEDS_VERIFICATION
    # ══════════════════════════════════════════════════════
    chatter_hits = _find_matches(search_text, COMMUNITY_CHATTER_PATTERNS)
    if len(chatter_hits) >= 2:
        if _has_insight_content(search_text):
            return SignalResult(
                tier_override=None,
                rumor_strength="WEAK",
                matched_patterns=chatter_hits,
                fact_label_hint="INSIGHT",
            )
        return SignalResult(
            tier_override="COMMUNITY_NOISE",
            rumor_strength="NONE",
            matched_patterns=chatter_hits,
            fact_label_hint="DROP",
        )

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
        fact_label_hint="NEEDS_VERIFICATION",
    )
