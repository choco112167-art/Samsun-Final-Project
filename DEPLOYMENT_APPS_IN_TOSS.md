# Apps in Toss Deployment Checklist

Last checked: 2026-05-12

## Current Project Settings

| Item | Current value |
| --- | --- |
| Framework | React 18 + Vite + `@apps-in-toss/web-framework` |
| TDS | `@toss/tds-mobile`, `@toss/tds-mobile-ait` |
| Granite config | `frontend/granite.config.ts` |
| App name | `samsun-newsapp` |
| Display name | `삼선뉴스` |
| Vite dev port | `5173` |
| Runtime backend | None. Frontend reads Supabase directly. |
| Build output | `frontend/dist` |
| AIT bundle | `frontend/samsun-newsapp.ait` |

TDS Mobile official start guide requires `@toss/tds-mobile`, `@toss/tds-mobile-ait`, `@emotion/react@^11`, React 18, and `TDSMobileAITProvider`. The current package and `frontend/src/components/TossAppProvider.tsx` match that shape.

## Local Browser Development

```bash
cd frontend
copy .env.example .env.local
npm install
npm run dev
```

Open:

```text
http://localhost:5173
```

## Real Device / Toss App Testing

1. Put the PC and phone on the same Wi-Fi.
2. Find the PC internal IP.

Windows:

```powershell
ipconfig
```

macOS/Linux:

```bash
ip addr
```

3. Start the frontend on all interfaces.

```bash
cd frontend
npm run dev
```

4. Set mobile frontend env before starting Vite:

```text
VITE_SUPABASE_URL=https://srdvlalyucbokdwfkmcf.supabase.co
VITE_SUPABASE_ANON_KEY=<PASTE_SUPABASE_ANON_KEY_HERE>
VITE_ENABLE_TDS_PROVIDER=0
```

5. Check phone browser first:

```text
http://<PC_INTERNAL_IP>:5173
```

If the phone cannot open this URL, check Windows Firewall or macOS firewall for port `5173`.

## `.ait` Bundle

```bash
cd frontend
npm run build
npm run ait:build
```

Expected output:

```text
frontend/samsun-newsapp.ait
```

Do not commit `.ait`; it is a build artifact and is ignored by `.gitignore`.

## Toss Console Upload Flow

1. Open Apps in Toss console.
2. Workspace -> app `삼선뉴스`.
3. App release / bundle upload menu.
4. Upload `frontend/samsun-newsapp.ait`.
5. Run QR or test scheme in Toss app.
6. Test requirements:
   - Toss app login.
   - Workspace member account.
   - Age requirement satisfied.
   - At least one test execution before review/release.

## Supabase Runtime

The Apps in Toss bundle does not call a hosted server, Vercel Functions, or a FastAPI server at runtime. It reads:

```text
VITE_SUPABASE_URL=https://srdvlalyucbokdwfkmcf.supabase.co
VITE_SUPABASE_ANON_KEY=<anon key>
```

Supabase RLS must allow anon read access to the fields used by the app:

```text
id, url_hash, title, title_ko, source, category, published_at,
summary_formal, summary_casual, translation, fact_label, url
```

Backend/FastAPI CORS is deprecated for the app runtime. It can remain for local batch/admin debugging only.

The frontend must never contain service-role keys. For final upload use:

```text
VITE_SUPABASE_URL=https://srdvlalyucbokdwfkmcf.supabase.co
VITE_SUPABASE_ANON_KEY=<anon key>
VITE_ENABLE_TDS_PROVIDER=1
```

## WebView Notes

- Prefer Apps in Toss `openURL` for external links; the app has a browser fallback for local testing.
- Do not rely only on `target="_blank"` in Toss WebView.
- Do not include model files, videos, or large binary artifacts in `frontend/dist`.
- Keep `.ait` under 100 MB. Current demo bundle is expected to be small because no model files are included.

## Debugging

Android WebView:

```text
chrome://inspect/#devices
```

iOS WebView:

```text
Safari -> Develop menu -> target device -> WebView
```

USB is for WebView inspection/debugging, not for ordinary QR execution.
