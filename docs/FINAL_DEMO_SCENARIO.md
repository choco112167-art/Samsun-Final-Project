# Final Demo Scenario

This is a 5-minute live demo flow for Samsun News / 삼선뉴스.

## 0:00-0:40 Opening

Problem statement:
- AI news moves quickly, but raw RSS feeds are mostly English, uneven in quality, and hard to trust.
- Users need Korean-first summaries, full translation, source access, terminology help, and a clear trust signal.

Positioning:
- Samsun News is an Apps in Toss mini-app that turns raw AI/tech news into a curated Korean mobile news experience.

## 0:40-1:20 Open The Apps In Toss App

Show:
- The uploaded `.ait` app running in Toss test mode.
- The first screen with polished May 1-May 18 articles and clearly labeled `[시연용]` demo examples.
- Korean titles only; no raw English title dominance.

Say:
- The `.ait` frontend reads Supabase directly and does not need a custom backend server.
- Data updates happen through Supabase, so the app does not need rebuild for content refresh.

## 1:20-1:50 Tone Preference

Show:
- Toggle `격식체` / `일상체`.
- Open a card and show that the same preference applies globally.

Say:
- Tone preference is persisted in localStorage.
- The app supports both formal news tone and casual reading tone.

## 1:50-2:30 Summary, Translation, Source

Show:
- 3-line Korean summary on a card.
- Detail page full translation section.
- `원문 보기` button/link.

Say:
- This is not only a headline summarizer. It stores Korean title, full translation, formal summary, casual summary, and source link.
- Weak or missing summaries are hidden behind “요약 생성 중입니다.”

## 2:30-3:05 Neologism Annotation

Show:
- Open an article containing terms like `프롬프트 주입`, `가드레일`, or `HITL`.
- Tap the highlighted term and show the bottom sheet explanation.

Say:
- Explanations come from the Supabase `neologisms` table.
- Unknown terms are not faked.

## 3:05-3:45 Fact Status And Trust

Show:
- Badges: `검증됨`, `확인 필요`, `루머 주의`, `분석글`, `전문가 검토 필요`.
- Trust ranking/helper text.

Say:
- The app does not pretend uncertain claims are true.
- Uncertain items become `확인 필요`; ambiguous items become `전문가 검토 필요`.
- `INSIGHT` preserves expert analysis/opinion pieces instead of dropping them as noise.
- Rumor examples are synthetic and clearly labeled `[시연용]`.

## 3:45-4:30 Pipeline And Supabase

Show briefly:
- Supabase `articles`, `fact_checks`, `neologisms`.
- Run or show output from `python scripts/audit_demo_readiness.py`.

Say:
- RSS/crawling and Sangjun SQLite import feed the preprocessing pipeline.
- For final demo, Sangjun import is strictly limited to May 1-May 18.
- Local Ollama `samsun-gemma4` handles offline import/backfill.
- Cloud refresh uses Supabase Edge/Cron plus OpenRouter/Gemini because Edge cannot access localhost Ollama.

## 4:30-5:00 Close

Summarize:
- Samsun News is a complete AI news curation product: data collection, AI preprocessing, Korean UX, fact status, neologism explanation, and Apps in Toss delivery.
- Limitations are explicit: local Ollama is not the production Edge model; advanced quantitative evaluation can be expanded.

Final line:
- “We built the path from raw AI news to a Korean-first trusted mobile news product.”

## Apps in Toss Console / Real-Device Demo Add-On

Use this flow when the evaluation includes the Apps in Toss test upload screen.

### 1. Toss Console Test Registration

Show:
- Apps in Toss Console app page for `samsun-newsapp`.
- Test/release upload area.
- Final artifact path:

```text
frontend/samsun-newsapp.ait
```

Say:
- The `.ait` bundle is generated with `npm run ait:build`.
- The frontend uses only Supabase anon environment values and does not include service-role keys.
- The app declares no unnecessary permissions in `frontend/granite.config.ts`.

### 2. Real Device Launch

Show:
- Open the registered test build in the Toss app on a real device.
- Confirm the Toss navigation area shows the 삼선뉴스 brand name/icon.

Say:
- This confirms the uploaded Apps in Toss artifact, not just the browser dev server.

### 3. Home Feed

Show:
- Korean-first home feed.
- Polished May-range articles and clearly marked demo rumor/HITL examples.
- Empty/error states only if Supabase is unavailable.

### 4. Article Detail

Show:
- Open a news card.
- Confirm detail page layout, back navigation, and safe mobile scrolling.

### 5. Tone Preference

Show:
- Toggle `격식체` / `일상체`.
- Return to another article and confirm the tone preference remains.

### 6. Fact Label

Show:
- `검증됨`, `확인 필요`, `루머 주의`, `분석글`, and `전문가 검토 필요` badges.
- Rumor demo copy: `이 항목은 검증되지 않은 시연용 루머 데이터입니다.`
- Optional hidden POC: open the test URL with `?review=1` to show the read-only `검토 대상 보기` list.

Say:
- This is not a full admin approval system. It demonstrates automatic fact labeling plus review-target separation.
- The review screen is read-only and does not modify Supabase rows.

### 7. Neologism Bottom Sheet

Show:
- Tap highlighted terms such as `프롬프트 주입`, `가드레일`, or `HITL`.
- Confirm the explanation bottom sheet opens.

Say:
- The explanation comes from Supabase `neologisms`; unknown terms are not faked.

### 8. Original Source Link

Show:
- Tap `원문 보기`.
- Confirm the original URL opens through the Toss WebView/openURL path.

Say:
- Full translation and original source access are separate, so users can read the Korean body and still verify the source.
