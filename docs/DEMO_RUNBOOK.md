# Samsun News Demo Runbook

This runbook prepares a Supabase-only, Apps in Toss `.ait` live demo feed. It never deletes production data by default.

## 1. Run Demo Readiness SQL

Open Supabase Dashboard -> SQL Editor and run:

```sql
-- backend/sql/add_demo_readiness_fields.sql
```

This adds optional demo visibility fields such as `is_hidden`, `is_demo`, `demo_visible`, `demo_priority`, `fact_status`, `fact_confidence`, and `hitl_required`.

## 2. Back Up Current Data

```bash
python scripts/export_articles_backup.py
```

Keep the generated backup file before changing demo visibility.

## 3. Audit Sangjun SQLite May Range

Only process real Sangjun SQLite articles from May 1 through May 18, 2026:

```bash
python scripts/audit_sangjun_sqlite.py --db-path samsun_345.db --since 2026-05-01 --until 2026-05-18
```

Rows with missing `published_at` are excluded unless `--include-missing-date` is explicitly provided.

## 4. Process May Articles With Local Ollama

Local demo/backfill processing uses Ollama on the same machine:

```bash
LLM_PROVIDER=ollama
MODE=local
MODEL_NAME=samsun-gemma4
OLLAMA_BASE_URL=http://localhost:11434
```

Supabase Edge Functions cannot use local Ollama because hosted Edge Functions run in Supabase's Deno runtime, not on the demo laptop where Ollama is listening.

Dry run:

```bash
python scripts/process_sangjun_sqlite_with_ollama.py --db-path samsun_345.db --since 2026-05-01 --until 2026-05-18 --limit 3 --dry-run
```

Process and write results back into SQLite:

```bash
python scripts/process_sangjun_sqlite_with_ollama.py --db-path samsun_345.db --since 2026-05-01 --until 2026-05-18 --limit 20 --write-sqlite
```

Process and upsert selected May rows into Supabase:

```bash
python scripts/process_sangjun_sqlite_with_ollama.py --db-path samsun_345.db --since 2026-05-01 --until 2026-05-18 --limit 20 --upsert-supabase
```

## 5. Hide Old Or Incomplete Rows For Demo

Preview first:

```bash
python scripts/prepare_demo_feed.py --since 2026-05-01 --until 2026-05-18
```

Apply after reviewing the preview:

```bash
python scripts/prepare_demo_feed.py --since 2026-05-01 --until 2026-05-18 --run
```

Rules:
- Rows outside May 1-May 18, 2026 are hidden from the main demo feed unless they are demo rows or high-priority demo rows.
- Rows missing Korean titles, valid summaries, or fact labels are hidden from the demo feed.
- Production rows are not deleted. The script updates `is_hidden=true` and `demo_visible=false` only when the SQL fields exist.

## 6. Seed Rich Demo Articles

```bash
python scripts/seed_demo_articles.py --replace-demo --confirm-delete
```

The seed inserts clearly marked synthetic rows only:
- `source="DEMO"`
- `title_ko` starts with `[시연용]`
- rumor/unverified rows say they are demo and unverified
- `fact_status`/`fact_label` show verified, unverified, rumor, and HITL states
- neologism terms are seeded into `neologisms`

## 7. Audit Demo Readiness

```bash
python scripts/audit_demo_readiness.py
```

Confirm there are enough demo-ready rows and that optional columns are detected.

## 8. Rebuild AIT

From `frontend/`, build with Supabase Vite env and polished demo mode:

```bash
npm run typecheck
npm run lint
npm run build
npm run ait:build
```

Generated bundle:

```text
frontend/samsun-newsapp.ait
```

## 9. Upload To Apps In Toss Console

1. Open Apps in Toss console.
2. Select the `samsun-newsapp` app.
3. Upload `frontend/samsun-newsapp.ait`.
4. Create or update the test deployment.
5. Open the generated QR/private test link in Toss.

## 10. QR Test Checklist

- First screen shows Korean titles only.
- First screen shows processed May 1-May 18 articles and clearly marked demo cards before old RSS rows.
- Cards show 3-line summaries, fact badges, and trust indicators.
- Status examples are visible: `검증됨`, `확인 필요`, `루머 주의`, `분석글`, `전문가 검토 필요`.
- Rumor detail page shows: `이 항목은 검증되지 않은 시연용 루머 데이터입니다.`
- Neologism terms such as `프롬프트 주입`, `가드레일`, and `HITL` highlight and open explanations.
- `원문 보기` opens the safe source URL.
- No custom backend URL is required.
