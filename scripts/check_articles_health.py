"""
Print Supabase articles health metrics for demo/ops checks.

DB field mapping:
  - Original article URL: articles.url
  - Korean title: articles.title_ko
  - Body translation: articles.translation
  - Summaries: articles.summary_formal / articles.summary_casual
"""

from __future__ import annotations

from article_pipeline_common import configure_stdio, get_supabase_client, supported_article_columns


def _count(sb, filter_expr: str | None = None) -> int:
    query = sb.table("articles").select("url_hash", count="exact")
    if filter_expr:
        query = query.or_(filter_expr)
    result = query.execute()
    return int(result.count or 0)


def _mock_rows(sb, limit: int = 20) -> list[dict]:
    return (
        sb.table("articles")
        .select("url_hash,title,title_ko,published_at,translation,summary_formal,summary_casual")
        .or_("translation.ilike.%[MOCK%,summary_formal.ilike.%[MOCK%,summary_casual.ilike.%[MOCK%")
        .order("published_at", desc=True)
        .limit(limit)
        .execute()
        .data
        or []
    )


def main() -> int:
    configure_stdio()
    sb = get_supabase_client()
    meta_fields = supported_article_columns(
        sb,
        (
            "ai_status",
            "ai_provider",
            "ai_model",
            "ai_generated_at",
            "ai_error",
            "content_source",
            "content_chars",
            "translation_chars",
            "detected_at",
            "created_at",
            "collected_at",
        ),
    )

    total = _count(sb)
    missing_title_ko = _count(sb, "title_ko.is.null,title_ko.eq.")
    missing_url = _count(sb, "url.is.null,url.eq.")
    missing_translation = _count(sb, "translation.is.null,translation.eq.")
    missing_content = _count(sb, "content.is.null,content.eq.")
    missing_summary_formal = _count(sb, "summary_formal.is.null,summary_formal.eq.")
    missing_summary_casual = _count(sb, "summary_casual.is.null,summary_casual.eq.")
    mock_rows = _mock_rows(sb)
    completed_inferred = total - _count(
        sb,
        "translation.is.null,translation.eq.,summary_formal.is.null,summary_formal.eq.,summary_casual.is.null,summary_casual.eq.",
    )
    pending_inferred = total - completed_inferred

    newest = (
        sb.table("articles")
        .select("published_at")
        .order("published_at", desc=True)
        .limit(1)
        .execute()
        .data
        or []
    )
    oldest = (
        sb.table("articles")
        .select("published_at")
        .order("published_at", desc=False)
        .limit(1)
        .execute()
        .data
        or []
    )

    print("== articles health ==")
    print(f"total_articles: {total}")
    print(f"missing_title_ko: {missing_title_ko}")
    print(f"missing_original_url(url): {missing_url}")
    print(f"missing_translation: {missing_translation}")
    print(f"missing_original_body(content): {missing_content}")
    print(f"missing_summary_formal: {missing_summary_formal}")
    print(f"missing_summary_casual: {missing_summary_casual}")
    print(f"mock_ai_outputs_detected: {len(mock_rows)}")
    print(f"ai_completed_inferred: {completed_inferred}")
    print(f"ai_pending_inferred: {pending_inferred}")
    print(f"ai_meta_columns: {','.join(sorted(meta_fields)) or '(not migrated)'}")
    print(f"newest_published_at: {(newest[0].get('published_at') if newest else '')}")
    print(f"oldest_published_at: {(oldest[0].get('published_at') if oldest else '')}")

    recent_select = [
        "url_hash",
        "title",
        "title_ko",
        "source",
        "url",
        "published_at",
        "translation",
        "summary_formal",
        "summary_casual",
    ]
    for optional in (
        "detected_at",
        "created_at",
        "collected_at",
        "ai_status",
        "ai_provider",
        "ai_model",
    ):
        if optional in meta_fields:
            recent_select.append(optional)

    recent = (
        sb.table("articles")
        .select(",".join(recent_select))
        .order("published_at", desc=True)
        .limit(20)
        .execute()
        .data
        or []
    )

    print("\n== recent 20 ==")
    for index, row in enumerate(recent, 1):
        title = (row.get("title") or "")
        title_ko_text = (row.get("title_ko") or "")
        title_ko = bool((row.get("title_ko") or "").strip())
        has_url = bool((row.get("url") or "").strip())
        has_translation = bool((row.get("translation") or "").strip())
        has_summary_formal = bool((row.get("summary_formal") or "").strip())
        has_summary_casual = bool((row.get("summary_casual") or "").strip())
        completed = has_translation and has_summary_formal and has_summary_casual
        inferred_status = "completed" if completed else "pending"
        detected = row.get("detected_at") or row.get("created_at") or row.get("collected_at") or ""
        title_only = title_ko and not completed
        print(
            f"{index:02d}. id={row.get('url_hash')} source={row.get('source')} "
            f"published_at={row.get('published_at')} detected_or_collected_at={detected} "
            f"title_ko={title_ko} original_url={has_url} url={row.get('url')} "
            f"translation={has_translation} summary_formal={has_summary_formal} "
            f"summary_casual={has_summary_casual} "
            f"ai_status={row.get('ai_status') or inferred_status} "
            f"ai_provider={row.get('ai_provider') or ''} ai_model={row.get('ai_model') or ''} "
            f"ingest_kind={'title-only/pending' if title_only else 'ai-completed' if completed else 'raw/pending'} "
            f"title_ko_text={title_ko_text[:80]} title={title[:80]}"
        )

    if mock_rows:
        print("\n== MOCK AI outputs ==")
        for index, row in enumerate(mock_rows, 1):
            fields = [
                name for name in ("translation", "summary_formal", "summary_casual")
                if "[MOCK" in str(row.get(name) or "")
            ]
            title = (row.get("title_ko") or row.get("title") or "")[:80]
            print(
                f"{index:02d}. url_hash={row.get('url_hash')} "
                f"published_at={row.get('published_at')} fields={','.join(fields)} title={title}"
            )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
