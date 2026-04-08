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
OUTPUT_FILE = "judgement_result.xlsx"

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

    results = []

    for i in range(4, min(4 + 1000, len(df))):  # 4행부터 1000건
        row = df.iloc[i]
        original    = str(row[5])
        translation = str(row[6])
        summary     = str(row[7])

        # 빈 행 스킵
        if not original or original == "nan":
            continue

        print(f"[{i-3}/1000] 평가 중...")
        result = evaluate(original, translation, summary)

        if result:
            results.append({
                "no":             i - 3,
                "accuracy":       result.get("accuracy"),
                "naturalness":    result.get("naturalness"),
                "rule_compliance": result.get("rule_compliance"),
                "summary_quality": result.get("summary_quality"),
                "total":          result.get("total"),
                "feedback":       result.get("feedback"),
                "original":       original[:200],
                "translation":    translation[:200],
                "summary":        summary[:200],
            })

    # 결과 저장
    result_df = pd.DataFrame(results)
    result_df.to_excel("judgement_result.xlsx", index=False)
    print(f"\n완료! judgement_result.xlsx 저장됨")
    print(f"평균 총점: {result_df['total'].mean():.2f}/20")


if __name__ == "__main__":
    main()
