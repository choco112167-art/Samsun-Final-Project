import os
from dotenv import load_dotenv
from supabase import create_client
from sentence_transformers import SentenceTransformer

load_dotenv()

sb = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY")
)

model = SentenceTransformer("Qwen/Qwen3-Embedding-4B")


# ── 1. 유저 온보딩 ──────────────────────────────
def save_user(user_id: str, interest_tags: list[str]):
    # 관심사 태그를 하나의 문장으로 합쳐서 임베딩
    combined = " ".join(interest_tags)
    user_vector = model.encode(
        combined,
        prompt_name="query",
        normalize_embeddings=True
    ).tolist()[:1024]

    sb.table("users").upsert({
        "user_id":       user_id,
        "interest_tags": interest_tags,
        "user_vector":   user_vector,
    }).execute()

    print(f"유저 {user_id} 저장 완료!")


# ── 2. 피드 추천 ──────────────────────────────
def get_feed(user_id: str, top_k: int = 10):
    # 유저 벡터 불러오기
    result = sb.table("users") \
               .select("user_vector") \
               .eq("user_id", user_id) \
               .execute()

    user_vector = result.data[0]["user_vector"]

    # pgvector 유사도 검색
    result = sb.rpc("match_articles", {
        "query_vector": user_vector,
        "top_k":        top_k,
    }).execute()

    return result.data


# ── 3. 테스트 ──────────────────────────────
if __name__ == "__main__":
    # 테스트 유저 저장
    save_user(
        user_id="550e8400-e29b-41d4-a716-446655440099",
        interest_tags=["LLM", "반도체", "AI 스타트업"]
    )

    # 피드 추천
    feed = get_feed("550e8400-e29b-41d4-a716-446655440099")
    for article in feed:
        print(article)