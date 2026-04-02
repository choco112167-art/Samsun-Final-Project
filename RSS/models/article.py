"""
三鮮 (삼선) - 데이터 모델
담당: 강주찬 (백엔드)
- Article 데이터 클래스
- crawler / db / FastAPI 모두 이 모델을 공유
"""

import hashlib
from dataclasses import dataclass, field


@dataclass
class Article:
    title: str
    url: str
    source: str
    category: str
    country: str
    published_at: str
    content: str = ""
    credibility_score: float = 0.0
    source_type: str = "media"          # 'media' | 'community'
    url_hash: str = field(init=False)

    def __post_init__(self):
        self.url_hash = hashlib.md5(self.url.encode()).hexdigest()