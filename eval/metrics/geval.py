"""
G-Eval — 요약 품질 자동 평가 (Claude Haiku via Anthropic API)
평가 4축: 충실성 / 유창성 / 간결성 / 관련성 (각 5점 척도)
대상: summary_formal (격식체)

점수 산출:
    g_eval_score    = (faithfulness + fluency + conciseness + relevance) / 4
    g_eval_weighted = faithfulness*0.4 + relevance*0.3 + fluency*0.2 + conciseness*0.1

설치:
    pip install anthropic
환경변수:
    ANTHROPIC_API_KEY
"""

import os
import json
import time
from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
EVAL_MODEL = "claude-haiku-4-5-20251001"

GEVAL_SYSTEM = "You are a strict and impartial evaluator for Korean AI/tech news summaries."

GEVAL_USER_TEMPLATE = """You will evaluate a MODEL-GENERATED Korean summary using four criteria.
Each criterion specifies EXACTLY which input to compare against — follow this precisely.

INPUTS:
- [A] Source Article: the original English news article
- [B] Reference Summary (GT): a human-quality Korean summary used ONLY as a length/density benchmark
- [C] Generated Summary: the model output you are evaluating

---

[A] Source Article
{source}

[B] Reference Summary (GT)
{gt_summary}

[C] Generated Summary
{generated_summary}

---

EVALUATION INSTRUCTIONS:
For each criterion below:
1. Identify which input(s) to compare against (specified per criterion)
2. Think step by step before scoring
3. Assign an integer score from 1 to 5
4. Do NOT let scores from one criterion influence another

---

CRITERION 1 — Faithfulness (충실성)
Compare: [C] vs [A] ONLY. Do NOT use [B].
Question: Does the generated summary accurately reflect the facts in the source article?

Scoring rubric:
5 — All facts correct; nothing hallucinated, added, or distorted
4 — No factual errors; at most one minor fact omitted
3 — One fact slightly distorted OR one important fact missing
2 — Two or more factual errors OR significant distortion of the main claim
1 — Contains hallucinated facts OR directly contradicts the source

Step-by-step reasoning (cite specific facts if penalizing):
Score:

---

CRITERION 2 — Fluency (유창성)
Compare: [C] ONLY. Do NOT use [A] or [B].
Question: Is the Korean natural and easy to read for a Korean tech news audience?

Terminology rule — ALL AI/tech proper nouns and neologisms MUST follow this format:
  영어 원어 (한국어 음차)  e.g., "RAG (래그)", "fine-tuning (파인튜닝)", "LLM (엘엘엠)"
  Violation types:
  - Missing English term (e.g., "래그" only) → -1 point per occurrence
  - Semantic translation used instead of transliteration (e.g., "검색 증강 생성") → -1 point per occurrence

Scoring rubric:
5 — Reads like native Korean tech journalism; all terminology correctly formatted
4 — Mostly natural; at most 1 minor awkward phrase OR 1 terminology formatting error
3 — Readable but noticeably unnatural phrasing OR 2 terminology formatting errors
2 — Difficult to read due to awkward Korean OR systematic terminology errors
1 — Unreadable; machine-translated feel throughout

Step-by-step reasoning (list any terminology violations found):
Score:

---

CRITERION 3 — Conciseness (간결성)
Compare: [C] vs [B] for length and information density ONLY.
Question: Is the generated summary appropriately concise, relative to the GT benchmark?

Scoring rubric:
5 — Similar sentence count and information density to GT; every sentence adds value
4 — Slightly more verbose or slightly sparser than GT; acceptable range
3 — Noticeably longer (padding present) OR noticeably shorter (too sparse) than GT
2 — Significantly over-compressed OR bloated with filler compared to GT
1 — Extreme mismatch: either one-liner that loses all detail OR paragraph-length rambling

Step-by-step reasoning (compare sentence count and density to GT):
Score:

---

CRITERION 4 — Relevance (관련성)
Compare: [C] vs [A] ONLY. Do NOT use [B].
Question: Does the generated summary cover the key points of the source article?

Scoring rubric:
5 — All key points from the source are present in the summary
4 — Most key points covered; at most one minor point omitted
3 — One important point missing OR the summary focuses on a secondary point
2 — Two or more important points missing
1 — Fails to convey the main topic of the source article

Step-by-step reasoning (list key points from source and check coverage):
Score:

---

OUTPUT FORMAT:
Respond with valid JSON only. No preamble, no explanation outside the JSON block.
Compute g_eval_score as the arithmetic mean of the four scores.
Compute g_eval_weighted = faithfulness*0.4 + relevance*0.3 + fluency*0.2 + conciseness*0.1

{{"faithfulness": {{"reasoning": "...", "score": X}}, "fluency": {{"reasoning": "...", "score": X}}, "conciseness": {{"reasoning": "...", "score": X}}, "relevance": {{"reasoning": "...", "score": X}}, "g_eval_score": X.X, "g_eval_weighted": X.X}}"""


def geval_single(
    source: str,
    summary: str,
    gt_summary: str = "",
    retries: int = 3,
) -> dict:
    """
    단일 요약문 G-Eval 채점 (4축).

    Returns:
        {
            "faithfulness": int,
            "fluency":      int,
            "conciseness":  int,
            "relevance":    int,
            "g_eval_score":    float,  # 단순평균
            "g_eval_weighted": float,  # 가중평균
            "raw": str,
        }
    """
    try:
        import anthropic
    except ImportError:
        raise ImportError("pip install anthropic")

    if not ANTHROPIC_API_KEY:
        raise ValueError("ANTHROPIC_API_KEY 환경변수를 설정하세요.")

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    user_msg = GEVAL_USER_TEMPLATE.format(
        source=source[:2000],
        gt_summary=gt_summary[:500] if gt_summary else "(not provided)",
        generated_summary=summary,
    )

    for attempt in range(retries):
        try:
            response = client.messages.create(
                model=EVAL_MODEL,
                max_tokens=8192,
                system=GEVAL_SYSTEM,
                messages=[{"role": "user", "content": user_msg}],
            )
            raw = response.content[0].text.strip()
            clean = raw.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
            scores = json.loads(clean)

            f  = int(scores["faithfulness"]["score"])
            fl = int(scores["fluency"]["score"])
            c  = int(scores["conciseness"]["score"])
            r  = int(scores["relevance"]["score"])

            simple   = round((f + fl + c + r) / 4, 2)
            weighted = round(f * 0.4 + r * 0.3 + fl * 0.2 + c * 0.1, 2)

            return {
                "faithfulness":    f,
                "fluency":         fl,
                "conciseness":     c,
                "relevance":       r,
                "g_eval_score":    simple,
                "g_eval_weighted": weighted,
                "raw":             raw,
            }

        except (json.JSONDecodeError, KeyError):
            # 파싱 실패는 재시도해도 동일 결과 — 즉시 반환
            return {
                "faithfulness": 0, "fluency": 0,
                "conciseness": 0, "relevance": 0,
                "g_eval_score": 0.0, "g_eval_weighted": 0.0,
                "raw": raw if "raw" in locals() else "parse error",
            }
        except Exception as e:
            # 400/401/402 등 클라이언트 에러는 재시도해도 의미없음 — 즉시 반환
            if hasattr(e, "status_code") and e.status_code < 500:
                return {
                    "faithfulness": 0, "fluency": 0,
                    "conciseness": 0, "relevance": 0,
                    "g_eval_score": 0.0, "g_eval_weighted": 0.0,
                    "raw": f"error: {e}",
                }
            if attempt < retries - 1:
                time.sleep(3)
            else:
                return {
                    "faithfulness": 0, "fluency": 0,
                    "conciseness": 0, "relevance": 0,
                    "g_eval_score": 0.0, "g_eval_weighted": 0.0,
                    "raw": f"error: {e}",
                }


def batch_geval(
    sources: list[str],
    summaries: list[str],
    gt_summaries: list[str] = None,
    delay: float = 0.5,
) -> dict:
    """여러 요약문 G-Eval 배치 채점."""
    if gt_summaries is None:
        gt_summaries = [""] * len(sources)

    results = []
    for i, (src, summ, gt) in enumerate(zip(sources, summaries, gt_summaries), 1):
        print(f"  G-Eval [{i}/{len(sources)}] 채점 중...")
        result = geval_single(src, summ, gt)
        results.append(result)
        time.sleep(delay)

    def mean(key):
        vals = [r[key] for r in results if r[key] > 0]
        return round(sum(vals) / len(vals), 2) if vals else 0.0

    return {
        "faithfulness_mean":    mean("faithfulness"),
        "fluency_mean":         mean("fluency"),
        "conciseness_mean":     mean("conciseness"),
        "relevance_mean":       mean("relevance"),
        "g_eval_score_mean":    mean("g_eval_score"),
        "g_eval_weighted_mean": mean("g_eval_weighted"),
        "scores":               results,
    }
