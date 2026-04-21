"""
평가 실행기
testset_1000.csv → Qwen3 추론 → BLEU/COMET/TPR + G-Eval → results.csv → Google Sheets

실행:
    python eval/run_eval.py                    # 전체 1000건
    python eval/run_eval.py --limit 10         # 빠른 테스트 (10건)
    python eval/run_eval.py --skip-geval       # G-Eval 제외 (비용 절약)
    python eval/run_eval.py --skip-sheets      # Google Sheets 업로드 제외

결과:
    eval/data/results.csv          (상세 결과 로컬 저장)
    Google Sheets → 평가결과 시트  (자동 업로드)
"""

import sys
import os
import csv
import argparse
import time

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "RSS"))

from pipeline.translate_summarize import translate_and_summarize, estimate_sentences
from eval.metrics.bleu_comet import calc_bleu_sentence, load_comet_model, calc_comet
from eval.metrics.term_preservation import check_term_preservation
from eval.metrics.geval import geval_single

TESTSET_PATH   = os.path.join(os.path.dirname(__file__), "data", "testset_300.csv")
RESULTS_PATH   = os.path.join(os.path.dirname(__file__), "data", "results_300.csv")
CREDENTIALS    = os.path.join(os.path.dirname(__file__), "..", "client_secret_43865832816-letrps5uc0nohpmaug4b5bo6lf2sf92j.apps.googleusercontent.com.json")
SPREADSHEET_ID = "1KV7gEN-lgxREAWenE4lKyFWi3rfwGpHtYIwHdQtp6Po"
SHEET_NAME     = "평가결과"   # 시트 탭 이름 (없으면 자동 생성)

RESULT_HEADERS = [
    "id", "url", "category",
    "en_text", "ko_gt",
    "translation", "summary_formal",
    "bleu", "comet", "tpr", "tpr_missing",
    "geval_consistency", "geval_fluency", "geval_coherence", "geval_relevance", "geval_avg", "geval_weighted",
    "n_sentences",
]


def load_testset(path: str) -> list[dict]:
    with open(path, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def upload_to_sheets(results_path: str):
    """results.csv 전체를 Google Sheets에 업로드"""
    try:
        import gspread
        from google_auth_oauthlib.flow import InstalledAppFlow

        SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

        # OAuth 인증 (첫 실행 시 브라우저 열림, 이후 token.json 재사용)
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

        # 시트 없으면 생성
        try:
            ws = sh.worksheet(SHEET_NAME)
            ws.clear()
        except gspread.WorksheetNotFound:
            ws = sh.add_worksheet(title=SHEET_NAME, rows=1100, cols=20)

        # 데이터 로드
        with open(results_path, encoding="utf-8-sig") as f:
            rows = list(csv.reader(f))

        ws.update(rows, value_input_option="RAW")
        print(f"Google Sheets 업로드 완료: {len(rows)-1}건 → '{SHEET_NAME}' 시트")

    except Exception as e:
        print(f"⚠ Google Sheets 업로드 실패: {e}")


def run_eval(limit: int = None, skip_geval: bool = False, skip_comet: bool = False, skip_sheets: bool = False):
    print("=" * 60)
    print("삼선뉴스 번역·요약 평가 시작")
    print("=" * 60)

    rows = load_testset(TESTSET_PATH)
    if limit:
        rows = rows[:limit]
    print(f"평가 대상: {len(rows)}건\n")

    # COMET 모델 사전 로드 (행마다 로드하면 느림)
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

        for row in rows:
            if row["id"] in done_ids:
                continue

            en_text = row["en_text"]
            ko_gt   = row["ko_text"]
            print(f"[{row['id']}/{len(rows)}] {en_text[:60]}...")

            # ── 1. 번역 + 요약 ──
            try:
                n = estimate_sentences(en_text)
                result = translate_and_summarize(en_text, summary_sentences=n)
                translation    = result.get("translation", "")
                summary_formal = result.get("summary_formal", "")
            except Exception as e:
                print(f"  ⚠ 모델 오류: {e}")
                translation = summary_formal = ""

            # ── 2. BLEU ──
            bleu = calc_bleu_sentence(translation, ko_gt) if translation else 0.0

            # ── 3. COMET ──
            comet_score = 0.0
            if comet_model and translation:
                c = calc_comet([en_text], [translation], [ko_gt], model=comet_model)
                comet_score = c["comet_mean"]

            # ── 4. TPR ──
            tpr_result  = check_term_preservation(translation, source=en_text)
            tpr         = tpr_result["tpr"]
            tpr_missing = "|".join(tpr_result["missing"])

            # ── 5. G-Eval (옵션) ──
            geval_con = geval_fl = geval_coh = geval_r = geval_avg = geval_weighted = 0.0
            if not skip_geval and summary_formal:
                g = geval_single(en_text, summary_formal, gt_summary=row.get("pseudo_gt", ""))
                geval_con      = g["consistency"]
                geval_fl       = g["fluency"]
                geval_coh      = g["coherence"]
                geval_r        = g["relevance"]
                geval_avg      = g["g_eval_score"]
                geval_weighted = g["g_eval_weighted"]
                time.sleep(0.5)

            writer.writerow({
                "id":                   row["id"],
                "url":                  row["url"],
                "category":             row["category"],
                "en_text":              en_text,
                "ko_gt":                ko_gt,
                "translation":          translation,
                "summary_formal":       summary_formal,
                "bleu":                 bleu,
                "comet":                comet_score,
                "tpr":                  tpr,
                "tpr_missing":          tpr_missing,
                "geval_consistency":    geval_con,
                "geval_fluency":        geval_fl,
                "geval_coherence":      geval_coh,
                "geval_relevance":      geval_r,
                "geval_avg":            geval_avg,
                "geval_weighted":       geval_weighted,
                "n_sentences":          row["n_sentences"],
            })
            f.flush()

            print(f"  BLEU={bleu:.1f}  COMET={comet_score:.4f}  TPR={tpr:.2f}  G-Eval={geval_avg:.1f}  G-Eval(W)={geval_weighted:.1f}")

    print(f"\n결과 저장 완료: {RESULTS_PATH}")

    # ── 5. Google Sheets 업로드 ──
    if not skip_sheets:
        print("\nGoogle Sheets 업로드 중...")
        upload_to_sheets(RESULTS_PATH)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit",        type=int,            default=None,  help="평가 건수 제한 (테스트용)")
    parser.add_argument("--skip-geval",   action="store_true",               help="G-Eval 건너뛰기")
    parser.add_argument("--skip-comet",   action="store_true",               help="COMET 건너뛰기")
    parser.add_argument("--skip-sheets",  action="store_true",               help="Google Sheets 업로드 건너뛰기")
    args = parser.parse_args()

    run_eval(limit=args.limit, skip_geval=args.skip_geval, skip_comet=args.skip_comet, skip_sheets=args.skip_sheets)
