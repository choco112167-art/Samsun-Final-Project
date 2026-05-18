-- Optional demo-readiness fields for Samsun News.
-- Run in Supabase SQL Editor before using hidden/demo visibility scripts.

ALTER TABLE articles ADD COLUMN IF NOT EXISTS is_hidden BOOLEAN DEFAULT FALSE;
ALTER TABLE articles ADD COLUMN IF NOT EXISTS is_demo BOOLEAN DEFAULT FALSE;
ALTER TABLE articles ADD COLUMN IF NOT EXISTS demo_visible BOOLEAN DEFAULT TRUE;
ALTER TABLE articles ADD COLUMN IF NOT EXISTS demo_priority INTEGER;
ALTER TABLE articles ADD COLUMN IF NOT EXISTS fact_status TEXT;
ALTER TABLE articles ADD COLUMN IF NOT EXISTS fact_confidence NUMERIC;
ALTER TABLE articles ADD COLUMN IF NOT EXISTS hitl_required BOOLEAN DEFAULT FALSE;

CREATE INDEX IF NOT EXISTS idx_articles_is_hidden ON articles (is_hidden);
CREATE INDEX IF NOT EXISTS idx_articles_is_demo ON articles (is_demo);
CREATE INDEX IF NOT EXISTS idx_articles_demo_visible ON articles (demo_visible);
CREATE INDEX IF NOT EXISTS idx_articles_demo_priority ON articles (demo_priority);
CREATE INDEX IF NOT EXISTS idx_articles_hitl_required ON articles (hitl_required);
