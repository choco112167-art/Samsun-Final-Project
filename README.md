# 삼선 — AI 테크 뉴스 큐레이션 미니앱

> 추천 · 요약 · 번역을 하나의 흐름으로  
> 토스 미니앱 | React + Vite + TypeScript | 생성 AI 7회차 Deep Dive 프로젝트

---

## 👥 팀 소개

| 이름 | 역할 | 담당 |
| --- | --- | --- |
| 김민규 (팀장) | PM + 프론트엔드 | 전체 일정 관리, 토스 미니앱 UI, 발표 총괄 |
| 이상준 | 데이터 수집 | RSS 크롤러 구축, 데이터 전처리 파이프라인, Supabase 저장 |
| 정수민 | 프론트엔드 | 토스 디자인 시스템(TDS) 적용, UI/UX 구현 |
| 이동우 | LLM 파이프라인 | Qwen3.5-4B 번역/요약 파이프라인, LoRA 파인튜닝 |
| 강주찬 | RAG + 백엔드 | FastAPI 백엔드, Supabase pgvector 추천, DB 설계 |

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
- **LoRA 파인튜닝** — AIHub 영-한 뉴스 코퍼스 등 (실험·평가는 `eval/`, 파이프라인 기본 경로와 별도).
- **로컬 접근** — Ollama 로컬 서버; 외부에서 붙을 때는 ngrok 등으로 `11434` 터널링.
- **`qwen3:0.6b` (Ollama `/api/embeddings`)** — 임베딩 전용 소형 모델, **출력 차원 1024**. 기사 번역문·신조어 텍스트 임베딩을 **동일 모델**로 통일. Supabase `pgvector`와 조합해 기사 추천 RAG 및 신조어 DB 유사도 검색에 사용.

### 인프라

- Ollama + RTX 4070 (12GB VRAM) — 로컬 LLM 서버 (**추후 연결 예정**)
- ngrok — 로컬 모델 외부 접속 터널링 (**추후 연결 예정**)
- Google Colab Pro (A100) — LoRA 파인튜닝 환경
- Hugging Face — 파인튜닝 모델 저장소 ([`mingyu3939/samsun-qwen3.5-4b-gguf`](https://huggingface.co/mingyu3939/samsun-qwen3.5-4b-gguf))
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

실제 저장소 기준 디렉터리입니다.

```
Samsun-Final-Project-main/
├── backend/                     # FastAPI (Railway 진입: uvicorn backend.main:app)
│   ├── main.py                  # 온보딩·피드·기사·검색·/health·/translate·/summarize
│   ├── embedder.py              # 임베딩 (Ollama `qwen3:0.6b`, 1024차원 등, USE_LOCAL_LLM에 따라 OpenRouter 분기)
│   ├── llm_dispatch.py          # 번역·요약 라우팅 (Ollama vs OpenRouter)
│   ├── openrouter_llm.py
│   └── save_articles.py         # Supabase articles 저장
├── collect/                     # RSS 수집 모듈 (크롤러·로컬 SQLite 등)
│   ├── crawler/rss_crawler.py
│   ├── main.py
│   ├── db/, admin/, models/
│   └── export.py
├── data/                        # 로컬 JSONL (gitignore, 커밋 제외)
│   ├── articles_raw.jsonl
│   ├── articles_translated.jsonl
│   └── articles_v2_dated.jsonl
├── eval/                        # BLEU/COMET/G-Eval 등 평가 스크립트·데이터
│   ├── run_eval.py, reprocess_failed.py, select_testset.py, …
│   ├── metrics/
│   └── README.md
├── frontend/                    # 토스 미니앱 (Granite / Vite / TDS)
├── pipeline/                    # 영→한 번역·요약 LLM 파이프라인
│   ├── translate_summarize.py
│   ├── translator.py, summarizer.py, utils.py
│   └── README.md
├── .cursor/                     # Cursor 에디터 전용 설정 폴더 (프로젝트 규칙·AI 보조 등)
├── .env
├── .gitignore
├── config.py
├── main.py                      # RSS 수집 → pipeline 번역·요약 → save_articles
├── poc_cycle.py                 # POC: 샘플 1건 번역·(옵션)임베딩·Supabase 검증
├── poc_dummy.py                 # 더미 기사 일괄 Supabase 저장 스크립트
├── Procfile
├── pyproject.toml
├── README.md
└── requirements.txt
```

### 폴더별 파일과 역할

#### `backend/`

토스 미니앱·클라이언트가 호출하는 **FastAPI 서버**. Supabase RPC(`match_articles`)·pgvector와 연동하고, `/health`, `/translate`, `/summarize` 등으로 LLM·추천 백엔드를 노출합니다.

| 파일 | 역할 |
| --- | --- |
| `main.py` | 앱 진입점. 온보딩·피드·기사·검색·`/health`·`/translate`·`/summarize` 등 API 라우트 정의 |
| `embedder.py` | 기사 등 텍스트 임베딩 (`qwen3:0.6b`, 1024차원 등 Ollama 또는 설정에 따른 OpenRouter 분기) |
| `llm_dispatch.py` | 번역·요약 요청을 로컬 Ollama(`pipeline`) 또는 OpenRouter로 라우팅 |
| `openrouter_llm.py` | OpenRouter 연동 클라이언트 |
| `save_articles.py` | 처리된 기사를 Supabase `articles` 등에 저장 |
| `__init__.py` | 패키지 선언 |

#### `pipeline/`

**영→한 번역·요약** LLM 파이프라인. Ollama(Qwen 계열) 기준으로 격식체·일상체 요약을 한 흐름에서 생성합니다. `backend/llm_dispatch.py`가 `USE_LOCAL_LLM`에 따라 이 모듈 또는 OpenRouter를 선택합니다.

| 파일 | 역할 |
| --- | --- |
| `translate_summarize.py` | 번역 + 격식/일상 요약 통합 호출의 중심 로직 |
| `translator.py` | 번역 단계 |
| `summarizer.py` | 요약(격식체·일상체) 단계 |
| `utils.py` | 공통 유틸·프롬프트 보조 등 |
| `README.md` | 파이프라인 사용·구조 설명 |

#### `collect/`

**영문 기사 RSS 수집** 및 메타데이터·신뢰도 처리, 로컬 DB·내보내기. 루트 `main.py`가 이 모듈과 `pipeline`을 묶어 일괄 배치로 동작합니다.

| 파일·경로 | 역할 |
| --- | --- |
| `main.py` | 수집 배치 진입점 |
| `crawler/rss_crawler.py` | RSS 피드 크롤링 |
| `db/database.py` | 로컬 SQLite 등 DB 접근 |
| `models/article.py` | 기사 도메인 모델 |
| `models/credibility.py` | 신뢰도 관련 로직 |
| `admin/stats.py` | 수집·통계 보조 |
| `export.py` | 수집 결과 내보내기 |
| `README.md` | 수집 모듈 설명 |

#### `eval/`

**품질 평가**(BLEU, COMET, 용어 보존, G-Eval)와 학습·평가용 데이터 준비·테스트셋 선별. 운영 API와 분리된 **실험·오프라인 스크립트** 모음입니다.

| 파일·경로 | 역할 |
| --- | --- |
| `run_eval.py` | 평가 실행 메인 스크립트 |
| `reprocess_failed.py` | 실패 샘플 재처리 |
| `select_testset.py` | 테스트셋 선별 |
| `report.py` | 결과 리포트 생성 |
| `rebuild_trainset_translate.py` | 번역 학습·평가용 데이터 재구축 |
| `prepare_finetune.py` | 파인튜닝용 데이터 준비 |
| `prepare_summary_finetune.py` | 요약 파인튜닝용 데이터 준비 |
| `build_dataset.py` | 데이터셋 빌드 |
| `check_trainset.py`, `check_trainset2.py`, `check_origin.py` | 학습·원본 데이터 점검 |
| `_make_jsonl.py` | JSONL 생성 보조 |
| `metrics/bleu_comet.py` | BLEU·COMET 지표 |
| `metrics/geval.py` | G-Eval 지표 |
| `metrics/term_preservation.py` | 용어 보존률 등 |
| `README.md` | 평가 디렉터리 설명 |

#### `frontend/`

**토스 미니앱 UI** (React · Vite · Granite · TDS). API 베이스 URL은 `frontend/.env`에서 설정합니다.

| 파일·경로 | 역할 |
| --- | --- |
| `package.json` | 의존성·스크립트 (`granite dev`, `ait build` 등) |
| `vite.config.ts` | Vite 번들 설정 |
| `granite.config.ts` | Apps in Toss / Granite 프로젝트 설정 |
| `index.html` | 엔트리 HTML |
| `src/main.tsx` | React 마운트 |
| `src/App.tsx` | 라우팅·앱 셸 |
| `src/pages/` | 화면: `HomePage`, `CategoryPage`, `HotPage`, `DetailPage`, `SearchPage`, `MyFeedPage`, `OnboardingPage` |
| `src/components/` | `ArticleCard`, `TabBar`, `Skeleton` 등 UI 컴포넌트 |
| `src/data/api.ts`, `articles.ts` | API 호출·목 데이터 |
| `src/hooks/useBookmarks.ts` | 북마크 상태 훅 |
| `src/styles/global.css` | 전역 스타일 |
| `.env` | API URL 등 환경 변수 (커밋 제외 권장) |

### 기타 경로 (요약)

| 경로 | 역할 |
| --- | --- |
| **`data/`** | 수집·가공 단계별 **JSONL** (`articles_raw.jsonl`, `articles_translated.jsonl`, `articles_v2_dated.jsonl`). 용량·환경 의존 → **Git 추적 제외** |
| **`.cursor/`** | Cursor 에디터 프로젝트 설정(규칙·스킬 등). 로컬 전용일 수 있음 |
| **루트 `main.py`** | 배치 진입점: RSS → `translate_and_summarize` → `save_articles`로 DB 반영 |
| **`poc_cycle.py`** | 스모크 테스트: 샘플 1건 번역·(옵션) 임베딩·Supabase 검증 |
| **`poc_dummy.py`** | 더미 기사 일괄 Supabase 저장 |
| **`config.py`** | `OPENROUTER_*`, `OLLAMA_*`, `SUPABASE_*`, `USE_LOCAL_LLM`, `CORS_ORIGINS` 등 환경 변수 로드 |

> 루트에 예전 `node_modules/`가 남아 있으면 지우고, 프론트는 루트 **`frontend/`** 에서 `npm install` 하면 됩니다.

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
- [x] LoRA 파인튜닝 (AIHub 영-한 코퍼스) ✅
- [x] GGUF 변환 + Hugging Face 업로드 ([`mingyu3939/samsun-qwen3.5-4b-gguf`](https://huggingface.co/mingyu3939/samsun-qwen3.5-4b-gguf)) ✅
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
