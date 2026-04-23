# 三鮮 (삼선) — collect / RSS

> 아래 `samsun/` 다이어그램은 **초기 구조 설명용**이며, 현재 레포에서는 `collect/crawler/`, `collect/db/` 등으로 동일 역할이 나뉘어 있습니다.

## 폴더 구조 (개념도)
```
samsun/
├── main.py                # 실행 진입점 (cron으로 1시간마다 실행)
├── db/
│   └── database.py        # DB 초기화 / 저장 / 조회 [담당: 강주찬]
├── crawler/
│   └── rss_crawler.py     # RSS 수집 + AI 필터링    [담당: 이상준]
├── models/
│   ├── article.py         # Article 데이터 클래스    [담당: 강주찬]
│   └── credibility.py     # 신뢰도 스코어링          [담당: 이상준/강주찬]
└── admin/
    └── stats.py           # 어드민 통계 / 로그 조회  [담당: 강주찬]
```

## 실행 방법
```bash
# 1회 수집
python main.py

# cron 등록 (1시간마다 자동 실행)
0 * * * * cd /path/to/samsun && python main.py >> logs/cron.log 2>&1
```

## FastAPI 연동 예시
```python
from db.database import get_connection, get_articles

conn = get_connection()
articles = get_articles(conn, limit=10, category="AI/스타트업")
```

## 토스 미니앱 연동 흐름
```
토스 미니앱 → FastAPI → db/database.py → SQLite/MySQL
                  ↑
         main.py (cron) → crawler → models → db
```
