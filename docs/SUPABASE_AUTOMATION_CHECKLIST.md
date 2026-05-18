# Supabase Automation Checklist

Use this checklist to enable scheduled Samsun News refresh without a custom app server and without rebuilding the `.ait` bundle for data updates.

## 0. What Supabase Can And Cannot Run

Supabase Edge Functions run TypeScript on the Deno-based Edge Runtime, not Python. The canonical repo pipeline is still:

```bash
python main.py --limit 10 --summary-sentences 3
```

That Python path uses Python-only dependencies such as `feedparser`, `requests`, `supabase-py`, optional `trafilatura`/`readability-lxml`, Google GenAI Python clients, OpenAI/OpenRouter clients, and optional local Ollama/GGUF paths. It is not realistic to run that exact pipeline inside hosted Supabase Edge Functions.

Hosted Edge Function limits also make the full Python-equivalent job a poor fit: current Supabase docs list 256 MB memory, 150s free-plan wall clock / 400s paid-plan wall clock, 2s CPU time per request, 150s request idle timeout, and 20 MB bundled function size.

Therefore there are three valid modes:

- **Fully automatic Supabase-only mode:** Supabase Cron calls the Edge Function with `mode=direct`. This runs a minimal TypeScript refresh path: fetch RSS, best-effort crawl body text, call OpenRouter or Gemini, and upsert Supabase `articles`.
- **Queue-only mode:** Supabase Cron calls the Edge Function with `mode=queue`. This only inserts into `pipeline_refresh_requests`; a trusted Python runner must process the queue.
- **Manual Python mode:** run `python main.py` directly for the full canonical pipeline.

Do not call queue-only mode "fully automatic" unless a separate runner is active.

## 1. Run The Queue Table SQL

Run this once in Supabase Dashboard -> `SQL Editor` -> `New query`:

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

Optional but recommended for richer tracking:

```text
backend/sql/add_pipeline_tracking_fields.sql
```

The direct Edge refresh detects optional columns before writing, so it can still run if the optional tracking migration is not applied.

## 2. Deploy The Edge Function

From the repo root:

```bash
supabase login
supabase projects list
supabase link --project-ref <project-ref>
supabase secrets set REFRESH_SECRET=<long-random-string>
supabase secrets set SUPABASE_SERVICE_ROLE_KEY=<service-role-key>
supabase secrets set EDGE_LLM_PROVIDER=openrouter
supabase secrets set OPENROUTER_API_KEY=<openrouter-api-key>
supabase secrets set OPENROUTER_TRANSLATION_MODEL=google/gemini-2.5-flash
supabase functions deploy refresh-articles --no-verify-jwt
supabase secrets list
```

For the known Samsun News Supabase URL `https://srdvlalyucbokdwfkmcf.supabase.co`, the project ref is:

```bash
supabase link --project-ref srdvlalyucbokdwfkmcf
```

Gemini alternative:

```bash
supabase secrets set EDGE_LLM_PROVIDER=gemini
supabase secrets set GEMINI_API_KEY=<gemini-api-key>
supabase secrets set GEMINI_TRANSLATION_MODEL=gemini-2.5-flash
```

Use `--no-verify-jwt` because this function performs its own shared-secret check with `Authorization: Bearer <REFRESH_SECRET>`.

## 3. Fully Automatic Mode: Supabase Cron Direct Refresh

This is the recommended Supabase-only production path for fresh articles.

Behavior:

- Cron invokes `refresh-articles` with `{"mode":"direct"}`.
- Edge Function fetches configured RSS feeds.
- Edge Function best-effort crawls article HTML and falls back to RSS summary.
- Edge Function calls OpenRouter or Gemini.
- Edge Function upserts Supabase `articles`.
- Edge Function writes a running/completed/failed row to `pipeline_refresh_requests`.
- Frontend `.ait` reads the new Supabase rows without rebuilding.

Limit:

- Direct mode clamps `limit` to at most `5` per invocation to stay inside hosted Edge limits. Use hourly or more frequent Cron instead of one large batch.
- This is not full Python feature parity. It does not run the complete Python fact-check/debate pipeline, local Ollama, or Python `trafilatura` extraction.

Manual direct test:

```bash
curl -X POST "https://<project-ref>.supabase.co/functions/v1/refresh-articles" \
  -H "Authorization: Bearer <REFRESH_SECRET>" \
  -H "Content-Type: application/json" \
  -d "{\"mode\":\"direct\",\"reason\":\"manual-direct\",\"limit\":3}"
```

Expected response shape:

```json
{
  "mode": "direct",
  "requested_limit": 3,
  "effective_limit": 3,
  "collected": 3,
  "saved": 3,
  "errors": [],
  "newest": {
    "published_at": "...",
    "collected_at": "..."
  }
}
```

Enable Cron in Dashboard:

1. Open Supabase Dashboard.
2. Go to `Integrations` -> `Cron`.
3. Create a new job.
4. Name it `refresh-samsun-news-direct-hourly`.
5. Schedule: `0 * * * *`.
6. Choose HTTP request job.
7. Method: `POST`.
8. URL: `https://<project-ref>.supabase.co/functions/v1/refresh-articles`.
9. Headers:
   - `Authorization: Bearer <REFRESH_SECRET>`
   - `Content-Type: application/json`
10. Body:

```json
{"mode":"direct","reason":"cron-direct","limit":3}
```

SQL alternative:

```sql
select cron.schedule(
  'refresh-samsun-news-direct-hourly',
  '0 * * * *',
  $$
  select net.http_post(
    url := 'https://<project-ref>.supabase.co/functions/v1/refresh-articles',
    headers := jsonb_build_object(
      'Authorization', 'Bearer <REFRESH_SECRET>',
      'Content-Type', 'application/json'
    ),
    body := jsonb_build_object('mode', 'direct', 'reason', 'cron-direct', 'limit', 3)
  );
  $$
);
```

Verify:

```sql
select id, reason, requested_limit, status, requested_at, started_at, finished_at, error
from pipeline_refresh_requests
order by requested_at desc
limit 10;

select title_ko, source, published_at, collected_at, summary_formal, summary_casual
from articles
order by collected_at desc
limit 10;
```

## 4. Queue-Only Mode

Use this only if you want Supabase Cron to enqueue work and a separate runner to execute the full Python pipeline.

Manual queue test:

```bash
curl -X POST "https://<project-ref>.supabase.co/functions/v1/refresh-articles" \
  -H "Authorization: Bearer <REFRESH_SECRET>" \
  -H "Content-Type: application/json" \
  -d "{\"mode\":\"queue\",\"reason\":\"manual-queue\",\"limit\":10}"
```

Expected response:

```json
{
  "mode": "queue",
  "queued": true,
  "request": {
    "id": "...",
    "reason": "manual-queue",
    "requested_limit": 10,
    "status": "queued",
    "requested_at": "..."
  }
}
```

Queue Cron body:

```json
{"mode":"queue","reason":"cron-queue","limit":10}
```

Then a trusted Python runner must run:

```bash
python main.py --check-env
python main.py --limit 10 --summary-sentences 3
python scripts/pipeline_health_check.py
```

Recommended trusted runner options for queue/full Python mode:

- Windows Task Scheduler on a trusted machine.
- A small VM or always-on desktop using Task Scheduler/systemd.
- GitHub Actions scheduled workflow only as a non-server fallback, not as the primary scheduler for this project.

Windows Task Scheduler example:

```powershell
$repo = "C:\samsun_news\samsun_news_main_final"
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-NoProfile -ExecutionPolicy Bypass -Command `"cd '$repo'; .\.venv\Scripts\python.exe main.py --limit 10 --summary-sentences 3; .\.venv\Scripts\python.exe scripts\pipeline_health_check.py`""
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).Date -RepetitionInterval (New-TimeSpan -Hours 1)
Register-ScheduledTask -TaskName "SamsunNewsPythonRefresh" -Action $action -Trigger $trigger -Description "Run Samsun News canonical Python refresh hourly"
```

## 5. Manual Python Mode

Use this for one-off full canonical refreshes and backfills.

```bash
python main.py --check-env
python main.py --limit 10 --summary-sentences 3
python scripts/backfill_article_ai_outputs.py --limit 5 --provider openrouter --run --summary-sentences 3
python scripts/pipeline_health_check.py
```

Required local env:

```text
SUPABASE_URL
SUPABASE_SERVICE_ROLE_KEY or SUPABASE_KEY or SUPABASE_ANON_KEY
LLM_PROVIDER=openrouter
EMBEDDING_PROVIDER=openrouter
OPENROUTER_API_KEY
```

## 6. Verify The `.ait` Frontend

The `.ait` app reads Supabase directly at runtime.

1. Confirm Cron/direct mode inserted or updated rows in Supabase.
2. Open the existing Toss test app or local frontend.
3. Refresh/reopen the feed.

No `.ait` rebuild is needed for new articles or updated AI fields.
