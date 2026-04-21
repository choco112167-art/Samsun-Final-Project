"""
eval/select_testset.py — testset 추출대기에서 45건 선별

흐름:
  1. testset 추출 원본 (비고='테스트' 320건) 로드
  2. 기존 testset_200.csv URL 기준 제외 (~155건)
  3. content 길이 내림차순 정렬
  4. 1건씩:
     a. 번역 채점 (Claude Haiku) — 평균 < 4.0 이면 G-Eval 스킵
     b. G-Eval 채점 (Claude Haiku) — 평균 < 4.0 이면 스킵
     c. 둘 다 ≥ 4.0 → selected_45.csv 누적 저장
  5. 목표 건수(기본 45) 달성 시 종료

실행:
  cd samseon
  python eval/select_testset.py              # 기본 실행
  python eval/select_testset.py --target 45  # 목표 건수 지정
  python eval/select_testset.py --dry-run    # 후보 목록만 출력 (API 호출 없음)

출력:
  eval/data/selected_45.csv    — 합격 기사 (testset_200.csv 와 동일 포맷)
  eval/data/select_progress.csv — 처리 이력 (재실행 시 이어서 진행)
"""

import os
import sys
import csv
import json
import time
import argparse
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import anthropic
import pandas as pd
from dotenv import load_dotenv

# Windows 터미널 UTF-8 출력
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

load_dotenv()

# ── 경로 설정 ──────────────────────────────────────────────────────────────────
BASE_DIR     = Path(__file__).resolve().parent.parent
CELL_FILE    = Path("C:/Users/이동우/Desktop/testset 추출대기.cell")
EXISTING_CSV = Path("C:/Users/이동우/Desktop/testset_200.csv")
PROGRESS_CSV = BASE_DIR / "eval" / "data" / "select_progress.csv"
OUTPUT_CSV   = BASE_DIR / "eval" / "data" / "selected_45.csv"

SHEET_NAME = "testset 추출 원본"
TARGET     = 45

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
EVAL_MODEL        = "claude-haiku-4-5-20251001"

# ── 컬럼 이름 상수 ─────────────────────────────────────────────────────────────
COL_CONTENT  = "원문 본문\n(content 전체)"
COL_TRANS    = "✏️수정\n본문번역"
COL_SUMMARY  = "✏️수정\n3줄요약"
COL_TITLE    = "원문 제목\n(title)"
COL_TITLE_KO = "✏️수정\n제목번역"


# ── 번역 채점 프롬프트 ─────────────────────────────────────────────────────────
TRANS_SYSTEM = "You are a strict evaluator of Korean translations of English AI/tech news articles."

TRANS_TEMPLATE = """Score the Korean translation of this English AI/tech news article on 4 axes (integer 1–5 each).

[ENGLISH ORIGINAL]
{source}

[KOREAN TRANSLATION]
{translation}

---
SCORING AXES:

1. 정확도 (Accuracy) — Compare [KOREAN TRANSLATION] vs [ENGLISH ORIGINAL]
   5: All facts and meaning accurately conveyed; nothing added or distorted
   4: Accurate overall; at most one minor omission or slight rephrasing
   3: One fact distorted or one important point missing
   2: Two or more inaccuracies or significant meaning loss
   1: Major factual errors or contradicts the source

2. 유창성 (Fluency) — Evaluate [KOREAN TRANSLATION] alone
   5: Reads like native Korean tech journalism; natural and smooth
   4: Mostly natural; at most 1 awkward phrase
   3: Readable but noticeably unnatural in places
   2: Difficult to read; clunky Korean throughout
   1: Unreadable; raw machine-translation feel

3. 용어 (Terminology) — Check compliance with these rules:
   - Keep in English: RAG, LLM, GPU, NPU, API, RLHF, SFT, LoRA, QLoRA, P2P, B2B, SNS
   - Standard transliterations: Fine-tuning→파인튜닝, Embedding→임베딩, Prompt→프롬프트,
     Transformer→트랜스포머, Startup→스타트업, Platform→플랫폼, Algorithm→알고리즘
   - Proper noun on FIRST mention: EnglishName(한국어 음차); English only after that
     IT 기업: Anthropic(앤트로픽) / OpenAI(오픈에이아이) / Google(구글) / Meta(메타) /
     Microsoft(마이크로소프트) / Nvidia(엔비디아) / Apple(애플) / Amazon(아마존) /
     Intel(인텔) / Tesla(테슬라) / SpaceX(스페이스X) / DeepMind(딥마인드) / xAI(xAI) /
     Huawei(화웨이) / ByteDance(바이트댄스) / Xiaomi(샤오미) / Tencent(텐센트) / Alibaba(알리바바)
     AI 스타트업: Cohere(코히어) / Perplexity AI(퍼플렉시티 AI) / Runway(런웨이) /
     Stability AI(스태빌리티 AI) / Midjourney(미드저니) / Mistral AI(미스트랄 AI) /
     Scale AI(스케일 AI) / Hugging Face(허깅 페이스) / Inflection AI(인플렉션 AI) / Together AI(투게더 AI)
     AI 모델: ChatGPT(챗GPT) / Gemini(제미나이) / Llama(라마) / Grok(그록) /
     Copilot(코파일럿) / Claude(클로드) / Sora(소라) / DALL-E(달리) / Gemma(젬마) / Phi(파이)
   - Model version numbers stay in English: e.g., GPT-4o, Claude 3.5 Sonnet, Llama 3.1 70B
   - Person names (first mention): FullName(한국어 음차) e.g., Sam Altman(샘 올트먼), Jensen Huang(젠슨 황)
   - Currency: $ → 달러, € → 유로, £ → 파운드, ¥ → 엔 (중국 화폐는 위안)
   - Numbers: T/trillion→조, B/billion→억, M/million→만, K/thousand→천
     (e.g., $2.5B→25억 달러, 70B params→700억 개 파라미터, 5K→5천)
   - No Chinese characters allowed in output
   5: All rules followed correctly
   4: At most 1 minor error
   3: 2–3 errors
   2: Systematic errors
   1: Rules largely ignored

4. 스타일 (Style) — Evaluate [KOREAN TRANSLATION] alone
   5: Appropriate formal journalistic Korean; consistent register
   4: Mostly appropriate; minor style inconsistency
   3: Noticeable style issues but acceptable
   2: Inappropriate register or inconsistent style throughout
   1: Completely wrong style

---
OUTPUT: valid JSON only, no explanation outside.
Compute avg as arithmetic mean of the four scores (round to 2 decimal places).
{{"accuracy": X, "fluency": X, "terminology": X, "style": X, "avg": X.X}}"""


def score_translation(source: str, translation: str, retries: int = 3) -> dict:
    """번역 품질 채점. 실패 시 avg=0.0 반환."""
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    user_msg = TRANS_TEMPLATE.format(
        source=source[:3000],
        translation=translation[:2000],
    )
    for attempt in range(retries):
        try:
            resp = client.messages.create(
                model=EVAL_MODEL,
                max_tokens=256,
                system=TRANS_SYSTEM,
                messages=[{"role": "user", "content": user_msg}],
            )
            raw   = resp.content[0].text.strip()
            clean = raw.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
            s = json.loads(clean)
            return {
                "accuracy":    int(s["accuracy"]),
                "fluency":     int(s["fluency"]),
                "terminology": int(s["terminology"]),
                "style":       int(s["style"]),
                "avg":         round(float(s["avg"]), 2),
            }
        except (json.JSONDecodeError, KeyError):
            return {"accuracy": 0, "fluency": 0, "terminology": 0, "style": 0, "avg": 0.0}
        except Exception as e:
            if hasattr(e, "status_code") and getattr(e, "status_code", 500) < 500:
                return {"accuracy": 0, "fluency": 0, "terminology": 0, "style": 0, "avg": 0.0}
            if attempt < retries - 1:
                time.sleep(3)
            else:
                return {"accuracy": 0, "fluency": 0, "terminology": 0, "style": 0, "avg": 0.0}


# ── 진행 이력 ──────────────────────────────────────────────────────────────────
PROGRESS_FIELDS = [
    "url", "status",
    "accuracy", "fluency_t", "terminology", "style", "trans_avg",
    "consistency", "fluency_g", "coherence", "relevance", "geval_avg", "geval_weighted",
]


def load_progress() -> dict:
    if not PROGRESS_CSV.exists():
        return {}
    with open(PROGRESS_CSV, encoding="utf-8-sig") as f:
        return {r["url"]: r for r in csv.DictReader(f)}


def save_progress(processed: dict):
    with open(PROGRESS_CSV, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=PROGRESS_FIELDS)
        w.writeheader()
        w.writerows(processed.values())


# ── 출력 CSV (testset_200.csv 와 동일 포맷) ────────────────────────────────────
OUTPUT_FIELDS = [
    "id", "source", "source_type", "category", "country", "url",
    "credibility_score", "published_at", "created_at",
    "원문 제목", "번역 제목", "원문 (orig_body)", "신규 번역 (new_body)",
    "정확도", "유창성", "용어", "스타일", "평균", "등급",
    "신규 3줄 요약 (new_summary)",
    "일관성\n(Coherence)", "일치성\n(Consistency)", "유창성\n(Fluency)", "관련성\n(Relevance)",
    "G-Eval\n평균", "등급.1", "비고",
]


def grade(avg: float) -> str:
    if avg >= 4.5: return "A"
    if avg >= 4.0: return "B"
    if avg >= 3.0: return "C"
    return "D"


# ── 메인 ───────────────────────────────────────────────────────────────────────
def main(target: int = TARGET, dry_run: bool = False):
    if not dry_run and not ANTHROPIC_API_KEY:
        print("ERROR: ANTHROPIC_API_KEY 환경변수를 설정하세요.")
        sys.exit(1)

    # 1. 데이터 로드 ─────────────────────────────────────────────────────────
    print("=" * 60)
    print("데이터 로드 중...")
    df_pool     = pd.read_excel(CELL_FILE, sheet_name=SHEET_NAME)
    df_existing = pd.read_csv(EXISTING_CSV, encoding="cp949")

    existing_urls = set(df_existing["url"].dropna().astype(str).str.strip())
    print(f"  추출 원본 전체: {len(df_pool)}건")
    print(f"  기존 선별 (제외): {len(existing_urls)}건")

    # 2. 필터 + 정렬 ─────────────────────────────────────────────────────────
    df_pool["_url"] = df_pool["url"].astype(str).str.strip()

    df_cand = df_pool[
        (df_pool["비고"] == "테스트") &          # testset 후보 풀만
        (~df_pool["_url"].isin(existing_urls)) &  # 기존 선별 제외
        df_pool[COL_TRANS].notna() &              # 번역 있는 것만
        df_pool[COL_SUMMARY].notna() &            # 요약 있는 것만
        df_pool[COL_CONTENT].notna()              # 원문 있는 것만
    ].copy()

    df_cand["_len"] = df_cand[COL_CONTENT].astype(str).str.len()
    df_cand = df_cand.sort_values("_len", ascending=False).reset_index(drop=True)

    print(f"  후보: {len(df_cand)}건 (필터 후, content 길이 내림차순)")

    if dry_run:
        print("\n[DRY RUN] 상위 30건 후보:")
        for i, row in df_cand.head(30).iterrows():
            print(f"  {i+1:3d}. [{row['출처']:25s}] {str(row[COL_TITLE])[:55]:<55s} ({row['_len']:,}자)")
        return

    # 3. 진행 이력 로드 ──────────────────────────────────────────────────────
    processed = load_progress()
    passed_urls = [u for u, r in processed.items() if r["status"] == "pass"]
    selected_count = len(passed_urls)
    print(f"  이미 처리: {len(processed)}건 / 이미 합격: {selected_count}건")
    print("=" * 60)

    if selected_count >= target:
        print(f"이미 {selected_count}/{target}건 달성됨.")
        return

    # 4. 출력 CSV 초기화 (이어쓰기) ─────────────────────────────────────────
    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    out_exists = OUTPUT_CSV.exists()
    out_f   = open(OUTPUT_CSV, "a", encoding="utf-8-sig", newline="")
    writer  = csv.DictWriter(out_f, fieldnames=OUTPUT_FIELDS)
    if not out_exists:
        writer.writeheader()

    from eval.metrics.geval import geval_single

    # 5. 1건씩 처리 ──────────────────────────────────────────────────────────
    for _, row in df_cand.iterrows():
        if selected_count >= target:
            break

        url = str(row["_url"])
        if url in processed:
            continue

        source      = str(row[COL_CONTENT]).strip()
        translation = str(row[COL_TRANS]).strip()
        summary     = str(row[COL_SUMMARY]).strip()

        print(f"\n[{selected_count}/{target}] #{row['No']} | {str(row[COL_TITLE])[:55]}")
        print(f"  출처: {row['출처']} | {row['_len']:,}자")

        # a. 번역 채점 ───────────────────────────────────────────────────────
        ts = score_translation(source, translation)
        print(f"  번역: 정확도={ts['accuracy']} 유창성={ts['fluency']} "
              f"용어={ts['terminology']} 스타일={ts['style']} → 평균={ts['avg']}")
        time.sleep(0.5)

        if ts["avg"] < 4.0:
            print(f"  ✗ 번역 불합격 ({ts['avg']} < 4.0) — G-Eval 스킵")
            processed[url] = {
                "url": url, "status": "fail_trans",
                "accuracy": ts["accuracy"], "fluency_t": ts["fluency"],
                "terminology": ts["terminology"], "style": ts["style"],
                "trans_avg": ts["avg"],
                "consistency": 0, "fluency_g": 0, "coherence": 0,
                "relevance": 0, "geval_avg": 0.0, "geval_weighted": 0.0,
            }
            save_progress(processed)
            continue

        # b. G-Eval 채점 ─────────────────────────────────────────────────────
        g = geval_single(source, summary, gt_summary="")
        print(f"  G-Eval: 일치성={g['consistency']} 유창성={g['fluency']} "
              f"일관성={g['coherence']} 관련성={g['relevance']} → 평균={g['g_eval_score']}")
        time.sleep(0.5)

        if g["g_eval_score"] < 4.0:
            print(f"  ✗ G-Eval 불합격 ({g['g_eval_score']} < 4.0)")
            processed[url] = {
                "url": url, "status": "fail_geval",
                "accuracy": ts["accuracy"], "fluency_t": ts["fluency"],
                "terminology": ts["terminology"], "style": ts["style"],
                "trans_avg": ts["avg"],
                "consistency": g["consistency"], "fluency_g": g["fluency"],
                "coherence": g["coherence"], "relevance": g["relevance"],
                "geval_avg": g["g_eval_score"], "geval_weighted": g["g_eval_weighted"],
            }
            save_progress(processed)
            continue

        # c. 합격 → 저장 ─────────────────────────────────────────────────────
        selected_count += 1
        print(f"  ✓ 합격! ({selected_count}/{target})")

        writer.writerow({
            "id":                        row["No"],
            "source":                    row["출처"],
            "source_type":               row["source_type"],
            "category":                  row["카테고리"],
            "country":                   row["country"],
            "url":                       url,
            "credibility_score":         row["credibility_score"],
            "published_at":              row["published_at"],
            "created_at":                row["created_at"],
            "원문 제목":                  row[COL_TITLE],
            "번역 제목":                  row[COL_TITLE_KO],
            "원문 (orig_body)":           source,
            "신규 번역 (new_body)":        translation,
            "정확도":                     ts["accuracy"],
            "유창성":                     ts["fluency"],
            "용어":                       ts["terminology"],
            "스타일":                     ts["style"],
            "평균":                       ts["avg"],
            "등급":                       grade(ts["avg"]),
            "신규 3줄 요약 (new_summary)":  summary,
            "일관성\n(Coherence)":         g["coherence"],
            "일치성\n(Consistency)":       g["consistency"],
            "유창성\n(Fluency)":           g["fluency"],
            "관련성\n(Relevance)":         g["relevance"],
            "G-Eval\n평균":               g["g_eval_score"],
            "등급.1":                     grade(g["g_eval_score"]),
            "비고":                       "O",
        })
        out_f.flush()

        processed[url] = {
            "url": url, "status": "pass",
            "accuracy": ts["accuracy"], "fluency_t": ts["fluency"],
            "terminology": ts["terminology"], "style": ts["style"],
            "trans_avg": ts["avg"],
            "consistency": g["consistency"], "fluency_g": g["fluency"],
            "coherence": g["coherence"], "relevance": g["relevance"],
            "geval_avg": g["g_eval_score"], "geval_weighted": g["g_eval_weighted"],
        }
        save_progress(processed)

    out_f.close()

    # 6. 결과 요약 ───────────────────────────────────────────────────────────
    passed    = sum(1 for r in processed.values() if r["status"] == "pass")
    fail_t    = sum(1 for r in processed.values() if r["status"] == "fail_trans")
    fail_g    = sum(1 for r in processed.values() if r["status"] == "fail_geval")

    print("\n" + "=" * 60)
    print(f"선별 완료: {passed}/{target}건")
    print(f"처리: {len(processed)}건")
    print(f"  번역 불합격: {fail_t}건 / G-Eval 불합격: {fail_g}건")
    if passed < target:
        print(f"  ※ 후보 소진 — 추가 기사 필요 ({target - passed}건 부족)")
    print(f"출력 파일: {OUTPUT_CSV}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="testset 추출대기에서 고품질 기사 선별")
    parser.add_argument("--target",  type=int,            default=TARGET, help=f"목표 선별 건수 (기본: {TARGET})")
    parser.add_argument("--dry-run", action="store_true",                 help="API 호출 없이 후보 목록만 출력")
    args = parser.parse_args()
    main(target=args.target, dry_run=args.dry_run)
