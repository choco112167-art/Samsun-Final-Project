# Evaluation Rubric Mapping

This document maps Samsun News / 삼선뉴스 to the official final evaluation rubric. The framing is intentionally honest: the app is a working Apps in Toss AI news curation product, while some advanced evaluation and fully autonomous cloud AI stages remain documented limitations.

## AI Model Selection And Preprocessing Design

What we implemented:
- Selected a Gemma/Gemma4-class local model path for Korean translation, Korean-first title generation, formal/casual summaries, and demo/backfill processing.
- Uses `samsun-gemma4` through Ollama for local May 1-May 18 Sangjun SQLite import/backfill.
- Uses OpenRouter/Gemini for cloud refresh because Supabase Edge Functions cannot call localhost Ollama.
- Designed preprocessing around RSS/body extraction, date filtering, Korean title policy, summary quality checks, neologism detection, and fact-status classification.

Where:
- `pipeline/translate_summarize.py`
- `scripts/process_sangjun_sqlite_with_ollama.py`
- `scripts/sangjun_sqlite_common.py`
- `scripts/demo_quality.py`
- `docs/MODEL_STRATEGY.md`
- `docs/DATA_PIPELINE.md`

How to demonstrate:
- Run `python scripts/audit_sangjun_sqlite.py --db-path samsun_345.db --since 2026-05-01 --until 2026-05-18`.
- Show that only the selected May range is processed.
- Open the app and show Korean title, full translation, formal/casual summaries, fact badge, and neologism explanation.

Remaining limitation:
- Local model quality varies on short/community posts; uncertain items are intentionally marked `UNVERIFIED` or `HITL_REQUIRED`.

Expected score rationale:
- Strong design coverage: model choice, local/cloud split, preprocessing policy, and safety policy are explicit.

## Model Training/Evaluation/Improvement Strategy

What we implemented:
- Project contains a fine-tuned Gemma/Gemma4 model serving plan and local Ollama/GGUF registration path.
- The strategy separates base model, local fine-tuned/demo model, and cloud models.
- Improvement loop uses audit scripts for missing/weak title, translation, summaries, fact labels, and demo readiness.
- Uncertainty handling prevents weak claims from being presented as verified.

Where:
- `MODEL_SERVING_OLLAMA.md`
- `pipeline/README.md`
- `scripts/audit_demo_readiness.py`
- `scripts/backfill_article_ai_outputs.py`
- `scripts/repair_demo_articles.py`
- `docs/MODEL_STRATEGY.md`

How to demonstrate:
- Show `ollama list` with `samsun-gemma4`.
- Run a dry run: `python scripts/process_sangjun_sqlite_with_ollama.py --db-path samsun_345.db --limit 3 --dry-run`.
- Show generated `fact_label` and `hitl_required` behavior.

Remaining limitation:
- BLEU/COMET/G-Eval and term preservation metrics are planned but not fully productionized in the final demo path.

Expected score rationale:
- Good practical tuning/serving story; partial quantitative evaluation coverage should be acknowledged.

## Real-Service Architecture

What we implemented:
- Apps in Toss `.ait` frontend reads directly from Supabase with anon key.
- Supabase stores articles, AI outputs, fact labels, fact checks, and neologisms.
- Supabase Edge/Cron can run cloud refresh with OpenRouter/Gemini.
- Local importer uses Ollama only for offline/demo backfill, not as a production Edge dependency.

Where:
- `frontend/src/data/api.ts`
- `supabase/functions/refresh-articles/index.ts`
- `backend/sql/add_demo_readiness_fields.sql`
- `docs/FINAL_ARCHITECTURE.md`
- `docs/SUPABASE_AUTOMATION_CHECKLIST.md`

How to demonstrate:
- Upload `frontend/samsun-newsapp.ait` to Apps in Toss console.
- Show the app still updates when Supabase data changes.
- Explain why `.ait` does not need a custom backend server.

Remaining limitation:
- Supabase visibility columns must be migrated before server-side hiding via `prepare_demo_feed.py` can update `is_hidden/demo_visible`.

Expected score rationale:
- Strong architecture: mobile app, data platform, batch AI processing, cloud refresh, and safety states are separated cleanly.

## Data Collection/Preprocessing Implementation

What we implemented:
- RSS/crawling and body extraction pipeline.
- Sangjun SQLite audit/import path with strict May 1-May 18 filtering.
- Preprocessing checks for Korean title, summary quality, translation completeness, fact status, and neologism terms.
- Safe demo seed data for rumor, unverified, and HITL examples.

Where:
- `main.py`
- `collect/crawler/rss_crawler.py`
- `scripts/audit_sangjun_sqlite.py`
- `scripts/process_sangjun_sqlite_with_ollama.py`
- `scripts/prepare_demo_feed.py`
- `scripts/seed_demo_articles.py`

How to demonstrate:
- Run audit and show `articles_in_selected_date_range`.
- Show Supabase rows from May range.
- Show demo seed rows with `[시연용]` and `source=DEMO`.

Remaining limitation:
- Some older Supabase rows are incomplete; the demo feed filters/prioritizes around them, and visibility migration is recommended.

Expected score rationale:
- Strong implementation: real data, strict date range, no mock production data, safety-aware demo rows.

## AI Model Training/Tuning Implementation

What we implemented:
- Local `samsun-gemma4` processing path with robust JSON parsing/retry.
- Generates `title_ko`, `translation`, `summary_formal`, `summary_casual`, `fact_status`, `fact_label`, `fact_confidence`, `hitl_required`, and neologism terms.
- Upserts processed outputs to Supabase.

Where:
- `scripts/process_sangjun_sqlite_with_ollama.py`
- `pipeline/translate_summarize.py`
- `pipeline/summarizer.py`
- `MODEL_SERVING_OLLAMA.md`

How to demonstrate:
- Run the dry run and a small upsert batch.
- Show generated Korean outputs in Supabase and the app.

Remaining limitation:
- The final app does not run LLM inference inside the `.ait`; it displays preprocessed Supabase outputs.

Expected score rationale:
- Solid applied model implementation; score depends on how much fine-tuning artifacts/evaluation evidence are shown during presentation.

## System Stability

What we implemented:
- Frontend handles missing Supabase env, query failures, zero articles, missing summaries, and missing translation.
- Neologism lookup is optional and cannot blank the feed.
- Demo mode prevents old 67-day articles from dominating.
- Local import scripts avoid processing all 1,784 rows and skip/continue on malformed model JSON.

Where:
- `frontend/src/data/api.ts`
- `frontend/src/pages/HomePage.tsx`
- `frontend/src/components/NeologismText.tsx`
- `scripts/process_sangjun_sqlite_with_ollama.py`
- `scripts/audit_demo_readiness.py`

How to demonstrate:
- Run `npm run build` and `npm run ait:build`.
- Show app feed and detail pages on mobile width.
- Show `python scripts/audit_demo_readiness.py`.

Remaining limitation:
- Browser-level automated screenshot verification is not currently committed as a test script.

Expected score rationale:
- Strong runtime stability for demo and `.ait`; additional automated UI tests would improve this further.

## Presentation Storytelling

What we implemented:
- Final demo scenario, architecture, model strategy, data pipeline, and checklist documents.
- Clear story: raw RSS/SQLite news becomes Korean-first AI-curated mobile news with fact status and neologism explanations.

Where:
- `docs/FINAL_DEMO_SCENARIO.md`
- `docs/FINAL_ARCHITECTURE.md`
- `docs/MODEL_STRATEGY.md`
- `docs/DATA_PIPELINE.md`
- `docs/FINAL_TEST_CHECKLIST.md`

How to demonstrate:
- Use the 5-minute demo flow document as the live presentation script.

Remaining limitation:
- Team contribution evidence should be supplemented with commit history or slides showing ownership.

Expected score rationale:
- Strong documentation and narrative readiness.

## Collaboration/Contribution

What we implemented:
- Clear separation of frontend, data pipeline, model, Supabase automation, and demo safety responsibilities.
- Runbooks and scripts allow each teammate to reproduce their part.

Where:
- `README.md`
- `docs/DEMO_RUNBOOK.md`
- `docs/EVALUATION_RUBRIC_MAPPING.md`
- Git history and task-specific scripts.

How to demonstrate:
- Show repository structure and runbooks.
- Present team roles around data collection, model processing, frontend, Supabase, and demo QA.

Remaining limitation:
- The repository documents workflow; the final presentation should explicitly name team member contributions.

Expected score rationale:
- Good reproducibility and handoff; final scoring improves if team contribution is stated clearly in slides.
