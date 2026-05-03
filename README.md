# 삼선 — AI 테크 뉴스 큐레이션 미니앱

> 추천 · 요약 · 번역을 하나의 흐름으로  
> 토스 미니앱 | React + Vite + TypeScript | 생성 AI 7회차 Deep Dive 프로젝트

---

## 🚀 팀원용 1분 로컬 셋팅 가이드

> 클론부터 로컬 실행까지 한 번에. **운영(Railway) 과 동일한 팀 공용 Supabase 를 그대로 바라봄** — 더미 DB 없이 실제 데이터로 개발합니다.

### 0. 사전 준비
- Python **3.11** (`runtime.txt` 기준), Node.js **20+**, npm
- Railway 대시보드 접근 권한 (Supabase anon key 복사를 위해 1회 필요)

### 1. 클론 & 진입

```bash
git clone https://github.com/choco112167-art/Samsun-Final-Project.git
cd Samsun-Final-Project
git switch feat/joochan       # 자동 배포 브랜치 (필요 시)
```

### 2. 프론트엔드 의존성 설치

```bash
cd frontend
npm install
cd ..
```

### 3. 백엔드 의존성 설치 (가상환경 권장)

```bash
python3.11 -m venv .venv
source .venv/bin/activate           # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 4. 🔑 환경 변수 셋팅 — **`backend/.env` 한 파일로 끝**

> ⚠️ **단일 `.env` 정책** (이슈 #18 청소 시 `.env.example` 폐기). `.gitignore` 에 등재되어 커밋되지 않습니다.

`backend/.env` 가 이미 placeholder 상태로 존재합니다. **`SUPABASE_KEY` 만 실제 값으로 채우면 끝**입니다.

```bash
# Railway 대시보드에서 anon key 복사:
#   https://railway.app  →  samsun-production  →  Variables  →  SUPABASE_KEY  →  Copy
# 그런 다음 placeholder 치환:
sed -i '' 's|<PASTE_TEAM_ANON_KEY_HERE>|<여기에_복사한_KEY>|' backend/.env
```

치환 후 `backend/.env` 의 모습:

```env
SUPABASE_URL=https://srdvlalyucbokdwfkmcf.supabase.co     # 운영 Railway 와 동일 인스턴스
SUPABASE_KEY=eyJhbGc...실제_anon_key...                    # 위에서 복사한 값
MODE=cloud
OLLAMA_BASE_URL=http://localhost:11434
OPENROUTER_API_KEY=sk-or-v1-...
```

> 새 머신에서 `.env` 가 없다면 위 5줄을 직접 작성하면 됩니다 (자세한 운영은 `HANDOFF.md` §9 참조).

### 5. 실행 — 서버 두 개 (백엔드 + 프론트엔드)

**터미널 ① — 백엔드 (FastAPI :8000)**

```bash
source .venv/bin/activate
uvicorn backend.main:app --reload --port 8000
# 헬스체크: curl http://localhost:8000/debug | python3 -m json.tool
#   → "sdk_ok": true  ✓
```

**터미널 ② — 프론트엔드 (Vite :5173)**

```bash
cd frontend
npm run dev
# → http://localhost:5173 접속
```

### 5-1. Apps in Toss 실기기 / 토스앱 WebView 테스트

현재 프론트는 Apps in Toss Web 프로젝트입니다.

- `frontend/package.json`: `@apps-in-toss/web-framework`, React 18, TDS 모바일 패키지 포함
- `frontend/granite.config.ts`: `appName: "samsun-newsapp"`, `brand.displayName: "삼선뉴스"`, `web.port: 5173`, `outdir: "dist"`
- `.ait` 업로드 번들은 `npm run ait:build`로 생성합니다. 일반 `npm run build`는 Vite 정적 빌드만 수행합니다.

실기기에서 PC 개발 서버를 보려면 휴대폰과 PC가 같은 Wi-Fi에 있어야 하고, `localhost` 대신 PC 내부 IP를 사용해야 합니다.

```powershell
# Windows: PC 내부 IP 확인
ipconfig

# 예: Wi-Fi IPv4가 192.168.45.27이라면
cd frontend
Copy-Item .env.mobile.example .env.development
# .env.development의 VITE_API_BASE_URL을 http://192.168.45.27:8000 으로 수정

# 백엔드도 외부 기기에서 접근 가능하게 실행
cd ..
uvicorn backend.main:app --host 0.0.0.0 --port 8000

# 프론트도 외부 기기에서 접근 가능하게 실행
cd frontend
npm run dev
```

Apps in Toss Granite dev를 실기기에서 쓸 때는 `web.host`를 PC 내부 IP로 넘깁니다.

```powershell
cd frontend
$env:AIT_WEB_HOST="192.168.45.27"
npm run ait:dev
```

점검할 네트워크 조건:

- 휴대폰과 PC가 같은 Wi-Fi에 연결되어 있어야 함
- Windows 방화벽에서 `5173`, `8000` 포트 접근 허용
- 프론트 `VITE_API_BASE_URL`은 `http://PC내부IP:8000`
- 최종 업로드/출시용 `VITE_API_BASE_URL`은 외부 HTTPS API URL
- 프론트에는 Supabase service role key를 절대 넣지 않음. 프론트는 FastAPI만 호출하고, Supabase 쓰기는 백엔드/배치 스크립트가 담당

토스 콘솔 업로드 흐름:

```bash
cd frontend
npm run lint
npm run build
npm run ait:build
# 생성된 samsun-newsapp.ait 파일을 Apps in Toss 콘솔 > 워크스페이스 > 앱 > 앱 출시 메뉴에 업로드
```

토스앱 테스트 조건:

- 토스앱 로그인 상태
- 해당 워크스페이스 멤버
- 만 19세 이상
- QR 코드 또는 테스트 스킴으로 토스앱 실행
- 앱 출시 전 테스트 최소 1회 완료

WebView 디버깅:

- Android: USB 디버깅을 켠 뒤 PC Chrome에서 `chrome://inspect/#devices`
- iOS: 설정에서 Safari Web Inspector를 켠 뒤 Mac Safari 개발자용 메뉴에서 WebView inspect
- USB는 앱 실행 자체에 필요한 것이 아니라, 실기기 WebView 내부 콘솔/네트워크를 디버깅할 때 필요함

### 6. 첫 검증 체크리스트

- [ ] `http://localhost:5173` 접속 시 흰 화면 없이 메인 렌더 ✓
- [ ] 하단 탭 5개(홈/카테고리/핫이슈/검색/내 피드) 아이콘 정상 표시 ✓
- [ ] 카테고리 탭 7개(`AI 연구`/`AI 심층`/`AI 스타트업`/`AI 비즈니스`/`AI 윤리`/`AI 커뮤니티`/`테크 전반`) 모두 기사가 채워짐 ✓
- [ ] `curl 'http://localhost:8000/articles?limit=5'` 가 운영과 동일한 카테고리 분포를 반환

위 4개가 통과하면 셋업 완료. 백엔드를 켜지 않고 프론트만 띄워도 DEV 모드 mock 폴백(`mock-articles.ts`) 이 동작해 7개 탭이 채워집니다.

---

## 👥 팀 소개

| 이름 | 역할 | 담당 |
| --- | --- | --- |
| 김민규 (팀장) | PM + 통합 + 파인튜닝 | 전체 일정 관리, 브랜치 통합, LoRA 파인튜닝, TDS 개발환경 설정, 발표 총괄 |
| 이상준 | 데이터 수집 | RSS 크롤러 구축, 데이터 전처리 파이프라인, Supabase 저장 |
| 정수민 | 프론트엔드 | 토스 디자인 시스템(TDS) UI/UX 디자인 및 구현 |
| 이동우 | LLM 평가 | 모델 테스트, G-Eval 평가, 합성 데이터셋 검토 |
| 강주찬 | RAG + 백엔드 | FastAPI 백엔드, 백엔드-프론트 연결, Supabase pgvector 추천, OpenRouter 연동, DB 설계 |

---

## 🎯 문제 정의

AI 종사자·학습자들은 수십 개의 해외 전문 매체에 흩어진 정보를 매일 직접 찾아 읽어야 합니다.

- **투자자** — AI 시장 흐름을 파악하고 싶지만 매일 수십 개 매체를 확인할 시간이 없음
- **개발자** — 최신 AI 기술 트렌드를 캐치하고 싶지만 업무 중 긴 원문을 읽을 여유가 없음
- **AI 학습 뉴비** — AI에 관심이 생겼지만 어디서 무엇부터 봐야 할지 모름

---

## ✨ 핵심 기능

| 기능 | 설명 | 기술 |
| --- | --- | --- |
| 📝 번역 + 3줄 요약 | 영문 기사를 단일 LLM 호출로 번역 및 3줄 요약 동시 생성 | Qwen3.5-4B (Ollama) |
| 🎨 격식체 / 일상체 | 동일 기사를 두 가지 문체로 동시 제공 + 복사 버튼 | Qwen3.5-4B |
| 🔍 개인화 추천 (RAG) | 관심 주제 기반 벡터 유사도 검색으로 맞춤 피드 | `qwen3:0.6b` (1024차원) + pgvector |
| 🔤 신조어 처리 (RAG) | AI 신조어를 DB에서 검색해 첫 등장 시 `Term(음차, 설명)` 형식으로 자동 포매팅 | `qwen3:0.6b` (1024차원) + pgvector |
| 📋 즉시 공유 포맷 | 복사 버튼 → 사내 메신저 바로 붙여넣기 | — |
| 🔔 부재중 요약 알림 | 오랜만에 접속 시 부재 중 기사 요약 알림 제공 | — |

> **신조어 출력 형식 예시**  
> 첫 등장: `RAG(Retrieval-Augmented Generation의 약자, 외부 지식을 검색해 LLM 답변에 활용하는 기법)`  
> 이후 등장: `RAG`

---

## 🛠 기술 스택

### Frontend

- React + Vite + TypeScript
- 토스 미니앱 (Apps in Toss) — WebView 방식
- Granite 프레임워크 + TDS (Toss Design System)

### Backend

- FastAPI (Railway 배포)
- Supabase (PostgreSQL + pgvector)
- Python **3.11**

### AI/ML

- **`qwen3.5:4b` (Ollama)** — 번역 + 요약 통합 (단일 LLM 호출). 환경 변수 `MODEL_NAME`으로 태그 변경 가능.
- **LoRA 파인튜닝** — **데이터셋:** RSS·크롤링으로 수집한 AI 뉴스 기사를 LLM으로 번역·요약해 만든 **자체 합성 데이터**. **학습:** epoch **8**, **Google Colab Pro (A100)**. (실험·평가는 `eval/`·파이프라인 기본 경로와 별도.)
- **공개 모델 (Hugging Face)** — LoRA Adapter [`mingyu3939/samsun123`](https://huggingface.co/mingyu3939/samsun123), GGUF [`mingyu3939/samsun1234`](https://huggingface.co/mingyu3939/samsun1234)
- **로컬 접근** — Ollama 로컬 서버; 외부에서 붙을 때는 ngrok 등으로 `11434` 터널링.
- **`qwen3:0.6b` (Ollama `/api/embeddings`)** — 임베딩 전용 소형 모델, **출력 차원 1024**. 기사 번역문·신조어 텍스트 임베딩을 **동일 모델**로 통일. Supabase `pgvector`와 조합해 기사 추천 RAG 및 신조어 DB 유사도 검색에 사용.

### 인프라

- Ollama + RTX 4070 (12GB VRAM) — 로컬 LLM 서버 (**추후 연결 예정**)
- ngrok — 로컬 모델 외부 접속 터널링 (**추후 연결 예정**)
- Google Colab Pro (A100) — LoRA 파인튜닝 (자체 합성 데이터, epoch 8)
- Hugging Face — LoRA Adapter [`mingyu3939/samsun123`](https://huggingface.co/mingyu3939/samsun123), GGUF [`mingyu3939/samsun1234`](https://huggingface.co/mingyu3939/samsun1234)
- Railway — FastAPI 서버 배포
- Supabase — DB + pgvector 벡터 검색

### 데이터 수집

- feedparser (RSS)
- 7개 AI 전문 매체 자동 수집 (크론탭 주기 실행)

---

## 📰 수집 언론사 (7개)

| 언론사 | 국가 | 특화 분야 |
| --- | --- | --- |
| TechCrunch | 미국 | AI 스타트업 |
| MIT Technology Review | 미국 | AI 심층 분석 |
| The Verge | 미국 | 테크 전반 |
| VentureBeat AI | 미국 | AI 비즈니스/투자 |
| The Guardian Tech | 영국 | AI 윤리 |
| IEEE Spectrum | 글로벌 | AI/반도체 |
| The Decoder | 독일 | AI 연구 및 산업 분석 |

---

## 📊 평가 지표

### 번역 (translation)

| 지표 | 유형 | 목표값 |
| --- | --- | --- |
| BLEU | 주지표 | ≥ 17.0 |
| COMET | 주지표 | 기준값 측정 후 설정 |
| Term Preservation Rate | 보조지표 | ≥ 95% |

### 요약 (summary_formal / summary_casual)

| 지표 | 유형 | 목표값 |
| --- | --- | --- |
| G-Eval 충실성 | 주지표 | ≥ 4.0 / 5.0 |
| G-Eval 유창성 | 주지표 | ≥ 4.0 / 5.0 |
| G-Eval 간결성 | 주지표 | ≥ 4.0 / 5.0 |

### 임베딩 (RAG 추천)

| 지표 | 설명 |
| --- | --- |
| Precision@K | 추천된 K개 기사 중 관련 기사 비율 |
| nDCG@10 | 상위 10개 결과 순위와 관련도 동시 평가 |
| MRR@K | 첫 번째 관련 기사 등장 속도 |
| Recall@K | 전체 관련 기사 중 K개 내 포함 비율 |

---

## 🏗 아키텍처

```
[토스 미니앱 - WebView]             frontend/
        ↓ HTTP 요청
[FastAPI - Railway]                 backend/
   ├── RSS 수집 (크론·main.py)       collect/
   │     └── RSS → Qwen3.5-4B
   ├── 번역/요약                     pipeline/
   │     ├── translate_and_summarize()
   │     └── 신조어 RAG 컨텍스트 주입
   │           ├── neologism DB 유사도 검색
   │           └── 첫등장: Term(음차, 설명) 포매팅
   ├── 검색/추천 API
   │     └── pgvector 유사 검색 (기사 추천)
   └── 유저 API
         └── 내피드 저장/조회
        ↓
[Supabase - DB + pgvector]
   ├── articles
   ├── embeddings
   ├── user_feeds
   └── neologisms                   ← 신조어 DB (`qwen3:0.6b`, 1024차원)
        ↓
[Qwen3.5-4B - Ollama + 로컬 GPU · ngrok 외부 접속] — **추후 연결 예정**
```

---

## 🚀 실행 방법

### 가상환경 설정 (최초 1회)

Windows:

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

Mac/Linux:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 프론트엔드 (Granite / Vite / TDS)

```bash
cd frontend
npm install
npm run dev
```

### 백엔드 (FastAPI)

저장소 **루트**에서 의존성 설치 후, 모듈 경로가 맞도록 루트에서 uvicorn을 실행합니다.

```bash
pip install -r requirements.txt
uvicorn backend.main:app --reload
```

Railway 배포 시 `Procfile`은 `uvicorn backend.main:app` 기준입니다.

**Railway 배포 주소:** https://sansunver2-production.up.railway.app

### 신조어 DB 초기화

```bash
# 1. Supabase SQL Editor에서 실행
#    supabase/neologisms_migration.sql

# 2. 신조어 데이터 임베딩 후 업로드
python pipeline/neologism/ingest.py
```

### RSS → 번역·요약 파이프라인 (루트 `main.py`)

```bash
pip install -r requirements.txt
python main.py
```

### 수집/보강 운영 파이프라인

이번 정렬 이슈의 원인은 프론트 정렬이 아니라 Supabase 데이터 결측이었습니다. `/articles`는 이미 `published_at desc`로 최신순 정렬합니다. 화면에서 첫 기사 다음에 오래된 기사가 나온 것은 DB에 최신 기사가 부족했고, 레거시 기사 대부분의 `title_ko`가 비어 있어서 영어 제목으로 fallback 되었기 때문입니다.

DB 필드 기준:

| 의미 | DB 필드 |
| --- | --- |
| 원문 기사 URL | `articles.url` |
| 원문 제목 | `articles.title` |
| 한국어 제목 | `articles.title_ko` |
| 본문 번역 | `articles.translation` |
| 격식체 요약 | `articles.summary_formal` |
| 일상체 요약 | `articles.summary_casual` |

스크립트 역할:

| 스크립트 | 용도 |
| --- | --- |
| `scripts/ingest_latest_titles.py` | 시연 전 빠른 최신 기사 반영. RSS 최신 기사에서 목록 화면에 필요한 `title_ko`, `published_at`, `url`, 소스/카테고리만 우선 채움. `translation`, `summary_formal`, `summary_casual`은 빈 문자열로 둠. |
| `scripts/backfill_title_ko.py` | 기존 DB 기사 중 `title_ko`가 비어 있는 행을 최신순으로 보강. 이미 채워진 행은 건드리지 않아 재실행 가능. |
| `scripts/backfill_article_ai_outputs.py` | DB에 이미 들어간 기사 중 `translation`, `summary_formal`, `summary_casual`이 비어 있는 행을 찾아 실제 LLM 출력으로 보강. 제목을 번역/요약 대체값으로 저장하지 않음. |
| `scripts/ingest_latest_fast.py` | 본문 번역/요약까지 수행하되, 심층 팩트체크 대기 시간을 줄인 로컬 시연용 전체 처리. 기사 본문 길이와 LLM/API 응답에 따라 느릴 수 있음. |
| `scripts/check_articles_health.py` | DB 상태 점검. 전체 기사 수, `title_ko`/URL/번역/요약 누락 수, 최신/최오래 날짜, 최근 20개 상태를 출력. |

공통 로직은 `scripts/article_pipeline_common.py`에 있습니다. Supabase 연결, RSS fetch, 기존 기사 hash 조회, `title_ko` 생성, `published_at` 정규화, `url_hash` 기준 upsert를 여기서 공유합니다. 중복 방지는 `url_hash = md5(url)`와 Supabase `upsert(..., on_conflict="url_hash")` 기준입니다.

시연 전 빠른 최신 기사 수집:

```bash
python scripts/ingest_latest_titles.py --max 20
python scripts/check_articles_health.py
curl "http://localhost:8000/articles?limit=15"
```

기존 `title_ko` 보강:

```bash
python scripts/backfill_title_ko.py --limit 100
python scripts/backfill_title_ko.py --limit 20 --dry-run
```

전체 번역/요약 배치:

```bash
# 운영 경로: RSS → 프리플라이트 → 번역/요약 → 팩트체크 → Supabase 저장
python main.py

# 시연용: 번역/요약은 수행하되 심층 팩트체크 대기 시간을 줄임
python scripts/ingest_latest_fast.py --max 5 --summary-sentences 1
```

이미 저장된 기사 AI 출력 백필:

```bash
# 시연 전 테스트용: 실제 모델 호출 없이 1건만 DB 저장 흐름 검증
python scripts/backfill_article_ai_outputs.py --limit 1 --provider mock --run

# 특정 기사 1건만 mock으로 재처리
python scripts/backfill_article_ai_outputs.py --url-hash <url_hash> --provider mock --overwrite --run

# 실제 provider 테스트는 반드시 1건부터
python scripts/backfill_article_ai_outputs.py --limit 1 --provider openrouter --model google/gemini-2.5-flash --run
python scripts/backfill_article_ai_outputs.py --limit 1 --provider gemini --model gemini-2.5-flash --run

# 대상과 본문 확보 가능 여부만 확인. --run 없으면 DB 업데이트 없음
python scripts/backfill_article_ai_outputs.py --limit 5

# 운영용 실제 백필. API 비용/쿼터가 발생하므로 작은 limit으로 나눠 실행
python scripts/backfill_article_ai_outputs.py --limit 5 --provider openrouter --model google/gemini-2.5-flash --run

# 5건 초과는 명시적으로 허용해야 함
python scripts/backfill_article_ai_outputs.py --limit 20 --allow-large-run --provider openrouter --run
```

`backfill_article_ai_outputs.py`는 기본적으로 `translation`, `summary_formal`, `summary_casual` 중 하나라도 비어 있는 기사만 조회합니다. DB의 `content`를 우선 사용하고, 비어 있으면 `url`에서 본문 크롤링을 시도합니다. 본문 확보에 실패하면 해당 기사는 건너뜁니다. `--overwrite`가 없으면 이미 채워진 AI 출력 필드는 덮어쓰지 않습니다.
기본값은 `--limit 1`, `provider=mock`, preview 모드입니다. `--run`을 붙이지 않으면 모델 호출과 DB 업데이트를 하지 않습니다. 5건을 초과하려면 `--allow-large-run`을 명시해야 합니다.
`provider=mock`은 API 호출 없이 `[MOCK 번역 전문]`과 3줄 요약을 저장해 “DB 저장 → 프론트 표시” 흐름만 검증합니다. `provider=openrouter`는 `OPENROUTER_API_KEY`와 OpenRouter Chat Completions endpoint만 사용하고, `provider=gemini`는 `GOOGLE_API_KEY` 또는 `GEMINI_API_KEY`만 사용합니다. API provider 사용 시 비용과 쿼터가 발생합니다.
`provider=mock` 결과는 데모 화면에 남기면 안 됩니다. 데모 전에는 반드시 mock 탐지와 정리를 실행합니다.

```bash
python scripts/check_articles_health.py
python scripts/clear_mock_ai_outputs.py --limit 10
python scripts/clear_mock_ai_outputs.py --limit 10 --run
python scripts/clear_mock_ai_outputs.py --url-hash <url_hash> --run
```

Local fine-tuned provider:

```bash
# 아직 local 모델 연결이 완료되지 않았다면 실패하는 것이 정상입니다.
python scripts/backfill_article_ai_outputs.py --limit 1 --provider local --run

# Ollama에 직접 등록한 fine-tuned/GGUF 모델을 쓸 때
ollama list
set LOCAL_LLM_CONFIGURED=1
set OLLAMA_BASE_URL=http://localhost:11434
python scripts/backfill_article_ai_outputs.py --limit 1 --provider local --model gemma4-e4b-6ep-samsun --run

# Transformers/PEFT/FastAPI 등 별도 서버를 쓸 때
set LOCAL_LLM_CONFIGURED=1
set LOCAL_LLM_ENDPOINT=http://localhost:8001/generate
python scripts/backfill_article_ai_outputs.py --limit 1 --provider local --model mingyu3939/gemma4-e4b-6ep-samsun-lora --run
```

`provider=local`은 `LOCAL_LLM_CONFIGURED=1`이 없으면 `local provider not configured`로 실패합니다. OpenRouter/Gemini로 몰래 fallback하지 않습니다. 아직 local fine-tuned model이 안정적으로 연결되지 않았다면 mock으로 DB 저장 흐름만 검증하고, 외부 provider 테스트 결과는 “fine-tuned model 결과가 아니라 external provider 결과”로 표시해야 합니다.

본문 크롤링 품질 확인:

```bash
python scripts/backfill_article_ai_outputs.py --limit 1 --provider mock --show-body-preview
```

URL 크롤링은 가능하면 `trafilatura`/`readability`로 기사 본문만 추출하고, TechCrunch 메뉴·푸터 텍스트가 강하게 섞이면 `body_ok=False`로 건너뜁니다. `--show-body-preview`를 붙이면 dry-run에서 추출 본문 앞 300자를 확인할 수 있습니다.

AI 처리 상태 컬럼은 선택 마이그레이션입니다. Supabase SQL Editor에서 다음 파일을 실행하면 새 기사와 AI worker 상태를 추적할 수 있습니다.

```bash
backend/sql/add_article_ai_status.sql
```

상태 설계:

| 필드 | 의미 |
| --- | --- |
| `ai_status` | `pending`, `processing`, `completed`, `failed`, `skipped` |
| `ai_provider` | `mock`, `openrouter`, `gemini`, `local` |
| `ai_model` | 실제 호출 모델명 |
| `ai_generated_at` | AI 출력 저장 시각 |
| `ai_error` | 실패 사유 |
| `content_source` | `db.content`, `rss_summary`, `url crawl` 등 본문 출처 |
| `content_chars` | 처리에 사용한 본문 길이 |
| `translation_chars` | 생성된 번역 전문 길이 |

새 기사 수집 흐름:

1. RSS/커뮤니티 수집 스크립트가 `title`, `title_ko`, `url`, `source`, `published_at`, `content`를 저장합니다.
2. `translation`, `summary_formal`, `summary_casual`은 비워둘 수 있고, 상태 컬럼이 있으면 `ai_status=pending`으로 남깁니다.
3. AI 처리 스크립트가 `pending` 또는 재시도 대상만 작은 단위로 조회합니다.
4. 본문이 짧으면 URL 크롤링으로 본문을 확보합니다.
5. provider가 `translation`, `summary_formal`, `summary_casual`을 생성합니다.
6. 성공 시 `ai_status=completed`, 실패 시 `ai_status=failed`와 `ai_error`를 저장합니다.

프론트는 실시간 모델 호출을 하지 않습니다. Supabase/API의 `translation`, `summary_formal`, `summary_casual` 값만 표시하고, 비어 있으면 준비 중 문구를 보여줍니다. `ai_status`가 API에 내려오면 상세 페이지에서 “AI 처리 중”, “처리 실패” 같은 상태 뱃지를 추가할 수 있도록 타입은 준비되어 있습니다.

느려질 수 있는 이유:

- OpenRouter/Gemini/Ollama LLM 호출은 기사 본문 길이에 따라 지연됩니다.
- Google Fact Check, Gemini Grounding, 신조어 검색 등 외부 API 단계가 네트워크 상태와 쿼터에 영향을 받습니다.
- 전체 번역/요약은 기사별 순차 호출이라 `--max` 값을 크게 잡으면 오래 걸립니다.

프론트 표시 정책:

- `title_ko`가 있으면 한국어 제목을 표시하고, 없으면 원문 `title`을 표시합니다.
- `translation`, `summary_formal`, `summary_casual`이 비어 있으면 제목으로 대체하지 않습니다.
- 빈 번역/요약은 “아직 준비 중입니다” 상태로 표시합니다.
- 원문 보기는 `articles.url`만 사용하며, 빈 URL이나 `http/https`가 아닌 값은 링크를 비활성화합니다.

배치 후 확인 엔드포인트:

```bash
curl "http://localhost:8000/health"
curl "http://localhost:8000/articles?limit=15"
curl "http://localhost:8000/debug"
```

### LLM 서버 (로컬)

```bash
ollama pull qwen3.5:4b
ollama serve

# 외부에서 붙일 때
ngrok http 11434
```

### POC 사이클

```bash
python poc_cycle.py
```

---

## 📁 프로젝트 구조

저장소에 실제로 포함된 경로·파일을 기준으로 정리했습니다. (`__pycache__/`, `node_modules/` 등은 생략)

```
Samsun-Final-Project-main/
├── backend/                     # FastAPI (Railway: uvicorn backend.main:app)
│   ├── main.py                  # 온보딩·피드·기사·검색·/health·/translate·/summarize
│   ├── embedder.py              # 임베딩 (Ollama qwen3-embedding:4b → 1024차원, MODE에 따라 OpenRouter 분기 가능)
│   ├── llm_dispatch.py          # /translate·/summarize → pipeline.translate_summarize (Ollama)
│   ├── rag.py                   # 실험용 RAG·임베딩 (SentenceTransformer 등)
│   └── save_articles.py         # Supabase articles 저장
├── collect/                     # RSS 수집
│   ├── main.py
│   └── crawler/
│       └── rss_crawler.py
├── data/                        # 로컬 JSONL (.gitignore, 커밋 제외)
│   ├── articles_raw.jsonl
│   ├── articles_translated.jsonl
│   └── articles_v2_dated.jsonl
├── eval/                        # 오프라인 평가·실험 스크립트
│   ├── run_eval.py
│   ├── run_eval_base.py
│   ├── select_testset.py
│   └── kaggle_finetune.py
├── frontend/                    # 토스 미니앱 (Granite / Vite / TDS)
│   ├── index.html
│   ├── package.json
│   ├── package-lock.json
│   ├── vite.config.ts
│   ├── granite.config.ts
│   ├── tsconfig.json
│   ├── tsconfig.app.json
│   ├── tsconfig.node.json
│   └── src/
│       ├── App.tsx
│       ├── components/          # ArticleCard, TabBar, Skeleton
│       ├── data/                # api.ts, articles.ts
│       ├── hooks/               # useBookmarks.ts
│       └── pages/               # HomePage, CategoryPage, SearchPage, MyFeedPage
├── pipeline/                    # 영→한 번역·요약 (Ollama)
│   ├── __init__.py
│   ├── translate_summarize.py
│   ├── translator.py
│   ├── summarizer.py
│   ├── utils.py
│   └── README.md
├── config.py                    # FastAPI용 설정 (pydantic-settings, .env)
├── main.py                      # 배치: RSS → translate_and_summarize → save_articles
├── poc_cycle.py                 # POC: 샘플 번역·임베딩·Supabase 검증
├── poc_dummy.py                 # 더미 기사 Supabase 저장 (.gitignore — 로컬 전용 스크립트)
├── Procfile
├── README.md
├── requirements.txt
├── runtime.txt                  # Railway 등 Python 런타임 버전
├── supabase_schema.sql          # Supabase 스키마 참고용 SQL
├── .gitattributes
├── .gitignore
└── .env                         # 비밀·URL (.gitignore)
```

### 폴더별 파일과 역할

#### `backend/`

토스 미니앱·클라이언트가 호출하는 **FastAPI 서버**. Supabase RPC(`match_articles`)·pgvector와 연동하고, `/health`, `/translate`, `/summarize` 등으로 LLM·추천 백엔드를 노출합니다.

| 파일 | 역할 |
| --- | --- |
| `main.py` | 앱 진입점. 온보딩·피드·기사·검색·`/health`·`/translate`·`/summarize` 등 API 라우트 정의 |
| `embedder.py` | 텍스트 임베딩 (기본: Ollama `qwen3-embedding:4b`, 1024차원; `MODE=cloud` 시 OpenRouter 분기 코드 포함) |
| `llm_dispatch.py` | 번역·요약 → `pipeline.translate_summarize.translate_and_summarize` (Ollama `qwen3.5:4b` 등) |
| `rag.py` | 실험용 RAG·유저/기사 임베딩 (`sentence_transformers` 등, 운영 경로와 별도) |
| `save_articles.py` | 처리된 기사를 Supabase `articles` 등에 저장 |

#### `pipeline/`

**영→한 번역·요약** LLM 파이프라인. Ollama(Qwen 계열) 기준으로 격식체·일상체 요약을 **단일 호출**에서 생성합니다.

| 파일 | 역할 |
| --- | --- |
| `translate_summarize.py` | 번역 + 격식/일상 요약 통합 호출의 중심 로직 |
| `translator.py` | 번역만 필요할 때 (격식/일상 스타일 선택) |
| `summarizer.py` | 별도 프롬프트 기반 요약 |
| `utils.py` | 전처리·JSON 필드 추출 등 |
| `README.md` | 파이프라인 사용·구조 설명 |

#### `collect/`

**영문 기사 RSS 수집**. 루트 `main.py`가 `crawler`와 `pipeline`을 묶어 배치로 동작합니다.

| 파일·경로 | 역할 |
| --- | --- |
| `main.py` | 수집 진입점 |
| `crawler/rss_crawler.py` | RSS 피드 크롤링 |

#### `eval/`

**품질 평가·실험**용 오프라인 스크립트. 운영 API와 분리됩니다.

| 파일·경로 | 역할 |
| --- | --- |
| `run_eval.py` | 평가 실행 |
| `run_eval_base.py` | 베이스라인 평가 |
| `select_testset.py` | 테스트셋 선별 |
| `kaggle_finetune.py` | 파인튜닝 관련 스크립트 |

#### `frontend/`

**토스 미니앱 UI** (React · Vite · Granite · TDS). API 베이스 URL은 `frontend/.env`에서 설정합니다.

| 파일·경로 | 역할 |
| --- | --- |
| `package.json`, `package-lock.json` | 의존성·잠금 파일 |
| `vite.config.ts` | Vite 설정 |
| `granite.config.ts` | Apps in Toss / Granite 프로젝트 설정 |
| `index.html` | 엔트리 HTML |
| `tsconfig*.json` | TypeScript 설정 |
| `src/App.tsx` | 앱 셸·라우팅 |
| `src/pages/` | `HomePage`, `CategoryPage`, `SearchPage`, `MyFeedPage` |
| `src/components/` | `ArticleCard`, `TabBar`, `Skeleton` |
| `src/data/api.ts`, `articles.ts` | API 호출·데이터 |
| `src/hooks/useBookmarks.ts` | 북마크 훅 |
| `.env` | API URL 등 (커밋 제외 권장) |

### 기타 경로 (요약)

| 경로 | 역할 |
| --- | --- |
| **`data/`** | 수집·가공 단계별 **JSONL**. `.gitignore`로 **커밋 제외** |
| **`supabase_schema.sql`** | DB 스키마 참고·초기화용 SQL |
| **`runtime.txt`** | 배포 환경 Python 버전 고정 |
| **`.gitattributes`** | 줄바꿈·텍스트 속성 |
| **루트 `main.py`** | RSS 수집 → `translate_and_summarize` 파이프라인 배치 |
| **`poc_cycle.py`** | POC 스모크: 번역·임베딩·Supabase 검증 |
| **`poc_dummy.py`** | 더미 기사 Supabase 저장 (`.gitignore` — 팀원 로컬에만 두는 경우가 많음) |
| **`config.py`** | FastAPI용 `supabase_url`, `supabase_anon_key`, `cors_origins`, `log_level` 등 (`.env`와 연동) |

> 프론트는 **`frontend/`** 에서 `npm install` 후 `npm run dev` 등을 사용합니다. 루트에 남은 `node_modules/`가 있다면 프론트와 혼동되지 않게 정리하세요.

---

## 📅 개발 일정

| 주차 | 기간 | 목표 |
| --- | --- | --- |
| 1주차 | 03/13 ~ 03/19 | RSS 수집 파이프라인 구축, 기획안 제출 ✅ |
| 2주차 | 03/20 ~ 03/26 | 기획안 발표, 피드백 수렴 ✅ |
| 3주차 | 03/27 ~ 04/09 | 기술 스택 확정, Supabase 세팅, POC 개발 ✅ |
| 4주차 | 04/10 ~ 04/23 | FastAPI 백엔드 연동, LoRA 파인튜닝, 신조어 RAG 구축 ✅ |
| 5주차 | 04/24 ~ 05/07 | RAG 추천, 토스 미니앱 UI 완성 |
| 6주차 | 05/08 ~ 05/19 | 성능 평가, 발표 자료 준비 |
| **최종** | **05/20** | **최종 발표 및 시연** |

---

## ✅ MVP 체크리스트

- [x] 토스 미니앱 UI (WebView 방식) ✅
- [ ] Qwen3.5-4B 번역 + 요약 통합 파이프라인
- [x] LoRA 파인튜닝 (RSS 크롤링으로 수집한 AI 뉴스 기사를 LLM으로 번역·요약한 자체 합성 데이터셋, epoch 8, Colab Pro A100) ✅
- [x] Hugging Face 공개 — LoRA Adapter [`mingyu3939/samsun123`](https://huggingface.co/mingyu3939/samsun123), GGUF [`mingyu3939/samsun1234`](https://huggingface.co/mingyu3939/samsun1234) ✅
- [x] Supabase pgvector RAG 추천 (기사) ✅
- [ ] BLEU / COMET / G-Eval 평가 파이프라인
- [x] 격식체 / 일상체 복사 버튼 ✅
- [x] 기사 클릭 기반 개인화 추천 (user_vector 업데이트) ✅
- [ ] 부재중 요약 알림
- [ ] 신뢰도·팩트 라벨 (미구현)
- [ ] **신조어 RAG**
  - [ ] 신조어 DB 구축 (Supabase pgvector, `qwen3:0.6b`, 1024차원)
  - [ ] 신조어 검색 API (`/neologisms/search`, `/neologisms/context`, `/neologisms/format`)
  - [ ] 번역 파이프라인 통합 (첫등장 포매팅 자동 적용)
  - [ ] Term Preservation Rate ≥ 95%

## ❌ 미구현 항목

- 부재중 요약 알림 ❌
- 한국어 검색 ❌
- 추천 검색어 (언급량 기반) ❌
- FACT 라벨링 실제 로직 ❌

---

*생성 AI 7회차 Deep Dive 프로젝트 | 최종 발표: 2026년 5월 20일*
