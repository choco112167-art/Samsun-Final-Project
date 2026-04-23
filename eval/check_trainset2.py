# -*- coding: utf-8 -*-
import pandas as pd
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

df = pd.read_csv('eval/data/trainset_translate_1000.csv', encoding='cp949')

print("=== 기본 정보 ===")
print(f"총 행수: {len(df)}")
print(f"컬럼 수: {len(df.columns)}")
print()

print("=== 컬럼명 ===")
for i, c in enumerate(df.columns):
    print(f"  [{i}] {repr(c)}")
print()

eng_col = df.columns[7]  # 영어 content
kor_col = df.columns[8]  # 한국어 content

# 한국어 번역본 기준 길이 분포
df['kor_len'] = df[kor_col].astype(str).apply(len)
df['eng_len'] = df[eng_col].astype(str).apply(len)

print("=== [핵심] 길이 기준: 한국어 번역본 ===")
b1 = (df['kor_len'] < 150).sum()
b2 = ((df['kor_len'] >= 150) & (df['kor_len'] < 300)).sum()
b3 = ((df['kor_len'] >= 300) & (df['kor_len'] < 500)).sum()
b4 = (df['kor_len'] >= 500).sum()
print(f"  150자 미만  : {b1}건  ← 기준 미달")
print(f"  150~300자   : {b2}건  (목표 400건) {'✅' if b2==400 else f'❌ 차이: {b2-400:+d}'}")
print(f"  300~500자   : {b3}건  (목표 350건) {'✅' if b3==350 else f'❌ 차이: {b3-350:+d}'}")
print(f"  500자 이상  : {b4}건  (목표 250건) {'✅' if b4==250 else f'❌ 차이: {b4-250:+d}'}")
print(f"  150자 이상 합계: {b2+b3+b4}건")
print()

print("=== [참고] 길이 기준: 영어 원문 ===")
e1 = (df['eng_len'] < 150).sum()
e2 = ((df['eng_len'] >= 150) & (df['eng_len'] < 300)).sum()
e3 = ((df['eng_len'] >= 300) & (df['eng_len'] < 500)).sum()
e4 = (df['eng_len'] >= 500).sum()
print(f"  150자 미만  : {e1}건")
print(f"  150~300자   : {e2}건  (목표 400건) {'✅' if e2==400 else f'❌ 차이: {e2-400:+d}'}")
print(f"  300~500자   : {e3}건  (목표 350건) {'✅' if e3==350 else f'❌ 차이: {e3-350:+d}'}")
print(f"  500자 이상  : {e4}건  (목표 250건) {'✅' if e4==250 else f'❌ 차이: {e4-250:+d}'}")
print()

print("=== source 분포 ===")
print(df['source'].value_counts().to_string())
print()

print("=== category 분포 ===")
print(df['category'].value_counts().to_string())
print()

print("=== 중복/결측 확인 ===")
print(f"  URL 중복: {df['url'].duplicated().sum()}건")
print(f"  id 중복: {df['id'].duplicated().sum()}건")
print(f"  영어 결측: {df[eng_col].isna().sum()}건")
print(f"  한국어 결측: {df[kor_col].isna().sum()}건")
print()

print("=== 한국어 길이 통계 ===")
print(f"  min: {df['kor_len'].min()}")
print(f"  max: {df['kor_len'].max()}")
print(f"  mean: {df['kor_len'].mean():.1f}")
print(f"  median: {df['kor_len'].median():.1f}")
print()

# 150자 미만 샘플 (문제 데이터)
short = df[df['kor_len'] < 150]
if len(short) > 0:
    print(f"=== 150자 미만 데이터 샘플 (총 {len(short)}건) ===")
    for i, row in short.head(3).iterrows():
        print(f"  id={row['id']} 한국어({row['kor_len']}자): {str(row[kor_col])[:120]}")
    print()

# id 중복 확인
dups = df[df['id'].duplicated(keep=False)]
if len(dups) > 0:
    print(f"=== id 중복 데이터 ({len(dups)}건) ===")
    print(dups[['id', 'url', 'kor_len']].to_string())
