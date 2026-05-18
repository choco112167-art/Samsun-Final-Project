# Supabase Scheduled Refresh Plan

Goal: refresh RSS-to-Supabase data without Railway and without putting service-role secrets in the frontend `.ait` bundle.

## Current Recommended Execution

The real pipeline is Python-based:

```bash
python main.py
```

It performs RSS collection, AI preflight, translation/summarization, fact labeling/checking, neologism tracking, and Supabase upsert. Run it from a trusted batch environment with repository secrets, not from the Toss WebView.

## Supabase Edge Function Role

Supabase Edge Functions are Deno/TypeScript, while this repository's crawler and AI pipeline are Python. The Edge Function should therefore be a lightweight scheduler/manual-trigger control plane, not a rewrite of the whole pipeline.

Function included in this repo:

```text
refresh-articles
```

Required behavior:

- Verify an `Authorization: Bearer <REFRESH_SECRET>` header.
- Insert a row into `pipeline_refresh_requests`.
- Return a JSON status for manual invocation.
- Never expose Supabase service role, OpenRouter, Gemini, Google Fact Check, or Ollama tunnel secrets to the frontend.

Apply the queue table first by pasting `backend/sql/create_pipeline_refresh_requests.sql` into the Supabase SQL Editor. If you move that SQL into a Supabase migration file later, `supabase db push` can apply it.

Deploy the function:

```bash
supabase functions deploy refresh-articles
supabase secrets set REFRESH_SECRET=<long-random-string>
supabase secrets set SUPABASE_SERVICE_ROLE_KEY=<service-role-key>
```

## Manual Invoke

```bash
curl -X POST "https://<project-ref>.functions.supabase.co/refresh-articles" \
  -H "Authorization: Bearer <REFRESH_SECRET>" \
  -H "Content-Type: application/json" \
  -d '{"reason":"manual"}'
```

## Supabase Cron

Use Supabase Cron to invoke the Edge Function on a fixed schedule, for example every hour:

```sql
select cron.schedule(
  'refresh-samsun-news-hourly',
  '0 * * * *',
  $$
  select net.http_post(
    url := 'https://<project-ref>.functions.supabase.co/refresh-articles',
    headers := jsonb_build_object(
      'Authorization', 'Bearer ' || current_setting('app.refresh_secret', true),
      'Content-Type', 'application/json'
    ),
    body := jsonb_build_object('reason', 'cron')
  );
  $$
);
```

## TODO Before Enabling

- Decide where the trusted Python worker runs. It can be a local machine, GitHub Actions workflow dispatch, or another non-Railway runner.
- Store `REFRESH_SECRET` and provider keys only in the trusted runner/Supabase secrets.
- After each run, execute `python scripts/pipeline_health_check.py`.

Railway is not part of this plan.
