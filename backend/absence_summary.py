"""
feat/soomin — 유저 부재 기간 놓친 기사 요약 알림

- users.last_seen_at 과 관심 벡터(user_vector)를 사용한다.
- Supabase RPC `match_articles_since` 가 없으면 `match_articles` 후 published_at 필터로 대체한다.
- 선택적으로 ABSENCE_DIGEST_LLM=1 일 때 pipeline.summarizer 로 묶음 요약 문자열 생성(sub_message).
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone, timedelta
from typing import Any

logger = logging.getLogger(__name__)


def _parse_dt(raw: str | None) -> datetime | None:
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None


def _articles_via_since_rpc(
    sb: Any,
    user_vector: list[float],
    since_iso: str,
    top_k: int,
) -> list[dict[str, Any]]:
    try:
        res = sb.rpc(
            "match_articles_since",
            {
                "query_vector": user_vector,
                "since_date": since_iso,
                "top_k": top_k,
            },
        ).execute()
        return list(res.data or [])
    except Exception as e:
        logger.debug("match_articles_since 사용 불가 — match_articles 폴백: %s", e)
        return []


def _articles_via_match_filter(
    sb: Any,
    user_vector: list[float],
    since_iso: str,
    top_k: int,
) -> list[dict[str, Any]]:
    since_dt = _parse_dt(since_iso)
    if since_dt is None:
        return []

    need = max(top_k * 8, 40)
    res = sb.rpc(
        "match_articles",
        {
            "query_vector": user_vector,
            "top_k": need,
        },
    ).execute()
    rows = list(res.data or [])
    out: list[dict[str, Any]] = []
    for r in rows:
        pa = r.get("published_at")
        if pa is None:
            continue
        pdt = _parse_dt(str(pa))
        if pdt is None:
            continue
        if pdt >= since_dt:
            out.append(r)
    out.sort(key=lambda x: float(x.get("similarity") or 0), reverse=True)
    return out[:top_k]


def fetch_absence_articles(
    sb: Any,
    user_vector: list[float],
    since_iso: str,
    top_k: int,
) -> list[dict[str, Any]]:
    """부재 구간 이후 발행분 중 유저 벡터와 유사한 기사."""
    if isinstance(user_vector, str):
        user_vector = json.loads(user_vector)

    hit = _articles_via_since_rpc(sb, user_vector, since_iso, top_k)
    if hit:
        return hit
    return _articles_via_match_filter(sb, user_vector, since_iso, top_k)


def maybe_digest_sub_message(articles: list[dict[str, Any]]) -> str | None:
    """환경변수로 켠 경우에만 LLM 묶음 요약."""
    raw = os.getenv("ABSENCE_DIGEST_LLM", "").strip().lower()
    if raw not in ("1", "true", "yes"):
        return None
    if not articles:
        return None
    parts: list[str] = []
    for a in articles[:5]:
        t = ((a.get("title_ko") or a.get("title")) or "").strip()
        s = (a.get("summary_formal") or "").strip()
        if t or s:
            parts.append(f"{t}\n{s}".strip())
    blob = "\n\n".join(parts)
    if len(blob) < 20:
        return None
    try:
        from pipeline.summarizer import summarize

        text = summarize(blob[:8000])
        return text.strip()[:1500] or None
    except Exception as e:
        logger.warning("부재 묶음 요약 실패: %s", e)
        return None


def compute_absence_summary(
    sb: Any,
    user_id: str,
    top_k: int = 5,
) -> dict[str, Any]:
    """
    GET /absence-summary/{user_id} 응답 dict.

    키: show, message?, sub_message?, days_away?, articles?
    """
    now = datetime.now(timezone.utc)

    user_res = sb.table("users").select("user_vector, last_seen_at").eq("user_id", user_id).execute()
    if not user_res.data:
        return {"show": False}

    user_data = user_res.data[0]
    user_vector = user_data.get("user_vector")
    last_seen = user_data.get("last_seen_at")

    def update_last_seen() -> None:
        sb.table("users").update({"last_seen_at": now.isoformat()}).eq("user_id", user_id).execute()

    if not user_vector or not last_seen:
        update_last_seen()
        return {"show": False}

    last_seen_dt = _parse_dt(str(last_seen))
    if last_seen_dt is None:
        update_last_seen()
        return {"show": False}

    days_away = (now - last_seen_dt).days

    if days_away < 1:
        update_last_seen()
        return {"show": False}

    if days_away == 1:
        fetch_days = 1
        message = "어제 놓친 기사예요!"
    elif days_away <= 6:
        fetch_days = days_away
        message = f"{days_away}일간 놓친 기사예요!"
    elif days_away < 30:
        fetch_days = min(days_away, 7)
        message = f"{days_away}일 만에 오셨네요! 최근 한 주 주요 기사예요"
    else:
        fetch_days = min(days_away, 14)
        message = "오랫동안 안 오셨네요! 최근 주요 기사만 추려봤어요"

    since_date = (now - timedelta(days=fetch_days)).isoformat()

    articles_raw = fetch_absence_articles(sb, user_vector, since_date, top_k)

    if not articles_raw:
        update_last_seen()
        return {"show": False}

    articles_out: list[dict[str, Any]] = []
    for r in articles_raw:
        articles_out.append(
            {
                "url_hash": r.get("url_hash"),
                "title": r.get("title") or "",
                "title_ko": r.get("title_ko") or "",
                "source": r.get("source") or "",
                "category": r.get("category") or "",
                "published_at": r.get("published_at"),
                "summary_formal": r.get("summary_formal") or "",
                "similarity": float(r.get("similarity") or 0),
            }
        )

    sub_message = maybe_digest_sub_message(articles_raw)

    payload: dict[str, Any] = {
        "show": True,
        "message": message,
        "days_away": days_away,
        "articles": articles_out,
    }
    if sub_message:
        payload["sub_message"] = sub_message

    return payload


def mark_user_seen(sb: Any, user_id: str) -> None:
    now = datetime.now(timezone.utc)
    sb.table("users").update({"last_seen_at": now.isoformat()}).eq("user_id", user_id).execute()
