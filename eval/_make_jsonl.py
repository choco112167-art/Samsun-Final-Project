"""
번역/요약 JSONL 생성 스크립트
실행: python eval/_make_jsonl.py
"""
import os, json, re
import pandas as pd

sys_path = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(sys_path, "data")

def clean_text(text):
    text = (str(text)
            .replace('\u201c', '"').replace('\u201d', '"')
            .replace('\u2018', "'").replace('\u2019', "'"))
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
    return text.strip()


# ── 번역 JSONL ─────────────────────────────────────────────
TRANSLATE_SYSTEM = """You are a professional AI news translator.
Translate the given English news article into natural Korean.

Rules:
- Keep abbreviations like RAG, LLM, GPU, API, NPU in English.
- Keep ALL proper nouns in English: company names (Anthropic, OpenAI, Google, Meta, Apple, Microsoft, Nvidia, Samsung, Amazon), product names (Alexa, Slack, ChatGPT), and newly coined AI terms.
- Transliterate technical terms: Fine-tuning->파인튜닝, Embedding->임베딩, Prompt->프롬프트.
- For NEW coinages, use: OriginalTerm(한국어, brief explanation) on first mention.
- Output ONLY the Korean translation. No explanation, no preamble."""

src_tr  = os.path.join(DATA_DIR, "trainset_translate_1000.csv")
out_tr  = os.path.join(DATA_DIR, "trainset_translate_chat.jsonl")

df = pd.read_csv(src_tr).dropna(subset=["content", "content_ko"])
df = df[df["content"].str.len() >= 30]
df = df[df["content_ko"].str.len() >= 10]

count = 0
with open(out_tr, "w", encoding="utf-8") as f:
    for _, row in df.iterrows():
        en = clean_text(row["content"])
        ko = clean_text(row["content_ko"])
        if len(en) < 30 or len(ko) < 10:
            continue
        f.write(json.dumps({
            "messages": [
                {"role": "system",    "content": TRANSLATE_SYSTEM},
                {"role": "user",      "content": en},
                {"role": "assistant", "content": ko},
            ]
        }, ensure_ascii=False) + "\n")
        count += 1
print(f"[translate] {count}개 → {out_tr}")


# ── 요약 JSONL ─────────────────────────────────────────────
SUMMARIZE_SYSTEM = """당신은 전문 뉴스 요약가입니다.
주어진 한국어 뉴스 기사를 핵심 내용 중심으로 정확히 3문장으로 요약하세요.

규칙:
- 반드시 3문장으로 요약하고, 각 문장은 서로 다른 측면을 다뤄야 합니다.
- 격식체(~습니다/~됩니다)를 사용하세요.
- RAG, LLM, GPU, API 등 약어는 영문 그대로 유지하세요.
- 고유명사(Anthropic, OpenAI, Google, Meta, Nvidia 등)는 영문 그대로 유지하세요.
- 요약문만 출력하세요. 설명이나 서두 없이."""

src_su = os.path.join(DATA_DIR, "trainset_summary_1120.csv")
out_su = os.path.join(DATA_DIR, "trainset_summarize_chat.jsonl")

df = pd.read_csv(src_su)
body_col = next(c for c in df.columns if "본문번역" in c)
sum_col  = next(c for c in df.columns if "3줄요약" in c)
df = df.dropna(subset=[body_col, sum_col])
df = df[df[body_col].str.len() >= 50]
df = df[df[sum_col].str.len() >= 20]

count = 0
with open(out_su, "w", encoding="utf-8") as f:
    for _, row in df.iterrows():
        body    = clean_text(row[body_col])
        summary = clean_text(row[sum_col])
        if len(body) < 50 or len(summary) < 20:
            continue
        f.write(json.dumps({
            "messages": [
                {"role": "system",    "content": SUMMARIZE_SYSTEM},
                {"role": "user",      "content": body},
                {"role": "assistant", "content": summary},
            ]
        }, ensure_ascii=False) + "\n")
        count += 1
print(f"[summarize] {count}개 → {out_su}")
