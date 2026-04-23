# -*- coding: utf-8 -*-
import pandas as pd

df = pd.read_csv('eval/data/trainset_translate_1000.csv', encoding='cp949')

print("=== 기본 정보 ===")
print(f"총 행수: {len(df)}")
print(f"컬럼 수: {len(df.columns)}")
print()

print("=== 컬럼명 ===")
for i, c in enumerate(df.columns):
    print(f"  [{i}] {repr(c)}")
print()

# content 영어, content 한국어 컬럼 찾기
eng_col = df.columns[7]  # 'content' (영어)
kor_col = df.columns[8]  # 'content 번역' (한국어)

print(f"영어 컬럼: {repr(eng_col)}")
print(f"한국어 컬럼: {repr(kor_col)}")
print()

# 한국어 번역본 기준 길이 분포 측정
df['kor_len'] = df[kor_col].astype(str).apply(len)

print("=== 한국어 번역본 길이 분포 ===")
print(f"  150자 미만: {(df['kor_len'] < 150).sum()}건")
print(f"  150~300자:  {((df['kor_len'] >= 150) & (df['kor_len'] < 300)).sum()}건  (목표: 400건)")
print(f"  300~500자:  {((df['kor_len'] >= 300) & (df['kor_len'] < 500)).sum()}건  (목표: 350건)")
print(f"  500자 이상: {(df['kor_len'] >= 500).sum()}건  (목표: 250건)")
print(f"  150자 이상 합계: {(df['kor_len'] >= 150).sum()}건")
print()

# 영어 기준도 확인
df['eng_len'] = df[eng_col].astype(str).apply(len)
print("=== 영어 원문 길이 분포 ===")
print(f"  150자 미만: {(df['eng_len'] < 150).sum()}건")
print(f"  150~300자:  {((df['eng_len'] >= 150) & (df['eng_len'] < 300)).sum()}건")
print(f"  300~500자:  {((df['eng_len'] >= 300) & (df['eng_len'] < 500)).sum()}건")
print(f"  500자 이상: {(df['eng_len'] >= 500).sum()}건")
print()

# source 분포
print("=== source 분포 ===")
print(df['source'].value_counts().to_string())
print()

# category 분포
print("=== category 분포 ===")
print(df['category'].value_counts().to_string())
print()

# 중복 url 확인
print("=== 중복 확인 ===")
print(f"  URL 중복: {df['url'].duplicated().sum()}건")
print(f"  id 중복: {df['id'].duplicated().sum()}건")
print()

# 결측값 확인
print("=== 결측값 ===")
print(f"  영어 결측: {df[eng_col].isna().sum()}건")
print(f"  한국어 결측: {df[kor_col].isna().sum()}건")
print()

# 샘플 출력
print("=== 샘플 (첫 2행) ===")
for i in range(min(2, len(df))):
    row = df.iloc[i]
    print(f"[{i}] 영어({len(str(row[eng_col]))}자): {str(row[eng_col])[:100]}...")
    print(f"[{i}] 한국어({len(str(row[kor_col]))}자): {str(row[kor_col])[:100]}...")
    print()
