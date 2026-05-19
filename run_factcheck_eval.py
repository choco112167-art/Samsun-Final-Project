"""
run_factcheck_eval.py
testset_200.csv 전체 200건을 팩트체크 파이프라인으로 실행하고
결과를 CSV로 저장한다.

출력: eval/data/factcheck_results_200.csv
"""

import sys, io, os, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv()

import pandas as pd
from fact_checker.pipeline import run_fact_check

INPUT_CSV  = "eval/data/testset_200.csv"
OUTPUT_CSV = "eval/data/factcheck_results_200.csv"
MAX_CONTENT_CHARS = 3000

df = pd.read_csv(INPUT_CSV).reset_index(drop=True)
print(f"testset_200.csv → {len(df)}건 전체 실행\n")

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

COLS = ['idx','id','source','source_type','title',
        'fact_label','step_label','confidence',
        'tier','step_reached','verification_method',
        'importance_score','matched_patterns','reasoning_trace','elapsed_sec']

out_rows = []

for i, row in df.iterrows():
    idx     = i + 1
    title   = str(row.get("원문 제목", "") or "")
    content = str(row.get("원문 (orig_body)", "") or "")[:MAX_CONTENT_CHARS]
    source  = str(row.get("source", "Unknown"))
    s_type  = str(row.get("source_type", "media"))

    print(f"[{idx:03d}/200] {source[:20]:<20} | {title[:50]}")

    t0 = time.time()
    try:
        r = run_fact_check(title=title, content=content,
                           source=source, source_type=s_type)
        elapsed = round(time.time() - t0, 2)
        sl = step_label(r.step_reached, r.verification_method, r.fact_label)
        out_rows.append({
            "idx": idx, "id": row.get("id",""),
            "source": source, "source_type": s_type, "title": title[:80],
            "fact_label": r.fact_label,
            "step_label": sl,
            "confidence": round(r.confidence, 3),
            "tier": r.tier,
            "step_reached": r.step_reached,
            "verification_method": r.verification_method,
            "importance_score": round(r.importance_score, 3) if r.importance_score else "",
            "matched_patterns": "|".join(r.matched_patterns[:3]) if r.matched_patterns else "",
            "reasoning_trace": (r.reasoning_trace or "")[:120],
            "elapsed_sec": elapsed,
        })
        print(f"           → {r.fact_label:<12} | {sl} ({elapsed}s)")
    except Exception as e:
        elapsed = round(time.time() - t0, 2)
        print(f"           → ERROR: {e}")
        out_rows.append({
            "idx": idx, "id": row.get("id",""),
            "source": source, "source_type": s_type, "title": title[:80],
            "fact_label": "ERROR", "step_label": "ERROR", "confidence": 0,
            "tier": "", "step_reached": "", "verification_method": "",
            "importance_score": "", "matched_patterns": "",
            "reasoning_trace": str(e)[:120], "elapsed_sec": elapsed,
        })

os.makedirs("eval/data", exist_ok=True)
result_df = pd.DataFrame(out_rows, columns=COLS)
result_df.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")

print("\n" + "=" * 60)
print(f"  저장 완료: {OUTPUT_CSV}")
print("=" * 60)
print("[라벨 분포]")
print(result_df["fact_label"].value_counts().to_string())
print("\n[단계별 분포]")
print(result_df["step_label"].value_counts().sort_index().to_string())
print(f"\n평균 처리 시간: {result_df['elapsed_sec'].mean():.2f}초/건")
print(f"총 소요 시간 : {result_df['elapsed_sec'].sum():.1f}초")
print("=" * 60)
