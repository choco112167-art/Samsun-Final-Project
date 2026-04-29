-- 부재 알림 (/absence-summary) 에 필요한 users 테이블 필드
-- Supabase SQL Editor 에서 실행 (기존 users 테이블이 있으면 ALTER 만 적용됨)

CREATE TABLE IF NOT EXISTS users (
    user_id       TEXT PRIMARY KEY,
    interest_tags TEXT[],
    user_vector   VECTOR(1024),
    last_seen_at  TIMESTAMPTZ
);

ALTER TABLE users ADD COLUMN IF NOT EXISTS last_seen_at TIMESTAMPTZ;

COMMENT ON COLUMN users.last_seen_at IS '마지막 앱 접속(또는 부재 알림 확인) 시각 — 부재 일수 계산';

-- 선택: 성능 최적화용 RPC (없으면 백엔드가 match_articles + 날짜 필터로 대체)
CREATE OR REPLACE FUNCTION match_articles_since(
    query_vector VECTOR(1024),
    since_date   TIMESTAMPTZ,
    top_k        INT DEFAULT 10
)
RETURNS TABLE (
    url_hash          VARCHAR,
    url               TEXT,
    title             TEXT,
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
