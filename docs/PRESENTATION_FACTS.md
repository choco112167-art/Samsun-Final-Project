# Presentation Facts

이 문서는 최종 발표/PPT에서 말해도 되는 사실과, 후속 고도화로 표현해야 하는 항목을 구분하기 위한 발표자용 기준표입니다.

## 한 문장 소개

삼선뉴스는 해외 AI·IT 뉴스를 한국어 제목, 전문 번역, 격식체/일상체 3줄 요약, 신조어 설명, fact label, 개인화 추천 피드로 재구성해 Apps in Toss에서 제공하는 AI 뉴스 큐레이션 미니앱입니다.

## 최종 제품 구조

| 항목 | 발표 기준 |
| --- | --- |
| 플랫폼 | Apps in Toss `.ait` 미니앱 |
| 프론트엔드 | React 18 + Vite + TypeScript + TDS Mobile |
| 최종 데이터 소스 | Supabase `public.articles` |
| 원천 기사 DB | `samsun_345.db` SQLite, 앱이 직접 읽지 않음 |
| AI 처리 경로 | SQLite/RSS -> Gemma4 E4B/Ollama -> Supabase upsert -> `.ait` 조회 |
| cloud refresh | Supabase Edge/Cron + OpenRouter/Gemini |
| 최종 산출물 | `frontend/samsun-newsapp.ait` |

## 발표에서 말해도 되는 구현 기능

| 기능 | 상태 | 말해도 되는 표현 |
| --- | --- | --- |
| 한국어 뉴스 피드 | 구현 | 해외 AI·IT 뉴스를 한국어 제목, 번역 전문, 3줄 요약으로 보여준다 |
| 격식체/일상체 | 구현 | 사용자가 선택한 말투를 localStorage에 저장해 카드/상세에 적용한다 |
| 원문 링크 | 구현 | `url -> source_url -> original_url` fallback으로 유효한 원문 링크를 연다 |
| 핫이슈 | 구현 | 조회 로그가 없어도 최신/신뢰도 기반 fallback으로 빈 화면을 방지한다 |
| 7개 카테고리 | 구현 | AI 연구, AI 심층, AI 스타트업, AI 윤리, AI 비즈니스, AI 커뮤니티, 테크 전반 |
| 개인화 추천 | 구현 | interest_tags, user_logs, user_vector, match_articles RPC와 fallback을 사용한다 |
| 신조어 RAG | 구현 | Supabase `neologisms`에 등록된 설명만 bottom sheet로 보여준다 |
| fact label | 구현 | FACT/UNVERIFIED/RUMOR/HITL_REQUIRED 상태를 카드/상세에 표시한다 |
| fact insight | 구현 | `fact_reason`/`fact_insight`가 있는 경우 상세에 보수적 설명을 표시한다 |
| HITL | 구현 범위 제한 | 완전한 관리자 승인 시스템이 아니라 검토 대상 분리 및 표시 구현 |

## 모델 전략

| 모델/기술 | 최종 역할 |
| --- | --- |
| Gemma4 E4B | 번역, 요약, 카테고리 분류, fact label 생성의 메인 모델 |
| Qwen3-Embedding-0.6B | 기사/사용자 embedding 전용 |
| Supabase pgvector | 사용자 벡터 기반 후보 검색 |
| Qwen 계열 번역 모델 | 초기 실험에서 한자 혼입 이슈가 있어 최종 메인 번역 모델에서 제외 |
| Qwen3.5 | 최종 추천 LLM으로 사용하지 않음 |
| LLM Re-ranking | 최종 데모 기본 비활성, Gemma4 기반 후속 확장 옵션 |

## 개인화 추천 설명 3문장

1. 삼선뉴스는 온보딩 관심사와 기사 클릭 이력을 Supabase `users`, `user_logs`에 저장해 사용자별 관심 프로필을 만든다.
2. 클릭한 기사에 1024차원 embedding이 있으면 `users.user_vector = old * 0.6 + article * 0.4`로 갱신하고, `match_articles` RPC로 유사한 후보를 가져온다.
3. RPC나 embedding이 없을 때도 앱이 깨지지 않도록 관심 카테고리, 최근 클릭 카테고리, 최신 완성 기사 기반 fallback 추천을 제공한다.

```mermaid
flowchart LR
  Interest["온보딩 interest_tags"] --> Users["users"]
  Click["기사 클릭"] --> Logs["user_logs"]
  Click --> Emb["articles.embedding<br/>Qwen3-Embedding-0.6B"]
  Emb --> Vector["users.user_vector<br/>old*0.6 + article*0.4"]
  Vector --> Match["match_articles RPC"]
  Match --> Feed["내 피드"]
  Users --> Fallback["interest/recent/latest fallback"]
  Logs --> Fallback
  Fallback --> Feed
```

## 신조어 RAG 설명

```mermaid
flowchart LR
  Terms["AI 처리 단계<br/>neologism_terms"] --> DB["Supabase neologisms"]
  DB --> Front["프론트 dictionary 조회"]
  Front --> Matcher["allowlist + stopword matcher"]
  Matcher --> UI["inline highlight"]
  UI --> Sheet["bottom sheet explanation"]
```

발표 표현:
- “모르는 용어는 임의 생성하지 않고, Supabase `neologisms.explanation`이 있는 등록 용어만 설명합니다.”
- “`The`, `Tech`, `AI`, `Meta`, `Google`, `OpenAI`, `Anthropic`, `Nvidia` 같은 일반 단어/회사명/출처명은 발표용 하이라이트에서 제외했습니다.”

## Fact label / HITL 표현

발표 표현:

> 삼선뉴스는 자동 팩트체크 결과가 불확실한 기사를 `HITL_REQUIRED`로 분류해 사람 검토가 필요한 대상으로 분리한다. 최종 데모에서는 기사 상세 화면에 `FACT`/`UNVERIFIED`/`RUMOR`/`HITL_REQUIRED` 라벨과 fact insight를 표시하며, 실제 운영 단계에서는 관리자가 최종 판정을 내리는 HITL 관리자 플로우로 확장할 수 있도록 설계했다.

주의:
- “완전한 관리자 승인 시스템 구현 완료”라고 말하지 않는다.
- “HITL 검토 대상 분리 및 표시 구현”이라고 표현한다.
- fact insight는 보수적 설명이며, 없는 경우 빈 박스를 띄우지 않는다.

## 데이터 수집 슬라이드 구조

| 구분 | 소스 |
| --- | --- |
| 언론사 RSS | TechCrunch, MIT Technology Review, The Verge, VentureBeat AI, The Guardian Tech, IEEE Spectrum, The Decoder |
| 커뮤니티 | Lemmy Technology, Hacker News AI/LLM/ML |
| 제외 | Reddit |

Reddit 제외 이유:

> 초기에는 Reddit 계열 커뮤니티 수집도 검토했으나, API/RSS 접근 정책 변화와 데이터 라이선싱 리스크로 인해 최종 수집 대상에서 제외했습니다. 대신 Lemmy API와 Hacker News hnrss.org를 활용해 커뮤니티 기반 AI/LLM/ML 소스를 안정적으로 수집했습니다.

## 최종 데모 데이터 스냅샷

| 항목 | 값 |
| --- | ---: |
| 최종 노출 가능 기사 수 | 104 |
| DEMO/[시연용] 노출 위반 | 0 |
| 미완성 노출 위반 | 0 |
| URL 없는 노출 기사 | 0 |
| invalid URL | 0 |
| 핫이슈 후보 | 104 |
| visible fact insight/reason 보유 기사 | 40 |
| visible HITL_REQUIRED 기사 | 2 |

카테고리 분포:

| 카테고리 | 기사 수 |
| --- | ---: |
| AI 연구 | 16 |
| AI 심층 | 13 |
| AI 스타트업 | 7 |
| AI 윤리 | 15 |
| AI 비즈니스 | 37 |
| AI 커뮤니티 | 8 |
| 테크 전반 | 8 |

## Apps in Toss 시연 순서

1. Toss Console test8에 `frontend/samsun-newsapp.ait` 업로드
2. 실기기 Toss 앱에서 삼선뉴스 실행
3. 홈 피드: 한국어 제목, 3줄 요약, 카테고리, fact label 확인
4. 카테고리: 7개 카테고리 탭 확인
5. 상세: 격식체/일상체 전환, 번역 전문, 원문 링크 확인
6. 핫이슈: 빈 화면 없이 후보 표시 확인
7. 내 피드: 개인화 추천과 deterministic reason 확인
8. 신조어: 하이라이트 탭 후 bottom sheet 설명 확인
9. Fact/HITL: 라벨과 fact insight 확인

## Supabase SQL Editor 적용 목록

발표 전 반드시 실행:

```text
backend/sql/final_demo_supabase_patch.sql
```

이 SQL은 `public.articles` 기준 `match_articles` RPC를 다시 만들고, `record_article_view`, `save_user_interests`, `blend_vectors_1024`, `users`, `user_logs`, `source_url/original_url`, `fact_reason/fact_insight`, demo visibility 필드를 보강한다. GitHub push만으로 Supabase SQL이 자동 적용되지는 않는다.

발표 전 실행하지 않아도 됨:

```text
backend/sql/optional_pgvector_indexes.sql
```

벡터 인덱스는 선택사항이다. Supabase free tier에서는 `maintenance_work_mem` 한도 때문에 ivfflat/hnsw index 생성이 실패할 수 있으므로, 발표용 소규모 데이터에서는 `final_demo_supabase_patch.sql`만 실행하면 된다.

## 후속 고도화로 말해야 하는 기능

- HITL 관리자 승인/반려 페이지
- Gemma4 기반 LLM Re-ranking
- 전체 기사 embedding 대규모 backfill
- 정량 평가 확대: 번역 품질, 요약 품질, 추천 만족도
- Supabase Edge/Cron refresh 운영 모니터링

## 말하면 안 되는 표현

- “Qwen3.5가 최종 추천 LLM이다”
- “LLM Re-ranking이 최종 데모 기본 경로다”
- “Reddit을 최종 커뮤니티 수집 소스로 쓴다”
- “완전한 HITL 관리자 승인 시스템을 구현했다”
- “SQLite DB를 앱이 직접 읽는다”
- “DEMO/미완성 기사를 최종 피드에 노출한다”
