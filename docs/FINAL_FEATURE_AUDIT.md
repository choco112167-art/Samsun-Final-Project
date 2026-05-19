# Final Feature Audit: Embeddings/RAG And Neologisms

This audit records what is actually implemented for final submission. It is intentionally conservative: if a feature exists only as a helper or demo/admin POC, it is marked as partial rather than presented as a full production feature.

## Status Table

| Feature | Status | Evidence | Notes |
| --- | --- | --- | --- |
| `articles.embedding vector(1024)` | Actually implemented | `supabase_schema.sql`, `backend/sql/add_title_ko.sql` | Main `articles` schema includes pgvector `VECTOR(1024)` and ivfflat cosine index. |
| `rss_articles_gamma.embedding` | Not used in this repo | Search result: no `rss_articles_gamma` table | Final product uses canonical Supabase `articles`; the gamma table name appears to be from report/planning context, not the submitted code path. |
| Qwen3-Embedding-0.6B local embedding adapter | Actually implemented as local POC | `backend/embedder.py`, `.env.example` | `LOCAL_EMBEDDING_MODEL=qwen3-embedding:0.6b`; vectors are fitted to 1024 dims before DB writes. |
| Article embedding generation | Actually implemented | `backend/save_articles.py` | Builds embedding from `title_ko + translation` and writes `articles.embedding` during Supabase upsert. |
| pgvector article search RPC | Actually implemented | `supabase_schema.sql`, `backend/sql/add_title_ko.sql` | `match_articles(query_vector vector(1024), top_k, filter_category)` uses cosine distance. |
| Hybrid vector + keyword search | Actually implemented | `supabase_schema.sql`, `backend/main.py` | `hybrid_search_articles` exists in SQL; `/search` uses vector search plus keyword fallback. |
| User interest vector profile | Actually implemented as backend/admin path | `supabase_schema.sql`, `backend/rag.py`, `backend/main.py` | `users.user_vector vector(1024)` and `/onboarding` save interest vectors. Apps in Toss frontend does not require backend server. |
| Click article → user_vector update | Minimal POC implemented | `backend/rag.py`, `backend/main.py` | `POST /users/{user_id}/click/{url_hash}` records `user_logs` and blends article embedding into `users.user_vector`. |
| Top 20 vector candidates | Minimal POC implemented | `backend/rag.py` | `fetch_recommendation_candidates(..., candidate_k=20)` feeds personalized recommendation. |
| LLM re-ranking | Partial / optional POC | `backend/rag.py` | Disabled by default. Set `RAG_LLM_RERANK_ENABLED=1` and `OPENROUTER_API_KEY` for local/admin FastAPI reranking. Not used by `.ait` frontend. |
| Supabase `neologisms` table | Actually implemented | `supabase_schema.sql`, `backend/sql/neologisms_pgvector.sql` | Base schema and migration include `embedding vector(1024)` and `match_neologisms`. |
| Neologism candidate extraction | Actually implemented | `backend/neologism_rag.py`, `scripts/sangjun_sqlite_common.py`, `scripts/process_sangjun_sqlite_with_ollama.py` | Extracts technical terms from title/body/generated output. |
| `articles.slang_terms` / `articles.neologism_terms` upsert | Partial, schema-dependent | `backend/save_articles.py`, `scripts/backfill_article_ai_outputs.py`, `supabase/functions/refresh-articles/index.ts`, `backend/sql/add_pipeline_tracking_fields.sql` | Written only when optional columns exist. Migration is documented. |
| Neologism prompt glossary | Actually implemented | `pipeline/translate_summarize.py`, `backend/neologism_rag.py` | Existing Supabase neologism rows can be injected into translation prompts. Unknown terms are not invented unless explicit Gemini grounding is enabled. |
| Frontend neologism lookup | Actually implemented | `frontend/src/data/api.ts`, `frontend/src/pages/DetailPage.tsx` | Fetches dictionary, per-article rows, and term-specific rows. Failures return `[]` and do not block article rendering. |
| Frontend inline highlight + bottom sheet | Actually implemented | `frontend/src/components/NeologismText.tsx`, `frontend/src/components/Overlay.tsx` | Known terms with DB explanations are highlighted. Tap opens bottom sheet; desktop hover shows tooltip. |
| Unknown term explanation policy | Actually implemented/documented | `frontend/src/components/NeologismText.tsx`, `docs/DATA_PIPELINE.md` | UI filters out entries without explanation; unknown terms are not faked. |

## How To Demonstrate Embedding / RAG

1. Run the pgvector schema/migrations in Supabase:

```sql
-- supabase_schema.sql
-- backend/sql/add_title_ko.sql if updating an existing DB
```

2. Configure local embedding:

```env
MODE=local
EMBEDDING_PROVIDER=local
LOCAL_EMBEDDING_MODEL=qwen3-embedding:0.6b
```

3. Prepare the local model:

```bash
ollama pull qwen3-embedding:0.6b
```

4. Upsert processed articles. `backend/save_articles.py` writes `articles.embedding`.

5. Local/admin recommendation POC:

```bash
uvicorn backend.main:app --reload
curl -X POST http://localhost:8000/onboarding \
  -H "Content-Type: application/json" \
  -d "{\"user_id\":\"demo\",\"interest_tags\":[\"AI\",\"반도체\",\"RAG\"]}"
curl http://localhost:8000/feed/demo?top_k=10
curl -X POST http://localhost:8000/users/demo/click/<url_hash>
```

For optional LLM reranking:

```env
RAG_LLM_RERANK_ENABLED=1
OPENROUTER_API_KEY=<key>
RAG_RERANK_MODEL=google/gemini-2.5-flash-lite
```

## How To Demonstrate Neologisms

1. Run the base schema and optional vector migration:

```sql
-- supabase_schema.sql
-- backend/sql/neologisms_pgvector.sql
-- backend/sql/add_pipeline_tracking_fields.sql for article-level slang fields
```

2. Seed demo terms:

```bash
python scripts/seed_demo_articles.py
```

3. Open a demo article containing `프롬프트 주입`, `가드레일`, or `HITL`.

4. Tap the highlighted term in summary/translation. The explanation comes from Supabase `neologisms`.

## Honest Limitations

- The Apps in Toss `.ait` frontend reads Supabase directly and does not call the local/admin FastAPI recommendation endpoints.
- LLM reranking is an optional POC path, not a default production feature.
- Article-level `slang_terms` / `neologism_terms` require `backend/sql/add_pipeline_tracking_fields.sql` on existing Supabase projects.
- Unknown neologism explanations are not fabricated in the UI. They appear only when a Supabase `neologisms.explanation` exists.
