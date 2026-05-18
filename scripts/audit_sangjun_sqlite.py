"""Audit the local Sangjun SQLite DB for the selected demo date range."""

from __future__ import annotations

import argparse
import sqlite3

from sangjun_sqlite_common import (
    DEFAULT_SINCE,
    DEFAULT_UNTIL,
    column_map,
    counter_for,
    detect_article_table,
    filter_rows,
    get_value,
    is_blank,
    parse_published_at,
    resolve_db_path,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db-path", default="samsun_345.db")
    parser.add_argument("--since", default=DEFAULT_SINCE)
    parser.add_argument("--until", default=DEFAULT_UNTIL)
    parser.add_argument("--include-missing-date", action="store_true")
    args = parser.parse_args()

    db_path = resolve_db_path(args.db_path)
    if not db_path.exists():
        print(f"[sangjun-audit] DB not found: {db_path}")
        return 2

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    table, columns = detect_article_table(conn)
    cmap = column_map(columns)
    rows = [dict(row) for row in conn.execute(f'SELECT rowid AS __rowid__, * FROM "{table}"')]
    selected = filter_rows(
        rows,
        cmap,
        since_text=args.since,
        until_text=args.until,
        include_missing_date=args.include_missing_date,
    )

    dates = [parse_published_at(get_value(row, cmap, "published_at")) for row in selected]
    dates = [date for date in dates if date is not None]

    def missing_count(logical: str) -> int:
        return sum(1 for row in selected if is_blank(get_value(row, cmap, logical)))

    rows_with_content = sum(1 for row in selected if not is_blank(get_value(row, cmap, "content")))

    print("[sangjun-audit]")
    print(f"db_path: {db_path}")
    print(f"table: {table}")
    print(f"detected_columns: {cmap}")
    print(f"date_range: {args.since}..{args.until}")
    print(f"total_articles_in_db: {len(rows)}")
    print(f"articles_in_selected_date_range: {len(selected)}")
    print(f"oldest_selected_published_at: {min(dates).isoformat() if dates else '(none)'}")
    print(f"newest_selected_published_at: {max(dates).isoformat() if dates else '(none)'}")
    print(f"rows_with_content_selected_range: {rows_with_content}")
    print(f"missing_title_ko_selected_range: {missing_count('title_ko')}")
    print(f"missing_translation_ko_selected_range: {missing_count('translation')}")
    print(f"missing_summary_ko_selected_range: {missing_count('summary_ko')}")
    print(f"missing_summary_formal_selected_range: {missing_count('summary_formal')}")
    print(f"missing_summary_casual_selected_range: {missing_count('summary_casual')}")

    print("source_counts_selected_range:")
    for source, count in counter_for(selected, cmap, "source").most_common(20):
        print(f"  {source}: {count}")

    print("category_counts_selected_range:")
    for category, count in counter_for(selected, cmap, "category").most_common(20):
        print(f"  {category}: {count}")

    print("sample_latest_rows_selected_range:")
    for row in selected[:10]:
        print(
            "  "
            f"published_at={get_value(row, cmap, 'published_at')} "
            f"source={get_value(row, cmap, 'source')} "
            f"category={get_value(row, cmap, 'category')} "
            f"title={(str(get_value(row, cmap, 'title')) or '')[:100]}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
