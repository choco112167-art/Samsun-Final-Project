import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv
from supabase import create_client
from backend.save_articles import save_articles as db_save_articles, make_embedding, make_url_hash

load_dotenv()

app = FastAPI()

sb = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY")
)


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
    user_vector = make_embedding(combined)

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
        raise HTTPException(status_code=404, detail="유저 없음")

    user_vector = result.data[0]["user_vector"]

    result = sb.rpc("match_articles", {
        "query_vector": user_vector,
        "top_k":        top_k,
    }).execute()

    return {"feed": result.data}


# ── 기사 저장 ──────────────────────────────
@app.post("/articles")
def save_articles(req: ArticleRequest):
    count = db_save_articles(req.articles)
    return {"message": f"{count}개 기사 저장 완료!"}


# ── 기사 상세 ──────────────────────────────
@app.get("/article/{url_hash}")
def get_article(url_hash: str):
    result = sb.table("articles") \
               .select("*") \
               .eq("url_hash", url_hash) \
               .execute()

    if not result.data:
        raise HTTPException(status_code=404, detail="기사 없음")

    return {"article": result.data[0]}


# ── 검색 ──────────────────────────────
@app.get("/search")
def search(q: str, top_k: int = 10):
    query_vector = make_embedding(q)

    result = sb.rpc("match_articles", {
        "query_vector": query_vector,
        "top_k":        top_k,
    }).execute()

    return {"results": result.data}
