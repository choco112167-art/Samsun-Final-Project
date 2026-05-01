"""
fact_checker/cross_source.py — 크로스 소스 검증 및 신뢰도 부스트

동일 claim을 독립적인 TIER 0/1 언론사가 여러 곳에서 보도할수록
신뢰도를 상향 조정한다.

근거:
  - Popat et al., WWW 2018 (CredEye): 다수 독립 소스 보도 = 신뢰도 상승의 가장 강한 신호
  - Vo & Lee, EMNLP 2020: 소스 다양성이 팩트체크 정확도 +12% 기여
"""

from .channel_config import ChannelTier, CHANNEL_PROFILES

# TIER 0 / TIER 1 소스 집합 (부스트 카운팅 대상)
_TIER01_SOURCES: frozenset[str] = frozenset(
    p.source
    for p in CHANNEL_PROFILES
    if p.default_tier in ("ACADEMIC_INSTITUTIONAL", "MEDIA_OFFICIAL")
)


def cross_source_boost(claim_title: str, all_sources: list[str]) -> float:
    """
    동일 claim을 보도한 TIER 0/1 독립 소스 수에 따라 신뢰도 부스트값 반환.

    Args:
        claim_title:  현재 기사 제목 (비교 키 — 실제 유사도 비교는 호출자가 전처리)
        all_sources:  동일 claim을 보도한 전체 소스 이름 목록

    Returns:
        boost (float): 0.00 / 0.05 / 0.10 / 0.20

    사용 예:
        boosted = profile.credibility_score + cross_source_boost(title, sources)
    """
    tier01_count = sum(1 for s in all_sources if s in _TIER01_SOURCES)

    if tier01_count >= 3:
        return 0.20   # TechCrunch + Guardian + Verge 모두 독립 보도
    elif tier01_count == 2:
        return 0.10
    elif tier01_count == 1:
        return 0.05
    return 0.00


def get_tier01_sources() -> frozenset[str]:
    """TIER 0/1 소스 집합 반환 (외부 참조용)."""
    return _TIER01_SOURCES
