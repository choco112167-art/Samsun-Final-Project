# Model Strategy

## Why A Gemma/Gemma4-Class Model

The project needs Korean translation, Korean title generation, and compact summaries for AI/tech news. A Gemma/Gemma4-class instruction model is a practical local model family for:
- Korean generation quality.
- Long enough context for article bodies.
- Local inference through Ollama/GGUF for demo/backfill.
- A clear path to fine-tuning or LoRA-based improvement.

The local demo model tag is:

```text
samsun-gemma4
```

Legacy local model defaults were removed; the local generation model is `samsun-gemma4`.

## Local Ollama / GGUF Role

Local Ollama is useful for:
- Offline/demo processing.
- Backfilling selected articles without exposing service-role keys to frontend.
- Running controlled imports from `samsun_345.db`.
- Demonstrating the team-owned model path.

Current local import path:

```bash
python scripts/process_sangjun_sqlite_with_ollama.py --db-path samsun_345.db --since 2026-05-01 --until 2026-05-18 --limit 20 --upsert-supabase
```

## Why Supabase Edge Cannot Use Localhost Ollama

Supabase Edge Functions run in Supabase's hosted Deno runtime. `http://localhost:11434` from that environment means the Edge runtime itself, not the presenter's laptop. Therefore production/cloud scheduled refresh cannot depend on local Ollama.

## Why OpenRouter/Gemini For Cloud Refresh

OpenRouter/Gemini are used in the cloud refresh path because:
- They are reachable from Supabase Edge Functions.
- They support scheduled refresh through Supabase Cron.
- They avoid maintaining a custom app server.

## Model Paths

| Path | Role | Runtime |
| --- | --- | --- |
| Base Gemma/Gemma4 | Foundation model family | Training/evaluation reference |
| `samsun-gemma4` | Local demo/backfill model | Ollama on developer machine |
| `Qwen3-Embedding-0.6B` | 1024-dim article/user embeddings for pgvector recommendation | Ollama on developer/admin machine |
| OpenRouter/Gemini | Production cloud refresh | Supabase Edge Function |
| Gemma4 reranking extension | Optional future reranking over pgvector candidates | Disabled in final `.ait` demo |

## Embedding / RAG Strategy

The final repo includes a local embedding POC aligned with the report:

```env
MODE=local
EMBEDDING_PROVIDER=local
LOCAL_EMBEDDING_MODEL=qwen3-embedding:0.6b
```

`backend/embedder.py` calls Ollama, normalizes the result to 1024 dimensions, and `backend/save_articles.py` writes article embeddings based on `title_ko + translation` into `articles.embedding VECTOR(1024)`.

Personalization is implemented in two compatible paths:
- Apps in Toss frontend path: `frontend/src/data/api.ts` saves onboarding `interest_tags`, records `user_logs`, updates `users.user_vector` when clicked article embeddings exist, calls Supabase `match_articles`, and falls back to category/recent-click/latest recommendations.
- Local/admin path: `backend/rag.py` and `backend/main.py` expose `/onboarding`, `/feed/{user_id}`, and `/users/{user_id}/click/{url_hash}` for batch tests and admin demos.

The final `.ait` demo does not depend on FastAPI. It reads Supabase directly with the anon key.

## LLM Re-ranking Position

LLM re-ranking is not a default final-demo feature. The stable path is:
1. Qwen3-Embedding-0.6B creates article/user vectors.
2. Supabase pgvector `match_articles` returns candidates.
3. The frontend shows deterministic reasons such as interest match, recent-click category, or vector similarity.

Gemma4/OpenRouter-based reranking remains a selectable extension for later evaluation. Do not present Qwen3.5-4B as the final recommendation LLM.

## Formal/Casual Summaries

The processing prompt asks for:
- `summary_formal`: 3-line Korean formal style.
- `summary_casual`: 3-line Korean casual style.

The frontend stores the user's tone preference in localStorage and globally applies the chosen summary style.

## Fact Labels

The app uses:
- `VERIFIED` / `FACT`: verified or source-supported.
- `UNVERIFIED`: insufficient evidence.
- `RUMOR`: rumor or explicitly unverified demo rumor item.
- `HITL_REQUIRED`: ambiguous or high-risk item requiring human review.

The safety policy is conservative: uncertainty becomes `UNVERIFIED` or `HITL_REQUIRED`, never fake certainty.

## Honest Limitation

The model can produce imperfect translations or weak JSON on some rows. The local import script retries JSON extraction and skips failed rows instead of corrupting Supabase. Quantitative metrics such as BLEU/COMET/G-Eval remain a recommended improvement area.
