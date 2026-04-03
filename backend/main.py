import os
from fastapi import FastAPI
from pydantic import BaseModel
from dotenv import load_dotenv
from supabase import create_client
from sentence_transformers import SentenceTransformer

load_dotenv()

app = FastAPI()

sb = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY")
)

model = SentenceTransformer("Qwen/Qwen3-Embedding-4B")


# ── 요청 데이터 형식 ──────────────────────────────
class OnboardingRequest(BaseModel):
    user_id: str
    interest_tags: list[str]

class ArticleRequest(BaseModel):
    articles: list[dict]


# ── 온보딩 ──────────────────────────────
@app.post("/onboarding")
def onboarding(req: OnboardingRequest):
    combined = " ".join(req.interest_tags)
    user_vector = model.encode(
        combined,
        prompt_name="query",
        normalize_embeddings=True
    ).tolist()[:1024]

    sb.table("users").upsert({
        "user_id":       req.user_id,
        "interest_tags": req.interest_tags,
        "user_vector":   user_vector,
    }).execute()

    return {"message": "온보딩 완료!"}


# ── 피드 추천 ──────────────────────────────
@app.get("/feed/{user_id}")
def get_feed(user_id: str, top_k: int = 10):
    result = sb.table("users") \
               .select("user_vector") \
               .eq("user_id", user_id) \
               .execute()

    if not result.data:
        return {"error": "유저 없음"}

    user_vector = result.data[0]["user_vector"]

    result = sb.rpc("match_articles", {
        "query_vector": user_vector,
        "top_k":        top_k,
    }).execute()

    return {"feed": result.data}


# ── 기사 저장 ──────────────────────────────
@app.post("/articles")
def save_articles(req: ArticleRequest):
    import hashlib
    batch = []

    for article in req.articles:
        url_hash = hashlib.md5(
            article["original_url"].encode()
        ).hexdigest()

        embedding = model.encode(
            article["translation"],
            prompt_name="document",
            normalize_embeddings=True
        ).tolist()[:1024]

        batch.append({**article, "url_hash": url_hash, "embedding": embedding})

    sb.table("articles").upsert(
        batch, on_conflict="url_hash"
    ).execute()

    return {"message": f"{len(batch)}개 기사 저장 완료!"}


# ── 기사 상세 ──────────────────────────────
@app.get("/article/{url_hash}")
def get_article(url_hash: str):
    result = sb.table("articles") \
               .select("*") \
               .eq("url_hash", url_hash) \
               .execute()

    if not result.data:
        return {"error": "기사 없음"}

    return {"article": result.data[0]}


# ── 검색 ──────────────────────────────
@app.get("/search")
def search(q: str, top_k: int = 10):
    query_vector = model.encode(
        q,
        prompt_name="query",
        normalize_embeddings=True
    ).tolist()[:1024]

    result = sb.rpc("match_articles", {
        "query_vector": query_vector,
        "top_k":        top_k,
    }).execute()

    return {"results": result.data}