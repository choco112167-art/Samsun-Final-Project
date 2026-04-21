-- ============================================================
-- 삼선뉴스 Supabase 스키마
-- Supabase > SQL Editor 에 전체 붙여넣고 실행
-- ============================================================

-- pgvector 확장 (최초 1회)
CREATE EXTENSION IF NOT EXISTS vector;


-- ============================================================
-- 1. articles  (메인 테이블)
-- ============================================================
CREATE TABLE IF NOT EXISTS articles (

    -- PK / 중복 방지
    url_hash          VARCHAR PRIMARY KEY,   -- MD5(url). upsert 기준 키
    url               TEXT NOT NULL,         -- 원문 URL

    -- 기사 메타데이터 (RSS 수집 · 이상준)
    title             TEXT,                  -- 기사 제목 (한국어, LLM 번역)
    title_en          TEXT,                  -- 기사 제목 (영문 원제)
    source            VARCHAR,               -- 언론사명 (TechCrunch, MIT TR 등)
    source_type       VARCHAR,               -- 'media' | 'community'
    category          VARCHAR,               -- 'AI' | 'Tech' 등. Hybrid Search 필터
    country           VARCHAR,               -- 발행 국가
    keywords          TEXT[],                -- 키워드 배열. 태그 UI + Hybrid Search
    published_at      TIMESTAMPTZ,           -- 기사 발행 시각 (ISO 8601)
    collected_at      TIMESTAMPTZ,           -- 파이프라인 수집 시각

    -- 원문
    content           TEXT,                  -- 영문 본문. BLEU·COMET·G-Eval 입력값

    -- 신뢰도
    credibility_score FLOAT,                 -- 출처 신뢰도 (0.0~1.0). RSS 수집 시 산정
    fact_label        VARCHAR DEFAULT 'UNVERIFIED',
                                             -- FACT | RUMOR | UNVERIFIED
                                             -- credibility_score 기반 자동 분류 (MVP)
                                             -- fact_checks 집계로 갱신 (MVP 이후)

    -- 번역·요약 출력 (이동우)
    translation       TEXT,                  -- 한국어 번역 전문
    summary_formal    TEXT,                  -- 격식체 3줄 요약 (~습니다)
    summary_casual    TEXT,                  -- 일상체 3줄 요약 (~해요)
    summary_en        TEXT,                  -- 영어 요약 (확장 화면용)

    -- RAG (강주찬)
    embedding         VECTOR(1024)           -- title(한국어) + translation 합산 임베딩
);

-- 인덱스
CREATE INDEX IF NOT EXISTS idx_articles_category    ON articles (category);
CREATE INDEX IF NOT EXISTS idx_articles_published   ON articles (published_at DESC);
CREATE INDEX IF NOT EXISTS idx_articles_fact_label  ON articles (fact_label);
CREATE INDEX IF NOT EXISTS idx_articles_embedding   ON articles USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);


-- ============================================================
-- 2. fact_checks  (팩트체크 세부 기록, 1:N)
-- ============================================================
CREATE TABLE IF NOT EXISTS fact_checks (

    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    article_url_hash  VARCHAR REFERENCES articles(url_hash) ON DELETE CASCADE,

    claim             TEXT,       -- 검증 대상 주장 원문
    verdict           VARCHAR,    -- FACT | RUMOR | UNVERIFIED
    confidence        FLOAT,      -- LLM 확신도 (0.0~1.0)

    -- MVP에서는 NULL 허용
    evidence_url      TEXT,       -- 근거 출처 URL
    checker_type      VARCHAR DEFAULT 'ai',  -- 'ai' | 'human'

    checked_at        TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_fact_checks_url_hash ON fact_checks (article_url_hash);


-- ============================================================
-- 3. neologisms  (신조어 캐시 + 파인튜닝 말뭉치)
-- ============================================================
CREATE TABLE IF NOT EXISTS neologisms (

    term                 VARCHAR PRIMARY KEY,  -- 영문 고유명사 원어 (예: 'Blackwell Ultra')

    -- 검색엔진 결과 (MVP에서는 NULL 허용, 수동 검수 후 채움)
    explanation          TEXT,    -- 설명 (예: 'NVIDIA의 차세대 데이터센터용 GPU')
    ko_suggestion        TEXT,    -- 한국어 음차 제안 (예: '블랙웰 울트라')

    -- 추적
    first_seen_url_hash  VARCHAR REFERENCES articles(url_hash) ON DELETE SET NULL,
    occurrence_count     INT DEFAULT 1,          -- 등장할 때마다 +1
    confirmed            BOOLEAN DEFAULT FALSE,  -- TRUE → AI_TERMS 목록 승격

    created_at           TIMESTAMPTZ DEFAULT NOW()
);


-- ============================================================
-- 4. eval_results  (파인튜닝 전/후 평가 지표, MVP 이후 활용)
-- ============================================================
CREATE TABLE IF NOT EXISTS eval_results (

    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    article_url_hash    VARCHAR REFERENCES articles(url_hash) ON DELETE CASCADE,
    model_version       VARCHAR,  -- 'qwen3-4b-base' | 'qwen3-4b-ft-v1' | 'gpt-4o'
    eval_type           VARCHAR,  -- 'translation' | 'summary_formal'

    -- 번역 평가 (eval_type = 'translation')
    bleu                FLOAT,    -- n-gram 표면 일치율
    comet               FLOAT,    -- 의미 보존 품질
    tpr                 FLOAT,    -- Term Preservation Rate

    -- 요약 평가 (eval_type = 'summary_formal')
    geval_faithfulness  FLOAT,    -- 충실성 (1~5)
    geval_fluency       FLOAT,    -- 유창성 (1~5)
    geval_conciseness   FLOAT,    -- 간결성 (1~5)
    geval_relevance     FLOAT,    -- 관련성 (1~5)

    evaluated_at        TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_eval_results_url_hash ON eval_results (article_url_hash);
CREATE INDEX IF NOT EXISTS idx_eval_results_model    ON eval_results (model_version);


-- ============================================================
-- 5. pg_trgm  (오타 허용 퍼지 검색용)
-- ============================================================

-- pg_trgm 확장 (최초 1회)
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- 제목·번역문 트라이그램 GIN 인덱스
-- hybrid_search_articles의 word_similarity() 쿼리를 인덱스로 가속
CREATE INDEX IF NOT EXISTS idx_articles_title_trgm
    ON articles USING gin (title gin_trgm_ops);

CREATE INDEX IF NOT EXISTS idx_articles_translation_trgm
    ON articles USING gin (translation gin_trgm_ops);


-- ============================================================
-- 6. match_articles  (RAG 벡터 검색 RPC · 강주찬)
-- ============================================================
CREATE OR REPLACE FUNCTION match_articles(
    query_vector VECTOR(1024),
    top_k        INT DEFAULT 10,
    filter_category VARCHAR DEFAULT NULL
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
        1 - (a.embedding <=> query_vector) AS similarity
    FROM articles a
    WHERE
        (filter_category IS NULL OR a.category = filter_category)
        AND a.embedding IS NOT NULL
    ORDER BY a.embedding <=> query_vector
    LIMIT top_k;
$$;


-- ============================================================
-- 7. hybrid_search_articles  (벡터 + 퍼지 키워드 하이브리드 검색)
--
-- 동작 방식:
--   1) vec_ranked  : pgvector 코사인 유사도로 후보 60개 추출
--   2) kw_ranked   : pg_trgm word_similarity + ILIKE 로 후보 60개 추출
--                    → 오타·부분 일치 모두 포괄
--   3) fused       : Reciprocal Rank Fusion(RRF, k=60) 으로 두 순위 결합
--   최종 top_k 개를 RRF 점수 내림차순으로 반환
-- ============================================================
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
    title_en          TEXT,
    source            VARCHAR,
    source_type       VARCHAR,
    category          VARCHAR,
    keywords          TEXT[],
    published_at      TIMESTAMPTZ,
    translation       TEXT,
    summary_formal    TEXT,
    summary_casual    TEXT,
    summary_en        TEXT,
    credibility_score FLOAT,
    fact_label        VARCHAR,
    similarity        FLOAT
)
LANGUAGE sql STABLE AS $$
    WITH
    -- ── 1. 벡터 검색 (의미 유사도) ───────────────────────────────
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
    -- ── 2. 퍼지 키워드 검색 (오타 허용) ──────────────────────────
    -- word_similarity: 쿼리 단어가 긴 텍스트 안에 얼마나 유사하게 존재하는지
    -- ILIKE: 정확한 부분 문자열 매칭 (짧은 쿼리·키워드 검색 보완)
    kw_ranked AS (
        SELECT
            a.url_hash,
            ROW_NUMBER() OVER (
                ORDER BY GREATEST(
                    word_similarity(query_text, a.title),
                    word_similarity(query_text, COALESCE(a.translation, '')),
                    similarity(query_text, a.title)
                ) DESC
            ) AS rnk
        FROM articles a
        WHERE
            (filter_category IS NULL OR a.category = filter_category)
            AND (
                a.title          ILIKE '%' || query_text || '%'
                OR a.title_en     ILIKE '%' || query_text || '%'
                OR a.translation  ILIKE '%' || query_text || '%'
                OR word_similarity(query_text, a.title)                          > 0.15
                OR word_similarity(query_text, COALESCE(a.title_en, ''))         > 0.15
                OR word_similarity(query_text, COALESCE(a.translation, ''))      > 0.15
                OR similarity(query_text, a.title)                               > 0.10
            )
        LIMIT 60
    ),
    -- ── 3. Reciprocal Rank Fusion (RRF, k=60) ────────────────────
    -- 두 순위를 1/(k+rank) 점수로 변환 후 합산
    -- 어느 한쪽에만 있어도 FULL OUTER JOIN 으로 포함
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
        a.title_en,
        a.source,
        a.source_type,
        a.category,
        a.keywords,
        a.published_at,
        a.translation,
        a.summary_formal,
        a.summary_casual,
        a.summary_en,
        a.credibility_score,
        a.fact_label,
        f.vec_sim AS similarity
    FROM fused f
    JOIN articles a ON a.url_hash = f.url_hash
    ORDER BY f.rrf_score DESC
    LIMIT top_k;
$$;
