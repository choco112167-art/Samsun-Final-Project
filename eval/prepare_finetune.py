"""
파인튜닝 데이터 준비
trainset.csv → trainset_chat.jsonl (Qwen3.5-4B 채팅 포맷)

Instruct 모델은 채팅 포맷(system/user/assistant)으로 학습해야 함.
HuggingFace TRL SFTTrainer가 읽는 표준 JSONL 형식으로 변환.

실행:
    python eval/prepare_finetune.py
    python eval/prepare_finetune.py --limit 500   # 샘플 수 제한

출력:
    eval/data/trainset_chat.jsonl   (파인튜닝 학습용)
    eval/data/testset_chat.jsonl    (파인튜닝 후 평가용, run_eval.py와 별도)
"""

import os
import sys
import csv
import json
import re
import argparse

sys.stdout.reconfigure(encoding="utf-8")

DATA_DIR      = os.path.join(os.path.dirname(__file__), "data")
TRAINSET_PATH = os.path.join(DATA_DIR, "trainset.csv")
TESTSET_PATH  = os.path.join(DATA_DIR, "testset_300.csv")
TRAIN_OUT     = os.path.join(DATA_DIR, "trainset_chat.jsonl")
TEST_OUT      = os.path.join(DATA_DIR, "testset_chat.jsonl")

# ── 시스템 프롬프트 (translate_summarize.py와 동일 규칙) ──────────────
SYSTEM_PROMPT = """You are a professional AI news translator.
Translate the given English news article into natural Korean.

Rules:
- Keep abbreviations like RAG, LLM, GPU, API, NPU in English.
- Keep ALL proper nouns in English: company names (Anthropic, OpenAI, Google, Meta, Apple, Microsoft, Nvidia, Samsung, Amazon), product names (Alexa, Slack, ChatGPT), and newly coined AI terms.
- Transliterate technical terms: Fine-tuning→파인튜닝, Embedding→임베딩, Prompt→프롬프트.
- For NEW coinages, use: OriginalTerm(한국어, brief explanation) on first mention.
- Output ONLY the Korean translation. No explanation, no preamble."""


def clean_text(text: str) -> str:
    """학습 데이터 텍스트 정제 — 스마트따옴표, 제어문자, 줄바꿈 정규화"""
    text = (text
            .replace('\u201c', '"').replace('\u201d', '"')
            .replace('\u2018', "'").replace('\u2019', "'"))
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
    return text.strip()


def to_chat_format(en_text: str, ko_text: str) -> dict:
    """(영어 원문, 한국어 번역) → 채팅 포맷 dict"""
    return {
        "messages": [
            {"role": "system",    "content": SYSTEM_PROMPT},
            {"role": "user",      "content": en_text},
            {"role": "assistant", "content": ko_text},
        ]
    }


def convert(src_csv: str, out_jsonl: str, limit: int = None):
    """CSV → JSONL 변환"""
    count = 0
    skipped = 0

    with open(src_csv, encoding="utf-8-sig") as f_in, \
         open(out_jsonl, "w", encoding="utf-8") as f_out:

        reader = csv.DictReader(f_in)
        for row in reader:
            if limit and count >= limit:
                break

            en_text = clean_text(row.get("en_text", ""))
            ko_text = clean_text(row.get("ko_text", ""))

            # 너무 짧거나 비어있는 쌍 제외
            if len(en_text) < 20 or len(ko_text) < 10:
                skipped += 1
                continue

            record = to_chat_format(en_text, ko_text)
            f_out.write(json.dumps(record, ensure_ascii=False) + "\n")
            count += 1

    return count, skipped


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None, help="trainset 최대 건수")
    args = parser.parse_args()

    print("=" * 50)
    print("파인튜닝 데이터 변환 시작")
    print("=" * 50)

    # trainset 변환
    print(f"\n[trainset] {TRAINSET_PATH}")
    n, skip = convert(TRAINSET_PATH, TRAIN_OUT, limit=args.limit)
    print(f"  완료: {n}건 저장 / {skip}건 스킵")
    print(f"  출력: {TRAIN_OUT}")

    # testset도 chat 포맷으로 변환 (Kaggle 추론 시 편의용)
    print(f"\n[testset] {TESTSET_PATH}")
    n, skip = convert(TESTSET_PATH, TEST_OUT)
    print(f"  완료: {n}건 저장 / {skip}건 스킵")
    print(f"  출력: {TEST_OUT}")

    print("\n완료! Kaggle에 두 파일 업로드하면 됩니다.")
    print(f"  - {TRAIN_OUT}")
    print(f"  - {TEST_OUT}")
