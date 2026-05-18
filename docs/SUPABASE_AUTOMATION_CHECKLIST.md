# Supabase Automation Checklist

Use this checklist to enable scheduled Samsun News refresh without Railway, without GitHub Actions as the primary scheduler, and without rebuilding the `.ait` bundle for data updates.

## 0. Scope Check

- Runtime data source: Supabase only.
- Scheduler: Supabase Cron.
- HTTP control plane: Supabase Edge Function `refresh-articles`.
- Pipeline execution: trusted Python runner for `python main.py --limit <n> --summary-sentences 3`.
- Frontend behavior: the Apps in Toss `.ait` reads Supabase at runtime, so new articles/summaries appear without rebuilding the `.ait`.

Important: the current Edge Function queues refresh requests in `pipeline_refresh_requests`. It does not run the Python RSS/AI crawler inside Deno. Keep a trusted Python runner polling or processing queued rows.

## 1. Run The Queue Table SQL

In Supabase Dashboard, open `SQL Editor` -> `New query`, paste this SQL, and run it:

```sql
CREATE TABLE IF NOT EXISTS pipeline_refresh_requests (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  reason TEXT NOT NULL DEFAULT 'manual',
  requested_limit INT NOT NULL DEFAULT 10 CHECK (requested_limit > 0 AND requested_limit <= 100),
  status TEXT NOT NULL DEFAULT 'queued' CHECK (status IN ('queued', 'running', 'completed', 'failed')),
  requested_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  started_at TIMESTAMPTZ,
  finished_at TIMESTAMPTZ,
  error TEXT
);

CREATE INDEX IF NOT EXISTS idx_pipeline_refresh_requests_status_requested
  ON pipeline_refresh_requests (status, requested_at DESC);

ALTER TABLE pipeline_refresh_requests ENABLE ROW LEVEL SECURITY;
```

This is the same SQL as `backend/sql/create_pipeline_refresh_requests.sql`.

## 2. Deploy The Edge Function With Supabase CLI

From the repo root:

```bash
supabase login
supabase projects list
supabase link --project-ref <project-ref>
supabase secrets set REFRESH_SECRET=<long-random-string>
supabase secrets set SUPABASE_SERVICE_ROLE_KEY=<service-role-key>
supabase functions deploy refresh-articles --no-verify-jwt
supabase secrets list
```

For the known Samsun News Supabase URL `https://srdvlalyucbokdwfkmcf.supabase.co`, the project ref is `srdvlalyucbokdwfkmcf`:

```bash
supabase link --project-ref srdvlalyucbokdwfkmcf
```

Use `--no-verify-jwt` because this function performs its own shared-secret check with `Authorization: Bearer <REFRESH_SECRET>`. Do not put `REFRESH_SECRET` or the service role key in frontend env files.

## 3. Confirm Edge Function Secrets In Dashboard

In Supabase Dashboard:

1. Open `Edge Functions`.
2. Open `Secrets`.
3. Confirm these secrets exist:
   - `REFRESH_SECRET`
   - `SUPABASE_SERVICE_ROLE_KEY`
4. Do not add OpenRouter, Gemini, Google Fact Check, or service-role secrets to the `.ait` frontend.

## 4. Manually Invoke The Function

Replace placeholders and run:

```bash
curl -X POST "https://<project-ref>.supabase.co/functions/v1/refresh-articles" \
  -H "Authorization: Bearer <REFRESH_SECRET>" \
  -H "Content-Type: application/json" \
  -d "{\"reason\":\"manual\",\"limit\":10}"
```

Expected result:

```json
{
  "queued": true,
  "request": {
    "id": "...",
    "reason": "manual",
    "requested_limit": 10,
    "status": "queued",
    "requested_at": "..."
  }
}
```

Then verify the queue row:

```sql
select id, reason, requested_limit, status, requested_at
from pipeline_refresh_requests
order by requested_at desc
limit 5;
```

## 5. Enable Supabase Cron

Dashboard path:

1. Open Supabase Dashboard.
2. Go to `Integrations` -> `Cron`.
3. Create a new job.
4. Name it `refresh-samsun-news-hourly`.
5. Schedule it as hourly: `0 * * * *`.
6. Choose an HTTP request job if the UI offers that mode.
7. Set method: `POST`.
8. Set URL: `https://<project-ref>.supabase.co/functions/v1/refresh-articles`.
9. Add headers:
   - `Authorization: Bearer <REFRESH_SECRET>`
   - `Content-Type: application/json`
10. Set body:

```json
{"reason":"cron","limit":10}
```

If using SQL instead of the Dashboard UI, run:

```sql
select cron.schedule(
  'refresh-samsun-news-hourly',
  '0 * * * *',
  $$
  select net.http_post(
    url := 'https://<project-ref>.supabase.co/functions/v1/refresh-articles',
    headers := jsonb_build_object(
      'Authorization', 'Bearer <REFRESH_SECRET>',
      'Content-Type', 'application/json'
    ),
    body := jsonb_build_object('reason', 'cron', 'limit', 10)
  );
  $$
);
```

After saving, run the job once from the Cron dashboard if available, then confirm a new queued row appears in `pipeline_refresh_requests`.

## 6. Process The Queued Refresh

On the trusted Python runner with backend secrets set:

```bash
python main.py --check-env
python main.py --limit 10 --summary-sentences 3
python scripts/pipeline_health_check.py
```

Required runner env:

```text
SUPABASE_URL
SUPABASE_SERVICE_ROLE_KEY or SUPABASE_KEY or SUPABASE_ANON_KEY
LLM_PROVIDER=openrouter
EMBEDDING_PROVIDER=openrouter
OPENROUTER_API_KEY
```

Backfill any remaining AI gaps:

```bash
python scripts/backfill_article_ai_outputs.py --limit 5 --provider openrouter --run --summary-sentences 3
python scripts/pipeline_health_check.py
```

## 7. Verify The Frontend Updates

1. Run `python scripts/pipeline_health_check.py`.
2. Confirm `newest_published_at` and `articles_inserted_or_updated_last_24h` improved.
3. Open the existing Toss test app or local frontend.
4. Refresh/reopen the feed.

No `.ait` rebuild is needed. The bundle reads the latest Supabase `articles` rows through the anon key.
