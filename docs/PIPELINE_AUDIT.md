# Samsun News Pipeline Audit

Date: 2026-05-18

## Executive Summary

The Apps in Toss `.ait` frontend reads directly from Supabase. The data freshness issue is not a frontend issue: the current Supabase data shows `newest_published_at=2026-05-02T21:54:58+00:00` and `articles_inserted_or_updated_last_24h=0` from `python scripts/pipeline_health_check.py`.

The working RSS-to-Supabase path is the root `main.py` pipeline:

```text
collect/crawler/rss_crawler.py
→ fact_checker/preflight.py
→ pipeline/translate_summarize.py
→ fact_checker/pipeline.py
→ backend/save_articles.py
→ Supabase articles/fact_checks/neologisms
```

A custom app server is not required and was not introduced.

## What Currently Exists

| Stage | Files | Current state |
| --- | --- | --- |
| RSS feed list and parsing | `collect/crawler/rss_crawler.py` | Active collector used by root `main.py`; includes media and community feeds. |
| Body extraction | `collect/crawler/rss_crawler.py`, `scripts/article_pipeline_common.py` | RSS summary extraction exists. Backfill scripts can fetch full body with `trafilatura` / `readability`. The main ingest mostly uses RSS content, so many rows may have short content. |
| Preprocessing / AI relevance | `collect/models/credibility.py`, `fact_checker/preflight.py` | Connected in root `main.py`; filters non-AI items for non-AI-only feeds and applies signal routing before expensive LLM calls. |
| Slang/new-word handling | `backend/neologism_rag.py`, `backend/sql/neologisms_pgvector.sql` | Connected to translation prompts through `translate_and_summarize()`. This audit also connected candidate term tracking to `save_articles()`: detected terms are written to `neologisms`, and optional per-article `slang_terms`/`neologism_terms` columns are populated if the DB has them. |
| Fact labeling/checking | `fact_checker/*`, `backend/save_articles.py`, `main.py` | Connected. Root `main.py` runs preflight and fact-check routing before save. `save_articles()` also runs fact-checking when callers did not mark `_pipeline_fact_checked`. Missing API keys cause Google FC / LLM deep steps to be skipped, not faked. |
| Korean title / translation / summaries | `pipeline/translate_summarize.py`, `scripts/backfill_article_ai_outputs.py` | Connected in root `main.py` and `ingest_latest_fast.py`; writes `title_ko`, `translation`, `summary_formal`, `summary_casual` through `save_articles()`. Backfill script can repair missing AI fields. |
| Supabase upsert | `backend/save_articles.py`, `scripts/article_pipeline_common.py` | Connected. Upserts by `url_hash`, writes `articles`, `fact_checks`, `neologisms`, optional AI metadata columns if migrated. |
| Health check | `scripts/pipeline_health_check.py`, `scripts/check_articles_health.py` | Connected. Prints freshness and missing-field counts. |
| Scheduling | `docs/SUPABASE_EDGE_REFRESH_PLAN.md`, `supabase/functions/refresh-articles-plan/README.md` | Plan added. Supabase Edge Function should enqueue or trigger trusted Python execution; no custom app server dependency. |

## What Is Connected

Root `main.py` is the canonical full pipeline. It calls:

1. `fetch_all()` from `collect/crawler/rss_crawler.py`.
2. `run_preflight()` from `fact_checker/preflight.py`.
3. `translate_and_summarize()` from `pipeline/translate_summarize.py`.
4. `run_fact_check()` from `fact_checker/pipeline.py` when preflight requires deep checking and keys are available.
5. `save_articles()` from `backend/save_articles.py`.

`save_articles()` writes:

- `title`
- `title_ko`
- `url`
- optional `source_url` if that column exists
- `source`
- `published_at`
- `content`
- optional `crawled_text` or `body` if those columns exist
- `translation`
- `summary_formal`
- `summary_casual`
- `fact_label`
- optional `fact_status` if that column exists
- optional `slang_terms` / `neologism_terms` and `slang_processed_at` if those columns exist
- `neologisms` table rows for detected terms
- `fact_checks` rows when claim payloads exist

## Missing Or Dead Code

- `collect/main.py` appears stale/dead for this repo state. It imports `collect/db/database.py` and `collect/admin/stats.py`, but those files are not present in the current tracked tree. Do not use it for production refresh.
- `scripts/ingest_latest_titles.py` is intentionally title-only. It can make the list look fresh, but it leaves translation and summaries empty.
- `scripts/ingest_latest_fast.py` runs translation/summaries but uses a source-prior fact label for demo speed. Treat it as a demo helper, not the strongest fact-check path.
- Supabase `articles` currently lacks per-article slang fields. Slang is tracked in the `neologisms` table and injected into prompts, but `missing_slang_processing` cannot be measured per article until a `slang_terms` or `neologism_terms` column is migrated. Optional migration: `backend/sql/add_pipeline_tracking_fields.sql`.
- Current schema lacks `updated_at`; health uses `collected_at` as the freshness proxy.

## Slang Handling Status

Slang/new-word handling is connected in two ways:

1. `translate_and_summarize()` calls `build_neologism_glossary_prompt_section()`, which looks up matching terms from the `neologisms` vector table and injects verified glossary lines into the translation prompt.
2. `save_articles()` now detects candidate English AI/tech terms for saved articles and writes them to `neologisms`. If article-level slang columns exist, it also writes those fields.

This is not a full human-verified slang pipeline. New unmatched terms are candidates unless they already exist as confirmed/explained rows in `neologisms`.

## Fact Labeling Status

Fact labeling is connected. The code does not fake completed fact-checking:

- If `GOOGLE_FC_API_KEY` is missing, Google Fact Check API is skipped.
- If `GEMINI_API_KEY`, `GOOGLE_API_KEY`, and `OPENROUTER_API_KEY` are missing, deep LLM checking is skipped.
- Preflight/source-prior labels can still produce `FACT`, `INSIGHT`, `RUMOR`, or `UNVERIFIED`.
- Detailed `fact_checks` rows are written when the pipeline produces claim payloads.

Health currently reports `missing_fact_label_or_status: 0` in Supabase.

## Translation And Summary Write Status

Translation and summaries are written by root `main.py` and `scripts/ingest_latest_fast.py` through `backend/save_articles.py`.

Pre-refresh Supabase health showed:

```text
total_articles: 975
missing_translation: 19
missing_summary_formal: 19
missing_summary_casual: 19
ai_completed_inferred: 956
ai_pending_inferred: 19
```

After the local smoke refresh on 2026-05-18:

```text
total_articles: 977
missing_translation: 17
missing_summary_formal: 17
missing_summary_casual: 17
ai_completed_inferred: 960
ai_pending_inferred: 17
newest_published_at: 2026-05-17T20:15:00+00:00
articles_inserted_or_updated_last_24h: 2
```

The newest 20 rows include many `title-only/pending` articles from `2026-05-03` collection time. That means a title-only or partial refresh ran, but full translation/summarization did not complete for those latest rows.

## Why Latest Articles May Be Stale

Observed from `python scripts/pipeline_health_check.py`:

```text
newest_published_at: 2026-05-02T21:54:58+00:00
articles_inserted_or_updated_last_24h: 0
```

This improved after running:

```bash
python main.py --limit 2 --summary-sentences 3
python scripts/backfill_article_ai_outputs.py --limit 1 --provider openrouter --run --summary-sentences 3
```

Likely causes:

- No scheduler has run the root `python main.py` pipeline recently.
- The previous refresh may have used `ingest_latest_titles.py`, which updates titles only and leaves AI fields pending.
- Supabase Edge Function support now has two documented modes: `mode=direct` for a minimal Supabase-only TypeScript refresh, and `mode=queue` for queueing work that still needs a trusted Python runner.
- If root `main.py` was run without provider keys or local Ollama, translation/fact-check stages can fail or be skipped.

## Operator Commands

Full refresh:

```bash
python main.py --limit 10 --summary-sentences 3
```

Fast demo refresh with translation/summaries:

```bash
python scripts/ingest_latest_fast.py --max 5 --summary-sentences 3
```

Repair missing AI outputs:

```bash
python scripts/backfill_article_ai_outputs.py --limit 5 --provider openrouter --run
```

Freshness/missing-field health:

```bash
python scripts/pipeline_health_check.py
```

## TODO

- Apply `backend/sql/add_pipeline_tracking_fields.sql` if per-article slang status and precise `updated_at` freshness are required.
- Enable Supabase Cron in `mode=direct` for Supabase-only automatic refresh, or use `mode=queue` with a trusted Python runner for full canonical pipeline parity.
- Decide whether `source_url` should be a real column or whether `url` remains the canonical source URL.
