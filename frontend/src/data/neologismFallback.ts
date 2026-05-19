import type { NeologismEntry } from './api';

export const FALLBACK_NEOLOGISMS: NeologismEntry[] = [
  { term: 'RAG', ko_suggestion: '검색 증강 생성', explanation: '외부 지식 검색 결과를 함께 넣어 답변 정확도를 높이는 생성 방식입니다.' },
  { term: 'LLM', ko_suggestion: '대규모 언어 모델', explanation: '대량의 텍스트를 학습해 문장을 이해하고 생성하는 AI 모델입니다.' },
  { term: 'Fine-tuning', ko_suggestion: '파인튜닝', explanation: '기존 모델을 특정 데이터와 목적에 맞게 추가 학습시키는 과정입니다.' },
  { term: 'LoRA', ko_suggestion: '저랭크 적응', explanation: '모델 전체가 아니라 작은 어댑터만 학습해 비용을 줄이는 튜닝 기법입니다.' },
  { term: 'Prompt Injection', ko_suggestion: '프롬프트 주입', explanation: '악의적 입력으로 AI가 원래 지시를 무시하게 만드는 공격 방식입니다.' },
  { term: 'Guardrail', ko_suggestion: '안전 가드레일', explanation: 'AI가 위험하거나 부적절한 출력을 내지 않도록 막는 안전 장치입니다.' },
  { term: 'Hallucination', ko_suggestion: '환각', explanation: 'AI가 실제 근거가 부족한 내용을 사실처럼 생성하는 현상입니다.' },
  { term: 'Inference', ko_suggestion: '추론 실행', explanation: '학습된 모델이 입력을 받아 실제 답변이나 예측을 생성하는 단계입니다.' },
  { term: 'Token', ko_suggestion: '토큰', explanation: '언어 모델이 문장을 처리할 때 나누어 보는 작은 텍스트 단위입니다.' },
  { term: 'Transformer', ko_suggestion: '트랜스포머', explanation: '어텐션 구조를 활용해 문맥을 처리하는 현대 언어 모델의 핵심 구조입니다.' },
  { term: 'Embedding', ko_suggestion: '임베딩', explanation: '텍스트나 문서를 의미가 반영된 숫자 벡터로 바꾸는 표현 방식입니다.' },
  { term: 'pgvector', ko_suggestion: 'Postgres 벡터 확장', explanation: 'PostgreSQL/Supabase에서 벡터 유사도 검색을 가능하게 하는 확장 기능입니다.' },
  { term: 'HITL', ko_suggestion: '사람 검토 포함', explanation: 'AI가 불확실한 결과를 사람 검토 대상으로 넘기는 운영 방식입니다.' },
  { term: 'CoVe', ko_suggestion: '검증 체인', explanation: '모델 답변을 다시 질문하고 검증해 오류를 줄이려는 검증 절차입니다.' },
  { term: 'Agentic AI', ko_suggestion: '에이전트형 AI', explanation: '목표를 세우고 도구를 사용해 여러 단계를 수행하는 AI 시스템입니다.' },
  { term: 'MCP', ko_suggestion: '모델 컨텍스트 프로토콜', explanation: 'AI 모델이 외부 도구와 데이터를 일관된 방식으로 연결하도록 돕는 프로토콜입니다.' },
  { term: 'Vibe Coding', ko_suggestion: '바이브 코딩', explanation: 'AI에게 의도를 설명하며 빠르게 코드를 생성·수정하는 개발 방식입니다.' },
  { term: 'Synthetic Data', ko_suggestion: '합성 데이터', explanation: '실제 데이터 대신 모델 학습이나 평가를 위해 인공적으로 만든 데이터입니다.' },
  { term: 'Quantization', ko_suggestion: '양자화', explanation: '모델 수치 정밀도를 낮춰 메모리와 연산 비용을 줄이는 최적화 방식입니다.' },
  { term: 'Reasoning Model', ko_suggestion: '추론형 모델', explanation: '복잡한 문제를 단계적으로 풀도록 설계되거나 학습된 AI 모델입니다.' },
];
