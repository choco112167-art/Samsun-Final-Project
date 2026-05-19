# Final Test Checklist

## Build And Upload

- [ ] `frontend/samsun-newsapp.ait` exists.
- [ ] `npm run build` passes.
- [ ] `npm run ait:build` passes.
- [ ] Upload `.ait` to Apps in Toss console.
- [ ] QR/private deployment opens in Toss.

## Environment

- [ ] `VITE_SUPABASE_URL` was set at build time.
- [ ] `VITE_SUPABASE_ANON_KEY` was set at build time.
- [ ] No service role key is exposed to frontend.
- [ ] `VITE_DEMO_POLISHED_FEED=1` for final demo.

## Feed

- [ ] First screen shows Korean-first titles.
- [ ] No raw English title dominates the feed.
- [ ] Old 67-day articles do not dominate.
- [ ] May 1-May 18 processed articles appear.
- [ ] `[시연용]` demo cards are clearly marked.

## Article Detail

- [ ] Tone preference persists after switching `격식체` / `일상체`.
- [ ] Summary changes according to tone.
- [ ] Weak/missing summary shows `요약 생성 중입니다.`
- [ ] Full translation section shows article translation, not only summary.
- [ ] Missing translation shows `번역 전문 생성 중입니다.`
- [ ] `원문 보기` opens the source URL.

## Neologism

- [ ] Known terms are highlighted.
- [ ] Tapping a term opens a bottom sheet.
- [ ] Explanation comes from Supabase `neologisms`.
- [ ] Unknown terms are not faked.

## Fact And Trust

- [ ] Cards show fact badges.
- [ ] Detail page shows fact status explanation.
- [ ] `검증됨`, `확인 필요`, `루머 주의`, `분석글`, `전문가 검토 필요` examples exist.
- [ ] Rumor article says it is unverified demo rumor data.
- [ ] Trust bars: top 3 ranked items blue, lower ranks gray unless rumor/HITL/unverified status overrides.
- [ ] Category/ranking numbers are labeled as `신뢰도 순위` or `검증 우선순위`.

## Supabase Data

- [ ] `python scripts/audit_demo_readiness.py` shows enough demo-ready articles.
- [ ] Fact label counts include verified/unverified/rumor/HITL.
- [ ] Demo rumor count is greater than zero.
- [ ] HITL count is greater than zero.
- [ ] Optional visibility migration status is known.

## Safety

- [ ] Synthetic rumor data is never presented as verified real news.
- [ ] Local Ollama is described as local/demo/backfill only.
- [ ] Cloud refresh is described as OpenRouter/Gemini through Supabase Edge/Cron.
