"""
Gemma 모델 비교 평가
testset_200.csv → Gemma (Ollama) 추론 → BLEU/COMET/TPR + G-Eval → results_200_gemma4.csv

실행:
    python eval/run_eval_gemma4.py                           # 기본 (gemma3:4b)
    python eval/run_eval_gemma4.py --model gemma3:4b         # 모델 명시
    python eval/run_eval_gemma4.py --limit 10                # 빠른 테스트
    python eval/run_eval_gemma4.py --skip-geval              # G-Eval 제외
    python eval/run_eval_gemma4.py --skip-comet              # COMET 제외
    python eval/run_eval_gemma4.py --skip-sheets             # Sheets 업로드 제외

사전 준비:
    ollama pull gemma3:4b          # 또는 원하는 gemma 모델명
"""

import sys
import os
import csv
import re
import json
import argparse
import time

import ollama

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from eval.metrics.bleu_comet import calc_bleu_sentence, load_comet_model, calc_comet
from eval.metrics.term_preservation import check_term_preservation
from eval.metrics.geval import geval_single
from pipeline.utils import extract_json as _extract_json

TESTSET_PATH   = os.path.join(os.path.dirname(__file__), "data", "testset_200.csv")
CREDENTIALS    = os.path.join(os.path.dirname(__file__), "..",
                              "client_secret_43865832816-letrps5uc0nohpmaug4b5bo6lf2sf92j.apps.googleusercontent.com.json")
SPREADSHEET_ID = "1KV7gEN-lgxREAWenE4lKyFWi3rfwGpHtYIwHdQtp6Po"

RESULT_HEADERS = [
    "id", "model_version", "url", "category",
    "en_text", "ko_gt",
    "translation", "summary_formal",
    "bleu", "comet", "tpr", "tpr_missing",
    "geval_consistency", "geval_fluency", "geval_coherence", "geval_relevance",
    "geval_avg", "geval_weighted",
    "n_sentences",
]

SYSTEM_PROMPT = """You are a professional Korean translator and summarizer.

━━━ RULE 0: OUTPUT LANGUAGE (ABSOLUTE PRIORITY) ━━━
Output MUST contain ONLY Korean (한글) + Latin (A-Z/a-z) + digits + punctuation.
ZERO TOLERANCE — even one character from the following scripts causes failure:
  • Chinese/Hanzi (漢字): including 去, 年, 的, 在 etc.
  • Cyrillic/Russian: А, Б, В … я etc.
  • Thai, Arabic, Hebrew, Japanese kana
If the source contains these scripts, translate or romanize them into Korean. NEVER copy them.

━━━ OUTPUT FORMAT ━━━
Return ONLY valid JSON. No markdown fences, no explanation outside JSON.
{{
  "title_ko": "<한국어 제목>",
  "translation": "<전체 한국어 번역>",
  "summary_formal": "<격식체 요약>",
  "summary_casual": "<일상체 요약>"
}}
All four fields are REQUIRED. Never leave any field empty.
If no title is provided, set "title_ko" to "".

━━━ TRANSLATION RULES ━━━
1. Translate the ENTIRE article into Korean.
   Use journalistic body style (~했다 / ~밝혔다 / ~에 따르면). Prefer active voice: '발표했다' over '발표됐다'.
2. Keep these abbreviations in English exactly as-is: RAG, LLM, GPU, NPU, API, RLHF, SFT, LoRA, QLoRA, P2P, B2B, SNS.
3. AI/tech terms must stay in English — do NOT transliterate:
   Fine-tuning, Embedding, Prompt, Transformer, Benchmark, Inference, Token, Dataset, Checkpoint
   General loanwords already standard in Korean are fine: Startup→스타트업, Platform→플랫폼, Algorithm→알고리즘

4. PROPER NOUNS — company names, product names, brand names must stay in English. No Korean transliteration.
   • Rule: English name ONLY — do NOT add Korean phonetic transcription in parentheses.
   • e.g., Anthropic (NOT 앤트로픽), OpenAI (NOT 오픈에이아이), Nvidia (NOT 엔비디아),
     Google (NOT 구글), Meta (NOT 메타), Microsoft (NOT 마이크로소프트),
     Gemini (NOT 제미나이), Llama (NOT 라마), Claude (NOT 클로드), ChatGPT (NOT 챗GPT)
   • Model version numbers always stay in English: e.g., GPT-4o, Claude 3.5 Sonnet, Llama 3.1 70B

5. PERSON NAMES — use English name only. Do NOT add Korean transliteration.
   • e.g., Sam Altman (NOT 샘 올트먼), Jensen Huang (NOT 젠슨 황), Elon Musk (NOT 일론 머스크)
   • Job titles are translated into Korean: professor→교수, researcher→연구원, founder→창업자

6. NUMBERS AND UNITS
   • Currency symbols: $ → 달러 / € → 유로 / £ → 파운드 / ¥ → 엔 (중국 화폐는 위안)
   • T / trillion → 조: $1T → 1조 달러
   • B / billion  → 억: $2.5B → 25억 달러
   • M / million  → 만: $500M → 5억 달러
   • K / thousand → 천: 5K → 5천
   • Unit context — always specify the unit: parameters→개, people→명, tokens→개
   • Multipliers: 2x → 2배 / 3x → 3배
   • Technical units (GB, TB, ms, TFLOPS, %) — keep as-is

7. Korean-origin names: write in Korean only, no parenthetical annotation.

8. Brand-new English coinages with no established Korean equivalent: EnglishTerm(한 줄 설명) on first mention.

━━━ SUMMARY RULES ━━━
- summary_formal: exactly {n} Korean sentence(s), 격식체 (~습니다/~됩니다). Must be complete.
- summary_casual: exactly {n} Korean sentence(s), 일상체 (~해요/~예요/~거예요). Must be complete.
- Summaries must NOT copy translation sentences verbatim — paraphrase with different expressions.
- Apply all language, proper noun, and number rules above."""

SUMMARY_ONLY_PROMPT = (
    "Korean summarizer. Return ONLY valid JSON, no markdown:\n"
    '{{"summary_formal":"<{n} sentence(s), ~습니다/됩니다 style>","summary_casual":"<{n} sentence(s), ~해요/거예요 style>"}}\n'
    "Rules: Korean only. Both fields required. No empty values."
)

_SUMMARY_INPUT_MAX = 2500


def estimate_sentences(text: str, max_sentences: int = 3) -> int:
    parts = re.split(r'(?<=[a-zA-Z]{2})[.!?]\s+', text.strip())
    return min(max(1, len(parts)), max_sentences)


def _extract_summary_from_raw(text: str) -> str:
    """summary_formal 전용 추출 — translation 없는/잘린 JSON 응답 처리."""
    from pipeline.utils import preprocess_text
    text = preprocess_text(text)

    # 1. 정상 JSON 파싱
    start = text.find("{")
    if start != -1:
        try:
            obj, _ = json.JSONDecoder().raw_decode(text, start)
            sf = obj.get("summary_formal", "")
            if sf and len(sf) > 10:
                return sf
        except Exception:
            pass

    # 2. 잘린 JSON — 닫는 따옴표 없어도 값 추출
    m = re.search(r'"summary_formal"\s*:\s*"((?:[^"\\]|\\.)*)', text, re.DOTALL)
    if m:
        val = m.group(1).rstrip("\\").replace('\\"', '"').replace('\\n', '\n')
        if len(val) > 10:
            return val.strip()

    # 3. 한국어 문장 블록 직접 추출
    sentences = re.findall(r'[가-힣][^。.!?\n]{15,}[습니다|됩니다|했습니다|입니다]', text)
    if sentences:
        return " ".join(sentences[:3])

    return ""


def _call_ollama(model: str, messages: list, options: dict) -> str:
    """think 파라미터 없이 Ollama 호출 (Gemma 호환)."""
    response = ollama.chat(model=model, messages=messages, options=options)
    return response.message.content


def _strip_markdown(text: str) -> str:
    """마크다운 서식 제거 — Gemma가 비정형 입력에서 JSON을 깨뜨리는 방지."""
    text = re.sub(r'\*{1,3}(.+?)\*{1,3}', r'\1', text)          # bold/italic
    text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)        # [text](url)
    text = re.sub(r'!\[([^\]]*)\]\([^\)]+\)', r'\1', text)       # ![alt](url)
    text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)   # 헤딩
    text = re.sub(r'`{1,3}[^`]*`{1,3}', '', text)               # 인라인 코드
    text = re.sub(r'^\s*[-*+]\s+', '', text, flags=re.MULTILINE) # 목록 기호
    text = re.sub(r'^\s*\d+\.\s+', '', text, flags=re.MULTILINE) # 순서 목록
    text = re.sub(r'\\([^\s])', r'\1', text)                     # 이스케이프 제거
    return text.strip()


def _is_valid_result(result: dict) -> bool:
    """번역·요약 모두 실질 내용이 있는지 확인."""
    t = result.get("translation", "")
    s = result.get("summary_formal", "")
    return (bool(t) and bool(s)
            and "(파싱 실패)" not in t
            and "(파싱 실패)" not in s)


def translate_and_summarize_gemma(text: str, model: str, summary_sentences: int = 3) -> dict:
    clean_text = _strip_markdown(text)
    system = SYSTEM_PROMPT.format(n=summary_sentences)
    options = {
        "temperature":    0.1,
        "num_predict":    -1,
        "num_ctx":        12288,
        "num_gpu":        99,
        "repeat_penalty": 1.15,
    }

    result = {}
    for _ in range(3):
        raw = _call_ollama(model, [
            {"role": "system", "content": system},
            {"role": "user",   "content": clean_text},
        ], options)
        result = _extract_json(raw)
        if _is_valid_result(result):
            return result

    # 번역은 됐는데 summary만 없는 경우 → summary-only 재호출 (JSON)
    trans = result.get("translation", "")
    if trans and "(파싱 실패)" not in trans:
        prompt = SUMMARY_ONLY_PROMPT.format(n=summary_sentences)
        ko_input = trans[:_SUMMARY_INPUT_MAX]
        for _ in range(2):
            try:
                raw = _call_ollama(model, [
                    {"role": "system", "content": prompt},
                    {"role": "user",   "content": ko_input},
                ], {**options, "num_predict": 800, "num_ctx": 4096})
                sf = _extract_summary_from_raw(raw)
                if sf:
                    result["summary_formal"] = sf
                    result["summary_casual"] = sf
                    return result
            except Exception:
                pass

        # 최후 폴백: JSON 없이 평문 요약 요청
        plain_prompt = (
            f"다음 한국어 기사를 격식체(~습니다)로 {summary_sentences}문장으로만 요약하세요. "
            "요약 문장 외에 다른 말은 절대 하지 마세요."
        )
        try:
            raw = _call_ollama(model, [
                {"role": "user", "content": f"{plain_prompt}\n\n{ko_input}"},
            ], {**options, "num_predict": 400, "num_ctx": 4096})
            sf = raw.strip()
            if sf and len(sf) > 10:
                result["summary_formal"] = sf
                result["summary_casual"] = sf
                return result
        except Exception:
            pass

    return result


def load_testset(path: str) -> list[dict]:
    with open(path, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def upload_to_sheets(results_path: str, sheet_name: str):
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
            ws = sh.worksheet(sheet_name)
            ws.clear()
        except gspread.WorksheetNotFound:
            ws = sh.add_worksheet(title=sheet_name, rows=210, cols=22)

        with open(results_path, encoding="utf-8-sig") as f:
            rows = list(csv.reader(f))

        ws.update(rows, value_input_option="RAW")
        print(f"Google Sheets 업로드 완료: {len(rows)-1}건 → '{sheet_name}' 시트")

    except Exception as e:
        print(f"⚠ Google Sheets 업로드 실패: {e}")


def print_summary(results_path: str, model_version: str):
    if not os.path.exists(results_path):
        return

    with open(results_path, encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))

    if not rows:
        return

    def mean(key):
        if key == "tpr":
            vals = [float(r[key]) for r in rows if r.get(key) not in ("", None)]
        else:
            vals = [float(r[key]) for r in rows if r.get(key) not in ("", "0", "0.0", None)]
        return round(sum(vals) / len(vals), 4) if vals else 0.0

    n          = len(rows)
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
    print(f"[Gemma 평가 결과] {model_version}  (n={n})")
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


def run_eval(model: str, limit: int = None, skip_geval: bool = False,
             skip_comet: bool = False, skip_sheets: bool = False):

    model_slug    = model.replace(":", "_").replace("/", "_")
    model_version = model
    results_path  = os.path.join(os.path.dirname(__file__), "data", f"results_200_{model_slug}.csv")
    sheet_name    = f"gemma_{model_slug}"[:100]

    print("=" * 60)
    print(f"삼선뉴스 Gemma 비교 평가 ({model_version})")
    print("=" * 60)

    rows = load_testset(TESTSET_PATH)
    if limit:
        rows = rows[:limit]
    print(f"평가 대상: {len(rows)}건\n")

    comet_model = None
    if not skip_comet:
        print("COMET 모델 로딩 중...")
        comet_model = load_comet_model()
        print("COMET 모델 로드 완료\n")

    done_ids = set()
    if os.path.exists(results_path):
        with open(results_path, encoding="utf-8-sig") as f:
            for r in csv.DictReader(f):
                done_ids.add(r["id"])
        print(f"이미 처리된 항목: {len(done_ids)}건 스킵\n")

    with open(results_path, "a", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=RESULT_HEADERS)
        if not done_ids:
            writer.writeheader()

        for i, row in enumerate(rows, 1):
            row_id = str(row["id"])
            if row_id in done_ids:
                continue

            en_text    = row.get("원문 (orig_body)", "").strip()
            ko_gt      = row.get("신규 번역 (new_body)", "").strip()
            gt_summary = row.get("신규 3줄 요약 (new_summary)", "").strip()
            url        = row.get("url", "")
            category   = row.get("category", "")

            print(f"[{i}/{len(rows)}] {en_text[:60]}...")

            # 1. 번역 + 요약
            try:
                n = estimate_sentences(en_text)
                result = translate_and_summarize_gemma(en_text, model=model, summary_sentences=n)
                translation    = result.get("translation", "")
                summary_formal = result.get("summary_formal", "")
            except Exception as e:
                print(f"  ⚠ 모델 오류: {e}")
                translation = summary_formal = ""
                n = 0

            # 2. BLEU
            bleu = calc_bleu_sentence(translation, ko_gt) if translation and ko_gt else 0.0

            # 3. COMET
            comet_score = 0.0
            if comet_model and translation and ko_gt:
                c = calc_comet([en_text], [translation], [ko_gt], model=comet_model)
                comet_score = c["comet_mean"]

            # 4. TPR
            tpr_result  = check_term_preservation(translation, source=en_text)
            tpr         = tpr_result["tpr"]
            tpr_missing = "|".join(tpr_result["missing"])

            # 5. G-Eval
            geval_con = geval_fl = geval_coh = geval_r = geval_avg = geval_weighted = 0.0
            if not skip_geval and summary_formal:
                try:
                    g = geval_single(en_text, summary_formal, gt_summary=gt_summary)
                    geval_con      = g["consistency"]
                    geval_fl       = g["fluency"]
                    geval_coh      = g["coherence"]
                    geval_r        = g["relevance"]
                    geval_avg      = g["g_eval_score"]
                    geval_weighted = g["g_eval_weighted"]
                except Exception as e:
                    print(f"  ⚠ G-Eval 실패 (geval_avg=0 저장): {e}")
                time.sleep(0.5)

            writer.writerow({
                "id":                row_id,
                "model_version":     model_version,
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

            print(f"  BLEU={bleu:.1f}  COMET={comet_score:.4f}  TPR={tpr*100:.1f}%  G-Eval={geval_avg:.1f}")

    print(f"\n결과 저장 완료: {results_path}")
    print_summary(results_path, model_version)

    if not skip_sheets:
        print("Google Sheets 업로드 중...")
        upload_to_sheets(results_path, sheet_name)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Gemma 모델 비교 평가 (testset_200.csv)")
    parser.add_argument("--model",        type=str,            default="gemma3:4b",  help="Ollama 모델명 (예: gemma3:4b, gemma4:2b)")
    parser.add_argument("--limit",        type=int,            default=None,         help="평가 건수 제한 (테스트용)")
    parser.add_argument("--skip-geval",   action="store_true",                       help="G-Eval 건너뛰기 (비용 절약)")
    parser.add_argument("--skip-comet",   action="store_true",                       help="COMET 건너뛰기 (속도 우선)")
    parser.add_argument("--skip-sheets",  action="store_true",                       help="Google Sheets 업로드 제외")
    args = parser.parse_args()

    run_eval(
        model=args.model,
        limit=args.limit,
        skip_geval=args.skip_geval,
        skip_comet=args.skip_comet,
        skip_sheets=args.skip_sheets,
    )
