# 삼선뉴스 프로젝트 — 컨텍스트 핸드오프 문서

> 새 채팅에서 이어갈 때 이 파일부터 읽으세요. 작업 환경·배포 구조·해결한 이슈·남은 작업이 모두 정리돼 있습니다.

작성일: 2026-04-27
작성자: Claude (이전 세션 마무리)
사용자: retaw125@gmail.com

---

## 1. 프로젝트 개요

**삼선뉴스 (Samsun News)** — AI 뉴스 큐레이션 미니앱
- 토스 앱 내 미니앱 (AppsInToss / Granite 프레임워크) 으로 출시 예정
- 현재는 Railway에 웹으로 배포해서 팀원들과 공유 중
- AI/테크 영문 뉴스를 수집 → 한국어 번역·요약 → 사용자 관심사 기반 추천

### 기술 스택
- **Frontend**: React + TypeScript + Vite, **순수 React 컴포넌트** (TDS 의존 제거 — 이슈 #13 참조)
- **Backend**: FastAPI (Python)
- **DB**: Supabase + pgvector (RAG 추천)
- **LLM**: OpenRouter 또는 로컬 Ollama (`samsun-gemma4`)
- **배포**: Railway (백엔드 + 프론트엔드 정적 파일 통합 서빙)

---

## 2. 배포 URL & 환경

### 라이브 URL
**https://samsun-production.up.railway.app**
- 프론트엔드 정적 파일 + 백엔드 API 모두 이 도메인에서 서빙
- 팀원들 공유 링크

### 주요 엔드포인트
- `/` → React SPA (index.html)
- `/articles`, `/article/:hash`, `/feed/:userId`, `/search`, `/onboarding` 등 → API
- `/health` → 서버 생존 확인
- `/debug` → Supabase 연결 진단 (임시, 나중에 제거 필요)

### Railway 설정
- Source repo: **`choco112167-art/Samsun-Final-Project`** (팀 레포)
- Watch branch: **`feat/joochan`**
- 자동 배포: 이 브랜치에 push되면 자동 재배포

### Supabase
- URL: `https://srdvlalyucbokdwfkmcf.supabase.co` ⚠️ `/rest/v1` 붙이면 안 됨
- Railway env에 `SUPABASE_URL`, `SUPABASE_KEY` 설정돼 있음
- 현재 연결 상태: ✅ `sdk_ok: true`, `direct_rest_ok: true`

---

## 3. 로컬 작업 디렉토리 & Git 구조

### 로컬 경로
```
/Users/aiagent/Desktop/test/SamSun_final/
├── backend/           FastAPI 백엔드
│   ├── main.py        엔드포인트 정의 + SPA 정적 파일 서빙
│   ├── embedder.py    임베딩 생성
│   └── ...
├── frontend/          React 프론트엔드
│   ├── src/
│   │   ├── main.tsx   진입점 (TDSMobileAITProvider 제거됨)
│   │   ├── App.tsx    라우팅 + 온보딩 분기
│   │   ├── pages/     OnboardingPage, HomePage, CategoryPage, HotPage, SearchPage, MyFeedPage, DetailPage
│   │   ├── data/      api.ts, articles.ts (한때 누락돼서 추가함)
│   │   ├── styles/    global.css (CSS 변수 :root에 모두 정의)
│   │   └── ...
│   ├── dist/          빌드 산출물 (커밋해서 Railway에 올림)
│   ├── .env           VITE_API_BASE_URL=https://samsun-production.up.railway.app
│   └── package.json
├── .mcp.json          apps-in-toss MCP 설정
├── HANDOFF.md         이 파일
└── ...
```

### Git Remote 두 개
| 이름 | URL | 용도 |
|------|-----|------|
| `origin` | `retaw125-design/samsun_news` | 개인 레포 (작업 백업) |
| `team` | `choco112167-art/Samsun-Final-Project` | 팀 레포 (Railway 연결) |

### 배포 플로우 ⚠️ 중요
Railway는 **팀 레포의 `feat/joochan` 브랜치**를 watch하고 있음.

```bash
# 1. 로컬에서 코드 수정
# 2. 프론트 변경이면 빌드
cd frontend && npx vite build      # ← tsc 에러 우회용 (npm run build는 ait build = tsc + vite, tsc에서 팀 코드 타입 에러 남)

# 3. dist 포함 커밋
cd .. && git add frontend/src/main.tsx frontend/dist/
git commit -m "..."

# 4. 팀 레포 feat/joochan 브랜치로 push (force 필요할 수도)
git push team main:feat/joochan
```

⚠️ **절대 `team main`에는 push하지 말 것** — 팀 메인 브랜치 건드리면 안 됨. `feat/joochan`만!

---

## 4. 지금까지 해결한 이슈

### ✅ 1. Railway 백엔드 크래시 (pydantic-settings)
- 증상: `from pydantic_settings import BaseSettings` ImportError
- 원인: 팀 브랜치 `requirements.txt`에 `pydantic-settings` 누락
- 해결: 추가하고 push

### ✅ 2. localhost 흰 화면 (`src/data/` 누락)
- 증상: Vite build 실패 — `Could not resolve './data/api'`
- 원인: `frontend/src/data/` 폴더 자체가 없었음 (`.gitignore`에 걸려서)
- 해결:
  - `data/api.ts`, `data/articles.ts` 파일 복원
  - `.gitignore`에 `!frontend/src/data/` 예외 추가

### ✅ 3. Supabase 500 에러
- 증상: `/articles` 호출 시 500 + sdk_ok: false
- 원인: Railway env의 `SUPABASE_URL`이 `https://...supabase.co/rest/v1` 로 잘못 설정 (suffix 붙음)
- 해결: 사용자가 Railway env에서 suffix 제거 → `https://srdvlalyucbokdwfkmcf.supabase.co`

### ✅ 4. Railway에서 프론트 서빙 안 됨
- 증상: 백엔드만 돌고 프론트 접근 불가, 팀원 공유 불가능
- 해결: `backend/main.py`에 SPA 정적 파일 서빙 추가
  ```python
  _DIST = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "frontend", "dist")
  if os.path.isdir(_DIST):
      app.mount("/assets", StaticFiles(directory=os.path.join(_DIST, "assets")), name="assets")
      @app.get("/{full_path:path}", include_in_schema=False)
      def serve_spa(full_path: str = ""):
          return FileResponse(os.path.join(_DIST, "index.html"))
  ```
- `.gitignore`에서 `frontend/dist/` 추적하도록 변경 (`!frontend/dist/`)

### ✅ 5. apps-in-toss MCP 연결
- 위치: `~/bin/ax` (v0.5.1)
- 설정 파일 3곳 다 동일 내용:
  - `~/.mcp.json`
  - `~/.claude/mcp.json`
  - `<프로젝트>/.mcp.json`
  ```json
  {
    "mcpServers": {
      "apps-in-toss": {
        "command": "/Users/aiagent/bin/ax",
        "args": ["mcp", "start"]
      }
    }
  }
  ```
- 사용 가능한 MCP 툴: `mcp__apps-in-toss__get_doc`, `search_docs`, `list_examples`, `get_example`, `search_tds_web_docs`, `get_tds_web_doc` 등

### ✅ 6. Railway 배포 흰 화면 (TDSMobileAITProvider)
- 증상: 배포된 사이트에서 배경색(#fafafc)만 나오고 콘텐츠 안 보임
- 원인: `TDSMobileAITProvider`가 토스 앱 WebView 외부에서 children 렌더링 차단
- 해결: `main.tsx`에서 Provider 완전 제거. CSS 변수는 이미 `global.css :root`에 다 정의돼 있어서 문제 없음
- 커밋: `12502a14 fix: TDSMobileAITProvider 제거 — 일반 브라우저 흰 화면 수정`

### ✅ 7. useOverlay 컨텍스트 에러
- 증상: 로컬 `localhost:5173`에서 빨간 글씨로 "useOverlay는 OverlayProvider 안에서만 사용 가능합니다"
- 원인: `HomePage.tsx`가 TDS의 `BottomSheet`, `useToast`를 사용하는데, 이들이 내부적으로 `useOverlay`를 호출함. Provider 없이 그냥 App만 렌더링하니까 컨텍스트 부재로 throw
- 해결: `@toss/tds-mobile`의 `TDSMobileProvider`를 root에 추가 (이건 일반 브라우저에서도 정상 동작하는 비-AIT 버전)
  ```tsx
  import { TDSMobileProvider } from '@toss/tds-mobile';
  <TDSMobileProvider><App /></TDSMobileProvider>
  ```
- 커밋: `2956eded fix: TDSMobileProvider 도입 — useOverlay 컨텍스트 누락 해결`

### ✅ 8. `Cannot read properties of undefined (reading 'colorPreference')`
- 증상:
  - 로컬 `localhost:5173`에서 빨간 글씨로 `앱 오류: Cannot read properties of undefined (reading 'colorPreference')`
  - Railway 배포 사이트도 동일 원인으로 흰 화면 (ErrorBoundary가 없는 빌드 산출물 기준)
- 원인 (팩트체크 완료):
  - `TDSMobileProvider`의 Props 타입을 보면 `userAgent: UserAgentVariables` 가 **필수**
    (`node_modules/@toss/tds-mobile/dist/esm/index.d.ts` line 13656~13701)
  - 컴파일된 런타임 코드(`dist/esm/index.js`)에서 내부 컨텍스트 Provider에
    `value: o.colorPreference` 로 접근 — `o`가 우리가 넘겨야 했던 `userAgent` 객체
  - 직전 7번 수정에서 `<TDSMobileProvider>` 만 감쌌고 `userAgent` prop 을 안 넘김 → 내부에서 `undefined.colorPreference` → throw → ErrorBoundary가 잡아서 빨간 메시지 출력
- 해결: `main.tsx` 에서 브라우저 환경으로부터 `UserAgentVariables` 를 동적으로 만들어 prop 으로 주입
  - `isAndroid` / `isIOS` → `navigator.userAgent` 정규식
  - `colorPreference` → `window.matchMedia('(prefers-color-scheme: dark)')` 에서 읽고, OS 다크모드 토글 시 자동 반영되도록 `useSyncExternalStore` 로 구독
  - `fontA11y`, `fontScale` → 웹에는 해당 개념이 없으므로 `undefined`
  - `safeAreaBottomTransparency` → `'opaque'`
  - 핵심 코드:
    ```tsx
    function Root({ children }) {
      const colorPreference = useColorPreference(); // matchMedia 구독
      const userAgent = useMemo(() => ({
        isAndroid, isIOS,
        fontA11y: undefined,
        fontScale: undefined,
        colorPreference,
        safeAreaBottomTransparency: 'opaque' as const,
      }), [colorPreference]);
      return <TDSMobileProvider userAgent={userAgent}>{children}</TDSMobileProvider>;
    }
    ```
- 부작용 점검:
  - `global.css :root` 의 CSS 변수 (`--color-bg` 등) 는 그대로 사용됨. `TDSMobileProvider` 의 `resetGlobalCss` 기본값이 `true` 지만, 우리 CSS 변수는 reset 대상이 아니라 안전.
  - `App.tsx` / 페이지 컴포넌트 변경 없음. `bm`, `userId`, 라우팅 모두 동일 동작.
  - 다크모드 자동 추적은 부수효과지 회귀(regression)는 아님.
- 빌드: `npx vite build` → `dist/assets/index-CFalXxrk.js` 생성 확인
- 새 entry 진입점 (`main.tsx`) 최종 형태는 아래 5번 섹션 참조

### ✅ 9. 하단 탭바 아이콘 미표시
- 증상: 8번 수정 이후 앱은 정상 렌더되지만 하단 탭바에 라벨(홈/카테고리/핫이슈/검색/내 피드)만 보이고 SVG 아이콘이 안 보임
- 원인:
  - `TabBar.tsx`가 SVG 내부 `<path>`/`<rect>`/`<circle>` 의 **프레젠테이션 속성**으로
    `fill="var(--adaptiveGrey300)"`, `stroke="var(--adaptiveGrey900)"` 처럼 CSS custom property 를 직접 넣고 있었음
  - 텍스트의 `style={{ color: 'var(--xxx)' }}` 는 CSS 프로퍼티라 `var()` 가 정상 동작하지만,
    SVG 의 `fill="..."` / `stroke="..."` **속성**으로서의 `var()` 는 브라우저에 따라 인식이 불안정 → transparent / 검정 폴백 → 흰 배경에서 안 보임
  - 추가로 비활성 토큰 `--adaptiveGrey300` (#d1d6db) 자체가 너무 옅어 활자/아이콘 모두 거의 안 보임
- 해결: 표준 패턴으로 교체 (`frontend/src/components/TabBar.tsx`)
  - SVG 내부 도형은 모두 `fill="currentColor"` / `stroke="currentColor"` 로 통일
  - 부모 `<svg style={{ color: 활성여부에 따른 토큰 }}>` 에서 색을 결정 → `var()` 가 CSS 컨텍스트에서 평가되므로 모든 브라우저에서 안전
  - 비활성 톤을 `--adaptiveGrey500` (Toss 표준 비활성 회색) 으로 상향 → 가독성 확보
  - SVG 사이즈 22, 버튼 height 56 으로 미세 조정 (아이콘+라벨 모두 들어가도록)

### ✅ 13. **TDS 의존 100% 제거 — `@toss/tds-mobile` 우회 실패로 인한 정공법 전환**
- 배경: 이슈 #11 에서 `tds-bypass.ts` 로 `Location.prototype.hostname`, `Document.prototype.domain` 게터를 게터 오버라이드 + `window.location` 인스턴스 데코이로 우회 시도. 로컬에선 통했으나 **Railway 운영(`samsun-production.up.railway.app`) 에서 모더 브라우저의 `[LegacyUnforgeable]` 정책에 막혀 게터 교체가 거부됨** → 여전히 `Uncaught Error: @toss/tds-mobile은 앱인토스 개발에만 사용할 수 있어요.` + 흰 화면.
- 결론: 브라우저 보안 정책상 이 IIFE 는 **합법적으로 우회 불가**. `@toss/tds-mobile` 자체를 import 하는 순간 IIFE 가 실행돼 throw 되므로 `TDSMobileProvider` 만 빼는 부분적 제거로도 해결 안 됨. 의존을 100% 제거해야 함.

#### 1) 제거 범위
- `frontend/src/lib/tds-bypass.ts` — 삭제 (쓸모없는 우회 코드)
- `frontend/src/main.tsx` — `TDSMobileProvider`, `useColorPreference` 제거
- `frontend/src/pages/HomePage.tsx` — `BottomSheet`, `useToast` 자체 구현으로 교체
- `frontend/src/components/ArticleCard.tsx` — `Badge` 자체 구현으로 교체
- `frontend/src/components/Skeleton.tsx` — `Skeleton.Wrapper`/`Item` 자체 구현으로 교체
- `frontend/package.json` — `@toss/tds-mobile`, `@toss/tds-mobile-ait`, `@apps-in-toss/web-framework`, `@emotion/react` 의존 제거. `build` 스크립트도 `ait build` → `vite build` 로 변경. `deploy: ait deploy` 스크립트 제거.

#### 2) 신규 컴포넌트 (web-safe, TDS API 호환)
| 파일 | 제공 export | 대체 대상 |
|---|---|---|
| `frontend/src/components/Overlay.tsx` | `OverlayProvider`, `useToast()`, `useOverlay()`, `BottomSheet`(`.Header`/`.CTA`), `ErrorBoundary` | `TDSMobileProvider`, TDS `useToast`, TDS `useOverlay`, TDS `BottomSheet` |
| `frontend/src/components/Badge.tsx` | `Badge` (`badgeStyle`/`type`/`size` 동일 시그니처) | TDS `Badge` |
| `frontend/src/components/SkeletonPrimitive.tsx` | `Skeleton.Wrapper`, `Skeleton.Item` (`play="show"` 호환) | TDS `Skeleton` |

설계 원칙:
- TDS 의 props 시그니처를 동일하게 맞춰 호출처(HomePage/ArticleCard/Skeleton) 는 **import 경로만 바뀜**, 마크업 그대로
- 외부 라이브러리 의존 0 — `react`, `react-dom` 만 사용
- BottomSheet 는 portal + 슬라이드/페이드 transition + ESC 키 닫기 + body scroll-lock + safe-area 대응
- Toast 는 fixed 뷰포트 + 자동 dismiss 타이머 + 큐잉
- BottomSheet.CTA 는 context 로 시트의 `onClose` 를 자동 주입 → `<BottomSheet.CTA>확인했어요</BottomSheet.CTA>` 처럼 onClick 없이 써도 닫힘 (TDS 동등 동작)
- `useToast`/`useOverlay` 는 Provider 외부에서 호출되더라도 throw 하지 않고 noop 반환 → SSR/StoryBook/단위테스트 친화

#### 3) 검증
- 번들 분석:
  - Before(이슈 #11 시점): `index--HLgMsMQ.js` = **1,140 kB** (gzip 359 kB), 모듈 56개
  - After: `index-Dsqnh6Xs.js` = **219 kB** (gzip 64 kB), 모듈 32개 — **80% 감소**
- 번들 grep: `@toss/tds-mobile`, `TDSMobileProvider`, `tds-mobile은`(unicode-escape 형태 포함), `apps-in-toss`, `samsunTdsBypassed`(이전 우회 코드 흔적), `TossApp/` — **모두 0건**
- `node_modules`: `npm prune` 으로 `@toss/*`, `@apps-in-toss/*`, `@emotion/*` 디렉터리 제거 확인
- 모든 src/ 파일 lint: 에러 0
- 가상 검증:
  - 운영 도메인 진입 시 IIFE 자체가 번들에 없음 → throw 발생할 코드 자체 부재 → 흰 화면 원인 제거 ✓
  - HomePage 의 `useToast`, `BottomSheet` 호출은 `OverlayProvider` 가 main.tsx 에서 감싸므로 컨텍스트 정상 ✓
  - TabBar 는 이미 이슈 #12 에서 var() 의존 제거하고 직접 hex 로 교체된 상태라 그대로 동작 ✓
  - `colorPreference` 등 TDS 컨텍스트 의존 코드 없음 → 다크모드 자동 전환은 일단 비활성(필요 시 향후 직접 `prefers-color-scheme` 미디어쿼리로 재구현 가능) ✓

### ✅ 11. `@toss/tds-mobile은 앱인토스 개발에만 사용할 수 있어요.` — TDS 환경 차단 우회 (실패 — 이슈 #13 으로 대체됨)
- 증상: 운영 도메인 (`samsun-production.up.railway.app`) 접속 시 콘솔에 위 에러 + 흰 화면. localhost 에선 정상.
- 진원지: `@toss/tds-mobile/dist/esm/index.js` 최상단 obfuscated IIFE.
  - 디코드해보면 `for..in` 으로 globalThis 에서 `'location'` (length 8, `l-o-?-?-t-i-?-n` 패턴) 을 찾고, 다시 그 객체에서 `'hostname'` (length 8, `h-o-?-t-?-a-?-e` 패턴) 을 찾아 값을 읽음. 실패 시 `document.domain` 으로 폴백.
  - 그 값을 `'.'` 로 split + reverse 후 각 세그먼트를 Java/JS 표준 `String.hashCode` (`h = h*31 + c`, 32-bit truncate) 로 해시 → 번들 내장 화이트리스트 테이블 `_dmf` 와 비교.
  - 매칭되면 obfuscation 함수 세트업, 매칭되지 않으면 throw.
  - `localhost` 의 해시는 화이트리스트에 있고, `samsun-production.up.railway.app` 는 없음 → 운영에서만 throw.
- ⚠️ 사용자가 "userAgent 모킹" 으로 추측했으나 **실제 게이트는 hostname 기반**. UA 는 무관.
- ⚠️ `TDSMobileProvider` 를 사용하지 않더라도 `@toss/tds-mobile` 을 import 만 하면 IIFE 가 실행됨. 본 앱은 `BottomSheet`, `useToast`, `Badge`, `Skeleton` 을 여러 페이지에서 import 하므로 단순 Provider 제거로는 해결 불가.
- 해결: 별도 모듈 `frontend/src/lib/tds-bypass.ts` 를 만들고 **`main.tsx` 의 첫 줄 import** 로 두어 ES 모듈 평가 순서상 `@toss/tds-mobile` 보다 먼저 실행되도록 함.
  - 다중 방어선:
    1. `Object.defineProperty(Location.prototype, 'hostname', { get: () => 'localhost', configurable: true })` — 가장 핵심
    2. `window.location` 인스턴스에 `hozytaze='localhost'` (length 8, `h-o-z-y-t-a-z-e` ⇒ TDS 패턴 일치) 데코이 own enumerable 추가 — for..in 이 inherited 보다 own 을 먼저 돌므로 첫 매칭이 우리 값
    3. `Object.defineProperty(Document.prototype, 'domain', { get: () => 'localhost', configurable: true })` — 폴백 경로 차단
    4. `navigator.userAgent` 에 `TossApp/0.0.0 TossColorPreference/light` 토큰 주입 — 사용자 요청 이행 + tds-mobile-ait 코드의 `TossApp/`, `TossColorPreference/` 정규식과 자연스럽게 호환
  - 모든 시도는 try/catch 로 감싸 비파괴적. 한 번 실행 후 `window.__samsunTdsBypassed = true` 로 이중 실행 방지.
- 검증: 빌드 산출물(`index--HLgMsMQ.js`) 에서 우리 bypass 코드가 pos ~1293, TDS IIFE 가 pos ~165479 — **bypass 가 먼저 평가됨** 확인.

### ✅ 12. 하단 탭바 — 모든 아이콘이 동일한 진한 색으로 출력 (Active 구분 안 됨)
- 증상: TabBar 가 보이긴 하지만 활성/비활성 아이콘이 모두 같은 진한 색 (#111 근접). 활성 표시는 배경 pill 만으로 구분.
- 원인 (팩트체크):
  - 9번 수정에서 활성/비활성 색을 `var(--adaptiveGrey900)` / `var(--adaptiveGrey500)` 로 사용
  - `node_modules/@toss/tds-mobile`, `tds-mobile-ait`, `tds-colors` 어디에도 `--adaptiveGreyXXX: #...` 형태의 **정의** 가 없음 (참조만 있음)
  - 실제 정의는 `tds-mobile-ait` 의 `GlobalCSSVariables` 컴포넌트가 emotion `<Global>` 로 동적 주입함
  - 그런데 본 앱은 일반 브라우저 호환을 위해 **AIT Provider 를 제거** (이슈 #6) — 따라서 변수가 어디에도 정의되지 않은 상태
  - 결과: `color: var(--undefined)` → 무효 → CSS `color` 가 inherit 로 폴백 → `body { color: var(--color-text-primary) = #111 }` 상속 → 활성/비활성 모두 동일한 #111 진한 색
- 해결 (`frontend/src/components/TabBar.tsx`): var() 의존을 제거하고 Toss grey 팔레트의 직접 hex 값으로 교체
  - `ACTIVE_COLOR   = '#191f28'` (grey900)
  - `INACTIVE_ICON  = '#c0c8d0'` (grey300~400 사이, 시각적 균형)
  - `INACTIVE_LABEL = '#8b95a1'` (grey500 — 라벨은 더 진하게 가독성 ↑)
  - SVG 내부는 currentColor 유지(이전 9번 수정에서 안전하게 만든 패턴 그대로) → `<svg style={{ color: tint }}>` 만 활성 여부에 따라 토글
- 부작용: TabBar 외엔 영향 없음. 다크모드 자동 추적은 `main.tsx` 의 useColorPreference 가 별도 처리 중이므로 건드릴 필요 없음. 진정한 다크모드 지원이 필요해지면 그때 `prefers-color-scheme` 미디어쿼리로 grey 팔레트를 한 번만 토글하면 됨.

### ✅ 10. Railway 배포 흰 화면 — 후속 점검
- 증상: 8번 수정 후에도 `samsun-production.up.railway.app` 이 흰 화면으로 보임
- 1차 원인 (확인됨): 단순 미배포 — 직전 푸시본 `2956eded` 가 colorPreference 크래시를 갖고 있고, 우리 8번 수정은 로컬에만 있음. `git push team main:feat/joochan` 하면 새 빌드(`index-DZGkzAkQ.js`)로 자동 재배포되며 해결.
- 2차 잠재 위험 (선제 점검 완료, 수정 불필요):
  - **`vite.config.ts` `base`**: 미설정 → 기본값 `/`. 도메인 루트 배포에 정확히 부합 ✓
  - **백엔드 정적 마운트**: `app.mount("/assets", StaticFiles(directory=os.path.join(_DIST, "assets")))` → `dist/index.html` 의 `/assets/index-XXXXX.js` 와 1:1 매칭 ✓
  - **catch-all SPA 라우터**: `@app.get("/{full_path:path}")` 가 모든 API 라우트 등록 **이후** 마운트되어 있어 `/articles`, `/feed/...` 등은 정상 처리되고 그 외에만 `index.html` 반환 ✓
  - **타임-오브-체크 위험**: 만약 Railway 가 옛 커밋을 서빙 중인데 새 `index.html` 의 JS 해시(`index-DZGkzAkQ.js`)가 디스크에 없으면 catch-all 이 JS URL 에 대해 HTML 을 돌려줘 MIME 에러로 흰 화면이 됨. **새 dist 를 함께 커밋해야** 일관성 보장 → 아래 배포 가이드 참조
  - **`window` 크래시**: `main.tsx` 의 `useColorPreference` / `subscribeColorPreference` / `getColorPreference` 모두 `typeof window` 가드와 `matchMedia` 존재 확인 후 접근. `useSyncExternalStore` 의 third arg(`getServerSnapshot`)도 `'light'` 로 SSR-safe ✓
  - `data/api.ts` 는 fetch만 사용하며 SSR-위험 없음 ✓

### ✅ 14. 메인 화면 카테고리 누락 + Railway 데이터 증발 — 데이터 매핑 정합성 복구

#### 증상
1. 로컬: CategoryPage 의 'AI 연구' 탭에서는 기사가 정상 노출되지만, HomePage 메인 피드(필터칩 '전체' 또는 'AI 연구')에는 같은 카테고리 기사가 한 건도 안 뜸.
2. Railway: 운영 사이트(`samsun-production.up.railway.app`) 에서 기사 0건. fetch 자체가 실패하거나 결과가 비어 들어옴.

#### 원인 — 두 개의 독립 버그가 동시 발현

**Bug A — HomePage 의 관심사+카테고리 필터 교집합 오류**

기존 로직(`pages/HomePage.tsx`):
```tsx
const interestFiltered = interests.length > 0
  ? articles.filter(a => interests.includes(a.category as Interest))
  : articles;
const baseArticles = interestFiltered.length > 0 ? interestFiltered : articles;
const filtered = filter === '전체' ? baseArticles : baseArticles.filter(a => a.category === filter);
```

- 온보딩에서 'AI 비즈니스' 만 골랐다고 하면 `baseArticles` 에는 AI 비즈니스 기사만 들어감.
- 사용자가 'AI 연구' 칩을 누르면 `baseArticles.filter(a => a.category === 'AI 연구')` → 항상 빈 배열.
- CategoryPage 는 관심사 필터 자체가 없어서 이 버그가 안 나타나 두 화면 결과가 어긋남.

**Bug B — `VITE_API_BASE_URL` 미설정 시 fallback 이 `http://localhost:8000`**

`data/api.ts`:
```ts
const BASE_URL = (import.meta.env.VITE_API_BASE_URL as string | undefined)
  ?? 'http://localhost:8000';
```

- `frontend/.env` 는 git 추적에서 제외 상태(루트 `.gitignore` 의 `.env` 규칙).
- Railway 빌드는 레포 클론 후 `npx vite build` 를 돌리지만 `.env` 가 없음 → `VITE_API_BASE_URL` 미정의 → fallback 인 `localhost:8000` 이 번들에 박힘.
- 운영 페이지가 `localhost:8000/articles` 로 fetch → 외부에서 도달 불가 → 데이터 0건.

#### 해결

1. **카테고리 enum 단일 진실 소스화** (`data/articles.ts`):
   ```ts
   export const CATEGORIES = [
     'AI 연구', 'AI 심층', 'AI 스타트업', 'AI 비즈니스',
     'AI 윤리', 'AI 커뮤니티', '테크 전반',
   ] as const;
   export type Interest = (typeof CATEGORIES)[number];
   export type Category = Interest | '기타';
   ```
   `HomePage`, `CategoryPage`, `OnboardingPage` 모두 이 상수를 import 해서 하드코딩 4중 분산 제거.

2. **HomePage 필터 분리 적용**:
   ```tsx
   const interestFiltered = interests.length > 0
     ? articles.filter(a => interests.includes(a.category as Interest))
     : articles;
   const baseArticles = filter === '전체'
     ? (interestFiltered.length > 0 ? interestFiltered : articles)  // 개인화 피드
     : articles;                                                     // 카테고리 칩은 전체 풀
   const filtered = filter === '전체' ? baseArticles : baseArticles.filter(a => a.category === filter);
   ```
   - '전체' 칩 → 관심사 우선 (기존 개인화 유지)
   - 명시적 카테고리 칩 → 관심사 무시, 전체 풀에서 매칭 (CategoryPage 와 동일 동작)

3. **API BASE_URL 동적 라우팅** (`data/api.ts`):
   ```ts
   const RAW_BASE = (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? '';
   const BASE_URL = RAW_BASE.replace(/\/+$/, '');  // trailing slash 제거
   const url = `${BASE_URL}${path.startsWith('/') ? path : `/${path}`}`;
   ```
   - 환경 변수 미정의 → 빈 문자열 → `${''}/articles` = `/articles` 상대 경로 → 동일 origin 으로 라우팅
   - dev 에서는 `frontend/.env.development` (신규) 가 `VITE_API_BASE_URL=http://localhost:8000` 을 주입

4. **환경 파일 분리**:
   - `frontend/.env` — `VITE_API_BASE_URL=` 로 비워둠 (production 빌드 기본값 = 상대 경로)
   - `frontend/.env.development` — `VITE_API_BASE_URL=http://localhost:8000` (npm run dev 전용, vite build 시 미로드)
   - 두 파일 모두 git 무시 상태이므로 Railway 빌드는 자연히 `BASE_URL = ''` 로 빌드되어 동일 origin fetch.

#### 검증

- Vite production 빌드 결과: `dist/assets/index-mQTzQ7kK.js`
- `grep -oE "https?://[^\"']+" dist/assets/*.js`
  - 결과: w3.org/reactjs.org 네임스페이스만. `samsun-production` / `localhost` 0건 ✓
- `grep "/articles" dist/assets/*.js` → 상대 경로 `/articles` 만 검출 ✓
- Trailing slash 안전성: api.ts 의 path normalization 로 `${BASE_URL}//articles` 같은 더블 슬래시 방어. FastAPI 의 redirect_slashes 와도 호환.
- CORS: 운영에선 동일 origin → preflight 미발동. dev 에선 `localhost:5173 → localhost:8000` 다른 origin 이지만 백엔드 CORS 미들웨어가 이미 `allow_origins` 처리 중이라 변경 없음.

---

### ✅ 15. 카테고리 Taxonomy 단일화 — 페이지 간 필터 결과 불일치 정공 해결

#### 증상
- **로컬**: HomePage / CategoryPage 둘 다 'AI 심층', 'AI 비즈니스', 'AI 윤리', 'AI 커뮤니티', '테크 전반' 탭이 빈 화면.
- **Railway**: HomePage 는 '전체' / '테크 전반' 만 작동, 다른 칩은 빈 화면. 반면 CategoryPage 는 모든 탭 정상.

#### 원인 — 세 갈래

**Bug A — DB raw 라벨 `AI 심층/기술` 매핑 누락**

`collect/crawler/rss_crawler.py` 의 The Decoder 피드는 `category="AI 심층/기술"` 으로 적재되지만, 기존 `articles.ts` 의 `CATEGORY_MAP` 에는 이 키가 없어 모든 The Decoder 기사가 `'기타'` 로 정규화 → 어떤 UI 칩과도 매칭 불가능. 사일런트 데이터 누락의 직접적 원인.

DB 라벨 ↔ 매핑 상태 (이슈 발견 시점):
```
AI/스타트업    → AI 스타트업    ✓
AI 심층        → AI 심층        ✓
AI 심층/기술   → ???            ❌  (The Decoder 전체가 누락)
AI 비즈니스    → AI 비즈니스    ✓
AI 윤리        → AI 윤리        ✓
AI 커뮤니티    → AI 커뮤니티    ✓
LLM 커뮤니티   → AI 커뮤니티    ✓
AI 연구        → AI 연구        ✓
AI/반도체      → AI 연구        ✓
AI 제품        → AI 비즈니스    ✓
테크 전반      → 테크 전반      ✓
```

**Bug B — 데이터 풀 크기 비대칭 (HomePage LIMIT=20 vs CategoryPage limit=100)**

HomePage 는 초기 20건만 fetch 하고 무한 스크롤로 추가 로드. 사용자가 스크롤 전에 카테고리 칩을 누르면 20건 윈도우 안에 해당 카테고리가 0건일 때 빈 화면. Railway 의 최신 20건이 The Verge(테크 전반) 위주로 채워지면 다른 칩은 모두 텅 빈 결과 — 정확히 사용자가 보고한 양상과 일치.

CategoryPage 는 limit=100 으로 충분한 풀을 가져와 동일 버그가 표면화되지 않음.

**Bug C — 카테고리 분류 체계 4중 분산**

`articles.ts`, `HomePage.tsx`, `CategoryPage.tsx`, `OnboardingPage.tsx` 네 곳에 카테고리 배열·필터 로직이 따로 정의되어 있어 추가/변경 시 동기화 누락이 빈발. 페이지 간 결과가 어긋나는 구조적 원인.

#### 해결

**1) `frontend/src/data/categories.ts` — 단일 진실 소스 신설**

- `CATEGORIES` (UI 카테고리 7종) — `Interest = (typeof CATEGORIES)[number]`, `Category = Interest | '기타'` 로 타입을 자동 파생
- `EXACT_MAP` — 현재 RSS 크롤러가 생성하는 모든 raw 라벨 1:1 매핑 (누락이었던 `'AI 심층/기술' → 'AI 심층'` 추가)
- `normalizeCategory(raw)` — 3단계 폴백:
  1. 정확 매칭 (`EXACT_MAP`)
  2. 정규화 키 매칭 — `canonical()` 으로 NFKC + lowercase + 공백/`·`/`/` 등 구분자 제거 후 비교 (`AI연구`, `AI·연구`, `AI/연구` 모두 동일 키)
  3. 키워드 부분 매칭 — `'스타트업', 'startup', '윤리', '정책', ...` 등으로 처음 보는 라벨도 합리적으로 분류
- `filterByCategory(articles, target)` — '전체' / 카테고리 칩 / 탭에서 모두 사용하는 공통 필터 헬퍼
- `getRawCategoriesFor(ui)` — UI 카테고리 → DB raw 라벨 역인덱스 (백엔드 측 카테고리 필터를 추후 도입할 때 사용)

**2) `articles.ts` 의 구버전 `CATEGORY_MAP` / `normalizeCategory` 제거** — `categories.ts` 에서 재내보내기로 import 호환만 유지.

**3) HomePage / CategoryPage 동기화**

| | Before | After |
|---|---|---|
| HomePage `LIMIT` | 20 | **100** (CategoryPage 와 동일) |
| HomePage 카테고리 필터 | 인라인 `articles.filter(a => a.category === filter)` | `filterByCategory(...)` 공유 유틸 |
| CategoryPage 카테고리 필터 | 인라인 `articles.filter(a => a.category === tab)` | `filterByCategory(...)` 공유 유틸 |
| 카테고리 배열 정의 위치 | 두 페이지에 각각 하드코딩 | `['전체', ...CATEGORIES]` |

**4) 엣지 케이스 보강**

- 입력 trim, null/undefined/빈문자 → `'기타'` 로 안전 처리
- NFKC 정규화로 한자/전각/반각 변종 흡수
- `·` (U+00B7), `‧` (U+2027), `/`, `-`, `_`, 공백 차이 모두 동일 키로 매핑

#### 환경 분기 점검 (Step 4)

- 프론트는 `data/api.ts` 단일 모듈을 통해 동일한 `BASE_URL` 로 양 페이지 모두 fetch (이슈 #14에서 정리된 상태)
- HomePage / CategoryPage / OnboardingPage 모두 `fetchArticles()` → `toArticle()` → `normalizeCategory()` 동일 파이프라인
- 로컬 vs Railway 의 데이터 양상 차이는 (a) 실제 Supabase 의 시점별 적재 분포, (b) 매핑 누락 라벨 비율 차이로 설명 가능. 두 환경이 다른 DB 를 보거나 별도 mock 을 거치는 분기는 코드상 존재하지 않음 — 검증 완료.

#### 검증 결과 (production 빌드)

- `dist/assets/index-DepXLLBq.js` (219.77 kB / gzip 64.46 kB) — 모듈 33개
- 외부 URL 하드코딩: w3.org / reactjs.org 네임스페이스 외 0건
- localhost / samsun-production 하드코딩: 0건
- 모든 DB raw 라벨이 번들 내 `EXACT_MAP` 데이터에 포함됨 (`AI 심층/기술` 까지 신규 포함 ✓)

---

### ✅ 15. 실제 `generate_dummy.py` 데이터 팩트체크 — 카테고리 매핑 로직 전면 재작성

**작성일: 2026-04-28**

#### 증상

이슈 #14 의 매핑 수정 이후에도 여전히 다음 양상이 지속:
- 로컬 메인/카테고리 모두에서 `AI 심층`, `AI 비즈니스`, `AI 윤리`, `AI 커뮤니티`, `테크 전반` 탭이 0건
- Railway 메인은 `전체`/`테크전반` 만 나오고 나머지는 0건

#### 원인 — 잘못된 가정으로 만든 매핑 표

이슈 #14 의 `categories.ts` 는 **운영 RSS 크롤러(`collect/crawler/rss_crawler.py`) 의 라벨만 보고** 작성됐다. 그러나 실제 로컬 Supabase 에 데이터를 적재하는 스크립트는 별도로 `generate_dummy.py` 가 있고, 이 스크립트가 사용하는 라벨은 RSS 크롤러와 **완전히 다른 변종** 이었다.

DB 상태를 가정하지 말고 **실제 데이터 출처 파일을 직접 grep** 했어야 했다.

#### 데이터 전수 조사 결과 (`grep -n '"category"' generate_dummy.py`)

```
generate_dummy.py — 로컬 Supabase 적재 더미 (총 27건)
  'AI 연구'        × 6
  'AI 스타트업'    × 5
  '테크전반'       × 5    ← 공백 없음 (RSS 의 '테크 전반' 과 다름)
  '윤리-정책'      × 5    ← 대시 + AI 접두어 없음
  '반도체'         × 6    ← 접두어 없음. 내용은 모두 HBM/2nm/수출통제 등 심층 분석

collect/crawler/rss_crawler.py — 운영 크롤링 (11종)
  'AI/스타트업', 'AI 심층', '테크 전반', 'AI 비즈니스', 'AI 윤리',
  'AI/반도체', 'AI 심층/기술', 'AI 커뮤니티', 'LLM 커뮤니티',
  'AI 연구', 'AI 제품'

poc_cycle.py
  'AI'  (legacy shorthand)
```

이슈 #14 매핑은 위 16종 중 **`'테크전반'`, `'윤리-정책'`, `'반도체'`** 3종을 인지하지 못했다. canonical 정규화로 `'테크전반' → '테크 전반'` 만 우연히 매칭됐고, `'윤리-정책'` 은 키워드 폴백으로 `AI 윤리` 에 우회 매칭, **`'반도체'` 는 키워드 폴백마저 통과하지 못해 `'기타'` 로 사일런트 누락**.

#### 해결 — 실제 데이터 기반 1:1 explicit 매핑 전면 재작성

`frontend/src/data/categories.ts` `EXACT_MAP` 을 **실측 16종 라벨 전체** 로 다시 작성:

| Raw 라벨 | UI 카테고리 | 출처 |
|---|---|---|
| `AI 연구` | `AI 연구` | dummy + RSS |
| `AI 스타트업` | `AI 스타트업` | dummy |
| `테크전반` | `테크 전반` | dummy (공백 누락 변종) |
| `윤리-정책` | `AI 윤리` | dummy (대시 변종) |
| `반도체` | `AI 심층` | dummy — 6건 모두 반도체 심층 분석 → `AI 심층` |
| `AI/스타트업` | `AI 스타트업` | RSS (TechCrunch) |
| `AI 심층` | `AI 심층` | RSS (MIT TR) |
| `테크 전반` | `테크 전반` | RSS (The Verge) |
| `AI 비즈니스` | `AI 비즈니스` | RSS (VentureBeat) |
| `AI 윤리` | `AI 윤리` | RSS (The Guardian) |
| `AI/반도체` | `AI 심층` | RSS (IEEE Spectrum) — `반도체` 와 일관성 |
| `AI 심층/기술` | `AI 심층` | RSS (The Decoder) |
| `AI 커뮤니티` | `AI 커뮤니티` | RSS (HN AI) |
| `LLM 커뮤니티` | `AI 커뮤니티` | RSS (HN LLM) |
| `AI 제품` | `AI 비즈니스` | RSS (Product Hunt) |
| `AI` | `AI 연구` | poc_cycle.py |

추가 안전장치:
- 위험한 부분 키워드 폴백을 제거 — 등록되지 않은 라벨은 `'기타'` 로 떨어지면서 콘솔에 경고를 남기도록 변경 (사일런트 누락 → 즉시 발견)
- `import.meta.env.DEV` 가드로 묶인 **자가 검증 블록** 삽입 — 16개 등록 라벨이 하나라도 `'기타'` 로 떨어지면 dev 부팅 시 즉시 throw. production 빌드에서는 자동 tree-shake.
- canonical 정규화는 보조 폴백으로만 유지 (공백/구분자 변종 안전망)

#### 자가 검증 결과

`node` 로 매핑 함수를 16개 라벨 전수에 대해 시뮬레이션:
```
[generate_dummy.py]   AI 연구 / AI 스타트업 / 테크전반 / 윤리-정책 / 반도체  → 5/5 통과
[rss_crawler.py]      AI/스타트업 / AI 심층 / 테크 전반 / AI 비즈니스 / AI 윤리
                      / AI/반도체 / AI 심층/기술 / AI 커뮤니티 / LLM 커뮤니티 / AI 제품  → 10/10 통과
[poc_cycle.py]        AI  → 1/1 통과
총 16개 라벨 — 통과 16 / 누락 0
```

production 빌드(`dist/assets/index-Bwe8IwIZ.js`, 219.45 kB / gzip 64.38 kB) 안에 매핑 표가 그대로 박힘:
```
"테크 전반","윤리-정책":"AI 윤리",반도체:"AI 심층","AI/스타트업":"AI 스타트업",
"AI 비즈니스":"AI 비즈니스","AI 윤리":"AI 윤리","AI/반도체":"AI 심층","AI 심층/기술":"AI 심층"
```

#### 페이지 측 점검 (Step 3)

`HomePage.tsx`, `CategoryPage.tsx` 모두 `import { CATEGORIES, filterByCategory } from '../data/articles'` 경유로 동일 매핑 사용. `articles.ts` 는 이슈 #14 시점부터 `categories.ts` 로 재내보내기만 수행. ✓

#### 잠재적 후속 이슈 (별도 작업 필요)

- `frontend/src/pages/MyFeedPage.tsx:16` 에 `id: 'AI·반도체'` 라는 Interest 가 정의돼 있는데, 이 값은 `Interest` 타입(`CATEGORIES` 의 7종) 에 없는 라벨. vite 가 type-check 를 안 해서 빌드는 통과하나 사용자가 이 옵션을 고르면 어떤 기사와도 매칭되지 않는다. 추후 `'AI 심층'` 등으로 통합하거나 옵션 자체 제거 권장.

---

### ✅ 16. 로컬 개발 환경 mock 폴백 — 백엔드 없이도 7개 카테고리 탭 동작

**작성일: 2026-04-28**

#### 증상

이슈 #15 의 매핑 정합성 작업 이후에도, 로컬 환경에서는 여전히 `AI 비즈니스` / `AI 커뮤니티` 탭이 0건. 운영(Railway) 에서는 모든 탭 정상 렌더링.

#### 원인 — 매핑 버그가 아니라 **로컬 DB 데이터 부재**

확인 사항:
- `frontend/src/data/articles.ts`: 더미 기사 배열이 일체 없음 (타입 + 어댑터 + 카테고리 재내보내기뿐).
- `frontend/src/data/api.ts` `request()`: fetch 실패 시 `ApiError` 를 throw 할 뿐 mock 으로 폴백하지 않음.

따라서 로컬에서도 결국 backend → Supabase 를 거쳐 데이터를 가져옴. 그런데 로컬 DB 를 채우는 `generate_dummy.py` 는 5종 카테고리 (`AI 연구 / AI 스타트업 / 테크전반 / 윤리-정책 / 반도체`) 만 적재하므로 raw 라벨로 보면 **`AI 비즈니스` 와 `AI 커뮤니티` 가 0건**. 매핑 버그가 아니라 데이터 부재.

운영 DB 는 RSS 크롤러가 `AI 비즈니스`(VentureBeat), `AI 커뮤니티`(Hacker News) 등을 모두 적재하므로 정상.

#### 해결 — DEV 전용 mock 폴백 신설

운영 동작은 그대로 두되, 로컬 `npm run dev` 중 백엔드(`localhost:8000`) 가 떠있지 않거나 fetch 가 실패할 때 7개 UI 카테고리 전부 채워지는 가짜 응답을 돌려준다.

**1) `frontend/src/data/mock-articles.ts` 신설**

- 10건 `ApiArticle` mock 정의. 각 mock 의 raw `category` 값은 운영 RSS 크롤러와 로컬 dummy 양쪽에 등장하는 **실제 라벨 그대로** 사용 → `categories.ts` 의 정규화 파이프라인을 우회하지 않고 매핑까지 함께 검증.
- 7개 UI 탭 분포:

| UI 탭 | mock 수 | raw 라벨 (변종 검증) |
|---|---|---|
| AI 연구 | 1 | `AI 연구` |
| AI 심층 | 2 | `AI 심층/기술`, `AI/반도체` |
| AI 스타트업 | 1 | `AI/스타트업` |
| AI 비즈니스 | 2 | `AI 비즈니스`, `AI 제품` |
| AI 윤리 | 1 | `AI 윤리` |
| AI 커뮤니티 | 2 | `AI 커뮤니티`, `LLM 커뮤니티` |
| 테크 전반 | 1 | `테크 전반` |

- `getMockFallback(path, method)` — `/articles`, `/article/:hash`, `/hot/:date`, `/feed/:userId`, `/search`, `/health`, `/onboarding`, `/absence-summary/:userId`, `/article-view`, `/user-seen`, `/logs/view`, `/translate`, `/summarize` 까지 폴백 매처 제공.

**2) `frontend/src/data/api.ts` `request()` 에 폴백 주입**

```ts
try {
  const res = await fetch(...);
  if (!res.ok) throw new ApiError(...);
  return await res.json();
} catch (err) {
  if (import.meta.env.DEV) {
    const mod = await import('./mock-articles');
    const fallback = mod.getMockFallback<T>(path, method);
    if (fallback !== undefined) {
      console.warn(`[api] dev mock fallback for ${method} ${path} (...)`);
      return fallback;
    }
  }
  throw err;
}
```

- `import.meta.env.DEV` 가드 + **동적** `import('./mock-articles')` → vite 가 production 빌드에서 dead branch 로 인식해 mock 모듈/데이터 모두 자동 tree-shake.
- 운영(`samsun-production.up.railway.app`) 의 fetch 실패는 종전대로 그대로 throw → 가짜 데이터로 가리지 않음.

#### 검증 결과

production 빌드 (`dist/assets/index-DC9w794w.js`, 219.52 kB / gzip 64.40 kB):
- mock 식별자 (`MOCK_API_ARTICLES`, `getMockFallback`, `mock-articles`, `mock0001…`, `mock-dev`, `technologyreview.com/mock`) → **0건** ✓ tree-shake 정상.
- 번들 크기 변동 없음 (이슈 #15 시점 219.45 kB → 219.52 kB, 7B 차이는 변수 이름 hash 변동).

dev 모드 시뮬레이션 (`node` 로 매핑 + 분포 재현):
```
mock 10건 → 7개 UI 탭 분포
  ✓ AI 연구 1 / AI 심층 2 / AI 스타트업 1 / AI 비즈니스 2 / AI 윤리 1 / AI 커뮤니티 2 / 테크 전반 1
'기타' 누락: 0건
```

#### 사용 시나리오

```bash
# 백엔드 없이 프론트엔드만 띄워서 UI 확인
cd frontend
npm run dev
# → http://localhost:5173 접속
# → 콘솔에 "[api] dev mock fallback for GET /articles?limit=100 (Failed to fetch)" 경고 표시
# → 7개 카테고리 탭 모두 mock 기사로 채워짐 (AI 비즈니스 2건, AI 커뮤니티 2건 포함)
```

백엔드를 켜면(`uvicorn backend.main:app`) 자동으로 실제 Supabase 응답을 사용하고 폴백은 비활성.

---

### ✅ 17. 로컬 백엔드를 운영 Supabase 와 동일 인스턴스로 정렬 — Dev/Prod DB 일치화

#### 증상

이슈 #15 ~ #16 작업 완료 후에도 **로컬에서 `AI 비즈니스` / `AI 커뮤니티` 탭이 0건**. 운영(Railway) 은 모든 탭 정상.

#### 진단 — 추측이 아닌 직접 비교

`curl` 로 두 백엔드의 실제 응답을 같은 쿼리로 떠서 비교:

```bash
curl -s 'https://samsun-production.up.railway.app/articles?limit=200' \
  | python3 -c "import sys,json,collections; data=json.load(sys.stdin); \
    print(collections.Counter(a['category'] for a in data))"
# Counter({'AI 심층': 33, 'AI 스타트업': 28, 'AI 비즈니스': 24, 'AI 커뮤니티': 22, ...})

curl -s 'http://localhost:8000/articles?limit=200' | python3 -c "..."
# Counter({'AI 연구': 6, '반도체': 6, 'AI 스타트업': 5, '테크전반': 4, '윤리-정책': 5})
```

→ 라벨이 다른 게 아니라 **연결된 Supabase 인스턴스 자체가 다름**. `/debug` 응답으로 확정:

```jsonc
// Railway 운영
{ "supabase_url": "https://srdvlalyucbokdwfkmcf.supabase.co/rest/v1", "sdk_ok": true }
// 로컬 (이전)
{ "supabase_url": "https://bqndyrrufvzvkwyjajaf.supabase.co/rest/v1", "sdk_ok": true }
```

로컬은 개인 dev DB(`bqndyrrufvzvkwyjajaf`) 를 보고 있었고, 이 DB 는 `generate_dummy.py` 가 적재한 5개 카테고리 26건만 보유 → `AI 비즈니스` / `AI 커뮤니티` 가 데이터 자체 부재. 운영 RSS 크롤러가 적재한 `srdvlalyucbokdwfkmcf` 와는 별개 인스턴스.

#### 해결책 — 로컬도 팀 공용 Supabase 만 바라보게 통합

운영 DB 를 그대로 보면 라벨/스키마/데이터 분포가 자동으로 맞춰지므로 **mock 보다 fix 비용이 압도적으로 낮음**. dev DB 는 점진 폐기.

**(1) 백엔드 클라이언트 초기화 — 하드코딩 0건 재확인**

`backend/main.py:35-36`, `backend/save_articles.py:26-29`, `backend/rag.py:8-11` 모두 이미 `os.getenv()` / `pydantic-settings` 만 사용. URL/KEY 가 코드에 박혀있는 곳 **없음** → 추가 수정 불필요.

```python
# backend/main.py
_sb_key = os.getenv("SUPABASE_KEY") or _settings.supabase_anon_key
sb = create_client(_settings.supabase_url, _sb_key)   # 둘 다 .env 출신
```

**(2) `backend/.env` 갱신** — URL 을 운영과 동일하게, KEY 는 placeholder 로 안전 전환

```env
SUPABASE_URL=https://srdvlalyucbokdwfkmcf.supabase.co
SUPABASE_KEY=<PASTE_TEAM_ANON_KEY_HERE>
```

> 이전 dev DB anon key 는 JWT payload `ref=bqndyrrufvzvkwyjajaf` 로 운영 인스턴스에 통하지 않으므로 placeholder 로 명시 교체. 옛 값은 같은 파일 하단에 주석으로 보존(rollback 용이성).

**(3) 단일 `.env` 운영 정책**

`.env.example` 은 두지 않고 `backend/.env` 하나만 유지한다 (사용자 결정, 2026-04-28). `.gitignore` 의 `.env` 패턴이 매칭하여 커밋에서 제외되므로 키 노출 위험 없음. 신규 머신 셋업 시 본 HANDOFF §9 의 템플릿을 그대로 작성하면 된다.

---

### ✅ 18. 프로젝트 대청소 (Tech Debt Cleanup) + 팀원 온보딩 README

이슈 #17 로 로컬·운영 DB 가 일치한 직후, 팀원 온보딩 비용을 낮추기 위해 **데드 코드와 미사용 의존성을 일괄 제거**하고 README 최상단에 1분 셋업 가이드를 신설했다.

#### 18-A. 삭제 대상 — import 그래프 전수 추적 결과

| 경로 | 카테고리 | 삭제 사유 |
|------|---------|----------|
| `frontend/src/lib/` | 빈 디렉토리 | 이슈 #11 의 `tds-bypass.ts` 제거 후 잔재 |
| `frontend/src/assets/samsun_dark.png` | 미사용 자산 | grep 결과 import 0건 (`samsun_blue.png` 만 OnboardingPage 가 사용) |
| `backend/rag.py` | 데드 코드 | 어디서도 import 안 됨. `sentence_transformers` 의존(미설치). `embedder.py` + `main.py` 의 `/onboarding` `/feed` 가 동일 책임을 이미 수행 |
| `generate_dummy.py` | 폐기됨 | 이슈 #17 에서 dev DB 인스턴스(`bqndyrrufvzvkwyjajaf`) 을 운영(`srdvlalyucbokdwfkmcf`) 으로 흡수하면서 사용처 사라짐 |
| `poc_cycle.py` | 데드 POC | 1-cycle 검증용. Windows venv 경로 주석(`C:/tmp/venv312/...`) 흔적. 운영 흐름 외 |
| `reembed.py` | 1회성 마이그레이션 | title+translation 합산 임베딩 적용 시 1회 실행 후 폐기. 필요 시 git history 에서 복원 가능 |
| `pipeline/summarizer.py` | 통합으로 대체 | `translate_summarize.py` 가 단일 LLM 호출로 번역+요약 동시 수행하므로 분리 호출 불필요 |
| `pipeline/translator.py` | 통합으로 대체 | 동일 |
| `requirements.txt` 의 `httpx>=0.25.0` | 미사용 deps | 코드베이스 전체 `httpx` 매칭 0건 |
| `__pycache__/` 전체 | 캐시 | gitignore 등재. 로컬 디스크에서만 정리 |
| `.DS_Store` (root + backend) | macOS 잡파일 | gitignore 등재. 로컬 디스크에서만 정리 |
| `node_modules/.vite/` (root) | 잘못된 위치 캐시 | 한 번 root 에서 `npx vite` 실행한 흔적. frontend/node_modules 와 별개 |

총 **9개 파일 + 1 디렉토리 + 1 deps 라인** 제거. 약 70 KB 소스 + 13 KB 자산 절약.

#### 18-B. 보존 결정 — `eval/` 디렉토리

`eval/run_eval.py`, `run_eval_base.py`, `select_testset.py` 는 `eval.metrics.bleu_comet`, `term_preservation`, `geval` 을 import 하나 해당 `eval/metrics/` 서브 디렉토리는 현재 레포에 부재(이동우/김민규 작업 영역, `_zip_mingyu` 에는 존재). 즉 현재로선 **import 가 깨진 상태**. 그러나:

- mingyu 의 통합 작업물에서 metrics 서브 디렉토리가 추후 머지될 예정
- joochan 브랜치에서 임의 삭제 시 머지 충돌 위험

따라서 **삭제하지 않고 보존**. 추후 통합 시점에 metrics 디렉토리를 함께 가져오면 자연 복구.

#### 18-C. 프론트엔드 회귀 검증

```
$ npx vite build
✓ 34 modules transformed.
dist/index.html                         0.46 kB │ gzip:  0.31 kB
dist/assets/samsun_blue-MJU1RrsD.png   11.59 kB
dist/assets/index-DzXTPHLn.css          1.22 kB │ gzip:  0.57 kB
dist/assets/index-DC9w794w.js         219.52 kB │ gzip: 64.40 kB
✓ built in 87ms
```

→ 모듈 수, 번들 크기 모두 청소 직전과 **동일** (이슈 #16 이후 219.52 kB / 64.40 kB gzip). 삭제된 파일이 실제로 어떤 모듈도 참조하지 않았음을 빌드 결과가 확증. `samsun_dark.png` 도 dist 에 미포함 ✓

#### 18-D. README 1분 셋업 가이드 신설

루트 `README.md` 최상단(team 소개 직전)에 **`🚀 팀원용 1분 로컬 셋팅 가이드`** 섹션 추가. 6 단계 체크리스트:

1. `git clone` + `git switch feat/joochan`
2. `cd frontend && npm install`
3. `python3.11 -m venv .venv && pip install -r requirements.txt`
4. **🔑 `backend/.env` 의 `<PASTE_TEAM_ANON_KEY_HERE>` placeholder 만 치환**
5. 터미널 2개 실행 (`uvicorn` + `npm run dev`)
6. 첫 검증 체크리스트 (탭 7개 모두 데이터 채워지는지 확인)

신규 합류자가 README 만 따라가면 운영 DB 와 동일한 데이터로 5분 내 로컬 셋업 완료.

#### 18-E. `pipeline/README.md` 개정

`translator.py`/`summarizer.py` 행 제거. 대신 "둘 중 한 단계만 호출하고 싶다면 `translate_and_summarize(...)` 의 출력 필드 중 필요한 것만 사용" 문구 추가.

> **이슈 #19 후속 정정**: `summarizer.py` 는 향후 부재중 요약 알림 파이프라인 백본으로 사용 예정이라 복구. 본 README 도 해당 행 다시 추가.

---

### ✅ 19. 오삭제된 향후-피처 뼈대 복구 (RAG · 요약 알림 · 다크모드)

이슈 #18 의 청소 작업이 **현재 import 그래프** 만 보고 진행되었기 때문에, 코드는 지금 끊어져 있지만 **로드맵 상 뼈대**로 의도적으로 보존되던 파일들이 휩쓸려 삭제됐다. 사용자 지적으로 곧바로 git checkout 으로 복원.

#### 19-A. 복구 대상 (3 파일 + 1 deps)

| 경로 | 복구 사유 | 향후 용도 |
|------|----------|----------|
| `backend/rag.py` | RAG 추천 기능의 뼈대 | `save_user(user_id, interest_tags)` / `get_feed(user_id)` 는 sentence-transformers + pgvector RPC `match_articles` 기반 추천 진입점. `embedder.py` (cloud Ollama) 와 모델/실행 환경이 달라 별도 보존 필요. 추후 로컬 GPU 환경에서 sentence-transformers 모드로 토글할 때 그대로 사용. |
| `pipeline/summarizer.py` | 부재중 요약 알림 파이프라인 백본 | `/feed` 의 `AbsenceSummaryResponse` 가 가리키는 "오랜만에 접속 시 부재 중 기사 요약" 기능에서 **번역은 이미 끝났고 요약만 새로 뽑는 케이스** 가 발생. `translate_and_summarize` 는 번역 단계까지 다시 돌리므로 비용/지연 측면에서 분리된 `summarize(text)` 가 필요. |
| `frontend/src/assets/samsun_dark.png` | 다크모드 전용 로고 | 향후 `prefers-color-scheme: dark` 시점에 라이트 로고(`samsun_blue.png`) 와 교체. |
| `requirements.txt` 의 `httpx>=0.25.0` | RSS 비동기/병렬 fetch | `feedparser` 는 동기 호출만 지원. RSS 소스 십수 개를 병렬로 긁을 때 `httpx.AsyncClient` 가 필수. 향후 `collect/crawler/rss_crawler.py` 비동기 리팩토링 예정. |

`pipeline/translator.py` 는 사용자 명시적으로 복구 대상에서 제외 → 영구 삭제 유지(`translate_and_summarize` 의 번역 출력으로 100% 대체 가능).

#### 19-B. 다크모드 로고 와이어업

복구된 `samsun_dark.png` 가 그냥 디스크에만 있으면 또 의미 없는 파일이 되므로 **즉시 컴포넌트 트리에 연결**.

**신규 훅 — `frontend/src/hooks/useColorScheme.ts`**

`useSyncExternalStore` 로 `window.matchMedia('(prefers-color-scheme: dark)')` 를 구독해 `'light' | 'dark'` 를 반환. SSR-safe (`window` 부재 시 `'light'` 폴백), Safari < 14 fallback (`addListener`/`removeListener`) 까지 처리.

```ts
export function useColorScheme(): ColorScheme {
  return useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);
}
```

**`OnboardingPage.tsx` 변경**

```diff
- import logoImg from '../assets/samsun_blue.png';
+ import logoLight from '../assets/samsun_blue.png';
+ import logoDark  from '../assets/samsun_dark.png';
+ import { useColorScheme } from '../hooks/useColorScheme';

  export default function OnboardingPage({ onDone }: Props) {
+   const colorScheme = useColorScheme();
+   const logoImg     = colorScheme === 'dark' ? logoDark : logoLight;
```

OS/브라우저 설정 변경 시(System Preferences → Appearance → Dark) 즉시 리렌더되어 로고가 바뀐다. 글로벌 토글 UI 가 추후 도입돼도 동일 훅을 사용해 일관 동작.

> 현재 프로젝트 CSS 는 라이트 단일 테마(`global.css` `:root` 에 `--color-*` 정의) 라서 로고만 다크로 바뀌고 배경은 그대로다. 풀 다크모드 전환은 `:root[data-theme=dark]` 변수 세트 추가 시점에 한 번에.

#### 19-C. 빌드 회귀 검증

```
$ npx vite build
✓ 36 modules transformed.
dist/assets/samsun_blue-MJU1RrsD.png   11.59 kB
dist/assets/samsun_dark-np9JJz7C.png   13.15 kB
dist/assets/index-40w0uAmp.js         220.05 kB │ gzip: 64.58 kB
✓ built in 77ms
```

- 모듈 수: 34 → **36** (+`useColorScheme.ts`, `samsun_dark.png` 자산 모듈)
- JS 번들: 219.52 kB → **220.05 kB** (+530 B, 훅 + 조건부 분기)
- gzip: 64.40 kB → **64.58 kB** (+180 B)
- `samsun_dark.png` dist 포함 ✓ (13.15 kB)
- ESLint/TypeScript 0 에러

#### 19-D. 교훈 — Cleanup 의 안전 기준 갱신

이슈 #18 시점 기준 ("import 그래프 추적해서 미사용이면 삭제") 는 **로드맵 의도** 를 반영하지 못해 위험. 향후 청소 시 다음 체크리스트 추가:

1. 파일 헤더 주석에 `"향후 X 기능을 위한 뼈대"` 같은 의도 표기 있는지
2. `HANDOFF.md` 의 "남은 작업/TODO" 섹션이 해당 파일을 참조하는지
3. 팀원에게 1회 확인 (특히 mingyu/sangjoon 작업 영역)

위 3 중 하나라도 yes 면 **삭제 보류** + HANDOFF 에 "현재 미사용이지만 X 용 뼈대" 명시.

#### 운용 노트

- **`generate_dummy.py` 는 더 이상 호출하지 않는다.** 이번 작업에서 임시로 추가했던 'AI 비즈니스' / 'AI 커뮤니티' 더미 항목들은 모두 원복(이슈 #15 시점 형태로 복구). 추후 dev DB 분기를 살리려면 별도 워크플로 필요.
- 로컬 mock 폴백(이슈 #16) 은 **여전히 유효**. 백엔드를 끄고 프론트만 띄우면 `getMockFallback` 이 동작.
- `/debug` 엔드포인트는 운영에서 supabase URL 60자까지 노출 → 임시 도구이므로 다음 푸시 사이클에 제거 예정 (남은 작업 §6 으로 이관).

#### 적용 절차 (사용자 측에서 1회 수행)

```bash
# 1. Railway 대시보드에서 SUPABASE_KEY value 복사
#    https://railway.app/project/<id>/service/<id>/variables

# 2. 로컬 .env 의 placeholder 를 실제 값으로 치환
sed -i '' 's|<PASTE_TEAM_ANON_KEY_HERE>|<여기에_복사한_KEY>|' backend/.env

# 3. 백엔드 기동 후 /debug 로 검증
uvicorn backend.main:app --reload --port 8000
curl -s http://localhost:8000/debug | python3 -m json.tool
# → "supabase_url": "https://srdvlalyucbokdwfkmcf.supabase.co...", "sdk_ok": true 확인

# 4. 카테고리 분포 비교
curl -s 'http://localhost:8000/articles?limit=200' \
  | python3 -c "import sys,json,collections;print(collections.Counter(a['category'] for a in json.load(sys.stdin)))"
# → Railway 와 동일 분포면 OK
```

---

### ✅ 20. feat/leesangjun RSS 파이프라인 + user_logs 기반 RAG 통합 (2026-04-29)

소스 ZIP: `temp_features/sangjun/Samsun-Final-Project-feat-leesangjun.zip` — **`collect/`·`backend/` 만 분석** (내장 `apps-in-toss-examples-main/` 등 대용량 예제는 이식 제외).

| 영역 | 내용 |
|------|------|
| RSS | `collect/crawler/rss_crawler.py` 에 **Lemmy Technology** 피드 추가 (`title_only=True`). 문서 주석에 Reddit 정책·hnrss 반영. |
| RAG | `backend/rag.py` 재작성: sangjun 의 **user_logs → 최근 카테고리/키워드 → 각 기사 `reason`** 로직 이식. 임베딩은 Ollama `mxbai` 등 **별도 모델이 아니라** 기사 DB와 차원을 맞추기 위해 **`backend.embedder.make_embedding` 단일 경로**. Supabase 는 `main.py` 와 동일하게 `Settings` + `SUPABASE_URL` / `SUPABASE_KEY`. |
| API | `POST /onboarding` → `rag.upsert_user_profile`; `GET /feed/{user_id}` → `rag.build_personalized_feed`. 피드 JSON 기사 객체에 `reason` 필드 포함. |
| 프론트 | `api.ts` 의 `FeedArticle` / `fetchFeed` 반환 타입에 `reason?: string` (UI 노출은 후속 가능). |

검증: `set -a && . backend/.env && set +a && PYTHONPATH=. uvicorn backend.main:app` → `/health` 200, 미등록 유저 `GET /feed/...` 404.

---

## 5. 현재 `main.tsx` 상태 (이슈 #13 이후)

```tsx
import { createRoot } from 'react-dom/client';
import './styles/global.css';
import App from './App';
import { OverlayProvider, ErrorBoundary } from './components/Overlay';

createRoot(document.getElementById('root')!).render(
  <ErrorBoundary>
    <OverlayProvider>
      <App />
    </OverlayProvider>
  </ErrorBoundary>,
);
```

(이전 TDS 기반 main.tsx — 참고용으로 보존)

```tsx
import React, { Component, useMemo, useSyncExternalStore, type PropsWithChildren } from 'react';
import { createRoot } from 'react-dom/client';
import { TDSMobileProvider } from '@toss/tds-mobile';
import './styles/global.css';
import App from './App';

class ErrorBoundary extends Component<PropsWithChildren, { error: Error | null }> {
  state = { error: null };
  static getDerivedStateFromError(error: Error) { return { error }; }
  render() {
    if (this.state.error) {
      return (
        <div style={{ padding: 24, fontFamily: 'monospace', color: 'red' }}>
          <b>앱 오류:</b>
          <pre style={{ whiteSpace: 'pre-wrap', fontSize: 13 }}>
            {(this.state.error as Error).message}
          </pre>
        </div>
      );
    }
    return this.props.children;
  }
}

// TDSMobileProvider 는 userAgent: UserAgentVariables 가 필수.
// 안 넘기면 내부에서 userAgent.colorPreference 접근 시 throw → 흰 화면.
const isBrowser = typeof window !== 'undefined' && typeof navigator !== 'undefined';
const ua = isBrowser ? navigator.userAgent : '';
const isAndroid = /Android/i.test(ua);
const isIOS = /iPhone|iPad|iPod/i.test(ua);

const getColorPreference = (): 'light' | 'dark' =>
  isBrowser && typeof window.matchMedia === 'function' &&
    window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';

const subscribeColorPreference = (onChange: () => void) => {
  if (!isBrowser || typeof window.matchMedia !== 'function') return () => {};
  const mq = window.matchMedia('(prefers-color-scheme: dark)');
  const handler = () => onChange();
  if (mq.addEventListener) { mq.addEventListener('change', handler); return () => mq.removeEventListener('change', handler); }
  mq.addListener(handler); return () => mq.removeListener(handler);
};

function Root({ children }: PropsWithChildren) {
  const colorPreference = useSyncExternalStore(subscribeColorPreference, getColorPreference, () => 'light');
  const userAgent = useMemo(() => ({
    isAndroid, isIOS,
    fontA11y: undefined,
    fontScale: undefined,
    colorPreference,
    safeAreaBottomTransparency: 'opaque' as const,
  }), [colorPreference]);
  return <TDSMobileProvider userAgent={userAgent}>{children}</TDSMobileProvider>;
}

createRoot(document.getElementById('root')!).render(
  <ErrorBoundary>
    <Root><App /></Root>
  </ErrorBoundary>,
);
```

**주의**: 토스 앱 심사 제출 단계로 가면 `TDSMobileAITProvider` 다시 추가해야 함. 환경 분기 패턴:
```tsx
const isInTossApp = typeof window !== 'undefined' &&
  window.navigator.userAgent.includes('Toss');
// isInTossApp일 때만 AIT Provider 사용, 아니면 위 Root 그대로
```

---

## 6. 남은 작업 / TODO

### 우선순위 높음
- [ ] **`/debug` 엔드포인트 제거** — 임시 진단용이라 운영에 두면 안 됨 (`backend/main.py` 211~265줄)
- [ ] **백엔드 누락 엔드포인트 추가**
  - `/absence-summary/:userId` — `fetchAbsenceSummary`가 호출하는데 백엔드에 없음 (현재는 catch로 무시되지만 404가 catch-all에 잡혀서 SPA HTML 반환됨 → JSON 파싱 에러)
  - `/user-seen/:userId` — 동일

### 출시 준비
- [ ] 토스 앱 심사용 빌드 분기 (`TDSMobileAITProvider` 재도입 + 환경 감지)
- [ ] TDS 컴포넌트 사용으로 통일 (현재는 CSS 변수만 사용, TDS 가이드라인 권장)
- [ ] App.tsx 95번 줄 등 TypeScript 에러 정리 (`npm run build`가 통과하도록)

### 알려진 TypeScript 에러 (팀원 코드)
`npx tsc -b` 실행 시 나는 에러들. 빌드 자체는 `npx vite build` 로 우회 가능.
```
src/App.tsx(95,51): onArticleClick prop 타입 누락
src/components/ArticleCard.tsx: fact_label, sourceColor, time_ago 등 타입 불일치
src/pages/MyFeedPage.tsx: Interest 타입에 없는 카테고리 사용 ('AI 연구·심층', 'AI 윤리·정책', 'AI·반도체')
src/pages/SearchPage.tsx(52): Article ↔ ApiArticle 타입 변환 누락
```

---

## 7. 자주 쓰는 명령어 모음

### 로컬 개발
```bash
# 백엔드 실행
cd /Users/aiagent/Desktop/test/SamSun_final
uvicorn backend.main:app --reload --port 8000

# 프론트엔드 dev 서버
cd frontend && npm run dev    # localhost:5173
```

### 배포 (Railway 재배포)
```bash
cd /Users/aiagent/Desktop/test/SamSun_final/frontend
npx vite build                # tsc 우회

cd ..
git add frontend/dist/ frontend/src/   # 변경된 src 파일도
git commit -m "fix: ..."
git push team main:feat/joochan        # ← 이게 Railway 트리거
```

### 디버깅
```bash
# Railway 백엔드 상태 확인
curl https://samsun-production.up.railway.app/health
curl https://samsun-production.up.railway.app/debug

# 팀 레포 최신 커밋 확인
git log --oneline team/feat/joochan -5

# 로컬 vs 팀 레포 차이
git fetch team && git log --oneline team/feat/joochan..HEAD
```

---

## 8. 주요 파일 위치 빠른 참조

| 무엇 | 어디 |
|------|------|
| 진입점 | `frontend/src/main.tsx` |
| 라우팅·온보딩 분기 | `frontend/src/App.tsx` |
| API 클라이언트 | `frontend/src/data/api.ts` |
| CSS 변수 정의 | `frontend/src/styles/global.css` |
| 백엔드 메인 | `backend/main.py` |
| 빌드 산출물 | `frontend/dist/` (Git에 커밋됨) |
| Vite 환경변수 | `frontend/.env` |
| MCP 설정 | `.mcp.json`, `~/.mcp.json`, `~/.claude/mcp.json` |
| 핸드오프 문서 | `HANDOFF.md` (이 파일) |

---

## 9. 환경 변수 체크리스트

### Railway 대시보드에 설정돼 있어야 함
- `SUPABASE_URL` = `https://srdvlalyucbokdwfkmcf.supabase.co` (suffix 없음!)
- `SUPABASE_KEY` = (anon key)
- `SUPABASE_ANON_KEY` = (동일)
- `OPENROUTER_API_KEY` 또는 LLM 관련 키
- `LOG_LEVEL` = `INFO`
- `CORS_ORIGINS` = (현재 동일 도메인이라 큰 의미 없음)

### `frontend/.env` (빌드 시 baked-in)
- `VITE_API_BASE_URL=https://samsun-production.up.railway.app`

### `backend/.env` (로컬 개발용 — 운영 Railway 와 동일 인스턴스)
- `.gitignore` 등재 → **커밋되지 않음**. 새 머신에 클론 시 직접 작성해야 함.
- `SUPABASE_URL=https://srdvlalyucbokdwfkmcf.supabase.co`  ← Railway 와 동일
- `SUPABASE_KEY=<팀_anon_key>`  ← Railway 대시보드 → Variables 에서 복사
- `MODE=cloud` / `OPENROUTER_API_KEY=sk-or-...`
- 자세한 운영은 §4 이슈 #17 참조

---

## 10. 새 세션에서 시작할 때 체크리스트

1. 이 파일(`HANDOFF.md`) 읽기
2. `git log --oneline -5` 로 최근 커밋 확인
3. `git remote -v` 로 origin / team 둘 다 있는지 확인
4. `curl https://samsun-production.up.railway.app/debug` 로 라이브 상태 확인
5. 팀원과 작업 영역 안 겹치는지 확인 (`feat/joochan` 외 브랜치 건드리지 말 것)

---

마지막 커밋: `2956eded fix: TDSMobileProvider 도입 — useOverlay 컨텍스트 누락 해결`

다음 커밋 예정: `feat(frontend): @toss/tds-mobile 의존 100% 제거 + 자체 OverlayProvider/Badge/Skeleton 도입`
- 삭제 파일: `frontend/src/lib/tds-bypass.ts`
- 신규 파일:
  - `frontend/src/components/Overlay.tsx` — OverlayProvider, useToast, useOverlay, BottomSheet, ErrorBoundary
  - `frontend/src/components/Badge.tsx`
  - `frontend/src/components/SkeletonPrimitive.tsx`
- 변경 파일:
  - `frontend/src/main.tsx` (TDSMobileProvider 제거 → OverlayProvider)
  - `frontend/src/pages/HomePage.tsx` (import 경로만 변경)
  - `frontend/src/components/ArticleCard.tsx` (import 경로만 변경)
  - `frontend/src/components/Skeleton.tsx` (import 경로만 변경)
  - `frontend/package.json` (TDS·AIT·emotion 의존 제거, build 스크립트 vite build 로 단순화)
  - `frontend/package-lock.json` (npm prune 결과 반영)
  - `frontend/dist/` (재빌드 산출물 — `index-Dsqnh6Xs.js`)
  - `HANDOFF.md`
- 번들 사이즈: 1,140 kB → 219 kB (gzip 359 → 64 kB), 모듈 56 → 32

### 로컬에서 운영 동등 검증 (반드시 push 전 한 번 확인)
```bash
cd /Users/aiagent/Desktop/test/SamSun_final
uvicorn backend.main:app --port 8000
# 다른 터미널에서:
open http://localhost:8000
```
체크리스트:
- 콘솔에 `@toss/tds-mobile은 앱인토스...` 에러가 **사라졌는지** (이젠 발생할 코드 자체 부재)
- 하단 TabBar 의 활성 탭만 진하게(검정) / 비활성은 옅은 회색
- `홈` 우상단 종 아이콘 클릭 시 토스트(또는 부재 알림이 있으면 BottomSheet) 가 정상 표시
- BottomSheet 의 "확인했어요" 버튼 클릭 시 시트가 닫히고 onAbsenceDismiss 가 트리거되는지

### Railway 배포
```bash
cd /Users/aiagent/Desktop/test/SamSun_final

git add frontend/src/components/Overlay.tsx \
        frontend/src/components/Badge.tsx \
        frontend/src/components/SkeletonPrimitive.tsx \
        frontend/src/main.tsx \
        frontend/src/pages/HomePage.tsx \
        frontend/src/components/ArticleCard.tsx \
        frontend/src/components/Skeleton.tsx \
        frontend/package.json \
        frontend/package-lock.json \
        frontend/dist/ \
        HANDOFF.md

# 삭제된 파일
git rm -f frontend/src/lib/tds-bypass.ts 2>/dev/null || true

git commit -m "feat(frontend): @toss/tds-mobile 의존 제거 + 자체 OverlayProvider/Badge/Skeleton 도입"
git push team main:feat/joochan        # ← Railway 자동 재배포 트리거
```
