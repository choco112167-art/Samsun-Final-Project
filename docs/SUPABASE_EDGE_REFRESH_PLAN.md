# Supabase Scheduled Refresh Plan

Goal: refresh RSS-to-Supabase data without Railway and without putting service-role or LLM secrets in the frontend `.ait` bundle.

## Decision

The exact canonical pipeline cannot realistically run inside hosted Supabase Edge Functions because it is Python-based:

```bash
python main.py --limit 10 --summary-sentences 3
```

That path uses Python RSS parsing, Python article-processing modules, optional Python body extraction libraries, fact-check modules, Supabase Python client code, OpenRouter/Gemini Python clients, and optional local Ollama/GGUF paths.

Supabase Edge Functions are TypeScript/Deno functions with hosted runtime limits. Supabase docs currently list 256 MB memory, 150s free-plan / 400s paid-plan wall-clock duration, 2s CPU time per request, 150s request idle timeout, and 20 MB bundled function size. This is appropriate for small orchestration jobs and small AI calls, not for a full Python crawler/fact-check/backfill pipeline.

## Implemented Modes

The `refresh-articles` Edge Function now supports two modes.

### 1. Fully Automatic Direct Mode

Request body:

```json
{"mode":"direct","reason":"cron-direct","limit":3}
```

This is the Supabase-only automatic mode. It:

- fetches RSS feeds in TypeScript,
- best-effort crawls article body text with `fetch`,
- calls OpenRouter or Gemini,
- upserts Supabase `articles`,
- records status in `pipeline_refresh_requests`,
- returns freshness/result JSON.

Direct mode clamps `limit` to at most `5` per invocation to stay within hosted Edge limits.

This mode is not full Python feature parity. It does not run local Ollama, Python `trafilatura`, the complete Python fact-check debate pipeline, or embedding generation.

### 2. Queue-Only Mode

Request body:

```json
{"mode":"queue","reason":"cron-queue","limit":10}
```

This only inserts a queued row into `pipeline_refresh_requests`. A trusted runner still needs to run:

```bash
python main.py --limit 10 --summary-sentences 3
```

Use queue-only mode when you want the full canonical Python pipeline and have a non-Railway runner.

## Deploy

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
```

Gemini instead of OpenRouter:

```bash
supabase secrets set EDGE_LLM_PROVIDER=gemini
supabase secrets set GEMINI_API_KEY=<gemini-api-key>
supabase secrets set GEMINI_TRANSLATION_MODEL=gemini-2.5-flash
```

## Manual Direct Invoke

```bash
curl -X POST "https://<project-ref>.supabase.co/functions/v1/refresh-articles" \
  -H "Authorization: Bearer <REFRESH_SECRET>" \
  -H "Content-Type: application/json" \
  -d "{\"mode\":\"direct\",\"reason\":\"manual-direct\",\"limit\":3}"
```

## Supabase Cron Direct Mode

Dashboard Cron body:

```json
{"mode":"direct","reason":"cron-direct","limit":3}
```

SQL Cron alternative:

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

## Non-Railway Full Pipeline Alternative

If full Python feature parity is required, keep Supabase Cron in queue mode and run a non-Railway trusted runner:

- Windows Task Scheduler on the demo/ops machine,
- a small VM with systemd timer,
- GitHub Actions scheduled workflow only as a fallback non-server runner, not the primary scheduler.

Railway is not part of this plan.
