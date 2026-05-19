# Fact Review / HITL 관리자 POC

삼선뉴스의 최종 사용자 앱에는 관리자 판정 화면을 넣지 않습니다. Apps in Toss `.ait`는 홈, 카테고리, 핫이슈, 검색, 내 피드, 기사 상세만 제공합니다.

이 문서는 발표용 내부 관리자 POC를 로컬 FastAPI에서 확인하는 방법을 정리합니다. 이 기능은 완전한 운영 관리자 승인 시스템이 아니라, AI 자동 팩트체크가 `HITL_REQUIRED`, `UNVERIFIED`, `RUMOR`, `INSIGHT`로 분리한 검토 대상 목록을 확인하고 필요 시 라벨을 수정하는 최소 POC입니다.

## 실행 위치

- 사용자 앱: 포함하지 않음
- 로컬/내부 관리자 POC: `backend/admin_hitl.py`
- FastAPI 라우트:
  - `GET /admin/fact-review`
  - `GET /admin/hitl`
  - `GET /admin/hitl-candidates`
  - `POST /admin/hitl-review`

## 환경변수

```bash
ADMIN_REVIEW_ENABLED=1
SUPABASE_URL=<supabase-project-url>
SUPABASE_SERVICE_ROLE_KEY=<local-only-service-role-key>
```

`SUPABASE_SERVICE_ROLE_KEY`는 로컬 backend 환경에서만 사용합니다. 프론트엔드 `.ait`에는 절대 넣지 않습니다.

service role key가 없으면 `GET /admin/fact-review`와 `GET /admin/hitl-candidates`는 검토 대상 확인용으로만 사용할 수 있고, 라벨 수정은 비활성화됩니다.

## 기능 범위

| 기능 | 상태 |
| --- | --- |
| 검토 대상 조회 | 구현 |
| FACT / RUMOR / UNVERIFIED / INSIGHT 라벨 변경 | service role key가 있을 때만 구현 |
| fact_reason / fact_insight 보강 | 구현 |
| updated_at 갱신 | 컬럼이 있을 때 구현 |
| admin_review_logs 기록 | optional SQL 적용 시 best-effort |
| Apps in Toss 사용자 앱 노출 | 하지 않음 |

## 적용 SQL

필수:

```sql
-- backend/sql/final_demo_supabase_patch.sql
```

선택:

```sql
-- backend/sql/admin_review_logs.sql
```

`admin_review_logs.sql`은 POC 검토 기록을 남기고 싶을 때만 실행합니다. 발표용 사용자 앱 동작에는 필요하지 않습니다.

## 발표 문구

말할 수 있는 표현:

- “AI 자동 판정이 불확실한 기사는 HITL_REQUIRED로 분리합니다.”
- “내부 Fact Review POC에서 검토 대상 목록을 확인하고, 로컬 관리 경로에서 라벨을 수정할 수 있습니다.”
- “사용자용 Apps in Toss 앱에는 관리자 기능을 노출하지 않습니다.”

말하면 안 되는 표현:

- “완전한 운영 관리자 승인 시스템을 구현했습니다.”
- “Apps in Toss 앱에서 관리자가 라벨을 수정합니다.”
- “모든 기사를 사람이 직접 판정합니다.”
