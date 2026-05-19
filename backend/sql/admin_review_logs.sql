-- Optional local/admin Fact Review POC audit log.
-- This is not required for the Apps in Toss .ait user app.

CREATE TABLE IF NOT EXISTS public.admin_review_logs (
  id bigserial PRIMARY KEY,
  url_hash text NOT NULL,
  fact_label text NOT NULL,
  reviewer_note text,
  fact_insight text,
  created_at timestamptz DEFAULT now()
);

COMMENT ON TABLE public.admin_review_logs IS
  'Optional audit log for local FastAPI Fact Review / HITL POC. Not used by the Apps in Toss user app.';
