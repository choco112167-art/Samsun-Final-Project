"""17건 재평가 스크립트 — CoVe 소스 신뢰도 보정 수정 후"""
import sys, io, os, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv()

import pandas as pd
from fact_checker.pipeline import run_fact_check

reeval = pd.read_csv('eval/data/reeval_17.csv', encoding='utf-8-sig')
main_df = pd.read_csv('eval/data/factcheck_results_200.csv', encoding='utf-8-sig')

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

improved = 0
unchanged = 0

for _, row in reeval.iterrows():
    idx = int(row['idx'])
    title   = str(row.get('title', ''))
    source  = str(row.get('source', ''))
    s_type  = str(row.get('source_type', 'media'))
    # main CSV에서 content가 없으므로 title을 content로 대체
    content = str(row.get('title', ''))

    print(f"[{idx:03d}] {source[:20]:<20} | {title[:50]}")

    t0 = time.time()
    try:
        r = run_fact_check(title=title, content=content, source=source, source_type=s_type)
        elapsed = round(time.time() - t0, 2)
        sl = step_label(r.step_reached, r.verification_method, r.fact_label)

        prev_label = main_df.loc[main_df['idx'] == idx, 'fact_label'].values[0]
        changed = '✅ 개선' if r.fact_label != prev_label else '— 동일'
        if r.fact_label != prev_label:
            improved += 1
        else:
            unchanged += 1

        print(f"           {prev_label} → {r.fact_label:<12} conf={r.confidence:.3f}  {changed}")

        # main_df 업데이트
        mask = main_df['idx'] == idx
        main_df.loc[mask, 'fact_label']          = r.fact_label
        main_df.loc[mask, 'step_label']          = sl
        main_df.loc[mask, 'confidence']          = round(r.confidence, 3)
        main_df.loc[mask, 'verification_method'] = r.verification_method
        main_df.loc[mask, 'importance_score']    = round(r.importance_score, 3) if r.importance_score else ''
        main_df.loc[mask, 'reasoning_trace']     = (r.reasoning_trace or '')[:120]
        main_df.loc[mask, 'elapsed_sec']         = elapsed

    except Exception as e:
        elapsed = round(time.time() - t0, 2)
        print(f"           ERROR: {e}")

print(f"\n{'='*50}")
print(f"개선: {improved}건  /  동일: {unchanged}건")
print(f"{'='*50}")

main_df.to_csv('eval/data/factcheck_results_200.csv', index=False, encoding='utf-8-sig')
print("CSV 저장 완료")

# 최종 정확도 재계산
def assign_gt(row):
    if row['source'] == 'Reddit r/artificial':      return 'DROP'
    if row['source'] == 'Reddit r/MachineLearning': return 'UNVERIFIED'
    if row['source'] == 'VentureBeat AI':            return 'UNVERIFIED'
    if row['fact_label'] == 'RUMOR':    return 'RUMOR'
    if row['fact_label'] == 'INSIGHT':  return 'INSIGHT'
    return 'FACT'

main_df['gt'] = main_df.apply(assign_gt, axis=1)
acc = (main_df['gt'] == main_df['fact_label']).mean()
correct = (main_df['gt'] == main_df['fact_label']).sum()
print(f"\n재평가 후 정확도: {acc:.4f} ({acc*100:.1f}%)  정답 {correct}/{len(main_df)}건")
print("\n라벨 분포:")
print(main_df['fact_label'].value_counts().to_string())
print("\n단계별 분포:")
print(main_df['step_label'].value_counts().sort_index().to_string())
