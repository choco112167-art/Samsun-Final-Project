"""
파인튜닝 전 베이스라인 평가 (qwen3.5-4b-base)
testset_200.csv → Qwen3.5-4B 추론 → BLEU/COMET/TPR + G-Eval → results_200_base.csv

컬럼 매핑 (testset_200.csv):
    원문 (orig_body)         → en_text  (영어 원문)
    신규 번역 (new_body)     → ko_gt    (레퍼런스 번역, BLEU/COMET 기준)
    신규 3줄 요약 (new_summary) → gt_summary (G-Eval 레퍼런스)

실행:
    python eval/run_eval_base.py                    # 전체 200건
    python eval/run_eval_base.py --limit 10         # 빠른 테스트 (10건)
    python eval/run_eval_base.py --skip-geval       # G-Eval 제외 (비용 절약)
    python eval/run_eval_base.py --skip-comet       # COMET 제외 (느릴 때)
    python eval/run_eval_base.py --skip-sheets      # Google Sheets 업로드 제외

결과:
    eval/data/results_200_base.csv  (상세 결과, 파인튜닝 후와 비교용)
    Google Sheets → "베이스라인_200" 시트
"""

import sys
import os
import csv
import argparse
import time

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pipeline.translate_summarize import translate_and_summarize, estimate_sentences
from eval.metrics.bleu_comet import calc_bleu_sentence, load_comet_model, calc_comet
from eval.metrics.term_preservation import check_term_preservation
from eval.metrics.geval import geval_single

TESTSET_PATH   = os.path.join(os.path.dirname(__file__), "data", "testset_200.csv")
RESULTS_PATH   = os.path.join(os.path.dirname(__file__), "data", "results_200_base.csv")
CREDENTIALS    = os.path.join(os.path.dirname(__file__), "..", "client_secret_43865832816-letrps5uc0nohpmaug4b5bo6lf2sf92j.apps.googleusercontent.com.json")
SPREADSHEET_ID = "1KV7gEN-lgxREAWenE4lKyFWi3rfwGpHtYIwHdQtp6Po"
SHEET_NAME     = "베이스라인_200"

MODEL_VERSION  = "qwen3.5-4b-base"

RESULT_HEADERS = [
    "id", "model_version", "url", "category",
    "en_text", "ko_gt",
    "translation", "summary_formal",
    "bleu", "comet", "tpr", "tpr_missing",
    "geval_consistency", "geval_fluency", "geval_coherence", "geval_relevance",
    "geval_avg", "geval_weighted",
    "n_sentences",
]


def load_testset(path: str) -> list[dict]:
    with open(path, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def upload_to_sheets(results_path: str):
    """results_200_base.csv → Google Sheets 업로드"""
    try:
        import gspread
        from google_auth_oauthlib.flow import InstalledAppFlow

        SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

        token_path = os.path.join(os.path.dirname(__file__), "..", "token.json")
        creds = None

        if os.path.exists(token_path):
            from google.oauth2.credentials import Credentials
            creds = Credentials.from_authorized_user_file(token_path, SCOPES)

        if not creds or not creds.valid:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS, SCOPES)
            creds = flow.run_local_server(port=0)
            with open(token_path, "w") as f:
                f.write(creds.to_json())

        gc = gspread.authorize(creds)
        sh = gc.open_by_key(SPREADSHEET_ID)

        try:
            ws = sh.worksheet(SHEET_NAME)
            ws.clear()
        except gspread.WorksheetNotFound:
            ws = sh.add_worksheet(title=SHEET_NAME, rows=210, cols=22)

        with open(results_path, encoding="utf-8-sig") as f:
            rows = list(csv.reader(f))

        ws.update(rows, value_input_option="RAW")
        print(f"Google Sheets 업로드 완료: {len(rows)-1}건 → '{SHEET_NAME}' 시트")

    except Exception as e:
        print(f"⚠ Google Sheets 업로드 실패: {e}")


def print_summary(results_path: str):
    """최종 집계 점수 출력"""
    if not os.path.exists(results_path):
        return

    with open(results_path, encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))

    if not rows:
        return

    def mean(key):
        vals = [float(r[key]) for r in rows if r.get(key) not in ("", "0", "0.0", None)]
        return round(sum(vals) / len(vals), 4) if vals else 0.0

    n = len(rows)
    bleu       = mean("bleu")
    comet      = mean("comet")
    tpr        = mean("tpr")
    geval_avg  = mean("geval_avg")
    geval_w    = mean("geval_weighted")
    g_con      = mean("geval_consistency")
    g_fl       = mean("geval_fluency")
    g_coh      = mean("geval_coherence")
    g_rel      = mean("geval_relevance")

    print()
    print("=" * 60)
    print(f"[베이스라인 평가 결과] {MODEL_VERSION}  (n={n})")
    print("=" * 60)
    print(f"  번역 지표")
    print(f"    BLEU  : {bleu:.2f}   (목표 ≥ 17.0)")
    print(f"    COMET : {comet:.4f}  (파인튜닝 후 비교 기준)")
    print(f"    TPR   : {tpr*100:.1f}%  (목표 ≥ 95%)")
    print()
    print(f"  요약 G-Eval (summary_formal)")
    print(f"    일치성(Consistency) : {g_con:.2f}")
    print(f"    유창성(Fluency)     : {g_fl:.2f}")
    print(f"    일관성(Coherence)   : {g_coh:.2f}")
    print(f"    관련성(Relevance)   : {g_rel:.2f}")
    print(f"    G-Eval 평균         : {geval_avg:.2f}   (목표 ≥ 4.0)")
    print(f"    G-Eval 가중평균     : {geval_w:.2f}")
    print("=" * 60)
    print(f"  결과 파일: {results_path}")
    print()


def run_eval(limit: int = None, skip_geval: bool = False,
             skip_comet: bool = False, skip_sheets: bool = False):
    print("=" * 60)
    print(f"삼선뉴스 파인튜닝 전 베이스라인 평가 ({MODEL_VERSION})")
    print("=" * 60)

    rows = load_testset(TESTSET_PATH)
    if limit:
        rows = rows[:limit]
    print(f"평가 대상: {len(rows)}건\n")

    # COMET 모델 사전 로드
    comet_model = None
    if not skip_comet:
        print("COMET 모델 로딩 중...")
        comet_model = load_comet_model()
        print("COMET 모델 로드 완료\n")

    # 이미 처리된 ID 확인 (중단 후 재시작 대비)
    done_ids = set()
    if os.path.exists(RESULTS_PATH):
        with open(RESULTS_PATH, encoding="utf-8-sig") as f:
            for r in csv.DictReader(f):
                done_ids.add(r["id"])
        print(f"이미 처리된 항목: {len(done_ids)}건 스킵\n")

    with open(RESULTS_PATH, "a", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=RESULT_HEADERS)
        if not done_ids:
            writer.writeheader()

        for i, row in enumerate(rows, 1):
            row_id = str(row["id"])
            if row_id in done_ids:
                continue

            # testset_200.csv 컬럼 매핑
            en_text    = row.get("원문 (orig_body)", "").strip()
            ko_gt      = row.get("신규 번역 (new_body)", "").strip()
            gt_summary = row.get("신규 3줄 요약 (new_summary)", "").strip()
            url        = row.get("url", "")
            category   = row.get("category", "")

            print(f"[{i}/{len(rows)}] {en_text[:60]}...")

            # ── 1. 번역 + 요약 ──
            try:
                n = estimate_sentences(en_text)
                result = translate_and_summarize(en_text, summary_sentences=n)
                translation    = result.get("translation", "")
                summary_formal = result.get("summary_formal", "")
            except Exception as e:
                print(f"  ⚠ 모델 오류: {e}")
                translation = summary_formal = ""
                n = 0

            # ── 2. BLEU ──
            bleu = calc_bleu_sentence(translation, ko_gt) if translation and ko_gt else 0.0

            # ── 3. COMET ──
            comet_score = 0.0
            if comet_model and translation and ko_gt:
                c = calc_comet([en_text], [translation], [ko_gt], model=comet_model)
                comet_score = c["comet_mean"]

            # ── 4. TPR ──
            tpr_result  = check_term_preservation(translation, source=en_text)
            tpr         = tpr_result["tpr"]
            tpr_missing = "|".join(tpr_result["missing"])

            # ── 5. G-Eval ──
            geval_con = geval_fl = geval_coh = geval_r = geval_avg = geval_weighted = 0.0
            if not skip_geval and summary_formal:
                g = geval_single(en_text, summary_formal, gt_summary=gt_summary)
                geval_con      = g["consistency"]
                geval_fl       = g["fluency"]
                geval_coh      = g["coherence"]
                geval_r        = g["relevance"]
                geval_avg      = g["g_eval_score"]
                geval_weighted = g["g_eval_weighted"]
                time.sleep(0.5)

            writer.writerow({
                "id":                row_id,
                "model_version":     MODEL_VERSION,
                "url":               url,
                "category":          category,
                "en_text":           en_text,
                "ko_gt":             ko_gt,
                "translation":       translation,
                "summary_formal":    summary_formal,
                "bleu":              bleu,
                "comet":             comet_score,
                "tpr":               tpr,
                "tpr_missing":       tpr_missing,
                "geval_consistency": geval_con,
                "geval_fluency":     geval_fl,
                "geval_coherence":   geval_coh,
                "geval_relevance":   geval_r,
                "geval_avg":         geval_avg,
                "geval_weighted":    geval_weighted,
                "n_sentences":       n,
            })
            f.flush()

            print(f"  BLEU={bleu:.1f}  COMET={comet_score:.4f}  TPR={tpr*100:.1f}%  G-Eval={geval_avg:.1f}  G-Eval(W)={geval_weighted:.1f}")

    print(f"\n결과 저장 완료: {RESULTS_PATH}")

    # 최종 집계 출력
    print_summary(RESULTS_PATH)

    # Google Sheets 업로드
    if not skip_sheets:
        print("Google Sheets 업로드 중...")
        upload_to_sheets(RESULTS_PATH)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="파인튜닝 전 베이스라인 평가 (testset_200.csv)")
    parser.add_argument("--limit",       type=int,            default=None, help="평가 건수 제한 (테스트용)")
    parser.add_argument("--skip-geval",  action="store_true",               help="G-Eval 건너뛰기 (비용 절약)")
    parser.add_argument("--skip-comet",  action="store_true",               help="COMET 건너뛰기 (속도 우선)")
    parser.add_argument("--skip-sheets", action="store_true",               help="Google Sheets 업로드 제외")
    args = parser.parse_args()

    run_eval(
        limit=args.limit,
        skip_geval=args.skip_geval,
        skip_comet=args.skip_comet,
        skip_sheets=args.skip_sheets,
    )
