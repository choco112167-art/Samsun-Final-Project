"""
articles 테이블 임베딩 재계산 스크립트
mxbai-embed-large → qwen3-embedding:0.6b 통일 작업

주의: 일반 생성 모델 qwen3:0.6b는 임베딩을 지원하지 않음.
      임베딩 전용 모델 qwen3-embedding:0.6b (1024차원) 사용.

실행:
    python scripts/reembed_articles_qwen3.py          # dry run (1건만 테스트)
    python scripts/reembed_articles_qwen3.py --apply  # 전체 적용
"""
import asyncio
import os
import sys
from supabase import create_client
import httpx
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
EMBED_MODEL = "qwen3-embedding:0.6b"
EXPECTED_DIM = 1024


async def get_embedding(text: str) -> list[float]:
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            f"{OLLAMA_URL}/api/embeddings",
            json={"model": EMBED_MODEL, "prompt": text}
        )
        resp.raise_for_status()
        return resp.json()["embedding"]


async def reembed_all(dry_run: bool = True):
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("❌ SUPABASE_URL 또는 SUPABASE_KEY가 .env에 없음")
        sys.exit(1)
    
    sb = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    print(f"📥 articles 테이블 조회 중...")
    res = sb.table("articles").select("url_hash, translation").execute()
    articles = [a for a in res.data if a.get("translation")]
    print(f"📊 대상 기사: {len(articles)}개")
    
    if not articles:
        print("⚠️ translation 있는 기사 없음. 종료.")
        return
    
    if dry_run:
        print("\n⚠️ DRY RUN 모드 — 실제 업데이트 안 함")
        sample = articles[0]
        print(f"샘플 url_hash: {sample['url_hash']}")
        print(f"샘플 translation 앞 100자: {sample['translation'][:100]}...")
        emb = await get_embedding(sample["translation"])
        print(f"✅ 임베딩 차원: {len(emb)} (예상: {EXPECTED_DIM})")
        print(f"✅ 처음 5개 값: {emb[:5]}")
        if len(emb) != EXPECTED_DIM:
            print(f"❌ 차원 불일치! Ollama 모델이 잘못 설치됐을 수 있음.")
            sys.exit(1)
        print("\n💡 정상이면 --apply 옵션으로 전체 실행:")
        print("   python scripts/reembed_articles_qwen3.py --apply")
        return
    
    print(f"\n🚀 {len(articles)}개 재임베딩 시작... (순차 처리, 요청 간 0.1s sleep)")
    success, fail = 0, 0
    for i, art in enumerate(articles, 1):
        try:
            emb = await get_embedding(art["translation"])
            if len(emb) != EXPECTED_DIM:
                print(f"⚠️ [{i}/{len(articles)}] 차원 이상 ({len(emb)}): {art['url_hash']}")
                fail += 1
                await asyncio.sleep(0.1)
                continue
            
            sb.table("articles").update(
                {"embedding": emb}
            ).eq("url_hash", art["url_hash"]).execute()
            success += 1
            
            if i % 10 == 0:
                print(f"  진행: {i}/{len(articles)} (성공 {success}, 실패 {fail})")
        except Exception as e:
            print(f"❌ [{i}/{len(articles)}] 실패 {art['url_hash']}: {e}")
            fail += 1

        await asyncio.sleep(0.1)

    print(f"\n✅ 완료: 성공 {success} / 실패 {fail}")


if __name__ == "__main__":
    apply = "--apply" in sys.argv
    asyncio.run(reembed_all(dry_run=not apply))
