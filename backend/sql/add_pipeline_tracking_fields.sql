-- Optional pipeline observability fields for Samsun News articles.
-- Run in Supabase SQL Editor if per-article freshness/slang/fact status tracking is desired.

ALTER TABLE articles ADD COLUMN IF NOT EXISTS source_url TEXT;
ALTER TABLE articles ADD COLUMN IF NOT EXISTS crawled_text TEXT;
ALTER TABLE articles ADD COLUMN IF NOT EXISTS slang_terms TEXT[] DEFAULT '{}';
ALTER TABLE articles ADD COLUMN IF NOT EXISTS slang_processed_at TIMESTAMPTZ;
ALTER TABLE articles ADD COLUMN IF NOT EXISTS fact_status VARCHAR;
ALTER TABLE articles ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW();

CREATE OR REPLACE FUNCTION set_articles_updated_at()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_articles_updated_at ON articles;
CREATE TRIGGER trg_articles_updated_at
BEFORE UPDATE ON articles
FOR EACH ROW
EXECUTE FUNCTION set_articles_updated_at();

CREATE INDEX IF NOT EXISTS idx_articles_updated_at ON articles (updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_articles_slang_processed_at ON articles (slang_processed_at DESC);
CREATE INDEX IF NOT EXISTS idx_articles_fact_status ON articles (fact_status);
