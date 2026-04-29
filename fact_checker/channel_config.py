"""
fact_checker/channel_config.py — 채널 등급 분류

근거:
  - Baly et al., EMNLP 2018 — 뉴스 소스 신뢰도 예측 (1,000개 소스 DB)
  - LIAR 논문(ACL 2017) — 발언자 신뢰 이력 인사이트
  - NewsGuard 100점 기준 (75점 이상 = 신뢰 가능)
  - Reuters Institute Digital News Report 2024

채널 등급 7종 (TIER 0~6):
    TIER 0  ACADEMIC_INSTITUTIONAL — 학술/기관 (IEEE, MIT TR, arXiv)        0.90~1.00
    TIER 1  MEDIA_OFFICIAL         — 공식 언론사 (TechCrunch, Verge 등)     0.78~0.92
    TIER 2  MEDIA_CREDIBLE_LEAK    — 전문미디어·유출 보도 (VentureBeat 등)  0.60~0.78
    TIER 3  INFLUENCER_VERIFIED    — 인플루언서·유튜브 (실명 전문가)         0.30~0.60
    TIER 4  COMMUNITY_HIGH_SIGNAL  — 커뮤니티 고신호 (Reddit ML 등)         0.20~0.45
    TIER 5  SOCIAL_UNVERIFIED      — 텔레그램·익명채널                       0.05~0.25
    (DROP)  MEDIA_OPINION          — 사설/의견 → DROP
    (DROP)  COMMUNITY_NOISE        — 밈/잡담 → DROP
"""

from dataclasses import dataclass
from typing import Literal

ChannelTier = Literal[
    "ACADEMIC_INSTITUTIONAL",   # TIER 0
    "MEDIA_OFFICIAL",           # TIER 1
    "MEDIA_CREDIBLE_LEAK",      # TIER 2
    "INFLUENCER_VERIFIED",      # TIER 3
    "COMMUNITY_HIGH_SIGNAL",    # TIER 4
    "SOCIAL_UNVERIFIED",        # TIER 5
    "MEDIA_OPINION",            # DROP
    "COMMUNITY_NOISE",          # DROP
]

DROP_TIERS = {"MEDIA_OPINION", "COMMUNITY_NOISE"}

# 소스 유형별 기본 tier 점수 (4팩터 공식의 source_tier_score 기준값)
TIER_BASE_SCORE: dict[str, float] = {
    "ACADEMIC_INSTITUTIONAL": 0.95,
    "MEDIA_OFFICIAL":         0.85,
    "MEDIA_CREDIBLE_LEAK":    0.69,
    "INFLUENCER_VERIFIED":    0.45,
    "COMMUNITY_HIGH_SIGNAL":  0.35,
    "SOCIAL_UNVERIFIED":      0.15,
    "MEDIA_OPINION":          0.00,
    "COMMUNITY_NOISE":        0.00,
}


@dataclass
class ChannelProfile:
    source: str
    source_type: Literal["media", "community", "influencer", "social"]
    default_tier: ChannelTier
    credibility_score: float   # 출처 신뢰도 기준값 (0.0~1.0), 4팩터 공식으로 산정
    transparency_score: float  # 운영자·출처 공개 여부 (0.0~1.0)
    citation_score: float      # 원문·논문 링크 포함 비율 (0.0~1.0)
    note: str = ""


# ── TIER 0 · TIER 1: 언론사 7개 ─────────────────────────────────────────────
# credibility_score = 0.40*tier_base + 0.25*track_record + 0.20*transparency + 0.15*citation
# track_record: MBFC VERY HIGH=1.0, HIGH=0.85, 비공식=0.70
CHANNEL_PROFILES: list[ChannelProfile] = [
    # TIER 0 — 학술/기관
    ChannelProfile(
        source="MIT Technology Review",
        source_type="media",
        default_tier="ACADEMIC_INSTITUTIONAL",
        credibility_score=0.95,   # 0.40*0.95 + 0.25*1.0 + 0.20*1.0 + 0.15*0.90
        transparency_score=1.0,
        citation_score=0.90,
        note="1899년 MIT 발행, MBFC VERY HIGH, NewsGuard 녹색",
    ),
    ChannelProfile(
        source="IEEE Spectrum",
        source_type="media",
        default_tier="ACADEMIC_INSTITUTIONAL",
        credibility_score=0.93,   # 0.40*0.95 + 0.25*1.0 + 0.20*1.0 + 0.15*0.80
        transparency_score=1.0,
        citation_score=0.80,
        note="IEEE(40만 회원 학술단체) 직속, MBFC VERY HIGH",
    ),
    # TIER 1 — 공식 언론사
    ChannelProfile(
        source="The Guardian Tech",
        source_type="media",
        default_tier="MEDIA_OFFICIAL",
        credibility_score=0.88,   # 0.40*0.85 + 0.25*0.85 + 0.20*1.0 + 0.15*0.75
        transparency_score=1.0,
        citation_score=0.75,
        note="MBFC HIGH, 5년간 팩트체크 실패 최소, 사설 비중 있음 → Opinion 신호 주의",
    ),
    ChannelProfile(
        source="TechCrunch",
        source_type="media",
        default_tier="MEDIA_OFFICIAL",
        credibility_score=0.82,   # 0.40*0.85 + 0.25*0.85 + 0.20*0.90 + 0.15*0.60
        transparency_score=0.90,
        citation_score=0.60,
        note="MBFC HIGH, NewsGuard 녹색, 스타트업 단독 보도 많음 → Credible Leak 주의",
    ),
    ChannelProfile(
        source="The Decoder",
        source_type="media",
        default_tier="MEDIA_OFFICIAL",
        credibility_score=0.82,   # 0.40*0.85 + 0.25*0.85 + 0.20*0.95 + 0.15*0.65
        transparency_score=0.95,
        citation_score=0.65,
        note="heise medien 산하(2024.01~), AI 전문 편집팀, 논문 링크 필수",
    ),
    ChannelProfile(
        source="The Verge",
        source_type="media",
        default_tier="MEDIA_OFFICIAL",
        credibility_score=0.80,   # 0.40*0.85 + 0.25*0.85 + 0.20*0.85 + 0.15*0.55
        transparency_score=0.85,
        citation_score=0.55,
        note="MBFC HIGH, Vox Media 편집권 독립, 리뷰·의견 기사 병행 → Opinion 주의",
    ),
    # TIER 2 — 전문미디어/유출 보도
    ChannelProfile(
        source="VentureBeat AI",
        source_type="media",
        default_tier="MEDIA_CREDIBLE_LEAK",
        credibility_score=0.72,   # 0.40*0.69 + 0.25*0.70 + 0.20*0.80 + 0.15*0.60
        transparency_score=0.80,
        citation_score=0.60,
        note="MBFC 공식 미평가(Biasly HIGH), 소식통 인용 많음 → 기본값 Credible Leak",
    ),
    # ── TIER 4: 커뮤니티 (Reddit) ─────────────────────────────────────────────
    # community 채널의 tier는 category_filter가 기사별로 HIGH_SIGNAL/NOISE 결정.
    ChannelProfile(
        source="Reddit r/MachineLearning",
        source_type="community",
        default_tier="COMMUNITY_HIGH_SIGNAL",
        credibility_score=0.42,   # 0.40*0.35 + 0.25*0.70 + 0.20*0.40 + 0.15*0.80
        transparency_score=0.40,
        citation_score=0.80,
        note="연구자 커뮤니티, arXiv 논문 공유 중심 → citation 높음",
    ),
    ChannelProfile(
        source="Reddit r/LocalLLaMA",
        source_type="community",
        default_tier="COMMUNITY_HIGH_SIGNAL",
        credibility_score=0.38,   # 0.40*0.35 + 0.25*0.65 + 0.20*0.35 + 0.15*0.75
        transparency_score=0.35,
        citation_score=0.75,
        note="오픈소스 LLM 실험, GitHub 릴리즈 공유 많음",
    ),
    ChannelProfile(
        source="Reddit r/artificial",
        source_type="community",
        default_tier="COMMUNITY_NOISE",
        credibility_score=0.28,
        transparency_score=0.30,
        citation_score=0.40,
        note="일반 AI 토론, 노이즈 비율 높음 — category_filter가 HIGH_SIGNAL로 올릴 수 있음",
    ),
    ChannelProfile(
        source="Product Hunt",
        source_type="community",
        default_tier="COMMUNITY_HIGH_SIGNAL",
        credibility_score=0.32,
        transparency_score=0.50,
        citation_score=0.30,
        note="AI 제품 런치 전문, ai_only=False라 필터링 필요",
    ),
    # ── TIER 3: 유튜브 채널 ───────────────────────────────────────────────────
    # Step 1 신호탐지 건너뜀 — 동영상 자막 특성상 패턴 탐지 신뢰도 낮음.
    # 항상 Step 3A Gemini부터 시작.
    ChannelProfile(
        source="YouTube: Two Minute Papers",
        source_type="influencer",
        default_tier="INFLUENCER_VERIFIED",
        credibility_score=0.55,   # 0.40*0.45 + 0.25*0.80 + 0.20*0.70 + 0.15*0.85
        transparency_score=0.70,
        citation_score=0.85,
        note="Károly Zsolnai-Fehér 박사 운영, 논문 인용 충실",
    ),
    ChannelProfile(
        source="YouTube: Andrej Karpathy",
        source_type="influencer",
        default_tier="INFLUENCER_VERIFIED",
        credibility_score=0.58,   # 논문 저자 본인 → track_record 상향
        transparency_score=0.90,
        citation_score=0.80,
        note="전 Tesla·OpenAI, 논문 저자 본인 채널 → track_record 상향",
    ),
    ChannelProfile(
        source="YouTube: AI Explained",
        source_type="influencer",
        default_tier="INFLUENCER_VERIFIED",
        credibility_score=0.42,
        transparency_score=0.60,
        citation_score=0.70,
        note="일반 AI 유튜버, 논문 요약 중심 — 의견 혼재 주의",
    ),
    # ── TIER 5: 텔레그램·익명 채널 ───────────────────────────────────────────
    # 기본값 RUMOR 처리. 크로스 소스 검증으로만 승격 가능.
    ChannelProfile(
        source="Telegram: AI News",
        source_type="social",
        default_tier="SOCIAL_UNVERIFIED",
        credibility_score=0.15,
        transparency_score=0.05,
        citation_score=0.20,
        note="익명 운영, 출처 추적 불가 → 기본 RUMOR, 크로스 소스 확인 시 승격",
    ),
    ChannelProfile(
        source="Telegram: LLM Leaks",
        source_type="social",
        default_tier="SOCIAL_UNVERIFIED",
        credibility_score=0.10,
        transparency_score=0.05,
        citation_score=0.10,
        note="유출 전문 채널, 조작 이미지 다수 → 크로스 소스 없으면 RUMOR 고정",
    ),
]

# source 이름 → ChannelProfile 룩업
_PROFILE_MAP: dict[str, ChannelProfile] = {p.source: p for p in CHANNEL_PROFILES}


def get_profile(source: str) -> ChannelProfile:
    """source 이름으로 ChannelProfile 반환. 미등록 시 기본값."""
    return _PROFILE_MAP.get(source, ChannelProfile(
        source=source,
        source_type="media",
        default_tier="MEDIA_OFFICIAL",
        credibility_score=0.50,
        transparency_score=0.50,
        citation_score=0.50,
        note="미등록 출처 — 기본값 적용",
    ))


def should_drop(tier: ChannelTier) -> bool:
    """DROP 대상 tier 여부."""
    return tier in DROP_TIERS


def compute_credibility_score(
    source_tier: ChannelTier,
    track_record_score: float,
    transparency_score: float,
    citation_score: float,
) -> float:
    """
    4팩터 가중합으로 신뢰도 점수 산정.

    Args:
        source_tier:        채널 티어 (TIER_BASE_SCORE 참조)
        track_record_score: 과거 팩트체크 실패율 역수 (NewsGuard DB + 자체 누적)
        transparency_score: 운영자·출처 공개 여부 (0.0~1.0)
        citation_score:     원문·논문 링크 포함 비율 (0.0~1.0)

    Returns:
        credibility_score (0.0~1.0)
    """
    tier_base = TIER_BASE_SCORE.get(source_tier, 0.50)
    score = (
        0.40 * tier_base
        + 0.25 * track_record_score
        + 0.20 * transparency_score
        + 0.15 * citation_score
    )
    return round(min(max(score, 0.0), 1.0), 4)
