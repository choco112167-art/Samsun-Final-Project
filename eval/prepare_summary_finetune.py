"""
요약 파인튜닝 데이터 준비
trainset_summary_1120.csv → trainset_summary_chat.jsonl (Qwen3.5-4B 채팅 포맷)

입력: 영문 원문 (원문 본문\n(content 전체))
출력: 한국어 3줄 요약 (✏️수정\n3줄요약)

실행:
    python eval/prepare_summary_finetune.py
    python eval/prepare_summary_finetune.py --limit 500

출력:
    eval/data/trainset_summary_chat.jsonl
"""

import os
import sys
import csv
import json
import re
import argparse

sys.stdout.reconfigure(encoding="utf-8")

DATA_DIR    = os.path.join(os.path.dirname(__file__), "data")
SRC_CSV     = os.path.join(DATA_DIR, "trainset_summary_1120.csv")
OUT_JSONL   = os.path.join(DATA_DIR, "trainset_summary_chat.jsonl")

# 컬럼명 (특수문자/줄바꿈 포함)
COL_BODY    = "원문 본문\n(content 전체)"   # 영문 원문
COL_SUMMARY = "✏️수정\n3줄요약"             # 한국어 3줄 요약

# ── 시스템 프롬프트 (kaggle_finetune.py와 동일) ──────────────
SYSTEM_PROMPT = """You are a professional AI news summarizer.
Summarize the given English news article into Korean formal style (격식체, ~습니다/~됩니다).

Rules:
- Summarize in exactly 3 sentences. Each sentence must cover a DIFFERENT aspect.
- Keep abbreviations like RAG, LLM, GPU, API, NPU in English.
- Keep ALL proper nouns in English (Anthropic, OpenAI, Google, Meta, Nvidia, Samsung, etc.).
- Output ONLY the Korean summary. No explanation, no preamble."""


def clean_text(text: str) -> str:
    """텍스트 정제 — 스마트따옴표, 제어문자, 줄바꿈 정규화"""
    text = (text
            .replace('\u201c', '"').replace('\u201d', '"')
            .replace('\u2018', "'").replace('\u2019', "'"))
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
    return text.strip()


def to_chat_format(body: str, summary: str) -> dict:
    """(영문 본문, 한국어 3줄 요약) → 채팅 포맷 dict"""
    return {
        "messages": [
            {"role": "system",    "content": SYSTEM_PROMPT},
            {"role": "user",      "content": body},
            {"role": "assistant", "content": summary},
        ]
    }


def convert(src_csv: str, out_jsonl: str, limit: int = None):
    count   = 0
    skipped = 0

    with open(src_csv, encoding="utf-8-sig") as f_in, \
         open(out_jsonl, "w", encoding="utf-8") as f_out:

        reader = csv.DictReader(f_in)
        for row in reader:
            if limit and count >= limit:
                break

            body    = clean_text(row.get(COL_BODY, "") or "")
            summary = clean_text(row.get(COL_SUMMARY, "") or "")

            # 너무 짧거나 비어있는 샘플 제외
            if len(body) < 50 or len(summary) < 20:
                skipped += 1
                continue

            # 3줄 요약이 실제로 여러 문장인지 확인 (마침표 또는 줄바꿈 기준)
            sentences = [s.strip() for s in re.split(r'[.\n]', summary) if s.strip()]
            if len(sentences) < 2:
                skipped += 1
                continue

            record = to_chat_format(body, summary)
            f_out.write(json.dumps(record, ensure_ascii=False) + "\n")
            count += 1

    return count, skipped


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None, help="최대 샘플 수")
    args = parser.parse_args()

    print("=" * 50)
    print("요약 파인튜닝 데이터 변환 시작")
    print("=" * 50)
    print(f"\n입력: {SRC_CSV}")

    if not os.path.exists(SRC_CSV):
        print(f"오류: 파일 없음 — {SRC_CSV}")
        sys.exit(1)

    n, skip = convert(SRC_CSV, OUT_JSONL, limit=args.limit)

    print(f"완료: {n}건 저장 / {skip}건 스킵")
    print(f"출력: {OUT_JSONL}")

    # 샘플 확인
    with open(OUT_JSONL, encoding="utf-8") as f:
        sample = json.loads(f.readline())
    print("\n[샘플 확인]")
    print(f"  user:      {sample['messages'][1]['content'][:80]}...")
    print(f"  assistant: {sample['messages'][2]['content'][:80]}...")
