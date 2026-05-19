# Samsun News Refresh Runbook

Use this runbook to manually refresh Supabase articles, backfill missing AI fields, and verify that the Apps in Toss frontend has fresh data.

## 1. Environment

Copy and fill the root env file:

```bash
copy .env.example .env
```

Required for `python main.py --limit 10` with the default cloud providers:

```text
SUPABASE_URL
SUPABASE_SERVICE_ROLE_KEY or SUPABASE_KEY or SUPABASE_ANON_KEY
LLM_PROVIDER=openrouter
EMBEDDING_PROVIDER=openrouter
OPENROUTER_API_KEY
```

Optional:

```text
GOOGLE_FC_API_KEY          # enables Google Fact Check lookup
GEMINI_API_KEY or GOOGLE_API_KEY
NEOLOGISM_PIPELINE_GEMINI=1 # enables new Gemini slang explanations during translation; off by default
```

Check the current environment without printing secrets:

```bash
python main.py --check-env
```

## 2. Manual Refresh

Safe small refresh:

```bash
python main.py --limit 10 --summary-sentences 3
```

Tiny smoke refresh:

```bash
python main.py --limit 2 --summary-sentences 3
```

Dry run without Supabase writes:

```bash
python main.py --limit 2 --dry-run
```

By default, articles that fail AI processing are skipped and are not saved with empty translation/summary fields. Use `--save-failed-rows` only for debugging.

## 3. Backfill Missing AI Fields

Preview the next missing row and body extraction:

```bash
python scripts/backfill_article_ai_outputs.py --limit 1 --provider openrouter --show-body-preview
```

Write one missing row:

```bash
python scripts/backfill_article_ai_outputs.py --limit 1 --provider openrouter --run --summary-sentences 3
```

Write up to five missing rows:

```bash
python scripts/backfill_article_ai_outputs.py --limit 5 --provider openrouter --run --summary-sentences 3
```

The backfill command fills:

- `translation`
- `summary_formal`
- `summary_casual`
- optional AI metadata columns if migrated
- optional `fact_status`, `slang_terms`, `neologism_terms`, `slang_processed_at` if migrated
- `neologisms` table candidate terms

Backfill does not use mock data unless `--provider mock` is explicitly selected. Do not use mock provider for final data.

## 4. Health Check

```bash
python scripts/pipeline_health_check.py
```

Check these lines:

```text
newest_published_at
newest_inserted_or_updated_at
articles_inserted_or_updated_last_24h
missing_translation
missing_summary_formal
missing_summary_casual
missing_fact_label_or_status
missing_slang_processing
```

## 5. Optional Supabase Tracking Migration

If you need per-article slang/fact/update tracking, run this SQL in Supabase SQL Editor:

```text
backend/sql/add_pipeline_tracking_fields.sql
```

If you want the Edge Function queue table, run:

```text
backend/sql/create_pipeline_refresh_requests.sql
```

## 6. Supabase Edge Function And Cron

Deploy:

```bash
supabase functions deploy refresh-articles --no-verify-jwt
supabase secrets set REFRESH_SECRET=<long-random-string>
supabase secrets set SUPABASE_SERVICE_ROLE_KEY=<service-role-key>
supabase secrets set EDGE_LLM_PROVIDER=openrouter
supabase secrets set OPENROUTER_API_KEY=<openrouter-api-key>
```

Fully automatic Supabase-only direct invoke:

```bash
curl -X POST "https://<project-ref>.supabase.co/functions/v1/refresh-articles" \
  -H "Authorization: Bearer <REFRESH_SECRET>" \
  -H "Content-Type: application/json" \
  -d '{"mode":"direct","reason":"manual-direct","limit":3}'
```

Queue-only invoke:

```bash
curl -X POST "https://<project-ref>.supabase.co/functions/v1/refresh-articles" \
  -H "Authorization: Bearer <REFRESH_SECRET>" \
  -H "Content-Type: application/json" \
  -d '{"mode":"queue","reason":"manual-queue","limit":10}'
```

Enable Supabase Cron using the direct-mode SQL in `docs/SUPABASE_EDGE_REFRESH_PLAN.md` or the one-page `docs/SUPABASE_AUTOMATION_CHECKLIST.md`.

Direct mode runs a minimal TypeScript RSS -> LLM -> Supabase refresh inside the Edge Function. Queue mode only queues refresh requests. For full Python feature parity, a trusted Python worker still needs to run:

```bash
python main.py --limit <requested_limit>
```

## 7. Verify Frontend Without Rebuilding `.ait`

The `.ait` app reads Supabase directly at runtime. After refresh/backfill:

1. Run `python scripts/pipeline_health_check.py`.
2. Open the existing Toss test app or local frontend.
3. Pull/reopen the home feed.

No `.ait` rebuild is needed for new articles or updated summaries because the bundle does not contain article data.
