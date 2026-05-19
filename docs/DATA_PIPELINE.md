# Data Pipeline

## 1. RSS And Crawling

RSS feeds are collected through the crawler pipeline and stored as article candidates. Body extraction and preprocessing remove low-quality or irrelevant content where possible.

Key files:
- `main.py`
- `collect/crawler/rss_crawler.py`
- `backend/save_articles.py`

Final community collection sources:

| Source | Collection path | Notes |
| --- | --- | --- |
| Lemmy Technology | `https://lemmy.world/feeds/c/technology.xml` + Lemmy API | RSS summaries are often too short, so the crawler resolves the Lemmy post ID and reads `post_view.post.embed_description` from the Lemmy API. This uses the preview text cached by the Lemmy server instead of unstable direct scraping. `title_only=True` is used for AI relevance filtering. |
| Hacker News AI / LLM / ML | `https://hnrss.org/newest?q=artificial+intelligence`, `?q=LLM`, `?q=machine+learning` | hnrss.org keyword-filtered RSS feeds are already scoped to AI/LLM/ML terms, so these feeds use `ai_only=True` and skip the extra relevance filter. |

Reddit is not a final collection source. It was considered early, but API/RSS access-policy changes and data-licensing risk made it unsuitable as a stable public collection path. The final community pipeline uses Lemmy API and Hacker News hnrss.org instead.

Presentation sentence:

> 초기에는 Reddit 계열 커뮤니티 수집도 검토했으나, API/RSS 접근 정책 변화와 데이터 라이선싱 리스크로 인해 최종 수집 대상에서 제외했습니다. 대신 Lemmy API와 Hacker News hnrss.org를 활용해 커뮤니티 기반 AI/LLM/ML 소스를 안정적으로 수집했습니다.

## 2. Sangjun SQLite Import

The Sangjun SQLite database is used as a local source for final demo-quality articles. The import is intentionally limited:

```text
published_at >= 2026-05-01
published_at <= 2026-05-18 23:59:59
```

Rows without `published_at` are excluded unless `--include-missing-date` is explicitly passed.

Key files:
- `scripts/audit_sangjun_sqlite.py`
- `scripts/process_sangjun_sqlite_with_ollama.py`
- `scripts/sangjun_sqlite_common.py`

## 3. Preprocessing

Preprocessing checks:
- Date range.
- Source/category filters.
- Content presence.
- Missing Korean title.
- Missing or weak summaries.
- Missing or short translation.
- Missing fact labels.

Key file:
- `scripts/demo_quality.py`

## 4. AI Generation

For selected May articles, local Ollama `samsun-gemma4` generates:
- `title_ko`
- `translation`
- `summary_ko`
- `summary_formal`
- `summary_casual`
- `fact_status`
- `fact_label`
- `fact_confidence`
- `hitl_required`
- `neologism_terms`

The script uses strict JSON prompts, retries invalid JSON, and skips failed rows safely.

## 5. Fact Labeling

Fact labels are conservative:
- Verified only when the article appears sufficiently supported.
- Unverified when evidence is weak.
- HITL when automatic judgment is not enough.
- Rumor for clearly labeled rumor/demo items.

Demo rumor articles are synthetic and visibly marked with `[시연용]` and `source=DEMO`.

## 6. Neologism Detection

Terms such as `HITL`, `프롬프트 주입`, and `가드레일` are stored in Supabase `neologisms`. The frontend highlights known terms and opens an explanation bottom sheet.

Unknown terms are not faked. The UI only shows explanations for terms returned from Supabase `neologisms` with a non-empty `explanation`; candidate terms without registered explanations are ignored visually.

## 7. Supabase Upsert

Processed rows are upserted into `articles`, with optional fields added only if the Supabase schema supports them:
- `source_url`
- `fact_status`
- `fact_confidence`
- `hitl_required`
- `neologism_terms`
- `slang_terms`
- `is_demo`
- `is_hidden`
- `demo_visible`
- `demo_priority`

Embeddings are generated in the backend save path:
- `backend/embedder.py`: local `Qwen3-Embedding-0.6B` through Ollama (`LOCAL_EMBEDDING_MODEL=qwen3-embedding:0.6b`) or cloud embedding through OpenRouter.
- `backend/save_articles.py`: embeds `title_ko + translation`.
- `supabase_schema.sql`: stores the result in `articles.embedding VECTOR(1024)`.

The personalized recommendation path uses:
- `users.interest_tags` from onboarding.
- `users.user_vector VECTOR(1024)` for pgvector personalization when embeddings are available.
- `user_logs` for article click history.
- `match_articles(query_vector, top_k)` for cosine-similarity candidate retrieval.
- `frontend/src/data/api.ts` for Apps in Toss direct Supabase recommendation: RPC first, then category/recent-click/latest fallback.
- `backend/rag.py` for local/admin testing and optional reranking extension.

LLM reranking is not the default final-demo path. It remains a Gemma4/OpenRouter extension after pgvector candidate retrieval.

## 8. Demo Readiness Filtering

The frontend demo mode `VITE_DEMO_POLISHED_FEED=1` prioritizes:
- May 1-May 18 processed articles.
- Complete Korean title/summary/translation rows.
- Fact-labeled articles.
- Clearly marked demo rumor/HITL examples.

Old 67-day articles do not dominate the demo feed.

## 9. Seed Demo Rumor/HITL Articles

`scripts/seed_demo_articles.py` inserts safe synthetic examples:
- Verified examples.
- Unverified examples.
- Rumor-labeled examples.
- HITL-required examples.
- Neologism examples.

Every synthetic item is marked:
- `title_ko` starts with `[시연용]`.
- `source=DEMO`.
- Rumor/unverified/HITL wording is explicit.
