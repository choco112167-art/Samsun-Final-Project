"""
데이터셋 빌더
한국어-영어 번역 병렬 말뭉치 xlsx 4개 →
    testset_1000.csv  : 평가용 (번역 BLEU/COMET + 요약 G-Eval 공용)
    trainset.csv      : 파인튜닝 학습용 (testset URL 완전 제외)

실행:
    python eval/build_dataset.py
"""

import os
import sys
import random
import csv
from collections import defaultdict

sys.stdout.reconfigure(encoding="utf-8")

# ── 설정 ──────────────────────────────────────────
XLSX_FILES = [
    r"C:\Users\이동우\Desktop\한국어-영어 번역(병렬) 말뭉치\3_문어체_뉴스(1)_200226.xlsx",
    r"C:\Users\이동우\Desktop\한국어-영어 번역(병렬) 말뭉치\3_문어체_뉴스(2).xlsx",
    r"C:\Users\이동우\Desktop\한국어-영어 번역(병렬) 말뭉치\3_문어체_뉴스(3).xlsx",
    r"C:\Users\이동우\Desktop\한국어-영어 번역(병렬) 말뭉치\3_문어체_뉴스(4).xlsx",
]

OUT_DIR       = os.path.join(os.path.dirname(__file__), "data")
TESTSET_PATH  = os.path.join(OUT_DIR, "testset_1000.csv")
TRAINSET_PATH = os.path.join(OUT_DIR, "trainset.csv")

MIN_SENTENCES = 5     # 요약 평가 가능한 최소 문장 수
TESTSET_SIZE  = 1000  # testset 건수
RANDOM_SEED   = 42    # 재현성 고정


def load_corpus(xlsx_files: list) -> dict:
    """4개 xlsx 파일 → URL 기준 기사 단위로 그룹핑"""
    try:
        import openpyxl
    except ImportError:
        print("pip install openpyxl 먼저 실행하세요.")
        sys.exit(1)

    articles = defaultdict(lambda: {"ko": [], "en": [], "category": ""})

    for path in xlsx_files:
        print(f"[읽기] {os.path.basename(path)}")
        wb = openpyxl.load_workbook(path, read_only=True)
        ws = wb.active

        for i, row in enumerate(ws.iter_rows(values_only=True)):
            if i == 0:
                continue  # 헤더 스킵

            # IT/과학 카테고리 필터
            cats = [str(row[c] or "") for c in range(2, 5)]
            if not any("IT" in c or "과학" in c for c in cats):
                continue

            url = str(row[5] or "").strip()
            ko  = str(row[7] or "").strip()
            en  = str(row[8] or "").strip()

            if url and ko and en:
                articles[url]["ko"].append(ko)
                articles[url]["en"].append(en)
                articles[url]["category"] = str(row[2] or "")

        wb.close()

    return articles


def build_datasets(articles: dict):
    """5문장 이상 기사를 testset/trainset으로 분리"""
    os.makedirs(OUT_DIR, exist_ok=True)

    # 5문장 이상 기사만 추출
    long_articles = [
        (url, data) for url, data in articles.items()
        if len(data["en"]) >= MIN_SENTENCES
    ]
    print(f"\n5문장 이상 기사: {len(long_articles)}건")

    # 재현 가능한 랜덤 샘플
    random.seed(RANDOM_SEED)
    random.shuffle(long_articles)

    testset  = long_articles[:TESTSET_SIZE]
    testset_urls = {url for url, _ in testset}

    # trainset: testset URL 완전 제외, 5문장 미만도 포함
    trainset = [
        (url, data) for url, data in articles.items()
        if url not in testset_urls
    ]

    # testset 저장
    _save_csv(testset, TESTSET_PATH)
    print(f"testset  저장 완료: {TESTSET_PATH} ({len(testset)}건)")

    # trainset 저장
    _save_csv(trainset, TRAINSET_PATH)
    print(f"trainset 저장 완료: {TRAINSET_PATH} ({len(trainset)}건)")


def _save_csv(items: list, path: str):
    """(url, data) 리스트 → CSV 저장"""
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["id", "url", "category", "en_text", "ko_text", "n_sentences"])
        for idx, (url, data) in enumerate(items, 1):
            en_text = " ".join(data["en"])
            ko_text = " ".join(data["ko"])
            writer.writerow([idx, url, data["category"], en_text, ko_text, len(data["en"])])


if __name__ == "__main__":
    print("=" * 50)
    print("데이터셋 빌드 시작")
    print("=" * 50)
    articles = load_corpus(XLSX_FILES)
    print(f"\n총 기사 수 (URL 기준): {len(articles)}건")
    build_datasets(articles)
    print("\n완료!")
