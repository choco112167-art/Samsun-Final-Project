import ollama
from dotenv import load_dotenv
import os
from pipeline.utils import preprocess_text

load_dotenv()

MODEL = os.getenv("MODEL_NAME", "qwen3.5:4b")

SYSTEM_PROMPT = """당신은 AI 뉴스 전문 요약가입니다.
입력된 뉴스 기사를 다음 규칙에 따라 한국어로 요약하세요.

규칙:
1. 반드시 3줄로 요약 (각 줄은 핵심 내용 하나)
2. 각 줄은 "• "으로 시작
3. 전문 용어는 영문 그대로 유지 (RAG, LLM, GPU 등)
4. 새로운 고유명사는 첫 등장 시 원어(한국어) 형식으로 표기
5. 객관적이고 간결하게 작성
"""

def summarize(text: str) -> str:
    """뉴스 기사를 3줄 한국어 요약으로 변환"""
    response = ollama.chat(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"다음 기사를 요약해주세요:\n\n{text}"},
        ],
        options={"temperature": 0.3, "num_gpu": 99},
        think=False,
    )
    content = response.message.content
    return preprocess_text(content)
