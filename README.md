# 三鮮 (삼선) — AI 테크 뉴스 큐레이션 미니앱

> 추천 · 요약 · 번역을 하나의 흐름으로  
> 토스 미니앱 | React + Vite + TypeScript | 생성 AI 7회차 Deep Dive 프로젝트

---

## 👥 팀 소개

| 이름 | 역할 | 담당 |
|---|---|---|
| 김민규 (팀장) | PM + 프론트엔드 | 전체 일정 관리, 토스 미니앱 UI, 발표 총괄 |
| 이상준 | 데이터 수집 | RSS/크롤러 구축, 데이터 전처리 파이프라인 |
| 정수민 | 번역 모델 | mBART/OPUS-MT 번역, BLEU 평가 |
| 이동우 | 요약 모델 | KoBART/mT5 요약, ROUGE 평가, 3줄 요약 최적화 |
| 강주찬 | RAG + 백엔드 | FAISS 기반 추천, FastAPI 백엔드, DB 설계 |

---

## 🎯 문제 정의

AI 종사자·학습자들은 수십 개의 해외 전문 매체에 흩어진 정보를 매일 직접 찾아 읽어야 합니다.

- **투자자** — AI 시장 흐름을 파악하고 싶지만 매일 수십 개 매체를 확인할 시간이 없음
- **개발자** — 최신 AI 기술 트렌드를 캐치하고 싶지만 업무 중 긴 원문을 읽을 여유가 없음
- **AI 학습 뉴비** — AI에 관심이 생겼지만 어디서 무엇부터 봐야 할지 모름

---

## ✨ 핵심 기능

| 기능 | 설명 | 모델 |
|---|---|---|
| 🔍 개인화 추천 (RAG) | 관심 주제 기반 벡터 유사도 검색으로 맞춤 피드 | FAISS + sentence-transformers |
| 📝 3줄 자동 요약 | 영문 기사를 3문장 한국어로 자동 요약 | KoBART / mT5 |
| 🌐 번역 스타일 비교 | 격식체 / 일상체 두 가지 번역 동시 제공 | mBART / OPUS-MT |
| ✅ 신뢰도 스코어링 | 루머 / 팩트 라벨 분리 + 출처 신뢰도 평가 | Claude API |
| 📋 즉시 공유 포맷 | 복사 버튼 → 사내 메신저 바로 붙여넣기 | — |

---

## 🛠 기술 스택

**Frontend**
- React + Vite + TypeScript
- 토스 미니앱 (Toss Apps in)

**Backend**
- FastAPI
- SQLite (개발) / MySQL (배포)
- FAISS (벡터 검색)

**AI/ML**
- `gogamza/kobart-summarization` — 한국어 요약
- `Helsinki-NLP/opus-mt-en-ko` — 영→한 번역
- `facebook/mbart-large-50` — 번역 스타일 실험
- `all-MiniLM-L6-v2` — 임베딩
- Claude API — 카테고리 분류 보조

**데이터 수집**
- feedparser, BeautifulSoup, Selenium
- 8개 AI 전문 매체 RSS 자동 수집 (1시간 주기)

---

## 📰 수집 언론사 (8개)

| 언론사 | 국가 | 특화 분야 |
|---|---|---|
| TechCrunch | 미국 | AI 스타트업 |
| MIT Technology Review | 미국 | AI 심층 분석 |
| The Verge | 미국 | 테크 전반 |
| VentureBeat AI | 미국 | AI 비즈니스/투자 |
| The Guardian Tech | 영국 | AI 윤리 |
| IEEE Spectrum | 글로벌 | AI/반도체 |
| Nikkei Asia Tech | 아시아 | 반도체/공급망 |
| BBC Technology | 영국 | AI 일반 |

---

## 🚀 실행 방법

```bash
# 프론트엔드
npm install
npm run dev

# 백엔드
pip install -r requirements.txt
uvicorn main:app --reload
```

---

## 📁 프로젝트 구조

```
samsun_news/
├── src/                  # React 프론트엔드
├── samsun_news_backend/  # FastAPI 백엔드
├── apps-in-toss-examples-main/  # 토스 미니앱 예제
├── public/               # 정적 파일
└── dist/                 # 빌드 결과물
```

---

## 📅 개발 일정

| 주차 | 기간 | 목표 |
|---|---|---|
| 1주차 | 03/13 ~ 03/19 | RSS 수집 파이프라인 구축, 기획안 제출 ✅ |
| 2주차 | 03/20 ~ 03/26 | KoBART 요약 파이프라인, FAISS 임베딩 |
| 3주차 | 03/27 ~ 04/09 | mBART/OPUS-MT 번역, DB 연동 |
| 4주차 | 04/10 ~ 04/23 | FastAPI 백엔드, 추천 알고리즘 연동 |
| 5주차 | 04/24 ~ 05/07 | 토스 미니앱 UI, 전체 파이프라인 통합 |
| 6주차 | 05/08 ~ 05/19 | 성능 개선, 평가 보고서 작성 |
| **최종** | **05/20** | **최종 발표 및 시연** |

---

## ✅ MVP 체크리스트

- [ ] 토스 미니앱 UI 인터페이스
- [ ] KoBART 요약 모델 실동작
- [ ] mBART/OPUS-MT 격식/일상체 비교 번역
- [ ] FAISS 벡터 검색 추천
- [ ] ROUGE/BLEU 모델 비교 실험 1건 이상
- [ ] 신뢰도 스코어링 + 루머/팩트 라벨
- [ ] 복사 버튼 (사내 공유 포맷)
- [ ] 어드민 페이지 (수집 현황 + 모델 성능 모니터링)

---

*생성 AI 7회차 Deep Dive 프로젝트 | 제출일: 2026년 3월 25일*
