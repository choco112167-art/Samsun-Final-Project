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
| Backend dev port | `8000` |
| Build output | `frontend/dist` |
| AIT bundle | `frontend/samsun-newsapp.ait` |

TDS Mobile official start guide requires `@toss/tds-mobile`, `@toss/tds-mobile-ait`, `@emotion/react@^11`, React 18, and `TDSMobileAITProvider`. The current package and `frontend/src/components/TossAppProvider.tsx` match that shape.

## Local Browser Development

Terminal 1:

```bash
copy .env.example .env
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

Terminal 2:

```bash
cd frontend
copy .env.example .env.local
npm install
npm run dev
```

Open:

```text
http://localhost:5173
http://localhost:8000/health
http://localhost:8000/articles?limit=5
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

3. Start the frontend and backend on all interfaces.

```bash
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
cd frontend
npm run dev
```

4. Set mobile frontend env before starting Vite:

```text
VITE_API_BASE_URL=http://<PC_INTERNAL_IP>:8000
VITE_ENABLE_TDS_PROVIDER=0
```

5. Check phone browser first:

```text
http://<PC_INTERNAL_IP>:5173
http://<PC_INTERNAL_IP>:8000/health
```

If the phone cannot open these URLs, check Windows Firewall or macOS firewall for ports `5173` and `8000`.

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

## Backend URL / CORS

Local browser:

```text
http://localhost:8000
```

Phone on same Wi-Fi:

```text
http://<PC_INTERNAL_IP>:8000
```

Toss uploaded bundle:

```text
https://<YOUR_HTTPS_BACKEND_DOMAIN>
```

Backend `CORS_ORIGINS` must include:

```text
http://localhost:5173
https://samsun-newsapp.private-apps.tossmini.com
https://samsun-newsapp.apps.tossmini.com
```

The frontend must never contain service-role keys. For final upload use only:

```text
VITE_API_BASE_URL=https://<YOUR_HTTPS_BACKEND_DOMAIN>
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
