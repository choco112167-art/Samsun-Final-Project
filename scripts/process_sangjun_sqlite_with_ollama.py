"""Process selected Sangjun SQLite articles with local Ollama samsun-gemma4.

Only rows in the requested date range are selected. The default range is
2026-05-01 through 2026-05-18 23:59:59.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
from datetime import datetime, timezone
from typing import Any

import requests

from article_pipeline_common import get_supabase_client, supported_article_columns
from sangjun_sqlite_common import (
    DEFAULT_SINCE,
    DEFAULT_UNTIL,
    WRITE_COLUMNS,
    column_map,
    detect_article_table,
    detect_neologisms,
    filter_rows,
    get_value,
    is_blank,
    json_dumps_ko,
    make_url_hash,
    parse_published_at,
    quote_ident,
    resolve_db_path,
    table_columns,
)


DEFAULT_MODEL = "samsun-gemma4"
OPTIONAL_SUPABASE_COLUMNS = (
    "source_url",
    "fact_status",
    "fact_confidence",
    "hitl_required",
    "neologism_terms",
    "slang_terms",
    "is_demo",
    "is_hidden",
    "demo_visible",
    "demo_priority",
    "ai_status",
    "ai_provider",
    "ai_model",
    "ai_generated_at",
    "content_source",
    "content_chars",
    "translation_chars",
    "updated_at",
)


def extract_json_object(text: str) -> dict[str, Any]:
    cleaned = (text or "").strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        obj = json.loads(cleaned)
        return obj if isinstance(obj, dict) else {}
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{.*\}", cleaned, flags=re.S)
    if match:
        try:
            obj = json.loads(match.group(0))
            return obj if isinstance(obj, dict) else {}
        except json.JSONDecodeError:
            return {}
    return {}


def normalize_fact_status(value: Any) -> str:
    raw = str(value or "").strip().upper()
    if raw in {"FACT", "VERIFIED", "TRUE"}:
        return "verified"
    if raw in {"RUMOR", "FALSE_RUMOR"}:
        return "rumor"
    if raw in {"HITL", "HITL_REQUIRED", "HUMAN_REVIEW_REQUIRED"}:
        return "hitl_required"
    return "unverified"


def fact_label_for_status(status: str) -> str:
    if status == "verified":
        return "VERIFIED"
    if status == "rumor":
        return "RUMOR"
    if status == "hitl_required":
        return "HITL_REQUIRED"
    return "UNVERIFIED"


def build_prompt(row: dict[str, Any], cmap: dict[str, str]) -> str:
    title = str(get_value(row, cmap, "title") or "")
    source = str(get_value(row, cmap, "source") or "")
    published_at = str(get_value(row, cmap, "published_at") or "")
    body = str(get_value(row, cmap, "content") or "")
    body = body[:8000]
    return f"""
You are a careful Korean AI news editor for Samsun News.
Process exactly one article. Do not invent facts.
If the article lacks enough evidence or is based on claims you cannot verify, mark it unverified.
If human review is needed, mark hitl_required.

Return ONLY valid JSON with these fields:
{{
  "title_ko": "natural Korean title",
  "translation": "full Korean translation of the article body, not a summary",
  "summary_ko": "3-line Korean summary",
  "summary_formal": "1. ...\\n2. ...\\n3. ...",
  "summary_casual": "1. ...\\n2. ...\\n3. ...",
  "fact_status": "verified | unverified | rumor | hitl_required",
  "fact_label": "VERIFIED | UNVERIFIED | RUMOR | HITL_REQUIRED",
  "fact_confidence": 0.0,
  "hitl_required": false,
  "neologism_terms": ["term"]
}}

Rules:
- Korean output first.
- Keep product/company names in English if common.
- For uncertainty, prefer unverified or hitl_required.
- Do not claim rumor/fake items are verified.

[SOURCE]
{source}

[PUBLISHED_AT]
{published_at}

[TITLE]
{title}

[BODY]
{body}
""".strip()


def call_ollama(prompt: str, model: str, base_url: str, timeout: int = 180) -> dict[str, Any]:
    response = requests.post(
        base_url.rstrip("/") + "/api/chat",
        json={
            "model": model,
            "messages": [
                {"role": "system", "content": "Return strict JSON only. You are a careful Korean AI news editor."},
                {"role": "user", "content": prompt},
            ],
            "stream": False,
            "options": {"temperature": 0.1, "num_predict": 4096},
        },
        timeout=timeout,
    )
    response.raise_for_status()
    body = response.json()
    content = ((body.get("message") or {}).get("content") or "").strip()
    parsed = extract_json_object(content)
    if not parsed:
        raise RuntimeError("Ollama response did not contain valid JSON")
    return parsed


def normalize_generated(data: dict[str, Any], row: dict[str, Any], cmap: dict[str, str]) -> dict[str, Any]:
    title_ko = str(data.get("title_ko") or data.get("title") or "").strip()
    translation = str(data.get("translation") or data.get("translation_ko") or "").strip()
    summary_formal = str(data.get("summary_formal") or data.get("summary_ko") or "").strip()
    summary_casual = str(data.get("summary_casual") or data.get("summary_ko") or "").strip()
    summary_ko = str(data.get("summary_ko") or summary_formal).strip()
    status = normalize_fact_status(data.get("fact_status") or data.get("fact_label"))
    label = fact_label_for_status(status)
    try:
        confidence = float(data.get("fact_confidence") or 0.45)
    except (TypeError, ValueError):
        confidence = 0.45
    confidence = max(0.0, min(1.0, confidence))
    hitl_required = bool(data.get("hitl_required")) or status == "hitl_required"
    neo_terms = data.get("neologism_terms")
    if not isinstance(neo_terms, list):
        neo_terms = []
    haystack = " ".join(
        [
            str(get_value(row, cmap, "title") or ""),
            title_ko,
            translation,
            summary_formal,
            summary_casual,
        ]
    )
    neo_terms = sorted({str(term).strip() for term in [*neo_terms, *detect_neologisms(haystack)] if str(term).strip()})
    return {
        "title_ko": title_ko,
        "translation": translation,
        "translation_ko": translation,
        "summary_ko": summary_ko,
        "summary_formal": summary_formal,
        "summary_casual": summary_casual,
        "fact_status": status,
        "fact_label": label,
        "fact_confidence": confidence,
        "hitl_required": hitl_required,
        "neologism_terms": neo_terms,
    }


def row_needs_processing(row: dict[str, Any], cmap: dict[str, str]) -> bool:
    return any(
        is_blank(get_value(row, cmap, logical))
        for logical in ("title_ko", "translation", "summary_formal", "summary_casual", "fact_status")
    )


def ensure_sqlite_columns(conn: sqlite3.Connection, table: str) -> None:
    existing = set(table_columns(conn, table))
    for column, column_type in WRITE_COLUMNS.items():
        if column not in existing:
            conn.execute(f"ALTER TABLE {quote_ident(table)} ADD COLUMN {quote_ident(column)} {column_type}")
    conn.commit()


def write_sqlite(conn: sqlite3.Connection, table: str, rowid: Any, generated: dict[str, Any]) -> None:
    payload = {
        "title_ko": generated["title_ko"],
        "translation_ko": generated["translation"],
        "translation": generated["translation"],
        "summary_ko": generated["summary_ko"],
        "summary_formal": generated["summary_formal"],
        "summary_casual": generated["summary_casual"],
        "fact_status": generated["fact_status"],
        "fact_label": generated["fact_label"],
        "fact_confidence": generated["fact_confidence"],
        "hitl_required": 1 if generated["hitl_required"] else 0,
        "neologism_terms": json_dumps_ko(generated["neologism_terms"]),
        "processed_at": datetime.now(timezone.utc).isoformat(),
    }
    assignments = ", ".join(f"{quote_ident(key)} = ?" for key in payload)
    values = list(payload.values()) + [rowid]
    conn.execute(f"UPDATE {quote_ident(table)} SET {assignments} WHERE rowid = ?", values)
    conn.commit()


def to_supabase_payload(
    row: dict[str, Any],
    cmap: dict[str, str],
    generated: dict[str, Any],
    optional: set[str],
    demo_priority: int,
    model: str,
) -> dict[str, Any]:
    url = str(get_value(row, cmap, "url") or "").strip()
    if not url:
        url = f"sangjun-sqlite://{row.get('__rowid__')}"
    published = parse_published_at(get_value(row, cmap, "published_at"))
    content = str(get_value(row, cmap, "content") or "")
    payload: dict[str, Any] = {
        "url_hash": make_url_hash(url),
        "url": url,
        "title": str(get_value(row, cmap, "title") or generated["title_ko"] or ""),
        "title_ko": generated["title_ko"],
        "source": str(get_value(row, cmap, "source") or "SANGJUN"),
        "source_type": "media",
        "category": str(get_value(row, cmap, "category") or "AI 연구"),
        "country": str(get_value(row, cmap, "country") or "KR"),
        "keywords": ["sangjun", "may-2026", "AI"],
        "published_at": published.isoformat() if published else None,
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "content": content,
        "credibility_score": generated["fact_confidence"],
        "fact_label": generated["fact_label"],
        "translation": generated["translation"],
        "summary_formal": generated["summary_formal"],
        "summary_casual": generated["summary_casual"],
    }
    extras: dict[str, Any] = {
        "source_url": str(get_value(row, cmap, "source_url") or url),
        "fact_status": generated["fact_status"],
        "fact_confidence": generated["fact_confidence"],
        "hitl_required": generated["hitl_required"],
        "neologism_terms": generated["neologism_terms"],
        "slang_terms": generated["neologism_terms"],
        "is_demo": False,
        "is_hidden": False,
        "demo_visible": True,
        "demo_priority": demo_priority,
        "ai_status": "completed",
        "ai_provider": "ollama",
        "ai_model": model,
        "ai_generated_at": datetime.now(timezone.utc).isoformat(),
        "content_source": "sangjun_sqlite",
        "content_chars": len(content),
        "translation_chars": len(generated["translation"]),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    for key, value in extras.items():
        if key in optional:
            payload[key] = value
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db-path", default="samsun_345.db")
    parser.add_argument("--since", default=DEFAULT_SINCE)
    parser.add_argument("--until", default=DEFAULT_UNTIL)
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--write-sqlite", action="store_true")
    parser.add_argument("--upsert-supabase", action="store_true")
    parser.add_argument("--only-missing", action="store_true")
    parser.add_argument("--include-missing-date", action="store_true")
    parser.add_argument("--source", default="")
    parser.add_argument("--category", default="")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--ollama-base-url", default=os.getenv("OLLAMA_BASE_URL") or "http://localhost:11434")
    args = parser.parse_args()

    db_path = resolve_db_path(args.db_path)
    if not db_path.exists():
        print(f"[sangjun-process] DB not found: {db_path}")
        return 2
    if args.model != DEFAULT_MODEL:
        print(f"[sangjun-process] model_override={args.model} default_expected={DEFAULT_MODEL}")

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    table, columns = detect_article_table(conn)
    cmap = column_map(columns)
    rows = [dict(row) for row in conn.execute(f"SELECT rowid AS __rowid__, * FROM {quote_ident(table)}")]
    selected = filter_rows(
        rows,
        cmap,
        since_text=args.since,
        until_text=args.until,
        include_missing_date=args.include_missing_date,
        source=args.source,
        category=args.category,
    )
    if args.only_missing:
        selected = [row for row in selected if row_needs_processing(row, cmap)]
    selected = selected[max(args.offset, 0): max(args.offset, 0) + max(args.limit, 0)]

    print(
        f"[sangjun-process] table={table} selected={len(selected)} "
        f"range={args.since}..{args.until} model={args.model} dry_run={args.dry_run}"
    )
    for row in selected[:10]:
        print(
            "  "
            f"rowid={row.get('__rowid__')} published_at={get_value(row, cmap, 'published_at')} "
            f"source={get_value(row, cmap, 'source')} title={(str(get_value(row, cmap, 'title')) or '')[:90]}"
        )
    if args.dry_run:
        print("[sangjun-process] dry-run: no Ollama call, no SQLite write, no Supabase upsert.")
        return 0
    if not args.write_sqlite and not args.upsert_supabase:
        print("[sangjun-process] no write target selected. Add --write-sqlite and/or --upsert-supabase.")
        return 0

    if args.write_sqlite:
        ensure_sqlite_columns(conn, table)
        columns = table_columns(conn, table)
        cmap = column_map(columns)

    sb = None
    optional: set[str] = set()
    if args.upsert_supabase:
        sb = get_supabase_client()
        optional = supported_article_columns(sb, OPTIONAL_SUPABASE_COLUMNS)

    upsert_rows: list[dict[str, Any]] = []
    processed = 0
    for index, row in enumerate(selected, start=1):
        prompt = build_prompt(row, cmap)
        generated = normalize_generated(call_ollama(prompt, args.model, args.ollama_base_url), row, cmap)
        if args.write_sqlite:
            write_sqlite(conn, table, row["__rowid__"], generated)
        if args.upsert_supabase:
            upsert_rows.append(to_supabase_payload(row, cmap, generated, optional, demo_priority=index, model=args.model))
        processed += 1
        print(
            f"[sangjun-process] processed={processed}/{len(selected)} "
            f"fact={generated['fact_label']} title_ko={generated['title_ko'][:60]}"
        )

    if sb is not None and upsert_rows:
        sb.table("articles").upsert(upsert_rows, on_conflict="url_hash").execute()
        print(f"[sangjun-process] supabase_upserted={len(upsert_rows)}")
    print(f"[sangjun-process] done processed={processed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
