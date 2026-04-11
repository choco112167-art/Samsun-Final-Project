"""
G-Eval — 요약 품질 자동 평가 (Claude Haiku via Anthropic API)
평가 4축: 일치성(Consistency) / 유창성(Fluency) / 일관성(Coherence) / 관련성(Relevance) (각 5점 척도)
대상: summary_formal (격식체)
논문 근거: Liu et al. (2023) "G-Eval: NLG Evaluation using GPT-4 with Better Human Alignment"
          Fabbri et al. (2021) "SummEval: Re-evaluating Summarization Evaluation"

점수 산출:
    g_eval_score    = (consistency + fluency + coherence + relevance) / 4
    g_eval_weighted = consistency*0.4 + relevance*0.3 + fluency*0.2 + coherence*0.1

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

CRITERION 1 — Consistency (일치성)
Compare: [C] vs [A] ONLY. Do NOT use [B].
Question: Are all facts in the generated summary consistent with the source article?

Scoring rubric:
5 — All facts consistent; nothing hallucinated, added, or distorted
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

Terminology rule — the summary must follow Korean tech journalism conventions:
  ① Abbreviations (RAG, LLM, GPU, NPU, API, etc.) → keep in English as-is; do NOT transliterate
  ② Standard transliterations: fine-tuning→파인튜닝, embedding→임베딩, prompt→프롬프트
  ③ Proper nouns on FIRST mention: EnglishName(한국어 음차), e.g., OpenAI(오픈에이아이)
     Key approved forms: ChatGPT(챗GPT) / Gemini(제미나이) / Llama(라마) / Claude(클로드) /
     Anthropic(앤트로픽) / Google(구글) / Meta(메타) / Microsoft(마이크로소프트) / Nvidia(엔비디아) /
     Mistral AI(미스트랄 AI) / Hugging Face(허깅 페이스) / Perplexity AI(퍼플렉시티 AI)
  ④ Currency: $ → 달러, € → 유로, £ → 파운드, ¥ → 엔/위안
  ⑤ Numbers: T/trillion→조, B/billion→억, M/million→만, K/thousand→천 (e.g., $2.5B→25억 달러)
  ⑥ Model version numbers stay in English: e.g., GPT-4o, Claude 3.5 Sonnet
  Violation types:
  - Transliterating abbreviations (e.g., "엘엘엠" for LLM) → -1 point
  - Missing English term on first proper noun mention → -1 point per occurrence
  - Wrong transliteration form (not matching approved list) → -1 point per occurrence
  - Wrong currency/number conversion (e.g., $2.5B → "2.5빌리언") → -1 point

Scoring rubric:
5 — Reads like native Korean tech journalism; all terminology correctly formatted
4 — Mostly natural; at most 1 minor awkward phrase OR 1 terminology formatting error
3 — Readable but noticeably unnatural phrasing OR 2 terminology formatting errors
2 — Difficult to read due to awkward Korean OR systematic terminology errors
1 — Unreadable; machine-translated feel throughout

Step-by-step reasoning (list any terminology violations found):
Score:

---

CRITERION 3 — Coherence (일관성)
Compare: [C] ONLY.
Question: Is the generated summary logically structured and coherent?

Scoring rubric:
5 — Well-structured; sentences flow naturally and connect logically; clear progression of ideas
4 — Mostly coherent; at most one slightly awkward transition between sentences
3 — Generally readable but with noticeable disorganization or abrupt transitions
2 — Hard to follow; sentences seem disconnected or appear in illogical order
1 — No discernible structure; reads like random unconnected sentences

Step-by-step reasoning (note any structural or transitional issues):
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
Compute g_eval_weighted = consistency*0.4 + relevance*0.3 + fluency*0.2 + coherence*0.1

{{"consistency": {{"reasoning": "...", "score": X}}, "fluency": {{"reasoning": "...", "score": X}}, "coherence": {{"reasoning": "...", "score": X}}, "relevance": {{"reasoning": "...", "score": X}}, "g_eval_score": X.X, "g_eval_weighted": X.X}}"""


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
            "consistency": int,
            "fluency":     int,
            "coherence":   int,
            "relevance":   int,
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

            con = int(scores["consistency"]["score"])
            fl  = int(scores["fluency"]["score"])
            coh = int(scores["coherence"]["score"])
            r   = int(scores["relevance"]["score"])

            simple   = round((con + fl + coh + r) / 4, 2)
            weighted = round(con * 0.4 + r * 0.3 + fl * 0.2 + coh * 0.1, 2)

            return {
                "consistency":     con,
                "fluency":         fl,
                "coherence":       coh,
                "relevance":       r,
                "g_eval_score":    simple,
                "g_eval_weighted": weighted,
                "raw":             raw,
            }

        except (json.JSONDecodeError, KeyError):
            # 파싱 실패는 재시도해도 동일 결과 — 즉시 반환
            return {
                "consistency": 0, "fluency": 0,
                "coherence": 0, "relevance": 0,
                "g_eval_score": 0.0, "g_eval_weighted": 0.0,
                "raw": raw if "raw" in locals() else "parse error",
            }
        except Exception as e:
            # 400/401/402 등 클라이언트 에러는 재시도해도 의미없음 — 즉시 반환
            if hasattr(e, "status_code") and e.status_code < 500:
                return {
                    "consistency": 0, "fluency": 0,
                    "coherence": 0, "relevance": 0,
                    "g_eval_score": 0.0, "g_eval_weighted": 0.0,
                    "raw": f"error: {e}",
                }
            if attempt < retries - 1:
                time.sleep(3)
            else:
                return {
                    "consistency": 0, "fluency": 0,
                    "coherence": 0, "relevance": 0,
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
        "consistency_mean":     mean("consistency"),
        "fluency_mean":         mean("fluency"),
        "coherence_mean":       mean("coherence"),
        "relevance_mean":       mean("relevance"),
        "g_eval_score_mean":    mean("g_eval_score"),
        "g_eval_weighted_mean": mean("g_eval_weighted"),
        "scores":               results,
    }
