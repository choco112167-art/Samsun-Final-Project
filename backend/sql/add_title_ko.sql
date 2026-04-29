-- ============================================================
-- 마이그레이션: articles.title_ko (한국어 헤드라인)
-- Supabase Dashboard → SQL Editor 에서 실행하세요.
--
-- 저장 규약:
--   title       원문 영어 헤드라인 (RSS)
--   title_ko    번역 한국어 제목 (nullable)
--
-- title_en 컬럼은 제거된 상태라면 backend/sql/drop_title_en.sql 참고.
-- ============================================================

ALTER TABLE articles ADD COLUMN IF NOT EXISTS title_ko TEXT;

COMMENT ON COLUMN articles.title IS '원문 영어 헤드라인 (RSS)';
COMMENT ON COLUMN articles.title_ko IS '번역 한국어 제목 (nullable)';

CREATE INDEX IF NOT EXISTS idx_articles_title_ko_trgm
    ON articles USING gin (title_ko gin_trgm_ops);


-- ── match_articles (피드 RAG RPC): 한국어 제목 필드 포함 ─────────────────
CREATE OR REPLACE FUNCTION match_articles(
    query_vector VECTOR(1024),
    top_k        INT DEFAULT 10,
    filter_category VARCHAR DEFAULT NULL
)
RETURNS TABLE (
    url_hash          VARCHAR,
    url               TEXT,
    title             TEXT,
    title_ko          TEXT,
    source            VARCHAR,
    category          VARCHAR,
    keywords          TEXT[],
    published_at      TIMESTAMPTZ,
    translation       TEXT,
    summary_formal    TEXT,
    summary_casual    TEXT,
    credibility_score FLOAT,
    fact_label        VARCHAR,
    similarity        FLOAT
)
LANGUAGE sql STABLE AS $$
    SELECT
        a.url_hash,
        a.url,
        a.title,
        a.title_ko,
        a.source,
        a.category,
        a.keywords,
        a.published_at,
        a.translation,
        a.summary_formal,
        a.summary_casual,
        a.credibility_score,
        a.fact_label,
        1 - (a.embedding <=> query_vector) AS similarity
    FROM articles a
    WHERE
        (filter_category IS NULL OR a.category = filter_category)
        AND a.embedding IS NOT NULL
    ORDER BY a.embedding <=> query_vector
    LIMIT top_k;
$$;


-- ── match_articles_since (부재 알림 최적화 RPC가 있는 경우) ────────────────
CREATE OR REPLACE FUNCTION match_articles_since(
    query_vector VECTOR(1024),
    since_date   TIMESTAMPTZ,
    top_k        INT DEFAULT 10
)
RETURNS TABLE (
    url_hash          VARCHAR,
    url               TEXT,
    title             TEXT,
    title_ko          TEXT,
    source            VARCHAR,
    category          VARCHAR,
    keywords          TEXT[],
    published_at      TIMESTAMPTZ,
    translation       TEXT,
    summary_formal    TEXT,
    summary_casual    TEXT,
    credibility_score FLOAT,
    fact_label        VARCHAR,
    similarity        FLOAT
)
LANGUAGE sql STABLE AS $$
    SELECT
        a.url_hash,
        a.url,
        a.title,
        a.title_ko,
        a.source,
        a.category,
        a.keywords,
        a.published_at,
        a.translation,
        a.summary_formal,
        a.summary_casual,
        a.credibility_score,
        a.fact_label,
        (1 - (a.embedding <=> query_vector))::FLOAT AS similarity
    FROM articles a
    WHERE a.embedding IS NOT NULL
      AND a.published_at >= since_date
    ORDER BY a.embedding <=> query_vector
    LIMIT top_k;
$$;


-- ── hybrid_search_articles: 제목 한국어 필드 검색 반영 ───────────────────────
CREATE OR REPLACE FUNCTION hybrid_search_articles(
    query_text      TEXT,
    query_vector    VECTOR(1024),
    top_k           INT DEFAULT 15,
    filter_category VARCHAR DEFAULT NULL
)
RETURNS TABLE (
    url_hash          VARCHAR,
    url               TEXT,
    title             TEXT,
    title_ko          TEXT,
    source            VARCHAR,
    source_type       VARCHAR,
    category          VARCHAR,
    keywords          TEXT[],
    published_at      TIMESTAMPTZ,
    translation       TEXT,
    summary_formal    TEXT,
    summary_casual    TEXT,
    credibility_score FLOAT,
    fact_label        VARCHAR,
    similarity        FLOAT
)
LANGUAGE sql STABLE AS $$
    WITH
    vec_ranked AS (
        SELECT
            a.url_hash,
            ROW_NUMBER() OVER (ORDER BY a.embedding <=> query_vector) AS rnk,
            (1 - (a.embedding <=> query_vector))::FLOAT AS vec_sim
        FROM articles a
        WHERE
            (filter_category IS NULL OR a.category = filter_category)
            AND a.embedding IS NOT NULL
        ORDER BY a.embedding <=> query_vector
        LIMIT 60
    ),
    kw_ranked AS (
        SELECT
            a.url_hash,
            ROW_NUMBER() OVER (
                ORDER BY GREATEST(
                    word_similarity(query_text, COALESCE(a.title, '')),
                    word_similarity(query_text, COALESCE(a.title_ko, '')),
                    word_similarity(query_text, COALESCE(a.translation, '')),
                    similarity(query_text, COALESCE(a.title, '')),
                    similarity(query_text, COALESCE(a.title_ko, ''))
                ) DESC
            ) AS rnk
        FROM articles a
        WHERE
            (filter_category IS NULL OR a.category = filter_category)
            AND (
                COALESCE(a.title, '')       ILIKE '%' || query_text || '%'
                OR COALESCE(a.title_ko, '') ILIKE '%' || query_text || '%'
                OR COALESCE(a.translation, '') ILIKE '%' || query_text || '%'
                OR word_similarity(query_text, COALESCE(a.title, ''))                  > 0.15
                OR word_similarity(query_text, COALESCE(a.title_ko, ''))               > 0.15
                OR word_similarity(query_text, COALESCE(a.translation, ''))             > 0.15
                OR similarity(query_text, COALESCE(a.title, ''))                       > 0.10
                OR similarity(query_text, COALESCE(a.title_ko, ''))                    > 0.10
            )
        LIMIT 60
    ),
    fused AS (
        SELECT
            COALESCE(v.url_hash, k.url_hash)                          AS url_hash,
            COALESCE(1.0 / (60 + v.rnk), 0.0)
                + COALESCE(1.0 / (60 + k.rnk), 0.0)                  AS rrf_score,
            COALESCE(v.vec_sim, 0.0)                                  AS vec_sim
        FROM vec_ranked v
        FULL OUTER JOIN kw_ranked k ON v.url_hash = k.url_hash
    )
    SELECT
        a.url_hash,
        a.url,
        a.title,
        a.title_ko,
        a.source,
        a.source_type,
        a.category,
        a.keywords,
        a.published_at,
        a.translation,
        a.summary_formal,
        a.summary_casual,
        a.credibility_score,
        a.fact_label,
        f.vec_sim AS similarity
    FROM fused f
    JOIN articles a ON a.url_hash = f.url_hash
    ORDER BY f.rrf_score DESC
    LIMIT top_k;
$$;
