-- Optional performance indexes for Samsun News.
--
-- Do NOT run this file for the final presentation if Supabase reports:
--   ERROR 54000: memory required is 41 MB, maintenance_work_mem is 32 MB
--
-- The final demo can run with backend/sql/final_demo_supabase_patch.sql only.
-- These indexes are useful after moving to a larger Supabase plan or when the
-- article table grows enough that sequential vector scans become too slow.

CREATE EXTENSION IF NOT EXISTS vector;

-- Vector similarity index. ivfflat is lighter than hnsw, but can still exceed
-- Supabase free-tier maintenance_work_mem depending on table size.
CREATE INDEX IF NOT EXISTS idx_articles_embedding
  ON public.articles USING ivfflat (embedding vector_cosine_ops)
  WITH (lists = 100);

-- Non-vector helper indexes. These are usually cheap, but remain optional so
-- the main final patch stays free-tier safe.
CREATE INDEX IF NOT EXISTS idx_articles_demo_visibility
  ON public.articles (is_hidden, is_demo, demo_visible, published_at DESC);

CREATE INDEX IF NOT EXISTS idx_users_last_seen_at
  ON public.users(last_seen_at DESC);

CREATE INDEX IF NOT EXISTS idx_user_logs_user_id_created_at
  ON public.user_logs(user_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_user_logs_url_hash
  ON public.user_logs(url_hash);
