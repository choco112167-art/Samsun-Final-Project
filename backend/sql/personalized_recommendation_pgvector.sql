-- Personalized recommendation support for the Apps in Toss demo.
-- Run in Supabase SQL Editor after enabling pgvector.
--
-- Default production path:
--   1) frontend stores onboarding interests in users.interest_tags
--   2) frontend records article views in user_logs
--   3) clicked article embeddings blend into users.user_vector
--   4) match_articles returns visible, complete articles by cosine similarity

CREATE EXTENSION IF NOT EXISTS vector;

ALTER TABLE articles ADD COLUMN IF NOT EXISTS embedding vector(1024);
ALTER TABLE articles ADD COLUMN IF NOT EXISTS is_hidden boolean DEFAULT false;
ALTER TABLE articles ADD COLUMN IF NOT EXISTS is_demo boolean DEFAULT false;
ALTER TABLE articles ADD COLUMN IF NOT EXISTS demo_visible boolean DEFAULT true;
ALTER TABLE articles ADD COLUMN IF NOT EXISTS source_url text;

CREATE TABLE IF NOT EXISTS users (
  user_id text PRIMARY KEY,
  interest_tags text[] DEFAULT '{}',
  user_vector vector(1024),
  last_seen_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

ALTER TABLE users ADD COLUMN IF NOT EXISTS interest_tags text[] DEFAULT '{}';
ALTER TABLE users ADD COLUMN IF NOT EXISTS user_vector vector(1024);
ALTER TABLE users ADD COLUMN IF NOT EXISTS last_seen_at timestamptz DEFAULT now();
ALTER TABLE users ADD COLUMN IF NOT EXISTS updated_at timestamptz DEFAULT now();

CREATE TABLE IF NOT EXISTS user_logs (
  id bigserial PRIMARY KEY,
  user_id text NOT NULL,
  url_hash text NOT NULL REFERENCES articles(url_hash) ON DELETE CASCADE,
  action text DEFAULT 'view',
  created_at timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_articles_embedding
  ON articles USING ivfflat (embedding vector_cosine_ops)
  WITH (lists = 100);
CREATE INDEX IF NOT EXISTS idx_users_last_seen_at ON users(last_seen_at DESC);
CREATE INDEX IF NOT EXISTS idx_user_logs_user_id_created_at ON user_logs(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_user_logs_url_hash ON user_logs(url_hash);

CREATE OR REPLACE FUNCTION match_articles(
  query_vector vector(1024),
  top_k int DEFAULT 10,
  filter_category varchar DEFAULT NULL
)
RETURNS TABLE (
  url_hash varchar,
  url text,
  source_url text,
  title text,
  title_ko text,
  source varchar,
  source_type varchar,
  category varchar,
  country varchar,
  keywords text[],
  published_at timestamptz,
  collected_at timestamptz,
  content text,
  translation text,
  summary_formal text,
  summary_casual text,
  credibility_score float,
  fact_label varchar,
  similarity float
)
LANGUAGE sql STABLE AS $$
  SELECT
    a.url_hash,
    a.url,
    COALESCE(a.source_url, a.url) AS source_url,
    a.title,
    a.title_ko,
    a.source,
    a.source_type,
    a.category,
    a.country,
    a.keywords,
    a.published_at,
    a.collected_at,
    a.content,
    a.translation,
    a.summary_formal,
    a.summary_casual,
    a.credibility_score,
    a.fact_label,
    (1 - (a.embedding <=> query_vector))::float AS similarity
  FROM articles a
  WHERE (filter_category IS NULL OR a.category = filter_category)
    AND a.embedding IS NOT NULL
    AND COALESCE(a.is_hidden, false) = false
    AND COALESCE(a.is_demo, false) = false
    AND COALESCE(a.demo_visible, true) = true
    AND COALESCE(a.source, '') <> 'DEMO'
    AND COALESCE(a.title_ko, '') <> ''
    AND COALESCE(a.translation, '') <> ''
    AND (COALESCE(a.summary_formal, '') <> '' OR COALESCE(a.summary_casual, '') <> '')
    AND COALESCE(a.title, '') NOT ILIKE '%DEMO%'
    AND COALESCE(a.title_ko, '') NOT ILIKE '%시연용%'
  ORDER BY a.embedding <=> query_vector
  LIMIT GREATEST(top_k, 1);
$$;

CREATE OR REPLACE FUNCTION record_article_view(
  p_user_id text,
  p_url_hash text
)
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER AS $$
DECLARE
  clicked_vector vector(1024);
  existing_vector vector(1024);
BEGIN
  INSERT INTO users(user_id, last_seen_at, updated_at)
  VALUES (p_user_id, now(), now())
  ON CONFLICT (user_id) DO UPDATE
    SET last_seen_at = now(), updated_at = now();

  INSERT INTO user_logs(user_id, url_hash, action, created_at)
  VALUES (p_user_id, p_url_hash, 'view', now());

  SELECT embedding INTO clicked_vector
  FROM articles
  WHERE url_hash = p_url_hash;

  IF clicked_vector IS NULL THEN
    RETURN;
  END IF;

  SELECT user_vector INTO existing_vector
  FROM users
  WHERE user_id = p_user_id;

  UPDATE users
  SET user_vector = CASE
      WHEN existing_vector IS NULL THEN clicked_vector
      ELSE existing_vector * 0.6 + clicked_vector * 0.4
    END,
    last_seen_at = now(),
    updated_at = now()
  WHERE user_id = p_user_id;
END;
$$;

GRANT EXECUTE ON FUNCTION match_articles(vector, int, varchar) TO anon, authenticated;
GRANT EXECUTE ON FUNCTION record_article_view(text, text) TO anon, authenticated;
