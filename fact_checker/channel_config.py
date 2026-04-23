"""
fact_checker/channel_config.py — 채널 등급 분류
LIAR 논문(ACL 2017) 발언자 신뢰 이력 인사이트 적용:
    출처 신뢰도를 정적 메타데이터로 명시적 정의
    (기존 credibility.py의 임의 배점을 근거 있게 대체)

채널 등급 5종:
    MEDIA_OFFICIAL       — 공식 보도 (팩트 자동 처리 후보)
    MEDIA_CREDIBLE_LEAK   — 유출/미확인 보도 → 팩트체크 파이프라인 (3A→3C)
    MEDIA_OPINION         — 사설/의견 → DROP
    COMMUNITY_HIGH_SIGNAL — arXiv/GitHub 기반 → 팩트체크 파이프라인 (3A→3C)
    COMMUNITY_NOISE       — 밈/질문/토론 → DROP
"""

from dataclasses import dataclass
from typing import Literal

ChannelTier = Literal[
    "MEDIA_OFFICIAL",
    "MEDIA_CREDIBLE_LEAK",
    "MEDIA_OPINION",
    "COMMUNITY_HIGH_SIGNAL",
    "COMMUNITY_NOISE",
]

DROP_TIERS = {"MEDIA_OPINION", "COMMUNITY_NOISE"}


@dataclass
class ChannelProfile:
    source: str
    source_type: Literal["media", "community"]
    default_tier: ChannelTier
    credibility_score: float   # 출처 신뢰도 기준값 (0.0~1.0)
    note: str = ""


# ── 언론사 7개 ──────────────────────────────────────────────
# default_tier = 기사 내용 분류 전 기본값.
# signal_detector 가 Opinion/Leak 신호 감지 시 tier 조정됨.
CHANNEL_PROFILES: list[ChannelProfile] = [
    ChannelProfile(
        source="MIT Technology Review",
        source_type="media",
        default_tier="MEDIA_OFFICIAL",
        credibility_score=0.95,
        note="학술·심층 보도 전문, 오류율 극히 낮음",
    ),
    ChannelProfile(
        source="IEEE Spectrum",
        source_type="media",
        default_tier="MEDIA_OFFICIAL",
        credibility_score=0.93,
        note="IEEE 공식 매체, 기술 검증 체계 보유",
    ),
    ChannelProfile(
        source="The Guardian Tech",
        source_type="media",
        default_tier="MEDIA_OFFICIAL",
        credibility_score=0.88,
        note="AI 윤리·정책 중심, 사설 비중 있음 → Opinion 신호 주의",
    ),
    ChannelProfile(
        source="TechCrunch",
        source_type="media",
        default_tier="MEDIA_OFFICIAL",
        credibility_score=0.82,
        note="스타트업/펀딩 단독 보도 많음 → Credible Leak 신호 주의",
    ),
    ChannelProfile(
        source="The Verge",
        source_type="media",
        default_tier="MEDIA_OFFICIAL",
        credibility_score=0.80,
        note="테크 전반, 리뷰·의견 기사 병행 → Opinion 신호 주의",
    ),
    ChannelProfile(
        source="The Decoder",
        source_type="media",
        default_tier="MEDIA_OFFICIAL",
        credibility_score=0.82,
        note="AI 전문 독립 매체, 단독 유출 보도 빈번 → Credible Leak 주의",
    ),
    ChannelProfile(
        source="VentureBeat AI",
        source_type="media",
        default_tier="MEDIA_CREDIBLE_LEAK",
        credibility_score=0.72,
        note="업계 소식통 인용 많음 → 기본값을 Credible Leak으로",
    ),
    # ── 커뮤니티 4개 ────────────────────────────────────────
    # community 채널의 tier는 category_filter가 기사별로 결정.
    # 여기서는 credibility_score 기준값만 정의.
    ChannelProfile(
        source="Reddit r/MachineLearning",
        source_type="community",
        default_tier="COMMUNITY_HIGH_SIGNAL",
        credibility_score=0.65,
        note="연구자 커뮤니티, arXiv 논문 공유 중심",
    ),
    ChannelProfile(
        source="Reddit r/LocalLLaMA",
        source_type="community",
        default_tier="COMMUNITY_HIGH_SIGNAL",
        credibility_score=0.60,
        note="오픈소스 LLM 실험, GitHub 릴리즈 공유 많음",
    ),
    ChannelProfile(
        source="Reddit r/artificial",
        source_type="community",
        default_tier="COMMUNITY_NOISE",   # category_filter가 HIGH_SIGNAL로 올릴 수 있음
        credibility_score=0.50,
        note="일반 AI 토론, 노이즈 비율 높음",
    ),
    ChannelProfile(
        source="Product Hunt",
        source_type="community",
        default_tier="COMMUNITY_HIGH_SIGNAL",
        credibility_score=0.48,
        note="AI 제품 런치 전문, ai_only=False라 필터링 필요",
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
        note="미등록 출처 — 기본값 적용",
    ))


def should_drop(tier: ChannelTier) -> bool:
    """DROP 대상 tier 여부."""
    return tier in DROP_TIERS
