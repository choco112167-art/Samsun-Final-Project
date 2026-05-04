"""
Backfill missing AI output fields in Supabase articles.

This script fills real model outputs for:
  - translation
  - summary_formal
  - summary_casual

It never stores title/title_ko as a translation or summary fallback. Rows with
no article body are skipped so the frontend can honestly show its prepared state
until a real model output is available.
"""

from __future__ import annotations

import argparse
import os
import requests
from typing import Any

from article_pipeline_common import (
    body_quality_warning,
    configure_stdio,
    fetch_article_body_from_url,
    get_supabase_client,
    is_blank,
)


AI_FIELDS = ("translation", "summary_formal", "summary_casual")
BASE_SELECT_FIELDS = (
    "url_hash,title,title_ko,url,source,published_at,content,"
    "translation,summary_formal,summary_casual"
)
AI_META_FIELDS = (
    "ai_status",
    "ai_provider",
    "ai_model",
    "ai_generated_at",
    "ai_error",
    "content_source",
    "content_chars",
    "translation_chars",
)
OPENROUTER_ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"


def _missing_filter() -> str:
    return ",".join(f"{field}.is.null,{field}.eq." for field in AI_FIELDS)


def fetch_target_articles(
    sb,
    limit: int,
    source: str | None,
    only_missing: bool,
    url_hash: str | None,
    repair_short_translation: bool,
    min_translation_chars: int,
    available_meta_fields: set[str],
) -> list[dict[str, Any]]:
    query_limit = limit * 5 if repair_short_translation and only_missing else limit
    select_fields = BASE_SELECT_FIELDS
    if available_meta_fields:
        select_fields = f"{select_fields},{','.join(sorted(available_meta_fields))}"
    query = sb.table("articles").select(select_fields).order("published_at", desc=True).limit(query_limit)
    if only_missing and not repair_short_translation:
        query = query.or_(_missing_filter())
    if source:
        query = query.eq("source", source)
    if url_hash:
        query = query.eq("url_hash", url_hash)
    result = query.execute()
    rows = result.data or []
    if repair_short_translation and only_missing:
        rows = [
            row for row in rows
            if any(is_blank(row.get(field)) for field in AI_FIELDS)
            or len(str(row.get("translation") or "").strip()) < min_translation_chars
        ]
    return rows[:limit]


def detect_ai_meta_fields(sb) -> set[str]:
    available: set[str] = set()
    for field in AI_META_FIELDS:
        try:
            sb.table("articles").select(field).limit(1).execute()
            available.add(field)
        except Exception:
            pass
    return available


def get_article_body(row: dict[str, Any], min_body_chars: int, max_body_chars: int) -> tuple[str, str, str]:
    content = (row.get("content") or "").strip()
    warning = body_quality_warning(content)
    if len(content) >= min_body_chars and not warning:
        return content[:max_body_chars], "db.content", ""

    url = (row.get("url") or "").strip()
    if not url:
        reason = "missing url" if not content else f"db.content unsuitable ({warning or len(content)}), missing url"
        return "", reason, warning

    try:
        fetched = fetch_article_body_from_url(url).strip()
    except Exception as exc:
        return "", f"db.content unsuitable ({warning or len(content)}), url crawl failed: {exc}", warning

    crawl_warning = body_quality_warning(fetched)
    if len(fetched) < min_body_chars or crawl_warning:
        return "", (
            f"body unsuitable: db.content={len(content)} chars warning={warning or '-'}, "
            f"url crawl={len(fetched)} chars warning={crawl_warning or '-'}"
        ), crawl_warning or warning
    return fetched[:max_body_chars], "url crawl", ""


def build_update_payload(
    row: dict[str, Any],
    generated: dict[str, Any],
    overwrite: bool,
    repair_short_translation: bool,
    min_translation_chars: int,
    provider: str,
    model: str,
    body_source: str,
    body_chars: int,
    available_meta_fields: set[str],
    ai_status: str,
    ai_error: str = "",
) -> dict[str, str]:
    payload: dict[str, Any] = {}
    for field in AI_FIELDS:
        value = str(generated.get(field) or "").strip()
        if not value:
            continue
        current = row.get(field)
        if field == "translation" and repair_short_translation:
            if overwrite or is_blank(current) or len(str(current).strip()) < min_translation_chars:
                payload[field] = value
            continue
        if overwrite or is_blank(current):
            payload[field] = value
    meta_values: dict[str, Any] = {
        "ai_status": ai_status,
        "ai_provider": provider,
        "ai_model": model,
        "ai_error": ai_error[:1000] if ai_error else None,
        "content_source": body_source,
        "content_chars": body_chars,
        "translation_chars": len(str(generated.get("translation") or "").strip()),
    }
    if ai_status == "completed":
        meta_values["ai_generated_at"] = "now()"
    for field, value in meta_values.items():
        if field not in available_meta_fields:
            continue
        if field == "ai_generated_at" and value == "now()":
            # Supabase-py sends values, not SQL expressions. Use ISO timestamp instead.
            from datetime import datetime, timezone

            payload[field] = datetime.now(timezone.utc).isoformat()
        else:
            payload[field] = value
    return payload


def needs_processing(row: dict[str, Any], repair_short_translation: bool, min_translation_chars: int) -> bool:
    if any(is_blank(row.get(field)) for field in AI_FIELDS):
        return True
    if repair_short_translation and len(str(row.get("translation") or "").strip()) < min_translation_chars:
        return True
    return False


def mock_outputs(title: str, body: str) -> dict[str, str]:
    clean_title = title.strip() or "테스트 기사"
    snippet = " ".join((body or "").split())[:260]
    return {
        "title": "",
        "translation": (
            f"[MOCK 번역 전문] {clean_title}\n\n"
            f"이 문장은 실제 모델 호출 없이 파이프라인 저장 흐름을 검증하기 위한 테스트 번역입니다. "
            f"원문 본문이 확보되면 이 위치에는 기사 전체를 한국어 기사체로 번역한 전문이 저장됩니다.\n\n"
            f"원문 일부: {snippet}"
        ),
        "summary_formal": (
            "[MOCK 격식체 요약]\n"
            "1. 이 기사는 AI 출력 저장 파이프라인을 검증하기 위한 테스트 대상입니다.\n"
            "2. 실제 운영에서는 모델이 원문 전체 번역과 3줄 요약을 생성합니다.\n"
            "3. 성공 시 Supabase의 AI 출력 필드가 채워지고 프론트에 그대로 표시됩니다."
        ),
        "summary_casual": (
            "[MOCK 일상체 요약]\n"
            "1. 지금은 AI 처리 흐름이 잘 저장되는지 확인하는 테스트예요.\n"
            "2. 운영 때는 모델이 전체 번역과 요약을 만들어 넣을 거예요.\n"
            "3. DB에 값이 들어가면 앱 상세 페이지에서 바로 보여요."
        ),
    }


def generate_outputs(provider: str, model: str, title: str, body: str, summary_sentences: int) -> dict[str, str]:
    endpoint_log = {
        "mock": "mock",
        "openrouter": "openrouter",
        "gemini": "gemini-direct",
        "local": os.getenv("LOCAL_LLM_ENDPOINT") or os.getenv("OLLAMA_BASE_URL") or "local-not-configured",
    }.get(provider, provider)
    print(f"[llm] provider={provider} model={model} endpoint={endpoint_log}", flush=True)

    if provider == "mock":
        return mock_outputs(title, body)

    if provider == "openrouter":
        from pipeline.translate_summarize import SYSTEM_PROMPT
        from pipeline.utils import extract_json

        api_key = os.getenv("OPENROUTER_API_KEY", "").strip()
        if not api_key:
            raise RuntimeError("OPENROUTER_API_KEY 환경변수 없음")
        system = SYSTEM_PROMPT.format(n=summary_sentences)
        response = requests.post(
            OPENROUTER_ENDPOINT,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": os.getenv("PUBLIC_API_BASE_URL", "http://localhost:8000"),
                "X-Title": "Samsun News AI output worker",
            },
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": f"[TITLE]\n{title}\n\n[BODY]\n{body}"},
                ],
                "temperature": 0.1,
                "max_tokens": 4096,
            },
            timeout=120,
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        return extract_json(content)

    if provider == "gemini":
        from pipeline.translate_summarize import SYSTEM_PROMPT
        from pipeline.utils import extract_json
        from google import genai
        from google.genai import types

        api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("GOOGLE_API_KEY 또는 GEMINI_API_KEY 환경변수 없음")
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=model,
            contents=f"[TITLE]\n{title}\n\n[BODY]\n{body}",
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT.format(n=summary_sentences),
                temperature=0.1,
                max_output_tokens=4096,
            ),
        )
        return extract_json(response.text or "")

    if provider == "local":
        endpoint = os.getenv("LOCAL_LLM_ENDPOINT", "").strip()
        ollama_base = os.getenv("OLLAMA_BASE_URL", "").strip()
        local_ready = os.getenv("LOCAL_LLM_CONFIGURED", "").strip().lower() in {"1", "true", "yes"}
        if not local_ready:
            raise RuntimeError(
                "local provider not configured. Set LOCAL_LLM_CONFIGURED=1 and "
                "LOCAL_LLM_ENDPOINT or OLLAMA_BASE_URL with your fine-tuned model."
            )
        if endpoint:
            from pipeline.translate_summarize import SYSTEM_PROMPT
            from pipeline.utils import extract_json

            response = requests.post(
                endpoint,
                json={
                    "model": model,
                    "system": SYSTEM_PROMPT.format(n=summary_sentences),
                    "title": title,
                    "body": body,
                    "summary_sentences": summary_sentences,
                },
                timeout=180,
            )
            response.raise_for_status()
            data = response.json()
            if all(key in data for key in ("translation", "summary_formal", "summary_casual")):
                return data
            return extract_json(data.get("text") or data.get("content") or "")
        if ollama_base:
            os.environ["LLM_PROVIDER"] = "local"
            os.environ["MODE"] = "local"
            os.environ["MODEL_NAME"] = model
            from pipeline.translate_summarize import translate_and_summarize

            return translate_and_summarize(text=body, title=title, summary_sentences=summary_sentences)
        raise RuntimeError("local provider not configured. Missing LOCAL_LLM_ENDPOINT or OLLAMA_BASE_URL.")

    raise RuntimeError(f"지원하지 않는 provider: {provider}")


def main() -> int:
    configure_stdio()
    parser = argparse.ArgumentParser(
        description="Backfill missing articles.translation / summary_formal / summary_casual fields."
    )
    parser.add_argument("--limit", type=int, default=1)
    parser.add_argument("--run", action="store_true", help="Actually update Supabase. Without this, no DB write occurs.")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--allow-large-run", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--source", type=str, default=None)
    parser.add_argument("--url-hash", type=str, default=None)
    parser.add_argument("--min-body-chars", type=int, default=800)
    parser.add_argument("--max-body-chars", type=int, default=12000)
    parser.add_argument("--repair-short-translation", action="store_true")
    parser.add_argument("--min-translation-chars", type=int, default=300)
    parser.add_argument(
        "--only-missing",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Only query rows with at least one missing AI output field. Default: true.",
    )
    parser.add_argument("--summary-sentences", type=int, default=3)
    parser.add_argument("--show-body-preview", action="store_true")
    parser.add_argument(
        "--provider",
        choices=("mock", "local", "openrouter", "gemini"),
        default="mock",
        help="Override LLM_PROVIDER for this run. Example: --provider openrouter",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="Override provider model for this run. OpenRouter uses OPENROUTER_TRANSLATION_MODEL.",
    )
    args = parser.parse_args()

    if args.dry_run:
        args.run = False

    if args.limit > 5 and not args.allow_large_run:
        raise SystemExit("--limit은 기본 최대 5입니다. 더 크게 실행하려면 --allow-large-run을 명시하세요.")

    provider = args.provider
    model = args.model or {
        "mock": "mock-static-v1",
        "openrouter": os.getenv("OPENROUTER_TRANSLATION_MODEL", "google/gemini-2.5-flash"),
        "gemini": os.getenv("GEMINI_TRANSLATION_MODEL", "gemini-2.5-flash"),
        "local": os.getenv("MODEL_NAME", "gemma4-e2b-samsun-lora"),
    }[provider]
    endpoint_label = {
        "mock": "mock",
        "openrouter": "openrouter",
        "gemini": "gemini-direct",
        "local": os.getenv("LOCAL_LLM_ENDPOINT") or os.getenv("OLLAMA_BASE_URL") or "local-not-configured",
    }[provider]

    sb = get_supabase_client()
    available_meta_fields = detect_ai_meta_fields(sb)
    rows = fetch_target_articles(
        sb=sb,
        limit=max(args.limit, 0),
        source=args.source,
        only_missing=args.only_missing,
        url_hash=args.url_hash,
        repair_short_translation=args.repair_short_translation,
        min_translation_chars=max(args.min_translation_chars, 1),
        available_meta_fields=available_meta_fields,
    )

    print(
        f"[backfill_ai] targets={len(rows)} limit={args.limit} "
        f"source={args.source or '*'} only_missing={args.only_missing} "
        f"overwrite={args.overwrite} run={args.run}"
        f" min_body_chars={args.min_body_chars} max_body_chars={args.max_body_chars}"
        f" repair_short_translation={args.repair_short_translation}"
        f" min_translation_chars={args.min_translation_chars}",
        flush=True,
    )
    print(
        f"[backfill_ai] provider={provider} model={model} "
        f"endpoint={endpoint_label} "
        f"ai_meta_fields={','.join(sorted(available_meta_fields)) or '(not migrated)'}",
        flush=True,
    )

    if not rows:
        return 0

    updated = 0
    skipped = 0
    failed = 0

    for index, row in enumerate(rows, 1):
        url_hash = row.get("url_hash") or ""
        title = (row.get("title_ko") or row.get("title") or "").strip()
        url = (row.get("url") or "").strip()
        print(f"\n[{index}/{len(rows)}] id={url_hash} title={title[:90]}", flush=True)
        print(f"  url={url}", flush=True)

        current_translation_len = len(str(row.get("translation") or "").strip())
        print(
            f"  current.translation_chars={current_translation_len} "
            f"summary_formal={not is_blank(row.get('summary_formal'))} "
            f"summary_casual={not is_blank(row.get('summary_casual'))}",
            flush=True,
        )

        if not args.overwrite and not needs_processing(
            row,
            repair_short_translation=args.repair_short_translation,
            min_translation_chars=max(args.min_translation_chars, 1),
        ):
            skipped += 1
            print("  skip=already has complete AI outputs", flush=True)
            continue

        body, body_source, quality_warning = get_article_body(
            row,
            min_body_chars=max(args.min_body_chars, 1),
            max_body_chars=max(args.max_body_chars, 1),
        )
        print(
            f"  body_ok={bool(body)} content_source={body_source} "
            f"content_chars={len(body)} body_quality_warning={quality_warning or '-'}",
            flush=True,
        )
        if args.show_body_preview and body:
            print(f"  body_preview={body[:300].replace(chr(10), ' ')}", flush=True)
        if not body:
            skipped += 1
            print("  update_ok=False reason=body unavailable", flush=True)
            continue

        if not args.run:
            print("  model_call=False run=False", flush=True)
            print("  update_ok=False reason=preview only; add --run to write DB", flush=True)
            continue

        try:
            generated = generate_outputs(
                provider=provider,
                model=model,
                title=row.get("title") or "",
                body=body,
                summary_sentences=args.summary_sentences,
            )
        except Exception as exc:
            failed += 1
            print(f"  update_ok=False reason=model failed: {exc}", flush=True)
            fail_payload: dict[str, Any] = {}
            if "ai_status" in available_meta_fields:
                fail_payload["ai_status"] = "failed"
            if "ai_provider" in available_meta_fields:
                fail_payload["ai_provider"] = provider
            if "ai_model" in available_meta_fields:
                fail_payload["ai_model"] = model
            if "ai_error" in available_meta_fields:
                fail_payload["ai_error"] = str(exc)[:1000]
            if fail_payload:
                try:
                    sb.table("articles").update(fail_payload).eq("url_hash", url_hash).execute()
                except Exception:
                    pass
            continue

        translation_len = len(str(generated.get("translation") or "").strip())
        if len(body) >= 800 and translation_len < max(args.min_translation_chars, 1):
            print(
                f"  WARNING short translation: body_chars={len(body)} "
                f"translation_chars={translation_len}",
                flush=True,
            )
            if "ai_status" in available_meta_fields:
                try:
                    status_payload: dict[str, Any] = {"ai_status": "failed"}
                    if "ai_provider" in available_meta_fields:
                        status_payload["ai_provider"] = provider
                    if "ai_model" in available_meta_fields:
                        status_payload["ai_model"] = model
                    if "ai_error" in available_meta_fields:
                        status_payload["ai_error"] = (
                            f"short translation: body_chars={len(body)} "
                            f"translation_chars={translation_len}"
                        )
                    sb.table("articles").update(status_payload).eq("url_hash", url_hash).execute()
                except Exception:
                    pass
            failed += 1
            print("  update_ok=False reason=short translation rejected", flush=True)
            continue

        payload = build_update_payload(
            row,
            generated,
            overwrite=args.overwrite,
            repair_short_translation=args.repair_short_translation,
            min_translation_chars=max(args.min_translation_chars, 1),
            provider=provider,
            model=model,
            body_source=body_source,
            body_chars=len(body),
            available_meta_fields=available_meta_fields,
            ai_status="completed",
        )
        print(f"  generated.translation={bool((generated.get('translation') or '').strip())}", flush=True)
        print(f"  generated.translation_chars={translation_len}", flush=True)
        print(f"  generated.summary_formal={bool((generated.get('summary_formal') or '').strip())}", flush=True)
        print(f"  generated.summary_casual={bool((generated.get('summary_casual') or '').strip())}", flush=True)

        if not payload:
            skipped += 1
            print("  update_ok=False reason=no non-empty generated values for missing fields", flush=True)
            continue

        print(f"  update_fields={','.join(payload.keys())}", flush=True)
        try:
            sb.table("articles").update(payload).eq("url_hash", url_hash).execute()
            updated += 1
            print("  update_ok=True", flush=True)
        except Exception as exc:
            failed += 1
            print(f"  update_ok=False reason=supabase update failed: {exc}", flush=True)

    print(f"\n[backfill_ai] updated={updated} skipped={skipped} failed={failed}", flush=True)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
