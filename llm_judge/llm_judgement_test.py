"""
LLM Judgement - gpt-4o로 번역/요약 품질 평가 (1건 테스트)
- 입력: translated_result.xlsx
- 평가 모델: gpt-4o
- 실행: python llm_judgement_test.py
"""

import pandas as pd
import openai
import os
import json
import re
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")

if not api_key:
    print("오류: .env 파일에서 'OPENAI_API_KEY'를 찾을 수 없습니다.")
else:
    client = openai.OpenAI(api_key=api_key)

INPUT_FILE = "translated_result.xlsx"

JUDGE_PROMPT = """
당신은 AI 뉴스 번역 및 요약 품질을 평가하는 전문가입니다.
아래 원문, 번역문, 요약문을 읽고 각 항목을 1~5점으로 평가하세요.

[평가 기준]
1. 정확성 (1~5점): 원문 내용을 빠짐없이 정확하게 번역했는가
   - 5점: 내용 손실 없이 완벽히 번역
   - 3점: 일부 내용 누락 또는 오역
   - 1점: 심각한 오역 또는 내용 왜곡

2. 자연스러움 (1~5점): 한국어 번역이 자연스러운가
   - 5점: 원어민이 쓴 것처럼 자연스러움
   - 3점: 어색한 표현이 일부 존재
   - 1점: 직역 투가 심하거나 매우 어색함

3. 규칙 준수 (1~5점): 고유명사/기술용어를 영문으로 유지했는가
   - 5점: 모든 고유명사/기술용어 영문 유지
   - 3점: 일부 한국어로 번역됨
   - 1점: 대부분 한국어로 번역됨

4. 요약 품질 (1~5점): 핵심 내용을 잘 담았는가
   - 5점: 핵심 내용을 간결하고 정확하게 요약
   - 3점: 핵심은 있으나 불필요한 내용 포함 또는 누락
   - 1점: 핵심 내용 누락 또는 요약이 부정확

[출력 형식]: 반드시 아래 JSON 형식으로만 출력하세요.
{
    "accuracy": 점수,
    "naturalness": 점수,
    "rule_compliance": 점수,
    "summary_quality": 점수,
    "total": 총점,
    "feedback": "전반적인 피드백 (한국어, 2~3문장)"
}
"""


def evaluate(original: str, translation: str, summary: str) -> dict:
    user_content = f"""
[원문]
{original}

[번역문]
{translation}

[요약문]
{summary}
"""
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": JUDGE_PROMPT},
                {"role": "user", "content": user_content}
            ],
            temperature=0.1
        )
        result = response.choices[0].message.content.strip()
        result = re.sub(r"```json|```", "", result).strip()
        parsed = json.loads(result)
        return parsed
    except Exception as e:
        print(f"Error: {e}")
        return {}


def main():
    if not api_key:
        return

    print(f"파일을 읽는 중: {INPUT_FILE}")
    df = pd.read_excel(INPUT_FILE, header=None)

    # 첫 번째 데이터 행 (4행, 인덱스 4)
    row = df.iloc[4]
    original   = str(row[5])  # 원문 본문
    translation = str(row[6]) # 번역 본문
    summary    = str(row[7])  # 요약

    print("\n=== 평가 대상 ===")
    print(f"원문: {original[:100]}...")
    print(f"번역: {translation[:100]}...")
    print(f"요약: {summary[:100]}...")

    print("\ngpt-4o로 평가 중...")
    result = evaluate(original, translation, summary)

    if result:
        print("\n=== 평가 결과 ===")
        print(f"정확성:     {result.get('accuracy')}/5")
        print(f"자연스러움: {result.get('naturalness')}/5")
        print(f"규칙 준수:  {result.get('rule_compliance')}/5")
        print(f"요약 품질:  {result.get('summary_quality')}/5")
        print(f"총점:       {result.get('total')}/20")
        print(f"피드백:     {result.get('feedback')}")
    else:
        print("평가 실패")


if __name__ == "__main__":
    main()
