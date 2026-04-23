# -*- coding: utf-8 -*-
import pandas as pd
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 인코딩 자동 감지
for enc in ['utf-8', 'utf-8-sig', 'cp949', 'euc-kr', 'latin-1']:
    try:
        df = pd.read_csv('eval/data/trainset_aihub.csv', encoding=enc)
        print(f'인코딩: {enc}')
        break
    except Exception as e:
        print(f'{enc} 실패: {e}')
        continue

print(f'총 행수: {len(df)}')
print(f'컬럼: {df.columns.tolist()}')
print()

eng_col = df.columns[7]
kor_col = df.columns[8]
print(f'영어 컬럼: {repr(eng_col)}')
print(f'한국어 컬럼: {repr(kor_col)}')

df['kor_len'] = df[kor_col].astype(str).apply(len)
print()
print('=== 한국어 기준 전체 분포 ===')
print(f'  150자 미만: {(df["kor_len"] < 150).sum()}건')
print(f'  150~300자:  {((df["kor_len"] >= 150) & (df["kor_len"] < 300)).sum()}건')
print(f'  300~500자:  {((df["kor_len"] >= 300) & (df["kor_len"] < 500)).sum()}건')
print(f'  500자 이상: {(df["kor_len"] >= 500).sum()}건')
print()
print('=== category 분포 (상위 25) ===')
print(df['category'].value_counts().head(25).to_string())
