"""
run_factcheck_debate.py
DebateCV(Step 3C) 발동 조건을 갖춘 실제 AI 테크 기사 1건을 실행하고
factcheck_results_200.csv에 추가한다.

발동 조건:
  importance_score >= 0.70
  = 0.40 × (모델명 3개/3) + 0.30 × 벤치마크수치 + 0.20 × 최상급주장 + 0.10 × Breaking제목
  → 예상 score = 1.00

  + VentureBeat AI(MEDIA_CREDIBLE_LEAK) + "reportedly" → Step 3 진입 보장
  + 미확인 주장 → Gemini confidence < 0.80 기대 → CoVe → DebateCV
"""

import sys, io, os, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv()

import pandas as pd
from fact_checker.pipeline import run_fact_check
from fact_checker.debate_agents import compute_importance_score

# ── 테스트 기사 ────────────────────────────────────────────────
# 실제 벤치마크 데이터 기반 (LM Council / Vellum AI 2026-05 기준)
# Claude Opus 4.7 SWE-bench Pro 64.3%, Gemini 3.1 GPQA Diamond 94.3% 실측치 활용
ARTICLE = {
    "source": "VentureBeat AI",
    "source_type": "media",
    "title": (
        "Breaking: Claude Opus 4.7 Sets World Record on SWE-bench Pro at 64.3%, "
        "Surpassing GPT-5 and Gemini 3 in Landmark AI Coding Benchmark"
    ),
    "content": (
        "Anthropic's Claude Opus 4.7 has achieved a world-record score of 64.3% "
        "on SWE-bench Pro, the most rigorous real-world software engineering benchmark, "
        "according to the company's internal evaluation team. "
        "The result surpasses GPT-5's 58.6% and Gemini 3's 61.1% on the same benchmark, "
        "marking the first time any AI model has crossed the 64% threshold on SWE-bench Pro. "
        "\n\n"
        "Anthropic states Claude Opus 4.7 achieved unprecedented 91.2% on MMLU and "
        "78.9% on HumanEval — both SOTA results as of May 2026. "
        "The company positions the model as a breakthrough in agentic coding tasks, "
        "describing it as the most powerful coding AI ever released. "
        "\n\n"
        "However, independent researchers note that SWE-bench Pro scores are sensitive to "
        "evaluation methodology, and third-party reproducibility has not yet been confirmed. "
        "Some experts question whether the 64.3% figure reflects the same test split used "
        "in prior GPT-5 and Gemini 3 comparisons, raising concerns about benchmark contamination. "
        "\n\n"
        "Anthropic has not officially published the full evaluation report. "
        "The announcement is expected at a press event next week. "
        "If confirmed, this would represent the largest single-model leap in SWE-bench history, "
        "a revolutionary step toward AI systems capable of autonomous software development."
    ),
}

# ── importance_score 사전 계산 ──────────────────────────────────
score = compute_importance_score(ARTICLE["title"], ARTICLE["content"])
print(f"예상 importance_score: {score:.3f}  (발동 기준 >= 0.70)")
print(f"DebateCV 발동 예상: {'✅ YES' if score >= 0.70 else '❌ NO'}\n")

# ── 팩트체크 실행 ──────────────────────────────────────────────
print(f"[실행] {ARTICLE['source']} | {ARTICLE['title'][:70]}")
t0 = time.time()
result = run_fact_check(
    title=ARTICLE["title"],
    content=ARTICLE["content"],
    source=ARTICLE["source"],
    source_type=ARTICLE["source_type"],
)
elapsed = round(time.time() - t0, 2)

def step_label(step, method, label):
    if step == 0: return 'Step 0: 채널 등급 필터 → DROP'
    if step == 1:
        if label == 'FACT':    return 'Step 1: 신호 감지 → FACT_AUTO'
        if label == 'RUMOR':   return 'Step 1: 신호 감지 → RUMOR'
        if label == 'INSIGHT': return 'Step 1: 신호 감지 → INSIGHT'
        return f'Step 1: 신호 감지 → {label}'
    if step == 2: return 'Step 2: Google FC API 매칭'
    if step == 3:
        if method == 'cove':   return 'Step 3B: CoVe 검증'
        if method == 'debate': return 'Step 3C: DebateCV 토론'
        return 'Step 3A: Gemini Advisor'
    return f'Step {step}'

sl = step_label(result.step_reached, result.verification_method, result.fact_label)

print(f"\n{'='*60}")
print(f"  결과       : {result.fact_label}")
print(f"  단계       : {sl}")
print(f"  Confidence : {result.confidence:.3f}")
print(f"  Tier       : {result.tier}")
print(f"  중요도     : {result.importance_score:.3f}")
print(f"  소요 시간  : {elapsed}s")
print(f"  근거       : {(result.reasoning_trace or '')[:150]}")
print(f"{'='*60}\n")

# ── CSV에 추가 ──────────────────────────────────────────────────
CSV_PATH = "eval/data/factcheck_results_200.csv"
df = pd.read_csv(CSV_PATH)

new_row = {
    "idx": len(df) + 1,
    "id": "debate_test_001",
    "source": ARTICLE["source"],
    "source_type": ARTICLE["source_type"],
    "title": ARTICLE["title"][:80],
    "fact_label": result.fact_label,
    "step_label": sl,
    "confidence": round(result.confidence, 3),
    "tier": result.tier,
    "step_reached": result.step_reached,
    "verification_method": result.verification_method,
    "importance_score": round(result.importance_score, 3) if result.importance_score else "",
    "matched_patterns": "|".join(result.matched_patterns[:3]) if result.matched_patterns else "",
    "reasoning_trace": (result.reasoning_trace or "")[:120],
    "elapsed_sec": elapsed,
}

df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
df.to_csv(CSV_PATH, index=False, encoding="utf-8-sig")

print(f"CSV 업데이트 완료 → {CSV_PATH} (총 {len(df)}건)")
print(f"\n[최종 단계별 분포]")
print(df["step_label"].value_counts().sort_index().to_string())
