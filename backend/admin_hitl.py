"""Local-only HITL review POC routes.

These routes are intentionally separate from the Apps in Toss `.ait` frontend.
They demonstrate review-target separation for presentation/local admin testing.
They are disabled unless ADMIN_REVIEW_ENABLED=1.
"""

from __future__ import annotations

import html
import os
from collections.abc import Callable
from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field


REVIEW_LABELS = {"HITL_REQUIRED", "HITL", "HUMAN_REVIEW", "UNVERIFIED", "RUMOR", "INSIGHT"}
UPDATE_LABELS = {"FACT", "RUMOR", "UNVERIFIED", "INSIGHT"}


class HitlReviewRequest(BaseModel):
    url_hash: str = Field(min_length=1)
    fact_label: Literal["FACT", "RUMOR", "UNVERIFIED", "INSIGHT"]
    fact_reason: str | None = None
    fact_insight: str | None = None


def _enabled() -> bool:
    return os.getenv("ADMIN_REVIEW_ENABLED", "").strip() == "1"


def _service_role_enabled() -> bool:
    return bool(os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip())


def _normalize_label(row: dict[str, Any]) -> str:
    if bool(row.get("hitl_required")):
        return "HITL_REQUIRED"
    raw = str(row.get("fact_status") or row.get("fact_label") or "").strip().upper()
    if raw in {"HITL", "HITL_REQUIRED", "HUMAN_REVIEW", "HUMAN_REVIEW_REQUIRED"}:
        return "HITL_REQUIRED"
    if raw in {"FACT", "VERIFIED"}:
        return "FACT"
    if raw in {"RUMOR", "INSIGHT", "UNVERIFIED"}:
        return raw
    return "UNVERIFIED"


def _article_url(row: dict[str, Any]) -> str:
    return str(row.get("url") or row.get("source_url") or row.get("original_url") or "").strip()


def _is_visible_candidate(row: dict[str, Any]) -> bool:
    title = f"{row.get('title') or ''} {row.get('title_ko') or ''}".upper()
    if bool(row.get("is_hidden")) or bool(row.get("is_demo")):
        return False
    if str(row.get("source") or "").strip().upper() == "DEMO":
        return False
    if "DEMO" in title or "MOCK" in title or "시연용" in str(row.get("title_ko") or ""):
        return False
    return _normalize_label(row) in REVIEW_LABELS


def _fetch_candidates(db: Any, limit: int) -> list[dict[str, Any]]:
    fields = (
        "url_hash,title,title_ko,source,url,source_url,original_url,published_at,"
        "fact_label,fact_status,fact_reason,fact_insight,credibility_score,"
        "hitl_required,is_hidden,is_demo"
    )
    result = (
        db.table("articles")
        .select(fields)
        .order("published_at", desc=True)
        .limit(max(limit * 4, limit))
        .execute()
    )
    rows = [row for row in (result.data or []) if _is_visible_candidate(row)]
    return rows[:limit]


def _row_to_payload(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "url_hash": row.get("url_hash"),
        "title_ko": row.get("title_ko") or row.get("title"),
        "source": row.get("source"),
        "published_at": row.get("published_at"),
        "fact_label": _normalize_label(row),
        "fact_reason": row.get("fact_reason"),
        "fact_insight": row.get("fact_insight"),
        "credibility_score": row.get("credibility_score"),
        "url": _article_url(row),
    }


def _html_page(rows: list[dict[str, Any]]) -> str:
    cards = []
    for row in rows:
        item = _row_to_payload(row)
        url = str(item["url"] or "")
        link = f'<a href="{html.escape(url)}" target="_blank">원문</a>' if url.startswith(("http://", "https://")) else "원문 없음"
        cards.append(
            "<article>"
            f"<strong>{html.escape(str(item['fact_label']))}</strong>"
            f"<h2>{html.escape(str(item['title_ko'] or '(untitled)'))}</h2>"
            f"<p>{html.escape(str(item['source'] or ''))} · {html.escape(str(item['published_at'] or ''))}</p>"
            f"<p>{html.escape(str(item['fact_insight'] or item['fact_reason'] or '설명 없음'))}</p>"
            f"<p>{link}</p>"
            "</article>"
        )
    return (
        "<!doctype html><meta charset='utf-8'>"
        "<title>삼선뉴스 검토 대상 POC</title>"
        "<style>"
        "body{font-family:system-ui,-apple-system,sans-serif;margin:24px;background:#f5f7fb;color:#191f28}"
        "main{max-width:860px;margin:auto}article{background:white;border:1px solid #e5e8eb;border-radius:12px;padding:16px;margin:12px 0}"
        "strong{display:inline-block;background:#f5f3ff;color:#6d28d9;border-radius:999px;padding:4px 10px;font-size:12px}"
        "h1{font-size:28px}h2{font-size:18px}p{color:#4e5968;line-height:1.6}"
        "</style><main>"
        "<h1>검토 대상 보기 POC</h1>"
        "<p>AI 자동 판정 결과 중 전문가 검토/확인 필요/루머/분석글 후보를 읽기 전용으로 보여줍니다. "
        "운영용 관리자 승인 시스템이 아니며, Apps in Toss 사용자 앱에는 포함되지 않습니다.</p>"
        + "".join(cards)
        + "</main>"
    )


def create_admin_hitl_router(get_db: Callable[[], Any]) -> APIRouter:
    router = APIRouter(prefix="/admin", tags=["local-admin-hitl"])

    def require_enabled() -> Any:
        if not _enabled():
            raise HTTPException(status_code=404, detail="Admin review POC is disabled. Set ADMIN_REVIEW_ENABLED=1 locally.")
        return get_db()

    @router.get("/hitl-candidates")
    def hitl_candidates(limit: int = Query(20, ge=1, le=100)) -> dict[str, Any]:
        db = require_enabled()
        rows = _fetch_candidates(db, limit)
        return {
            "mode": "local_admin_poc_read_only",
            "updates_enabled": _service_role_enabled(),
            "count": len(rows),
            "items": [_row_to_payload(row) for row in rows],
        }

    @router.get("/hitl", response_class=HTMLResponse)
    def hitl_page(limit: int = Query(20, ge=1, le=100)) -> HTMLResponse:
        db = require_enabled()
        return HTMLResponse(_html_page(_fetch_candidates(db, limit)))

    @router.post("/hitl-review")
    def hitl_review(req: HitlReviewRequest) -> dict[str, Any]:
        db = require_enabled()
        if not _service_role_enabled():
            raise HTTPException(
                status_code=403,
                detail="Review updates require SUPABASE_SERVICE_ROLE_KEY in local backend env. The .ait app never uses this key.",
            )
        payload: dict[str, Any] = {
            "fact_label": req.fact_label,
            "fact_status": req.fact_label,
            "hitl_required": False,
        }
        if req.fact_reason is not None:
            payload["fact_reason"] = req.fact_reason
        if req.fact_insight is not None:
            payload["fact_insight"] = req.fact_insight
        db.table("articles").update(payload).eq("url_hash", req.url_hash).execute()
        return {"message": "review updated", "url_hash": req.url_hash, "fact_label": req.fact_label}

    return router
