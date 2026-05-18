# refresh-articles Edge Function Plan

This folder is a plan placeholder, not a deployed function.

The Samsun News refresh pipeline is currently Python (`python main.py`). A Supabase Edge Function can safely schedule or enqueue refresh work, but it should not pretend to run the Python crawler inside Deno.

See `docs/SUPABASE_EDGE_REFRESH_PLAN.md` for the manual invoke and Supabase Cron plan.
