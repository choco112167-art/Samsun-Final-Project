import os
import requests
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

sb = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY")
)

OLLAMA_URL  = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1").replace("/v1", "")
EMBED_MODEL = "mxbai-embed-large"


def make_embedding(text: str) -> list[float]:
    resp = requests.post(
        f"{OLLAMA_URL}/api/embeddings",
        json={"model": EMBED_MODEL, "prompt": text},
    )
    resp.raise_for_status()
    return resp.json()["embedding"]


# ── 1. 유저 온보딩 ──────────────────────────────
def save_user(user_id: str, interest_tags: list[str]):
    combined    = " ".join(interest_tags)
    user_vector = make_embedding(combined)

    sb.table("users").upsert({
        "user_id":       user_id,
        "interest_tags": interest_tags,
        "user_vector":   user_vector,
    }).execute()

    print(f"유저 {user_id} 저장 완료!")


# ── 2. 피드 추천 ──────────────────────────────
def get_feed(user_id: str, top_k: int = 10):
    result = sb.table("users") \
               .select("user_vector") \
               .eq("user_id", user_id) \
               .execute()

    user_vector = result.data[0]["user_vector"]

    result = sb.rpc("match_articles", {
        "query_vector": user_vector,
        "top_k":        top_k,
    }).execute()

    return result.data


# ── 3. 테스트 ──────────────────────────────
if __name__ == "__main__":
    save_user(
        user_id="550e8400-e29b-41d4-a716-446655440099",
        interest_tags=["LLM", "반도체", "AI 스타트업"]
    )

    feed = get_feed("550e8400-e29b-41d4-a716-446655440099")
    for article in feed:
        print(article)
