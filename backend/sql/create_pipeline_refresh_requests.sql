-- Queue table used by the Supabase Edge Function refresh-articles.
-- A trusted Python worker can poll this table and run `python main.py --limit ...`.

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

-- No anon access. Use the service role from Edge Functions / trusted workers.
