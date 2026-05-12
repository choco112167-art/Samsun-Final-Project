# Samsun News Pipeline Audit

Last checked: 2026-05-12

## Branch / Feature Map

| Branch | Useful parts found | Current MVP decision |
| --- | --- | --- |
| `main` | Integrated React/Vite frontend, FastAPI backend, Supabase article API, Apps in Toss config, AI backfill scripts, mock fallback. | Use as current presentation base. |
| `codex/main-final` | Previous integration branch with article detail UX, safe AI backfill, Apps in Toss docs/config. | Already merged into main lineage. Keep as reference only. |
| `feat/joochan` | Broad base app: frontend screens, backend API, RAG/fact checker skeletons. | Base concepts already integrated. Do not re-merge wholesale. |
| `feat/leesangjun` | RSS/crawler and Apps in Toss experiments. Some package versions drifted to React 19. | RSS/crawler pieces are already represented in `collect/` and `scripts/`. Avoid React 19 changes. |
| `feat/dongwoo` | Fact labeling and source credibility/fact checker pipeline. | `fact_checker/` and `backend/save_articles.py` integration are present. |
| `feat/soomin` | Absence summary / missed article notification flow. | `/absence-summary/{user_id}` is integrated in `backend/main.py`. |

## Pipeline Status

| Step | Status | Files | Notes / risk |
| --- | --- | --- | --- |
| 1. RSS AI news collection | Implemented | `collect/crawler/rss_crawler.py`, `scripts/ingest_latest_titles.py`, `scripts/ingest_latest_fast.py`, root `main.py` | Fast demo ingest exists. Full translation batch must be run in small limits only. |
| 2. Community post collection | Partial | `collect/crawler/rss_crawler.py` | Hacker News and Lemmy style sources exist. Coverage is demo-level. |
| 3. Dedupe / preprocessing | Implemented | `backend/save_articles.py`, `scripts/article_pipeline_common.py` | `url_hash` based dedupe/upsert is used. |
| 4. Fact labeling | Implemented, API-key dependent | `fact_checker/`, `backend/save_articles.py` | Falls back to heuristic/skip if Google Fact Check or LLM keys are missing. |
| 5. Neologism detection | Implemented | `backend/neologism_rag.py` | Candidate extraction and DB match path exist. |
| 6. Existing neologism DB lookup | Implemented | `backend/neologism_rag.py`, `backend/save_articles.py` | Requires Supabase `neologisms` table and embedding dimensions to match. |
| 7. New neologism grounding search | Implemented, key dependent | `backend/neologism_rag.py` | Uses Gemini Google Search grounding when Gemini/Google key is configured. |
| 8. Save article outputs to Supabase | Implemented | `backend/save_articles.py`, `scripts/backfill_article_ai_outputs.py` | Saves title, title_ko, url, translation, summaries, fact label, optional AI status fields. |
| 9. Frontend reads stored data | Implemented | `frontend/src/data/api.ts`, `frontend/src/data/notices.ts` | Frontend uses backend API by `VITE_API_BASE_URL`. It does not call LLMs directly. |
| 10. Home/category/search/detail/feed | Implemented with fallback | `frontend/src/pages/`, `frontend/src/data/mock-articles.ts` | Search has API path plus keyword fallback. UI should still be tested on mobile. |
| 11. Frontend no direct LLM | Implemented | `frontend/src/data/api.ts` | No Gemini/OpenRouter/Ollama secret usage in frontend runtime. |
| 12. API failure mock fallback | Implemented | `frontend/src/data/mock-articles.ts` | Dev/demo fallback keeps screens alive when API is down. |
| 13. `.ait` bundle | Implemented | `frontend/package.json`, `frontend/granite.config.ts` | `npm run ait:build` creates `frontend/samsun-newsapp.ait`; keep ignored by git. |
| 14. Toss WebView risks | Documented / partial | `config.py`, `.env.example`, `DEPLOYMENT_APPS_IN_TOSS.md` | Need final HTTPS backend URL before production QR/public testing. |

## Supabase Tables / Policies Needed

| Table | Purpose | RLS note |
| --- | --- | --- |
| `articles` | Main article rows, AI outputs, fact labels, optional AI worker status. | Public/read policy or backend-only read through FastAPI. Writes should be service-role/backend only. |
| `neologisms` | Term cache, descriptions, embeddings. | Reads can be public/backend; writes backend only. |
| `user_logs` | Views, seen state, feed signals. | User-scoped read/write policy required if called directly. Current MVP uses backend. |
| `eval_results` | Optional model evaluation logs. | Backend/service-role only. |

Recommended optional `articles` AI worker fields:

```sql
alter table articles add column if not exists ai_status text default 'pending';
alter table articles add column if not exists ai_provider text;
alter table articles add column if not exists ai_model text;
alter table articles add column if not exists ai_generated_at timestamptz;
alter table articles add column if not exists ai_error text;
alter table articles add column if not exists content_source text;
alter table articles add column if not exists content_chars integer;
alter table articles add column if not exists translation_chars integer;
```

## P0 Reality Check

Ready enough for demo:

- React/Vite app and FastAPI API have local run paths.
- Article list/detail can render Supabase data.
- Missing translation/summary data does not crash the UI.
- Mock fallback exists for presentation safety.
- Apps in Toss WebView dependencies/config are present.

Needs manual final check before presentation:

- Confirm `.env` contains real Supabase anon/service-role keys only on backend machine.
- Confirm `ollama list` contains `gemma4-e4b-samsun` or a compatible merged/quantized model.
- Confirm external HTTPS backend URL is configured for Toss QR/device testing.
- Run one real `provider=local` article AI update after local model server is up.
