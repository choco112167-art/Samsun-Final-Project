"""
Export Supabase demo-related tables before any cleanup.

Usage:
    python scripts/export_articles_backup.py
    python scripts/export_articles_backup.py --out backups/demo_backup.json
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from article_pipeline_common import configure_stdio, get_supabase_client


ROOT = Path(__file__).resolve().parents[1]


def fetch_all(sb, table: str) -> list[dict]:
    rows: list[dict] = []
    offset = 0
    page_size = 1000
    while True:
        result = sb.table(table).select("*").range(offset, offset + page_size - 1).execute()
        page = result.data or []
        rows.extend(page)
        if len(page) < page_size:
            return rows
        offset += page_size


def optional_fetch_all(sb, table: str) -> list[dict]:
    try:
        return fetch_all(sb, table)
    except Exception as exc:
        print(f"[backup] skipped {table}: {exc}")
        return []


def main() -> int:
    configure_stdio()
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=str, default="")
    args = parser.parse_args()

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = Path(args.out) if args.out else ROOT / "backups" / f"articles_backup_{timestamp}.json"
    out.parent.mkdir(parents=True, exist_ok=True)

    sb = get_supabase_client()
    payload = {
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "tables": {
            "articles": fetch_all(sb, "articles"),
            "fact_checks": optional_fetch_all(sb, "fact_checks"),
            "neologisms": optional_fetch_all(sb, "neologisms"),
        },
    }
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[backup] wrote {out}")
    print(f"[backup] articles={len(payload['tables']['articles'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
