# -*- coding: utf-8 -*-
"""
trainset_translate_1000.csv 재작업
- 기준: ko_text(한국어 번역본) 길이
- 목표: 150~300자 400건 / 300~500자 350건 / 500자 이상 250건
- 카테고리: IT/AI/테크 관련만
- 중복 id 제거
- 랜덤 시드 고정 (재현성)
"""
import pandas as pd
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

SEED = 42

# ─── 1. 원본 로드 ───────────────────────────────────────────
df = pd.read_csv('eval/data/trainset_aihub.csv', encoding='utf-8')
print(f"원본 행수: {len(df)}")
print(f"컬럼: {df.columns.tolist()}")
print()

# ─── 2. IT/AI/테크 카테고리 필터 ────────────────────────────
# 원본 category 값 확인
print("=== 전체 category 분포 ===")
print(df['category'].value_counts().to_string())
print()

IT_CATS = [
    'IT_과학,IT_과학일반', 'IT_과학,인터넷_SNS', 'IT_과학,모바일',
    'IT_과학,과학', 'IT_과학,보안', 'IT_과학,콘텐츠',
    'IT_과학,게임', 'IT_과학,하드웨어',
    '경제,반도체',   # 반도체는 AI/테크 핵심
]

df_it = df[df['category'].isin(IT_CATS)].copy()
print(f"IT/테크 카테고리 필터 후: {len(df_it)}건")
print(df_it['category'].value_counts().to_string())
print()

# ─── 3. 결측/빈값 제거 ─────────────────────────────────────
df_it = df_it.dropna(subset=['en_text', 'ko_text'])
df_it = df_it[df_it['ko_text'].astype(str).str.strip() != '']
df_it = df_it[df_it['en_text'].astype(str).str.strip() != '']
print(f"결측 제거 후: {len(df_it)}건")

# ─── 4. id 중복 제거 (첫 번째 유지) ────────────────────────
df_it = df_it.drop_duplicates(subset='id', keep='first')
print(f"id 중복 제거 후: {len(df_it)}건")
print()

# ─── 5. 한국어 길이 계산 ────────────────────────────────────
df_it['kor_len'] = df_it['ko_text'].astype(str).apply(len)

b150 = df_it[df_it['kor_len'] < 150]
b1   = df_it[(df_it['kor_len'] >= 150) & (df_it['kor_len'] < 300)]
b2   = df_it[(df_it['kor_len'] >= 300) & (df_it['kor_len'] < 500)]
b3   = df_it[df_it['kor_len'] >= 500]

print("=== 한국어 기준 구간별 가용 건수 ===")
print(f"  150자 미만: {len(b150)}건  (사용 안 함)")
print(f"  150~300자:  {len(b1)}건  (목표 400건)")
print(f"  300~500자:  {len(b2)}건  (목표 350건)")
print(f"  500자 이상: {len(b3)}건  (목표 250건)")
print()

# ─── 6. 구간별 샘플링 ──────────────────────────────────────
TARGET = {150: 400, 300: 350, 500: 250}
samples = []

# 150~300자: 400건
n = min(400, len(b1))
s1 = b1.sample(n=n, random_state=SEED)
samples.append(s1)
print(f"150~300자 샘플: {len(s1)}건")

# 300~500자: 350건
n = min(350, len(b2))
s2 = b2.sample(n=n, random_state=SEED)
samples.append(s2)
print(f"300~500자 샘플: {len(s2)}건")

# 500자 이상: 250건
n = min(250, len(b3))
s3 = b3.sample(n=n, random_state=SEED)
samples.append(s3)
print(f"500자 이상 샘플: {len(s3)}건")

result = pd.concat(samples).reset_index(drop=True)
print(f"\n최종 합계: {len(result)}건")

# ─── 7. 부족분 보완 (500자 이상 부족할 경우 150~500 보충) ──
total_target = 1000
if len(result) < total_target:
    shortage = total_target - len(result)
    used_ids = set(result['id'])
    # 이미 사용된 것 제외한 150자 이상 데이터에서 보충
    pool = df_it[(df_it['kor_len'] >= 150) & (~df_it['id'].isin(used_ids))]
    extra = pool.sample(n=min(shortage, len(pool)), random_state=SEED)
    result = pd.concat([result, extra]).reset_index(drop=True)
    print(f"부족분 보완 +{len(extra)}건 → 합계: {len(result)}건")

# ─── 8. 컬럼 정리 & 저장 ────────────────────────────────────
# trainset_translate_1000.csv 기존 스키마에 맞게 컬럼 정렬
# 원본: id, url, source, title, category, en_text, ko_text, n_sentences
out = result[['id', 'url', 'source', 'title', 'category', 'en_text', 'ko_text', 'n_sentences', 'kor_len']].copy()
out = out.rename(columns={'en_text': 'content', 'ko_text': 'content_ko'})

out_path = 'eval/data/trainset_translate_1000.csv'
out.to_csv(out_path, index=False, encoding='utf-8-sig')
print(f"\n저장 완료: {out_path}")
print()

# ─── 9. 최종 검증 ───────────────────────────────────────────
print("=== 최종 검증 ===")
vf = pd.read_csv(out_path, encoding='utf-8-sig')
vf['kor_len'] = vf['content_ko'].astype(str).apply(len)
print(f"  총 행수: {len(vf)}")
print(f"  150자 미만: {(vf['kor_len'] < 150).sum()}건  (목표: 0건)")
print(f"  150~300자:  {((vf['kor_len'] >= 150) & (vf['kor_len'] < 300)).sum()}건  (목표: 400건)")
print(f"  300~500자:  {((vf['kor_len'] >= 300) & (vf['kor_len'] < 500)).sum()}건  (목표: 350건)")
print(f"  500자 이상: {(vf['kor_len'] >= 500).sum()}건  (목표: 250건)")
print(f"  URL 중복: {vf['url'].duplicated().sum()}건")
print(f"  id 중복: {vf['id'].duplicated().sum()}건")
print()
print("=== category 분포 ===")
print(vf['category'].value_counts().to_string())
print()
print("=== 한국어 길이 통계 ===")
print(f"  min: {vf['kor_len'].min()} / max: {vf['kor_len'].max()} / mean: {vf['kor_len'].mean():.1f} / median: {vf['kor_len'].median():.1f}")
