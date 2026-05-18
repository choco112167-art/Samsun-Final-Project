"""
Seed clearly marked, synthetic demo articles for Samsun News.

Safety rules:
- Every article uses source="DEMO".
- Every Korean title starts with "[시연용]".
- Rumor/HITL rows explicitly say they are unverified demo data.
- Existing production rows are not deleted.

Usage:
    python scripts/seed_demo_articles.py
    python scripts/seed_demo_articles.py --replace-demo --confirm-delete
"""

from __future__ import annotations

import argparse
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Any

from article_pipeline_common import configure_stdio, get_supabase_client, supported_article_columns


OPTIONAL_ARTICLE_COLUMNS = (
    "source_url",
    "fact_status",
    "is_demo",
    "demo_visible",
    "demo_priority",
    "hitl_required",
    "ai_status",
    "ai_provider",
    "ai_model",
    "ai_generated_at",
    "content_source",
    "content_chars",
    "translation_chars",
    "updated_at",
    "slang_terms",
    "neologism_terms",
)


def make_hash(url: str) -> str:
    return hashlib.md5(url.encode("utf-8")).hexdigest()


def now_iso(offset_minutes: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(minutes=offset_minutes)).isoformat()


def demo_articles() -> list[dict[str, Any]]:
    base = "https://example.com/samsun-news-demo"
    return [
        {
            "slug": "verified-ai-chip",
            "title": "[DEMO] Verified AI accelerator benchmark briefing",
            "title_ko": "[시연용] 국내 AI 가속기 벤치마크 공개, 검증 자료와 함께 발표",
            "category": "1",
            "credibility_score": 0.92,
            "fact_label": "FACT",
            "published_at": now_iso(18),
            "summary_formal": "1. 한 국내 연구팀이 AI 가속기 벤치마크 결과를 공개했습니다.\n2. 발표 자료와 테스트 조건이 함께 제공되어 검증 가능성이 높습니다.\n3. 업계는 전력 효율과 추론 성능 개선 폭을 주요 관전 포인트로 보고 있습니다.",
            "summary_casual": "1. 국내 연구팀이 AI 가속기 성능 결과를 공개했어요.\n2. 테스트 조건과 자료가 같이 나와서 확인하기 쉬운 편이에요.\n3. 전력 효율과 추론 속도가 이번 발표의 핵심 포인트예요.",
            "translation": "이 시연용 검증 기사에서는 국내 연구팀이 공개한 AI 가속기 벤치마크 결과를 소개합니다. 발표에는 테스트 환경, 비교 기준, 전력 측정 방식이 함께 포함되어 있어 사용자가 결과를 검토할 수 있습니다.\n\n업계 관계자들은 추론 처리량과 전력 효율이 실제 서비스 비용에 직접적인 영향을 주기 때문에 이번 자료를 참고 지표로 보고 있습니다. 이 데이터는 실제 뉴스가 아니라 데모 화면에서 검증됨 상태를 보여주기 위한 안전한 샘플입니다.",
            "content": "Synthetic demo article for a verified AI accelerator benchmark briefing. This is not real news.",
            "claims": [
                {"claim": "시연용 벤치마크 자료에는 테스트 조건과 전력 측정 기준이 포함되어 있습니다.", "verdict": "FACT", "confidence": 0.92},
            ],
        },
        {
            "slug": "unverified-breaking-model",
            "title": "[DEMO] Unverified breaking model release note",
            "title_ko": "[시연용] 새 AI 모델 공개 소식, 공식 확인 전 단계",
            "category": "2",
            "credibility_score": 0.56,
            "fact_label": "UNVERIFIED",
            "published_at": now_iso(35),
            "summary_formal": "1. 한 AI 모델 공개 소식이 커뮤니티를 통해 먼저 확산되었습니다.\n2. 공식 발표 자료가 아직 확인되지 않아 미검증 상태로 분류했습니다.\n3. 후속 확인이 이뤄지기 전까지는 참고 정보로만 보는 것이 적절합니다.",
            "summary_casual": "1. 새 AI 모델이 나왔다는 이야기가 커뮤니티에서 먼저 퍼졌어요.\n2. 아직 공식 발표가 확인되지 않아서 미검증으로 표시했어요.\n3. 나중에 공식 자료가 나오면 다시 확인하는 게 좋아요.",
            "translation": "이 시연용 미검증 기사에서는 커뮤니티에서 먼저 퍼진 AI 모델 공개 소식을 다룹니다. 현재 공식 발표문이나 검증 가능한 원문 자료가 확인되지 않았기 때문에 앱은 이 항목을 미검증으로 표시합니다.\n\n사용자는 제목과 요약을 읽을 수 있지만, 신뢰도 배지와 상세 안내를 통해 아직 확인되지 않은 정보임을 알 수 있습니다. 이 항목은 실제 뉴스가 아니라 데모용 샘플입니다.",
            "content": "Synthetic demo article for an unverified breaking AI model release. This is not real news.",
            "claims": [
                {"claim": "공식 발표 자료가 확인되지 않은 시연용 모델 공개 소식입니다.", "verdict": "UNVERIFIED", "confidence": 0.56},
            ],
        },
        {
            "slug": "verified-agent-workflow",
            "title": "[DEMO] Verified enterprise AI agent workflow case",
            "title_ko": "[시연용] 기업용 AI 에이전트 도입 사례, 검증된 자료로 정리",
            "category": "2",
            "credibility_score": 0.88,
            "fact_label": "FACT",
            "published_at": now_iso(44),
            "summary_formal": "1. 한 기업이 내부 문서 검색과 고객 응대에 AI 에이전트를 적용한 시연용 사례입니다.\n2. 적용 범위와 제한 조건이 명확히 제시되어 검증됨 상태로 표시했습니다.\n3. 데모에서는 완성도 높은 일반 AI 뉴스 카드가 어떻게 보이는지 확인할 수 있습니다.",
            "summary_casual": "1. 한 기업이 문서 검색과 고객 응대에 AI 에이전트를 쓰는 시연용 사례예요.\n2. 적용 범위와 한계가 분명해서 검증됨으로 표시했어요.\n3. 데모에서 일반적인 완성형 AI 뉴스 카드 모습을 볼 수 있어요.",
            "translation": "이 시연용 검증 기사에서는 기업용 AI 에이전트 도입 사례를 다룹니다. 내부 문서 검색, 반복 고객 문의 응답, 담당자 검토 흐름을 연결하는 구성이며, 적용 범위와 제한 조건이 함께 제시되어 있습니다.\n\n이 항목은 실제 뉴스가 아니라 데모 화면에서 검증됨 상태와 완성된 번역·요약·제목 구성을 보여주기 위한 안전한 샘플입니다.",
            "content": "Synthetic verified enterprise AI agent workflow article. This is not real news.",
            "claims": [
                {"claim": "기업용 AI 에이전트 도입 과정을 보여주는 검증됨 상태의 시연용 기사입니다.", "verdict": "FACT", "confidence": 0.88},
            ],
        },
        {
            "slug": "rumor-lab-acquisition",
            "title": "[DEMO] Rumor about a lab acquisition",
            "title_ko": "[시연용] 미확인 인수설 확산, 루머 의심으로 표시",
            "category": "3",
            "credibility_score": 0.32,
            "fact_label": "RUMOR",
            "published_at": now_iso(52),
            "summary_formal": "1. 한 AI 연구소 인수설이 확인되지 않은 게시글을 통해 확산되었습니다.\n2. 공식 입장과 교차검증 자료가 없어 루머 의심 상태로 표시했습니다.\n3. 이 항목은 시연용 데이터이며 실제 검증된 뉴스가 아닙니다.",
            "summary_casual": "1. 어떤 AI 연구소가 인수된다는 말이 온라인에 퍼졌어요.\n2. 공식 확인이나 다른 출처 확인이 없어서 루머 의심으로 표시했어요.\n3. 이건 시연용 데이터라 실제 뉴스처럼 믿으면 안 돼요.",
            "translation": "이 항목은 루머 표시 UI를 보여주기 위해 만든 시연용 데이터입니다. 확인되지 않은 게시글에서 시작된 AI 연구소 인수설이라는 설정을 사용하지만, 실제 기업이나 실제 거래를 주장하지 않습니다.\n\n앱은 이 항목을 루머 의심으로 표시하고, 상세 화면에서 검증되지 않은 시연용 루머 데이터라는 안내를 제공합니다. 사용자는 이 정보가 확인된 뉴스가 아니라는 점을 즉시 알 수 있어야 합니다.",
            "content": "Synthetic demo rumor article. It is intentionally unverified and does not describe a real acquisition.",
            "claims": [
                {"claim": "이 항목은 실제 인수 사실이 아니라 시연용 루머 데이터입니다.", "verdict": "RUMOR", "confidence": 0.32},
            ],
        },
        {
            "slug": "neologism-prompt-injection",
            "title": "[DEMO] Neologism example about prompt injection defense",
            "title_ko": "[시연용] 프롬프트 주입 방어와 가드레일 운영 사례",
            "category": "3",
            "credibility_score": 0.82,
            "fact_label": "FACT",
            "published_at": now_iso(60),
            "summary_formal": "1. 프롬프트 주입 공격을 막기 위한 가드레일 운영 사례를 소개하는 시연용 기사입니다.\n2. 신조어 설명 기능을 보여주기 위해 관련 용어를 본문과 요약에 포함했습니다.\n3. 사용자는 강조된 용어를 눌러 Supabase neologisms 설명을 확인할 수 있습니다.",
            "summary_casual": "1. 프롬프트 주입을 막는 가드레일 운영 사례를 보여주는 시연용 기사예요.\n2. 신조어 설명 기능을 보여주려고 관련 용어를 요약과 번역에 넣었어요.\n3. 강조된 단어를 누르면 DB에 저장된 설명을 볼 수 있어요.",
            "translation": "이 시연용 기사는 프롬프트 주입과 가드레일이라는 용어를 앱에서 어떻게 설명하는지 보여줍니다. 프롬프트 주입은 사용자가 모델 지시문을 우회하도록 유도하는 공격 방식이며, 가드레일은 이러한 위험을 줄이기 위해 입력과 출력을 제한하고 점검하는 운영 장치입니다.\n\n이 항목은 실제 보안 사고를 주장하지 않습니다. 신조어 하이라이트와 설명 팝오버가 데모에서 자연스럽게 보이도록 만든 안전한 샘플입니다.",
            "content": "Synthetic neologism demo article for prompt injection and guardrails. This is not real news.",
            "slang_terms": ["프롬프트 주입", "가드레일"],
            "claims": [
                {"claim": "프롬프트 주입과 가드레일 설명 기능을 보여주는 시연용 기사입니다.", "verdict": "FACT", "confidence": 0.82},
            ],
        },
        {
            "slug": "hitl-policy-review",
            "title": "[DEMO] HITL policy review needed",
            "title_ko": "[시연용] AI 정책 해석 차이, 사람 검토 필요",
            "category": "4",
            "credibility_score": 0.48,
            "fact_label": "HITL_REQUIRED",
            "published_at": now_iso(70),
            "summary_formal": "1. AI 정책 문서의 해석이 출처별로 다르게 나타난 시연용 사례입니다.\n2. 자동 판별만으로 결론을 내리기 어려워 사람 검토 필요로 표시했습니다.\n3. 데모에서는 HITL 상태가 어떻게 보이는지 확인할 수 있습니다.",
            "summary_casual": "1. AI 정책 문서를 두고 해석이 갈리는 상황을 보여주는 시연용 사례예요.\n2. 자동으로 판단하기 애매해서 사람 검토 필요로 표시했어요.\n3. 데모에서 HITL 상태가 어떻게 보이는지 확인할 수 있어요.",
            "translation": "이 시연용 항목은 Human-in-the-Loop 검토 상태를 보여주기 위한 데이터입니다. 정책 문서의 해석이 출처마다 다르게 제시되는 상황을 가정했으며, 자동 판별만으로는 충분하지 않다는 점을 표현합니다.\n\n앱은 이 항목을 HITL 검토 필요로 표시합니다. 이는 사용자가 자동 요약과 신뢰도 점수를 참고하되, 최종 판단에는 사람의 검토가 필요하다는 의미입니다.",
            "content": "Synthetic demo HITL article for human review required state. This is not real news.",
            "claims": [
                {"claim": "정책 해석이 갈리는 시연용 사례로, 사람 검토 필요 상태를 보여줍니다.", "verdict": "HITL_REQUIRED", "confidence": 0.48},
            ],
        },
    ]


def article_payloads(sb) -> list[dict[str, Any]]:
    optional = supported_article_columns(sb, OPTIONAL_ARTICLE_COLUMNS)
    rows: list[dict[str, Any]] = []
    for index, item in enumerate(demo_articles(), 1):
        url = f"https://example.com/samsun-news-demo/{item['slug']}"
        row: dict[str, Any] = {
            "url_hash": make_hash(url),
            "url": url,
            "title": item["title"],
            "title_ko": item["title_ko"],
            "source": "DEMO",
            "source_type": "media",
            "category": item["category"],
            "country": "KR",
            "keywords": ["demo", "AI", "시연용"],
            "published_at": item["published_at"],
            "collected_at": datetime.now(timezone.utc).isoformat(),
            "content": item["content"],
            "credibility_score": item["credibility_score"],
            "fact_label": item["fact_label"],
            "translation": item["translation"],
            "summary_formal": item["summary_formal"],
            "summary_casual": item["summary_casual"],
        }
        extras: dict[str, Any] = {
            "source_url": url,
            "fact_status": item["fact_label"],
            "is_demo": True,
            "demo_visible": True,
            "demo_priority": index,
            "hitl_required": item["fact_label"] == "HITL_REQUIRED",
            "ai_status": "completed",
            "ai_provider": "demo-seed",
            "ai_model": "synthetic-demo-v1",
            "ai_generated_at": datetime.now(timezone.utc).isoformat(),
            "content_source": "synthetic_demo",
            "content_chars": len(item["content"]),
            "translation_chars": len(item["translation"]),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "slang_terms": item.get("slang_terms", []),
            "neologism_terms": item.get("slang_terms", []),
        }
        for key, value in extras.items():
            if key in optional:
                row[key] = value
        rows.append(row)
    return rows


def seed_fact_checks(sb, rows: list[dict[str, Any]]) -> None:
    try:
        hashes = [row["url_hash"] for row in rows]
        sb.table("fact_checks").delete().in_("article_url_hash", hashes).execute()
        fact_rows = []
        by_slug = {make_hash(f"https://example.com/samsun-news-demo/{item['slug']}"): item for item in demo_articles()}
        for row in rows:
            for claim in by_slug[row["url_hash"]]["claims"]:
                fact_rows.append({
                    "article_url_hash": row["url_hash"],
                    "claim": claim["claim"],
                    "verdict": claim["verdict"],
                    "confidence": claim["confidence"],
                    "evidence_url": row["url"],
                    "checker_type": "demo",
                    "checked_at": datetime.now(timezone.utc).isoformat(),
                })
        if fact_rows:
            sb.table("fact_checks").insert(fact_rows).execute()
            print(f"[seed-demo] fact_checks inserted={len(fact_rows)}")
    except Exception as exc:
        print(f"[seed-demo] fact_checks skipped: {exc}")


def seed_neologisms(sb) -> None:
    rows = [
        {
            "term": "HITL",
            "explanation": "Human-in-the-Loop의 약자로, AI 판단 뒤 사람이 최종 검토하는 절차입니다.",
            "ko_suggestion": "사람 검토",
            "occurrence_count": 1,
            "confirmed": True,
        },
        {
            "term": "프롬프트 주입",
            "explanation": "모델의 지시문을 우회하거나 악용하도록 입력을 조작하는 공격 방식입니다.",
            "ko_suggestion": "지시문 조작 공격",
            "occurrence_count": 1,
            "confirmed": True,
        },
        {
            "term": "가드레일",
            "explanation": "AI 입력과 출력을 제한·점검해 위험한 응답을 줄이는 안전 장치입니다.",
            "ko_suggestion": "안전 장치",
            "occurrence_count": 1,
            "confirmed": True,
        },
    ]
    try:
        for row in rows:
            try:
                sb.table("neologisms").upsert(row, on_conflict="term").execute()
            except Exception:
                sb.table("neologisms").insert(row).execute()
        print(f"[seed-demo] neologisms upserted={len(rows)}")
    except Exception as exc:
        print(f"[seed-demo] neologisms skipped: {exc}")


def main() -> int:
    configure_stdio()
    parser = argparse.ArgumentParser()
    parser.add_argument("--replace-demo", action="store_true")
    parser.add_argument("--confirm-delete", action="store_true")
    args = parser.parse_args()

    sb = get_supabase_client()
    if args.replace_demo:
        if not args.confirm_delete:
            raise SystemExit("--replace-demo requires --confirm-delete")
        existing = sb.table("articles").select("url_hash").eq("source", "DEMO").execute().data or []
        hashes = [row["url_hash"] for row in existing if row.get("url_hash")]
        if hashes:
            try:
                sb.table("fact_checks").delete().in_("article_url_hash", hashes).execute()
            except Exception as exc:
                print(f"[seed-demo] fact_checks cleanup skipped: {exc}")
        sb.table("articles").delete().eq("source", "DEMO").execute()
        print("[seed-demo] existing source=DEMO articles deleted")

    rows = article_payloads(sb)
    sb.table("articles").upsert(rows, on_conflict="url_hash").execute()
    seed_fact_checks(sb, rows)
    seed_neologisms(sb)
    print(f"[seed-demo] articles upserted={len(rows)}")
    print("[seed-demo] all rows are synthetic and marked with source=DEMO and [시연용].")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
