# 📱 삼선뉴스 — Frontend

> **React 19 + TypeScript + Vite**로 구현한 토스 미니앱 UI  
> 토스 디자인 시스템(TDS) 기반 

---

## 📌 목차

- [기술 스택](#-기술-스택)
- [화면 구성](#-화면-구성)
- [폴더 구조](#-폴더-구조)
- [API 연동](#-api-연동)
- [로컬 실행](#-로컬-실행)
- [빌드 & 배포](#-빌드--배포)

---

## 🛠 기술 스택

| 항목 | 내용 |
|------|------|
| **프레임워크** | React 19 + TypeScript |
| **빌드 도구** | Vite 8 + Granite (토스 미니앱) |
| **UI 라이브러리** | `@toss/tds-mobile` — 토스 디자인 시스템 |
| **스타일링** | CSS 변수 + 인라인 스타일 |
| **배포** | 토스 미니앱 AIT (`ait build` / `ait deploy`) |

---

## 🖼 화면 구성

| 페이지 | 파일 | 설명 |
|--------|------|------|
| 온보딩 | `OnboardingPage.tsx` | 관심 주제 선택, 사용자 ID 발급 → RAG 추천에 활용 |
| 홈 | `HomePage.tsx` | 속보 배너 + 카테고리 필터 + 기사 피드 |
| 카테고리 | `CategoryPage.tsx` | 분야별 기사 탐색 |
| 인기 | `HotPage.tsx` | 조회수 기반 HOT 기사 |
| 검색 | `SearchPage.tsx` | pgvector RAG 기반 시맨틱 검색 |
| 마이피드 | `MyFeedPage.tsx` | 개인화 추천 피드 + 북마크 모음 |

### 공통 컴포넌트

| 컴포넌트 | 파일 | 설명 |
|----------|------|------|
| 하단 탭바 | `TabBar.tsx` | 홈 / 카테고리 / 인기 / 검색 / 마이 |
| 기사 카드 | `ArticleCard.tsx` | 썸네일, 신뢰도 점수, 팩트 라벨 표시 |
| 스켈레톤 | `Skeleton.tsx` | 로딩 플레이스홀더 |

---

## 📁 폴더 구조

```
frontend/
├── src/
│   ├── pages/
│   │   ├── OnboardingPage.tsx   # 온보딩
│   │   ├── HomePage.tsx         # 홈
│   │   ├── CategoryPage.tsx     # 카테고리
│   │   ├── HotPage.tsx          # 인기
│   │   ├── SearchPage.tsx       # 검색
│   │   └── MyFeedPage.tsx       # 마이피드
│   ├── components/
│   │   ├── TabBar.tsx           # 하단 탭 네비게이션
│   │   ├── ArticleCard.tsx      # 기사 카드
│   │   └── Skeleton.tsx         # 로딩 스켈레톤
│   ├── hooks/
│   │   └── useBookmarks.ts      # 북마크 상태 관리
│   ├── lib/
│   │   ├── api.ts               # FastAPI 클라이언트
│   │   └── articles.ts          # 기사 유틸 함수
│   └── App.tsx                  # 라우팅 + 전역 상태
├── granite.config.ts            # 토스 미니앱 설정
├── vite.config.ts
├── tsconfig.json
└── package.json
```

---

## 🔌 API 연동

백엔드(`FastAPI`)와 `api.ts`를 통해 통신합니다.

```
VITE_API_BASE_URL (기본값: http://localhost:8000)
         │
     api.ts
         ├── fetchArticles()          GET  /articles
         ├── fetchArticleById()       GET  /articles/:id
         ├── translateArticle()       POST /translation/
         ├── translateBoth()          POST /translation/both   ← 격식체 + 일상체 동시
         ├── postOnboarding()         POST /onboarding
         ├── fetchFeed()              GET  /feed/:userId       ← RAG 개인화 추천
         └── searchArticles()         GET  /search?q=          ← 시맨틱 검색
```

---

## 🚀 로컬 실행

### 1. 의존성 설치

```bash
cd frontend
npm install
```

### 2. 환경 변수 설정

```bash
# frontend/.env.local
VITE_API_BASE_URL=http://localhost:8000
```

### 3. 개발 서버 실행

```bash
npm run dev
```

> ⚠️ **`granite.config.ts`의 `web.host`에 본인 IPv4 주소를 입력해야 합니다.**  
> (`ipconfig` 또는 `ifconfig`로 확인)

---

## 📦 빌드 & 배포

```bash
# 빌드 (dist/ + samsun-newsapp.ait 생성)
npm run build

# 토스 미니앱 배포
npm run deploy
```

| 명령어 | 내용 |
|--------|------|
| `npm run dev` | Granite 개발 서버 실행 |
| `npm run build` | `tsc -b && vite build` → `dist/` 생성 |
| `npm run deploy` | `ait deploy` — 토스 AIT 플랫폼 배포 |
| `npm run lint` | ESLint 검사 |
