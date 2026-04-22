-- ============================================================
-- backend/neologism_rag.py 가 필요로 하는 스키마 보강
--
-- 기존 supabase_schema.sql 의 `neologisms` 테이블에 벡터 컬럼과
-- 캐시 검색 RPC 를 추가합니다. Supabase > SQL Editor 에 붙여넣고 1회 실행.
-- ============================================================

-- pgvector 확장 (이미 있을 수 있음)
CREATE EXTENSION IF NOT EXISTS vector;

-- 1) 임베딩 / 출처 컬럼 추가
ALTER TABLE neologisms
    ADD COLUMN IF NOT EXISTS embedding VECTOR(1024),
    ADD COLUMN IF NOT EXISTS source    TEXT;

-- 2) cosine 기반 ivfflat 인덱스
CREATE INDEX IF NOT EXISTS idx_neologisms_embedding
    ON neologisms USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 50);

-- 3) 유사도 검색 RPC (threshold 기본 0.85, top_k 기본 1)
CREATE OR REPLACE FUNCTION match_neologisms(
    query_vector    VECTOR(1024),
    match_threshold FLOAT DEFAULT 0.85,
    top_k           INT   DEFAULT 1
)
RETURNS TABLE (
    term          VARCHAR,
    explanation   TEXT,
    ko_suggestion TEXT,
    source        TEXT,
    similarity    FLOAT
)
LANGUAGE sql STABLE AS $fn$
    SELECT
        n.term,
        n.explanation,
        n.ko_suggestion,
        n.source,
        1 - (n.embedding <=> query_vector) AS similarity
    FROM neologisms n
    WHERE n.embedding IS NOT NULL
      AND 1 - (n.embedding <=> query_vector) >= match_threshold
    ORDER BY n.embedding <=> query_vector
    LIMIT top_k;
$fn$;
