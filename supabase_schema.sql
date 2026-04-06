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
    title             TEXT,                  -- 기사 제목 (영문)
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

    -- RAG (강주찬)
    embedding         VECTOR(1024)           -- translation 임베딩. mxbai-embed-large
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
-- 5. match_articles  (RAG 벡터 검색 RPC · 강주찬)
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
