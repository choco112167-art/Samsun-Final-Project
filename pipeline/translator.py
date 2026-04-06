import ollama
from dotenv import load_dotenv
import os

load_dotenv()

MODEL = os.getenv("MODEL_NAME", "qwen3.5:4b")

FORMAL_PROMPT = """당신은 AI 뉴스 전문 번역가입니다.
입력된 기사를 한국어 격식체로 번역하세요.

규칙:
1. RAG, LLM, GPU, API, NPU 등 약어는 영문 유지
2. Fine-tuning→파인튜닝, Embedding→임베딩 등 음차 처리
3. 신조어는 첫 등장 시 원어(한국어, 설명) 형식으로 표기
4. 격식체 사용 (~습니다, ~됩니다)
"""

CASUAL_PROMPT = """당신은 AI 뉴스 전문 번역가입니다.
입력된 기사를 한국어 일상체로 번역하세요.

규칙:
1. RAG, LLM, GPU, API, NPU 등 약어는 영문 유지
2. Fine-tuning→파인튜닝, Embedding→임베딩 등 음차 처리
3. 신조어는 첫 등장 시 원어(한국어, 설명) 형식으로 표기
4. 일상체 사용 (~해요, ~예요, ~거예요)
"""

def translate(text: str, style: str = "formal") -> str:
    """기사를 한국어로 번역 (style: formal / casual)"""
    system_prompt = FORMAL_PROMPT if style == "formal" else CASUAL_PROMPT
    response = ollama.chat(
        model=MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"다음 기사를 번역해주세요:\n\n{text}"},
        ],
        options={"temperature": 0.3, "num_gpu": 99},
        think=False,
    )
    content = response.message.content
    if "</think>" in content:
        content = content.split("</think>")[-1].strip()
    return content
