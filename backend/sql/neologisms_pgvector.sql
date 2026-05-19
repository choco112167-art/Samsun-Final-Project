-- Neologism vector search — Supabase SQL Editor 또는 마이그레이션으로 실행
-- pgvector 확장 (프로젝트에 이미 있으면 무시됨)
CREATE EXTENSION IF NOT EXISTS vector;

-- 벡터 컬럼·출처 (feat/mingyu 신조어 RAG)
ALTER TABLE neologisms ADD COLUMN IF NOT EXISTS embedding VECTOR(1024);
ALTER TABLE neologisms ADD COLUMN IF NOT EXISTS source TEXT;

-- 코사인 유사도 검색 (임베딩 차원은 반드시 1024 — backend/embedder.make_embedding 과 일치)
CREATE OR REPLACE FUNCTION match_neologisms(
  query_vector vector(1024),
  match_threshold float,
  top_k int
)
RETURNS TABLE (
  term text,
  ko_suggestion text,
  explanation text,
  similarity float
)
LANGUAGE sql
STABLE
AS $$
  SELECT
    n.term::text,
    COALESCE(n.ko_suggestion, '')::text,
    COALESCE(n.explanation, '')::text,
    (1::float - (n.embedding <=> query_vector)::float) AS similarity
  FROM neologisms n
  WHERE n.embedding IS NOT NULL
    AND (1::float - (n.embedding <=> query_vector)::float) >= match_threshold
  ORDER BY n.embedding <=> query_vector
  LIMIT GREATEST(top_k, 1);
$$;

COMMENT ON FUNCTION match_neologisms IS '신조어 테이블 코사인 유사도 검색 (1024차원, backend/neologism_rag.py)';
