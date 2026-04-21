"""
POC 1 사이클
: 영어 기사 → 번역+요약(Qwen3.5-4B) → 임베딩(mxbai-embed-large) → Supabase 저장 → 조회

실행: C:/tmp/venv312/Scripts/python.exe poc_cycle.py
"""
import os, sys, hashlib, uuid, requests
sys.path.insert(0, os.path.dirname(__file__))
sys.stdout.reconfigure(encoding="utf-8")

from dotenv import load_dotenv
load_dotenv()

from supabase import create_client
from pipeline.translate_summarize import translate_and_summarize, estimate_sentences

OLLAMA_URL  = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1").replace("/v1", "")
EMBED_MODEL = "mxbai-embed-large"

SAMPLE_ARTICLE = {
    "source":       "TechCrunch",
    "source_type":  "news",
    "url":          "https://techcrunch.com/poc-test-001",
    "title":        "OpenAI Releases GPT-4o with Improved Reasoning",
    "published_at": "2026-04-03T10:00:00+00:00",
    "collected_at": "2026-04-03T10:05:00+00:00",
    "category":     "AI",
    "keywords":     ["AI", "LLM", "RAG"],
    "content": (
        "OpenAI has released a new version of GPT-4 that significantly improves "
        "reasoning capabilities. The model, called GPT-4o, is now available through "
        "the OpenAI API and can process text, images, and audio simultaneously. "
        "According to OpenAI CEO Sam Altman, the model is twice as fast and half the "
        "cost compared to the previous version. Developers can start testing it today "
        "via the developer playground. The company also announced improvements to "
        "fine-tuning capabilities and a new context window of 128k tokens."
    ),
}

def make_embedding(text: str) -> list[float]:
    resp = requests.post(
        f"{OLLAMA_URL}/api/embeddings",
        json={"model": EMBED_MODEL, "prompt": text},
    )
    resp.raise_for_status()
    return resp.json()["embedding"]

def main():
    sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
    print("✓ Supabase 연결 완료\n")

    # Step 1: 번역 + 요약
    print("Step 1: 번역 + 요약 (Qwen3.5-4B via Ollama)...")
    en_text = SAMPLE_ARTICLE["content"]
    n = estimate_sentences(en_text)
    result = translate_and_summarize(en_text, summary_sentences=n)
    translation    = result.get("translation", "")
    summary_formal = result.get("summary_formal", "")
    summary_casual = result.get("summary_casual", "")

    sep = "-" * 60
    print(f"\n[원문]\n{en_text}\n")
    print(sep)
    print(f"[번역]\n{translation}\n")
    print(sep)
    print(f"[요약 — 격식체]\n{summary_formal}\n")
    print(sep)
    print(f"[요약 — 일상체]\n{summary_casual}\n")

    # Step 2: 임베딩
    print("Step 2: 임베딩 생성 (mxbai-embed-large via Ollama)...")
    embedding = make_embedding(translation)
    print(f"  벡터 차원: {len(embedding)}\n")

    # Step 3: Supabase 저장
    print("Step 3: Supabase articles 테이블에 저장...")
    url_hash = hashlib.md5(SAMPLE_ARTICLE["url"].encode()).hexdigest()
    record = {
        **SAMPLE_ARTICLE,
        "url_hash":       url_hash,
        "translation":    translation,
        "summary_formal": summary_formal,
        "summary_casual": summary_casual,
        "embedding":      embedding,
    }
    sb.table("articles").upsert(record, on_conflict="url_hash").execute()
    print(f"  저장 완료 (url_hash={url_hash})\n")

    # Step 4: 저장 확인
    print("Step 4: 저장 확인...")
    r = sb.table("articles").select("url_hash, source, summary_formal").eq("url_hash", url_hash).execute()
    if r.data:
        row = r.data[0]
        print(f"  ✓ 조회 성공")
        print(f"    url_hash     : {row['url_hash']}")
        print(f"    source       : {row['source']}")
        print(f"    summary_formal: {row['summary_formal']}\n")

    # Step 5: 전체 기사 수
    r2 = sb.table("articles").select("url_hash", count="exact").execute()
    print(f"Step 5: 총 {r2.count}건 저장됨\n")
    print("=== POC 1 사이클 완료 ===")

if __name__ == "__main__":
    main()
