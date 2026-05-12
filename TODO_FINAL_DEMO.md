# Final Demo TODO

Last checked: 2026-05-12

## What Works Now

- React 18 + Vite frontend has `npm run dev`, `npm run build`, and `npm run ait:build`.
- Apps in Toss WebView config exists at `frontend/granite.config.ts`.
- FastAPI backend remains for batch/admin debugging only; app runtime no longer depends on it.
- Supabase project URL is configured as `https://srdvlalyucbokdwfkmcf.supabase.co`.
- Frontend uses `VITE_SUPABASE_URL` and `VITE_SUPABASE_ANON_KEY`; service-role keys are not exposed.
- Article detail uses stored `title_ko`, `translation`, `summary_formal`, and `summary_casual`; empty fields show preparation text instead of repeating the title.
- API failure mock fallback exists in `frontend/src/data/mock-articles.ts`.
- RSS/community collection, dedupe, fact labeling, neologism RAG, and AI backfill scripts exist.
- `provider=mock`, `provider=openrouter`, `provider=gemini`, and `provider=local` are separated in `scripts/backfill_article_ai_outputs.py`.

## P0 - Must Finish Before Final Presentation

- [ ] Put real frontend env in `frontend/.env.local` on the demo machine:
  - `VITE_SUPABASE_URL=https://srdvlalyucbokdwfkmcf.supabase.co`
  - `VITE_SUPABASE_ANON_KEY=<anon key>`
- [ ] Confirm Supabase RLS allows anon read on `articles`.
- [ ] Confirm frontend:
  - `cd frontend`
  - `npm run dev`
  - open `http://localhost:5173`
- [ ] Confirm production build:
  - `npm run lint`
  - `npm run typecheck`
  - `npm run build`
  - `npm run ait:build`
- [ ] Confirm `.ait` upload file exists:
  - `frontend/samsun-newsapp.ait`
- [ ] Register or serve the local fine-tuned model:
  - `ollama list` must show `gemma4-e4b-samsun`, or
  - `LOCAL_LLM_ENDPOINT` must point to a Transformers/PEFT server.
- [ ] Run one local-provider DB update after model server is ready:
  - `python scripts/backfill_article_ai_outputs.py --limit 1 --provider local --model gemma4-e4b-samsun --run`
- [ ] Clear mock DB outputs before demo:
  - `python scripts/check_articles_health.py`
  - `python scripts/clear_mock_ai_outputs.py --dry-run`
  - `python scripts/clear_mock_ai_outputs.py --run`

## P1 - Important But Demo Can Survive With Fallback

- [ ] Keep FastAPI/Railway references deprecated in demo docs.
- [ ] If batch writes are needed, put service-role key only in root `.env`, never in `frontend/.env*`.
- [ ] Run fresh RSS quick ingest:
  - `python scripts/ingest_latest_titles.py --limit 20`
- [ ] Run small AI processing batches only:
  - `python scripts/backfill_article_ai_outputs.py --limit 1 --provider local --run`
- [ ] Confirm fact labeling writes `fact_label`/`fact_checks` when keys are available.
- [ ] Confirm neologism table has RLS/write permissions for backend service-role path.

## P2 - Nice To Have

- [ ] Improve community feed coverage.
- [ ] Add search quality evaluation for Korean/English/typo queries.
- [ ] Add model output quality dashboard.
- [ ] Add full user-specific RAG recommendation tuning.

## Known Constraints

- The Hugging Face `gemma4-e4b-6ep-samsun-lora` repository is a LoRA adapter, not a ready Ollama GGUF. Ollama requires a merged/quantized GGUF first.
- Existing old articles may still have missing `translation`/summary fields. Do not mass-backfill all rows with paid providers before presentation.
- The frontend mock fallback is for demo resilience. Mock rows in Supabase must be cleared before showing real article details.
