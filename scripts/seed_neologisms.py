"""Seed final demo-safe AI terminology into Supabase neologisms.

The frontend only highlights terms that already have a non-empty explanation in
Supabase. This script keeps the demo useful without adding generic/company/source
terms that caused false positives such as "The", "AI", or "Meta".

Usage:
    python scripts/seed_neologisms.py --dry-run
    python scripts/seed_neologisms.py --run
"""

from __future__ import annotations

import argparse
from typing import Any

from article_pipeline_common import configure_stdio, get_supabase_client


SEED_TERMS: list[dict[str, Any]] = [
    {
        "term": "RAG",
        "ko_suggestion": "검색 증강 생성",
        "explanation": "외부 지식 검색 결과를 함께 넣어 답변 정확도를 높이는 생성 방식입니다.",
    },
    {
        "term": "LLM",
        "ko_suggestion": "대규모 언어 모델",
        "explanation": "대량의 텍스트를 학습해 문장을 이해하고 생성하는 AI 모델입니다.",
    },
    {
        "term": "SLM",
        "ko_suggestion": "소형 언어 모델",
        "explanation": "가벼운 환경에서 빠르게 동작하도록 규모를 줄인 언어 모델입니다.",
    },
    {
        "term": "Fine-tuning",
        "ko_suggestion": "파인튜닝",
        "explanation": "기존 모델을 특정 데이터와 목적에 맞게 추가 학습시키는 과정입니다.",
    },
    {
        "term": "LoRA",
        "ko_suggestion": "저랭크 적응",
        "explanation": "모델 전체가 아니라 작은 어댑터만 학습해 비용을 줄이는 튜닝 기법입니다.",
    },
    {
        "term": "QLoRA",
        "ko_suggestion": "양자화 LoRA",
        "explanation": "양자화된 모델 위에 LoRA를 적용해 메모리 사용을 줄이는 학습 방식입니다.",
    },
    {
        "term": "RLHF",
        "ko_suggestion": "인간 피드백 강화학습",
        "explanation": "사람의 선호 피드백을 반영해 모델 응답을 조정하는 학습 방법입니다.",
    },
    {
        "term": "DPO",
        "ko_suggestion": "직접 선호 최적화",
        "explanation": "선호 데이터로 모델 출력을 직접 조정하는 정렬 학습 방법입니다.",
    },
    {
        "term": "Prompt Injection",
        "ko_suggestion": "프롬프트 주입",
        "explanation": "악의적 입력으로 AI가 원래 지시를 무시하게 만드는 공격 방식입니다.",
    },
    {
        "term": "Jailbreak",
        "ko_suggestion": "탈옥 프롬프트",
        "explanation": "AI 안전 제한을 우회하도록 유도하는 프롬프트 공격입니다.",
    },
    {
        "term": "Guardrail",
        "ko_suggestion": "안전 가드레일",
        "explanation": "AI가 위험하거나 부적절한 출력을 내지 않도록 막는 안전 장치입니다.",
    },
    {
        "term": "Hallucination",
        "ko_suggestion": "환각",
        "explanation": "AI가 실제 근거가 부족한 내용을 사실처럼 생성하는 현상입니다.",
    },
    {
        "term": "Inference",
        "ko_suggestion": "추론 실행",
        "explanation": "학습된 모델이 입력을 받아 실제 답변이나 예측을 생성하는 단계입니다.",
    },
    {
        "term": "Token",
        "ko_suggestion": "토큰",
        "explanation": "언어 모델이 문장을 처리할 때 나누어 보는 작은 텍스트 단위입니다.",
    },
    {
        "term": "Transformer",
        "ko_suggestion": "트랜스포머",
        "explanation": "어텐션 구조를 활용해 문맥을 처리하는 현대 언어 모델의 핵심 구조입니다.",
    },
    {
        "term": "Embedding",
        "ko_suggestion": "임베딩",
        "explanation": "텍스트나 문서를 의미가 반영된 숫자 벡터로 바꾸는 표현 방식입니다.",
    },
    {
        "term": "Vector DB",
        "ko_suggestion": "벡터 데이터베이스",
        "explanation": "임베딩 벡터를 저장하고 의미적으로 가까운 항목을 빠르게 찾는 데이터베이스입니다.",
    },
    {
        "term": "pgvector",
        "ko_suggestion": "Postgres 벡터 확장",
        "explanation": "PostgreSQL/Supabase에서 벡터 유사도 검색을 가능하게 하는 확장 기능입니다.",
    },
    {
        "term": "Re-ranking",
        "ko_suggestion": "재순위화",
        "explanation": "검색된 후보들을 추가 기준으로 다시 정렬해 추천 품질을 높이는 단계입니다.",
    },
    {
        "term": "CoVe",
        "ko_suggestion": "검증 체인",
        "explanation": "모델 답변을 다시 질문하고 검증해 오류를 줄이려는 검증 절차입니다.",
    },
    {
        "term": "HITL",
        "ko_suggestion": "사람 검토 포함",
        "explanation": "AI가 불확실한 결과를 사람 검토 대상으로 넘기는 운영 방식입니다.",
    },
    {
        "term": "Agentic AI",
        "ko_suggestion": "에이전트형 AI",
        "explanation": "목표를 세우고 도구를 사용해 여러 단계를 수행하는 AI 시스템입니다.",
    },
    {
        "term": "AI Agent",
        "ko_suggestion": "AI 에이전트",
        "explanation": "사용자 목표를 위해 도구 호출과 작업 흐름을 수행하는 AI 프로그램입니다.",
    },
    {
        "term": "MCP",
        "ko_suggestion": "모델 컨텍스트 프로토콜",
        "explanation": "AI 모델이 외부 도구와 데이터를 일관된 방식으로 연결하도록 돕는 프로토콜입니다.",
    },
    {
        "term": "Context Engineering",
        "ko_suggestion": "컨텍스트 엔지니어링",
        "explanation": "모델이 필요한 정보를 잘 활용하도록 입력 문맥과 도구 결과를 설계하는 작업입니다.",
    },
    {
        "term": "Vibe Coding",
        "ko_suggestion": "바이브 코딩",
        "explanation": "AI에게 의도를 설명하며 빠르게 코드를 생성·수정하는 개발 방식입니다.",
    },
    {
        "term": "Synthetic Data",
        "ko_suggestion": "합성 데이터",
        "explanation": "실제 데이터 대신 모델 학습이나 평가를 위해 인공적으로 만든 데이터입니다.",
    },
    {
        "term": "Model Collapse",
        "ko_suggestion": "모델 붕괴",
        "explanation": "AI 생성 데이터가 반복 학습에 섞이며 모델 품질과 다양성이 떨어지는 현상입니다.",
    },
    {
        "term": "Quantization",
        "ko_suggestion": "양자화",
        "explanation": "모델 수치 정밀도를 낮춰 메모리와 연산 비용을 줄이는 최적화 방식입니다.",
    },
    {
        "term": "Reasoning Model",
        "ko_suggestion": "추론형 모델",
        "explanation": "복잡한 문제를 단계적으로 풀도록 설계되거나 학습된 AI 모델입니다.",
    },
    {
        "term": "Chain of Thought",
        "ko_suggestion": "사고 사슬",
        "explanation": "문제를 단계별 추론 과정으로 나누어 해결하도록 유도하는 접근입니다.",
    },
    {
        "term": "Multimodal",
        "ko_suggestion": "멀티모달",
        "explanation": "텍스트, 이미지, 음성 등 여러 형태의 입력을 함께 처리하는 AI 방식입니다.",
    },
]


def supported_columns(sb: Any) -> set[str]:
    candidates = ("term", "explanation", "ko_suggestion", "confirmed", "source")
    out: set[str] = set()
    for column in candidates:
        try:
            sb.table("neologisms").select(column).limit(1).execute()
            out.add(column)
        except Exception:
            pass
    return out


def build_payload(row: dict[str, Any], columns: set[str]) -> dict[str, Any]:
    payload = {key: row[key] for key in ("term", "explanation", "ko_suggestion") if key in columns}
    if "confirmed" in columns:
        payload["confirmed"] = True
    if "source" in columns:
        payload["source"] = "FINAL_DEMO_SEED"
    return payload


def main() -> int:
    configure_stdio()
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Print rows without writing. Default if --run is omitted.")
    parser.add_argument("--run", action="store_true", help="Upsert terms into Supabase neologisms.")
    args = parser.parse_args()
    dry_run = not args.run

    sb = get_supabase_client()
    columns = supported_columns(sb)
    if "term" not in columns or "explanation" not in columns:
        raise RuntimeError("neologisms table must expose at least term and explanation columns")

    payloads = [build_payload(row, columns) for row in SEED_TERMS]
    print("[seed-neologisms]")
    print(f"mode: {'dry-run' if dry_run else 'run'}")
    print(f"supported_columns: {', '.join(sorted(columns))}")
    print(f"seed_terms: {len(payloads)}")
    for payload in payloads:
        print(f"  - {payload['term']}: {payload.get('ko_suggestion') or ''}")

    if dry_run:
        print("updated_rows: 0")
        return 0

    for payload in payloads:
        sb.table("neologisms").upsert(payload, on_conflict="term").execute()
    print(f"updated_rows: {len(payloads)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
