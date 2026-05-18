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

## 3. Hide Old Or Incomplete Rows For Demo

Preview first:

```bash
python scripts/prepare_demo_feed.py --limit 1000
```

Apply after reviewing the preview:

```bash
python scripts/prepare_demo_feed.py --limit 1000 --run
```

Rules:
- Rows older than 30 days are hidden from the main demo feed unless they are demo rows or high-priority demo rows.
- Rows missing Korean titles, valid summaries, or fact labels are hidden from the demo feed.
- Production rows are not deleted. The script updates `is_hidden=true` and `demo_visible=false` only when the SQL fields exist.

## 4. Seed Rich Demo Articles

```bash
python scripts/seed_demo_articles.py --replace-demo --confirm-delete
```

The seed inserts clearly marked synthetic rows only:
- `source="DEMO"`
- `title_ko` starts with `[시연용]`
- rumor/unverified rows say they are demo and unverified
- `fact_status`/`fact_label` show verified, unverified, rumor, and HITL states
- neologism terms are seeded into `neologisms`

## 5. Audit Demo Readiness

```bash
python scripts/audit_demo_readiness.py
```

Confirm there are enough demo-ready rows and that optional columns are detected.

## 6. Rebuild AIT

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

## 7. Upload To Apps In Toss Console

1. Open Apps in Toss console.
2. Select the `samsun-newsapp` app.
3. Upload `frontend/samsun-newsapp.ait`.
4. Create or update the test deployment.
5. Open the generated QR/private test link in Toss.

## 8. QR Test Checklist

- First screen shows Korean titles only.
- First screen has 8-12 polished demo cards before old RSS rows.
- Cards show 3-line summaries, fact badges, and trust indicators.
- Status examples are visible: `검증됨`, `미검증`, `루머 의심`, `HITL 검토 필요`.
- Rumor detail page shows: `이 항목은 검증되지 않은 시연용 루머 데이터입니다.`
- Neologism terms such as `프롬프트 주입`, `가드레일`, and `HITL` highlight and open explanations.
- `원문 보기` opens the safe source URL.
- No Railway URL is required.
