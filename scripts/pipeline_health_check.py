"""Pipeline freshness and AI-field health check.

Run:
  python scripts/pipeline_health_check.py

This is intentionally a thin alias around check_articles_health.py so the
operator-facing command name matches the RSS-to-Supabase pipeline concern.
"""

from __future__ import annotations

from check_articles_health import main


if __name__ == "__main__":
    raise SystemExit(main())
