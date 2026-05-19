-- Final Samsun News demo patch.
-- Apply manually in Supabase SQL Editor before the final Apps in Toss test upload.
-- This file is idempotent and intentionally uses public.articles only.

CREATE EXTENSION IF NOT EXISTS vector;

ALTER TABLE public.articles ADD COLUMN IF NOT EXISTS embedding vector(1024);
ALTER TABLE public.articles ADD COLUMN IF NOT EXISTS is_hidden boolean DEFAULT false;
ALTER TABLE public.articles ADD COLUMN IF NOT EXISTS is_demo boolean DEFAULT false;
ALTER TABLE public.articles ADD COLUMN IF NOT EXISTS demo_visible boolean DEFAULT false;
ALTER TABLE public.articles ADD COLUMN IF NOT EXISTS demo_priority integer DEFAULT 0;
ALTER TABLE public.articles ADD COLUMN IF NOT EXISTS source_url text;
ALTER TABLE public.articles ADD COLUMN IF NOT EXISTS original_url text;
ALTER TABLE public.articles ADD COLUMN IF NOT EXISTS fact_status text;
ALTER TABLE public.articles ADD COLUMN IF NOT EXISTS fact_confidence double precision;
ALTER TABLE public.articles ADD COLUMN IF NOT EXISTS fact_reason text;
ALTER TABLE public.articles ADD COLUMN IF NOT EXISTS fact_insight text;
ALTER TABLE public.articles ADD COLUMN IF NOT EXISTS hitl_required boolean DEFAULT false;

CREATE TABLE IF NOT EXISTS public.users (
  user_id text PRIMARY KEY,
  interest_tags text[] DEFAULT '{}',
  user_vector vector(1024),
  last_seen_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

ALTER TABLE public.users ADD COLUMN IF NOT EXISTS interest_tags text[] DEFAULT '{}';
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS user_vector vector(1024);
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS last_seen_at timestamptz DEFAULT now();
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS updated_at timestamptz DEFAULT now();

CREATE TABLE IF NOT EXISTS public.user_logs (
  id bigserial PRIMARY KEY,
  user_id text NOT NULL,
  url_hash text NOT NULL REFERENCES public.articles(url_hash) ON DELETE CASCADE,
  action text DEFAULT 'view',
  created_at timestamptz DEFAULT now()
);

-- Index creation is intentionally not included here.
-- Supabase free-tier projects may fail vector index creation with:
--   ERROR 54000: memory required is 41 MB, maintenance_work_mem is 32 MB
-- For the final demo's small visible dataset, the RPC below works without a vector index.
-- Optional indexes live in backend/sql/optional_pgvector_indexes.sql.

-- Existing match_articles functions may have a different RETURNS TABLE shape.
-- PostgreSQL cannot CREATE OR REPLACE a function when OUT parameters change,
-- so drop only the RPC signatures first. Data tables are not touched.
DROP FUNCTION IF EXISTS public.match_articles(vector, integer, character varying);
DROP FUNCTION IF EXISTS public.match_articles(vector, integer, varchar);
DROP FUNCTION IF EXISTS public.match_articles(vector, int, varchar);
DROP FUNCTION IF EXISTS public.match_articles(vector, integer);
DROP FUNCTION IF EXISTS public.match_articles(vector, int);

CREATE OR REPLACE FUNCTION public.match_articles(
  query_vector vector(1024),
  top_k int DEFAULT 10,
  filter_category varchar DEFAULT NULL
)
RETURNS TABLE (
  url_hash varchar,
  url text,
  source_url text,
  original_url text,
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
  credibility_score double precision,
  fact_label varchar,
  fact_status text,
  fact_confidence double precision,
  fact_reason text,
  fact_insight text,
  similarity double precision
)
LANGUAGE sql
STABLE
AS $$
  SELECT
    a.url_hash,
    a.url,
    COALESCE(a.source_url, a.url) AS source_url,
    COALESCE(a.original_url, a.source_url, a.url) AS original_url,
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
    a.fact_status,
    a.fact_confidence,
    a.fact_reason,
    a.fact_insight,
    (1 - (a.embedding <=> query_vector))::double precision AS similarity
  FROM public.articles a
  WHERE (filter_category IS NULL OR a.category = filter_category)
    AND a.embedding IS NOT NULL
    AND COALESCE(a.is_hidden, false) = false
    AND COALESCE(a.is_demo, false) = false
    AND COALESCE(a.demo_visible, true) = true
    AND COALESCE(a.source, '') <> 'DEMO'
    AND COALESCE(a.title, '') NOT ILIKE '%DEMO%'
    AND COALESCE(a.title_ko, '') NOT ILIKE '%DEMO%'
    AND COALESCE(a.title_ko, '') NOT ILIKE '%시연용%'
    AND COALESCE(a.title_ko, '') <> ''
    AND COALESCE(a.translation, '') <> ''
    AND (COALESCE(a.summary_formal, '') <> '' OR COALESCE(a.summary_casual, '') <> '')
  ORDER BY a.embedding <=> query_vector, a.published_at DESC NULLS LAST
  LIMIT GREATEST(top_k, 1);
$$;

CREATE OR REPLACE FUNCTION public.blend_vectors_1024(
  p_base vector(1024),
  p_clicked vector(1024),
  p_base_weight double precision DEFAULT 0.6,
  p_clicked_weight double precision DEFAULT 0.4
)
RETURNS vector(1024)
LANGUAGE sql
IMMUTABLE
AS $$
  SELECT CASE
    WHEN p_clicked IS NULL THEN p_base
    WHEN p_base IS NULL THEN p_clicked
    ELSE (
      SELECT (
        '[' || string_agg(
          ((base_vals.val::double precision * p_base_weight)
            + (clicked_vals.val::double precision * p_clicked_weight))::text,
          ',' ORDER BY base_vals.ord
        ) || ']'
      )::vector(1024)
      FROM unnest(string_to_array(trim(both '[]' from p_base::text), ',')) WITH ORDINALITY AS base_vals(val, ord)
      JOIN unnest(string_to_array(trim(both '[]' from p_clicked::text), ',')) WITH ORDINALITY AS clicked_vals(val, ord)
        ON base_vals.ord = clicked_vals.ord
    )
  END;
$$;

CREATE OR REPLACE FUNCTION public.record_article_view(
  p_user_id text,
  p_url_hash text
)
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
  clicked_vector vector(1024);
  existing_vector vector(1024);
BEGIN
  INSERT INTO public.users(user_id, last_seen_at, updated_at)
  VALUES (p_user_id, now(), now())
  ON CONFLICT (user_id) DO UPDATE
    SET last_seen_at = now(), updated_at = now();

  INSERT INTO public.user_logs(user_id, url_hash, action, created_at)
  VALUES (p_user_id, p_url_hash, 'view', now());

  SELECT embedding INTO clicked_vector
  FROM public.articles
  WHERE url_hash = p_url_hash;

  IF clicked_vector IS NULL THEN
    RETURN;
  END IF;

  SELECT user_vector INTO existing_vector
  FROM public.users
  WHERE user_id = p_user_id;

  UPDATE public.users
  SET user_vector = CASE
      WHEN existing_vector IS NULL THEN clicked_vector
      ELSE public.blend_vectors_1024(existing_vector, clicked_vector, 0.6, 0.4)
    END,
    last_seen_at = now(),
    updated_at = now()
  WHERE user_id = p_user_id;
END;
$$;

CREATE OR REPLACE FUNCTION public.save_user_interests(
  p_user_id text,
  p_interest_tags text[]
)
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
  INSERT INTO public.users(user_id, interest_tags, last_seen_at, updated_at)
  VALUES (p_user_id, COALESCE(p_interest_tags, '{}'), now(), now())
  ON CONFLICT (user_id) DO UPDATE
    SET interest_tags = COALESCE(p_interest_tags, public.users.interest_tags),
        last_seen_at = now(),
        updated_at = now();
END;
$$;

GRANT EXECUTE ON FUNCTION public.match_articles(vector, int, varchar) TO anon, authenticated;
GRANT EXECUTE ON FUNCTION public.blend_vectors_1024(vector, vector, double precision, double precision) TO anon, authenticated;
GRANT EXECUTE ON FUNCTION public.record_article_view(text, text) TO anon, authenticated;
GRANT EXECUTE ON FUNCTION public.save_user_interests(text, text[]) TO anon, authenticated;
