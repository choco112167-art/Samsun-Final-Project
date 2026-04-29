-- title_en 컬럼 삭제 (이미 삭제했다면 무시됨)
-- 이후 hybrid_search_articles 등 RPC 도 아래처럼 title_en 참조 없이 재생성해야 함.
-- 동일 함수 정의는 supabase_schema.sql 또는 backend/sql/add_title_ko.sql 의 hybrid 블록 참고.

ALTER TABLE articles DROP COLUMN IF EXISTS title_en;
