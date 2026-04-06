# 三鮮 (삼선) — AI 테크 뉴스 큐레이션 미니앱

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
| 📝 번역 + 3줄 요약 | 영문 기사를 단일 LLM 호출로 번역 및 3줄 요약 동시 생성 | Qwen3.5-4B (LoRA 파인튜닝) |
| 🎨 격식체 / 일상체 | 동일 기사를 두 가지 문체로 동시 제공 + 복사 버튼 | Qwen3.5-4B |
| 🔍 개인화 추천 (RAG) | 관심 주제 기반 벡터 유사도 검색으로 맞춤 피드 | Qwen3-Embedding-4B + pgvector |
| ✅ 신뢰도 스코어링 | 루머 / 팩트 / 불명확 라벨 분류 + 출처 신뢰도 평가 | Gemini 2.5 Flash |
| 🔤 신조어 처리 | AI 신조어(LoRA, Blackwell 등) 영문 원문 유지 | Term Preservation Rate 측정 |
| 📋 즉시 공유 포맷 | 복사 버튼 → 사내 메신저 바로 붙여넣기 | — |
| 🔔 부재중 요약 알림 | 오랜만에 접속 시 부재 중 기사 요약 알림 제공 | — |

---

## 🛠 기술 스택

### Frontend

- React + Vite + TypeScript
- 토스 미니앱 (Apps in Toss) — WebView 방식
- Granite 프레임워크 + TDS (Toss Design System)

### Backend

- FastAPI (Railway 배포)
- Supabase (PostgreSQL + pgvector)

### AI/ML

- `Qwen/Qwen3.5-4B` — 번역 + 요약 통합 (단일 LLM 호출)
  - LoRA 파인튜닝 (AIHub 영-한 뉴스 코퍼스 활용)
  - Ollama 로컬 서버 + ngrok 터널링
- `Qwen/Qwen3-Embedding-4B` — 벡터 임베딩 (MTEB 69.45점)
- `Gemini 2.5 Flash` — 팩트 분류 (환각률 7.8%)

### 인프라

- Ollama + RTX 4070 (12GB VRAM) — 로컬 LLM 서버
- ngrok — 로컬 모델 외부 접속 터널링
- Railway — FastAPI 서버 배포
- Supabase — DB + pgvector 벡터 검색
- Kaggle — LoRA 파인튜닝 환경

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
| BBC Technology | 영국 | AI 일반 |

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
[토스 미니앱 - WebView]          frontend/
        ↓ HTTP 요청
[FastAPI - Railway]              backend/
   ├── RSS 수집 (크론·main.py)    collect/
   │     └── RSS → Qwen3.5-4B
   ├── 번역/요약                  pipeline/
   │     └── translate_and_summarize()
   ├── 검색/추천 API
   │     └── pgvector 유사 검색
   └── 유저 API
         └── 내피드 저장/조회
        ↓
[Supabase - DB + pgvector]
   ├── articles
   ├── embeddings
   └── user_feeds
        ↓
[Qwen3.5-4B - Ollama + RTX 4070]
   └── ngrok으로 외부 접속
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

```
samsun_news/
├── frontend/                    # React + Vite + TDS (토스 미니앱)
│   ├── src/
│   ├── public/
│   ├── granite.config.ts
│   ├── package.json
│   └── samsun-newsapp.ait       # 빌드 시 생성
├── backend/                     # FastAPI + Supabase 연동
│   ├── main.py
│   └── save_articles.py
├── collect/                     # RSS 크롤러·수집
├── pipeline/                    # 번역·요약 (Qwen 등)
├── eval/                        # 평가·실험
├── apps-in-toss-examples-main/  # 토스 예제(참고)
├── main.py                      # RSS → 번역·요약 파이프라인 진입
├── poc_cycle.py                 # POC 검증
├── supabase_schema.sql          # Supabase SQL
├── Procfile                     # Railway
├── requirements.txt
└── README.md
```

| 디렉터리 | 담당(예시) |
| --- | --- |
| `frontend/` | PM·프론트 (민규) / 수민 — TDS·UI |
| `backend/` | RAG·API (주찬) |
| `collect/` | RSS (상준) |
| `pipeline/` · `eval/` | LLM·평가 (동우) |

> 루트에 예전 `node_modules/`가 남아 있으면 지우고, 프론트는 `frontend/`에서만 `npm install` 하면 됩니다.

---

## 📅 개발 일정

| 주차 | 기간 | 목표 |
| --- | --- | --- |
| 1주차 | 03/13 ~ 03/19 | RSS 수집 파이프라인 구축, 기획안 제출 ✅ |
| 2주차 | 03/20 ~ 03/26 | 기획안 발표, 피드백 수렴 ✅ |
| 3주차 | 03/27 ~ 04/09 | 기술 스택 확정, Supabase 세팅, POC 개발 ✅ |
| 4주차 | 04/10 ~ 04/23 | FastAPI 백엔드 연동, LoRA 파인튜닝 |
| 5주차 | 04/24 ~ 05/07 | RAG 추천, 토스 미니앱 UI 완성 |
| 6주차 | 05/08 ~ 05/19 | 성능 평가, 발표 자료 준비 |
| **최종** | **05/20** | **최종 발표 및 시연** |

---

## ✅ MVP 체크리스트

- [ ] 토스 미니앱 UI (WebView 방식)
- [ ] Qwen3.5-4B 번역 + 요약 통합 파이프라인
- [ ] LoRA 파인튜닝 (AIHub 영-한 코퍼스)
- [ ] Supabase pgvector RAG 추천
- [ ] BLEU / COMET / G-Eval 평가 파이프라인
- [ ] 신뢰도 스코어링 (팩트 / 루머 / 불명확)
- [ ] 격식체 / 일상체 복사 버튼
- [ ] 부재중 요약 알림
- [ ] 신조어 영문 유지 (Term Preservation Rate ≥ 95%)

---

*생성 AI 7회차 Deep Dive 프로젝트 | 최종 발표: 2026년 5월 20일*
