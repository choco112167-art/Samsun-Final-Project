# 삼선 — AI 테크 뉴스 큐레이션 미니앱

> 추천 · 요약 · 번역을 하나의 흐름으로  
> 토스 미니앱 | React + Vite + TypeScript | 생성 AI 7회차 Deep Dive 프로젝트

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
