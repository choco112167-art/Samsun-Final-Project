import os
import hashlib
from dotenv import load_dotenv
from supabase import create_client
from sentence_transformers import SentenceTransformer

load_dotenv()

sb = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY")
)

# 임베딩 모델 로드
model = SentenceTransformer("Qwen/Qwen3-Embedding-4B")

def make_url_hash(url: str) -> str:
    return hashlib.md5(url.encode()).hexdigest()

def save_articles(articles: list):
    batch = []

    for article in articles:
        url_hash = make_url_hash(article["original_url"])

        # 임베딩 생성 (translation 기준)
        embedding = model.encode(
            article["translation"],
            prompt_name="document",
            normalize_embeddings=True
            ).tolist()[:1024]

        batch.append({
            "url_hash":      url_hash,
            "article_id":    article.get("article_id"),
            "source":        article.get("source"),
            "source_type":   article.get("source_type"),
            "original_url":  article.get("original_url"),
            "published_at":  article.get("published_at"),
            "collected_at":  article.get("collected_at"),
            "original_text": article.get("original_text"),
            "translation":   article.get("translation"),
            "summary_formal":article.get("summary_formal"),
            "summary_casual":article.get("summary_casual"),
            "keywords":      article.get("keywords"),
            "category":      article.get("category"),
            "embedding":     embedding,
        })

    # 배치 삽입 (중복이면 스킵)
    sb.table("articles").upsert(
        batch,
        on_conflict="url_hash"
    ).execute()

    print(f"{len(batch)}개 기사 저장 완료!")