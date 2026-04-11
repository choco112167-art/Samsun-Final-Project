"""
results.csv 인플레이스 업데이트
  - 파싱 실패 건 재처리
  - COMET 점수 미채점 건 채우기 (--fill-comet)
  - G-Eval 점수 미채점 건 채우기 (--fill-geval)

실행:
    python eval/reprocess_failed.py                      # 파싱 실패만
    python eval/reprocess_failed.py --fill-comet         # COMET 채우기
    python eval/reprocess_failed.py --fill-geval         # G-Eval 채우기
    python eval/reprocess_failed.py --fill-comet --fill-geval  # 둘 다
"""
import sys, os, csv, time, argparse
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pipeline.translate_summarize import translate_and_summarize, estimate_sentences
from eval.metrics.bleu_comet import calc_bleu_sentence, load_comet_model, calc_comet
from eval.metrics.term_preservation import check_term_preservation
from eval.metrics.geval import geval_single

TESTSET_PATH = os.path.join(os.path.dirname(__file__), "data", "testset_300.csv")
RESULTS_PATH = os.path.join(os.path.dirname(__file__), "data", "results_300.csv")

RESULT_HEADERS = [
    "id", "url", "category",
    "en_text", "ko_gt",
    "translation", "summary_formal",
    "bleu", "comet", "tpr", "tpr_missing",
    "geval_consistency", "geval_fluency", "geval_coherence", "geval_relevance",
    "g_eval_score", "g_eval_weighted",
    "n_sentences",
]


def save(results: dict):
    sorted_rows = sorted(results.values(), key=lambda r: int(r["id"]))
    with open(RESULTS_PATH, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=RESULT_HEADERS)
        writer.writeheader()
        writer.writerows(sorted_rows)


def main(fill_comet: bool = False, fill_geval: bool = False):
    # 기존 results 로드
    with open(RESULTS_PATH, encoding="utf-8-sig") as f:
        results = {r["id"]: r for r in csv.DictReader(f)}

    # 모든 행에 comet 컬럼 보장 (기존 CSV에 없을 수 있음)
    for r in results.values():
        r.setdefault("comet", "0")

    # ── 1. 파싱 실패 재처리 ──────────────────────────────
    fail_ids = {rid for rid, r in results.items() if "(파싱 실패)" in r.get("summary_formal", "")}
    print(f"파싱 실패 재처리 대상: {len(fail_ids)}건")

    with open(TESTSET_PATH, encoding="utf-8-sig") as f:
        testset = {r["id"]: r for r in csv.DictReader(f)}

    success = 0
    for i, rid in enumerate(sorted(fail_ids, key=lambda x: int(x)), 1):
        if rid not in testset:
            continue
        row = testset[rid]
        en_text = row["en_text"]
        ko_gt   = row["ko_text"]
        print(f"[{i}/{len(fail_ids)}] id={rid} {en_text[:50]}...")

        try:
            n = estimate_sentences(en_text)
            result = translate_and_summarize(en_text, summary_sentences=n)
            translation    = result.get("translation", "")
            summary_formal = result.get("summary_formal", "")
        except Exception as e:
            print(f"  ⚠ 오류: {e}")
            continue

        if "(파싱 실패)" in summary_formal:
            print(f"  ✗ 여전히 실패")
            continue

        bleu = calc_bleu_sentence(translation, ko_gt) if translation else 0.0
        tpr_result  = check_term_preservation(translation)
        old = results[rid]
        results[rid] = {
            "id":                   rid,
            "url":                  old.get("url", row.get("url", "")),
            "category":             old.get("category", row.get("category", "")),
            "en_text":              en_text,
            "ko_gt":                ko_gt,
            "translation":          translation,
            "summary_formal":       summary_formal,
            "bleu":                 bleu,
            "comet":                old.get("comet", "0"),
            "tpr":                  tpr_result["tpr"],
            "tpr_missing":          "|".join(tpr_result["missing"]),
            "geval_consistency":    old.get("geval_consistency", "0"),
            "geval_fluency":        old.get("geval_fluency", "0"),
            "geval_coherence":      old.get("geval_coherence", "0"),
            "geval_avg":            old.get("geval_avg", "0"),
            "n_sentences":          old.get("n_sentences", n),
        }
        success += 1
        print(f"  ✓ BLEU={bleu:.1f}")

    if fail_ids:
        save(results)
        print(f"파싱 실패 재처리 완료: {success}/{len(fail_ids)}건\n")

    # ── 2. COMET 채우기 ──────────────────────────────────
    if fill_comet:
        pending = [
            r for r in results.values()
            if r.get("translation", "").strip()
            and float(r.get("comet", 0) or 0) == 0
        ]
        print(f"COMET 미채점 대상: {len(pending)}건")

        if pending:
            print("COMET 모델 로딩 중...")
            comet_model = load_comet_model()
            print("로드 완료\n")

            for i, row in enumerate(sorted(pending, key=lambda r: int(r["id"])), 1):
                rid = row["id"]
                en_text    = row["en_text"]
                translation = row["translation"]
                ko_gt      = row.get("ko_gt", "")
                print(f"  COMET [{i}/{len(pending)}] id={rid}...")

                c = calc_comet([en_text], [translation], [ko_gt], model=comet_model)
                results[rid]["comet"] = c["comet_mean"]

                if i % 50 == 0:
                    save(results)
                    print(f"  -- 중간 저장 ({i}건) --")

            save(results)
            comet_vals = [float(r["comet"]) for r in results.values() if float(r.get("comet", 0) or 0) > 0]
            print(f"COMET 채점 완료 / 평균: {sum(comet_vals)/len(comet_vals):.4f}\n")

    # ── 3. G-Eval 채우기 ─────────────────────────────────
    if fill_geval:
        # pseudo_gt 로드 (testset_300.csv)
        pseudo_gt_map = {}
        if os.path.exists(TESTSET_PATH):
            with open(TESTSET_PATH, encoding="utf-8-sig") as f:
                for r in csv.DictReader(f):
                    pseudo_gt_map[r["id"]] = r.get("pseudo_gt", "")

        pending = [
            r for r in results.values()
            if r.get("summary_formal", "").strip()
            and "(파싱 실패)" not in r.get("summary_formal", "")
            and float(r.get("g_eval_score", 0) or 0) == 0
        ]
        print(f"G-Eval 미채점 대상: {len(pending)}건")

        for i, row in enumerate(sorted(pending, key=lambda r: int(r["id"])), 1):
            rid = row["id"]
            pseudo_gt = pseudo_gt_map.get(rid, "")
            print(f"  G-Eval [{i}/{len(pending)}] id={rid}...")

            g = geval_single(row["en_text"], row["summary_formal"], gt_summary=pseudo_gt)
            results[rid]["geval_consistency"]  = g["consistency"]
            results[rid]["geval_fluency"]      = g["fluency"]
            results[rid]["geval_coherence"]    = g["coherence"]
            results[rid]["geval_relevance"]    = g["relevance"]
            results[rid]["g_eval_score"]       = g["g_eval_score"]
            results[rid]["g_eval_weighted"]    = g["g_eval_weighted"]
            print(f"    score={g['g_eval_score']} weighted={g['g_eval_weighted']}")

            if i % 10 == 0:
                save(results)
                print(f"  -- 중간 저장 ({i}건) --")

            time.sleep(0.5)

        if pending:
            save(results)
            vals = [float(r["g_eval_score"]) for r in results.values() if float(r.get("g_eval_score", 0) or 0) > 0]
            wvals = [float(r["g_eval_weighted"]) for r in results.values() if float(r.get("g_eval_weighted", 0) or 0) > 0]
            print(f"G-Eval 채점 완료 / 단순평균: {sum(vals)/len(vals):.2f} / 가중평균: {sum(wvals)/len(wvals):.2f}\n")

    print(f"결과 저장: {RESULTS_PATH}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--fill-comet", action="store_true", help="COMET 미채점 행 채우기")
    parser.add_argument("--fill-geval", action="store_true", help="G-Eval 미채점 행 채우기")
    args = parser.parse_args()
    main(fill_comet=args.fill_comet, fill_geval=args.fill_geval)
