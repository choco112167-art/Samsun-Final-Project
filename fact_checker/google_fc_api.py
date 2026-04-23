"""
fact_checker/google_fc_api.py — Google Fact Check Tools API 래퍼 (Step 2)

Google ClaimReview DB(AFP·PolitiFact·Snopes 등 200개+ 기관) 조회.
무료, ~200ms.

환경변수:
    GOOGLE_FC_API_KEY  — Google Cloud Console에서 발급
                         (없으면 API 호출 스킵, SKIP 반환)

참고: https://developers.google.com/fact-check/tools/api/reference/rest
"""

import os
import requests
from dataclasses import dataclass

# 모듈 임포트 시점에 env가 아직 로드 안 됐을 수 있어 query() 내부에서 재조회
FC_API_URL = "https://factchecktools.googleapis.com/v1alpha1/claims:search"
REQUEST_TIMEOUT = 3   # 초


@dataclass
class FCResult:
    matched: bool
    verdict: str          # "FACT" | "RUMOR" | "UNVERIFIED" | "SKIP" | "NO_MATCH"
    claim_text: str = ""
    claimant: str = ""
    rating: str = ""      # 원본 rating 문자열 (True / False / Mostly True 등)
    publisher: str = ""
    evidence_url: str = ""
    confidence: float = 0.0


# ── rating → 내부 라벨 매핑 ────────────────────────────────
_FACT_RATINGS = {
    "true", "mostly true", "correct", "accurate",
    "verified", "confirmed", "사실", "사실로 확인",
}
_RUMOR_RATINGS = {
    "false", "mostly false", "incorrect", "inaccurate",
    "pants on fire", "fabricated", "fake", "misleading",
    "허위", "거짓", "잘못된 정보",
}


def _map_rating(rating: str) -> tuple[str, float]:
    """
    rating 문자열 → (내부 라벨, confidence).
    매핑 불가 시 UNVERIFIED 반환.
    """
    r = rating.lower().strip()
    if any(f in r for f in _FACT_RATINGS):
        return "FACT", 0.90
    if any(f in r for f in _RUMOR_RATINGS):
        return "RUMOR", 0.90
    return "UNVERIFIED", 0.60


def query(title: str, max_age_days: int = 365) -> FCResult:
    """
    기사 제목 앞 60자로 Google Fact Check Tools API 조회.

    Args:
        title:        기사 제목 (영문)
        max_age_days: 이 기간 내 팩트체크 결과만 사용 (기본 1년)

    Returns:
        FCResult
    """
    # 모듈 임포트 이후에 dotenv가 로드될 수 있어 호출 시점에 재조회
    api_key = os.getenv("GOOGLE_FC_API_KEY", "")
    if not api_key:
        return FCResult(matched=False, verdict="SKIP",
                        rating="API 키 없음 — .env에 GOOGLE_FC_API_KEY 설정 필요")

    query_text = title[:60].strip()
    if not query_text:
        return FCResult(matched=False, verdict="NO_MATCH")

    params = {
        "key":           api_key,
        "query":         query_text,
        "languageCode":  "en",   # 영문 기사 기준
        "maxAgeDays":    max_age_days,
        "pageSize":      3,      # 상위 3개 결과만
    }

    try:
        resp = requests.get(FC_API_URL, params=params, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
    except requests.Timeout:
        return FCResult(matched=False, verdict="NO_MATCH", rating="API 타임아웃")
    except Exception as e:
        return FCResult(matched=False, verdict="NO_MATCH", rating=f"API 오류: {e}")

    claims = data.get("claims", [])
    if not claims:
        return FCResult(matched=False, verdict="NO_MATCH")

    # 첫 번째 결과 사용 (Google 관련도 순 정렬)
    claim = claims[0]
    reviews = claim.get("claimReview", [])
    if not reviews:
        return FCResult(matched=False, verdict="NO_MATCH")

    review = reviews[0]
    rating     = review.get("textualRating", "")
    publisher  = review.get("publisher", {}).get("name", "")
    review_url = review.get("url", "")

    verdict, confidence = _map_rating(rating)

    return FCResult(
        matched=True,
        verdict=verdict,
        claim_text=claim.get("text", ""),
        claimant=claim.get("claimant", ""),
        rating=rating,
        publisher=publisher,
        evidence_url=review_url,
        confidence=confidence,
    )
