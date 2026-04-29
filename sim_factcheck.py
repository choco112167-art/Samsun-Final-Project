"""
sim_factcheck.py — 팩트체크 파이프라인 시뮬레이션

Step 0~1은 API 없이 즉시 실행.
Step 2(Google FC API) / Step 3(Gemini) 는 .env에 키가 있으면 실제 호출,
없으면 skip_fc_api=True / skip_llm=True 로 우회.

실행:
    python sim_factcheck.py
"""

import os
import sys
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv()

from fact_checker.pipeline import run_fact_check

# API 키 유무로 skip 여부 자동 결정
HAS_GOOGLE_FC  = bool(os.getenv("GOOGLE_FC_API_KEY"))
HAS_GEMINI     = bool(os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"))

SKIP_FC  = not HAS_GOOGLE_FC
SKIP_LLM = not HAS_GEMINI

# ── 테스트 케이스 ─────────────────────────────────────────────
CASES = [
    {
        "name": "① MIT TR — 공식 보도, 루머 신호 없음 → FACT_AUTO 기대",
        "title": "NVIDIA Blackwell Ultra GPU Sets New AI Benchmark Record",
        "content": (
            "NVIDIA announced that its Blackwell Ultra GPU has achieved new records "
            "in AI inference benchmarks. The company released detailed performance "
            "data showing 3x improvement over the previous generation H100. "
            "The chip will be available to cloud providers starting Q3 2026."
        ),
        "source": "MIT Technology Review",
        "source_type": "media",
    },
    {
        "name": "② The Guardian — Opinion 패턴 2개 이상 → DROP 기대",
        "title": "Opinion: Why We Should Regulate AI Before It's Too Late",
        "content": (
            "In my view, governments have been too slow to act. I believe that "
            "AI development should be paused until proper regulatory frameworks "
            "are established. This is an editorial perspective shared by many "
            "experts in the field who think the case for regulation is clear."
        ),
        "source": "The Guardian Tech",
        "source_type": "media",
    },
    {
        "name": "③ TechCrunch — 단독 유출 + 약한 루머 → NEEDS_VERIFICATION 기대",
        "title": "Exclusive: OpenAI Expected to Launch GPT-5 Next Month, Sources Say",
        "content": (
            "According to sources familiar with the matter, OpenAI is expected to "
            "announce GPT-5 as early as next month. The release could potentially "
            "include multimodal capabilities that might surpass current models. "
            "People familiar with the timeline said the launch is likely in May."
        ),
        "source": "TechCrunch",
        "source_type": "media",
    },
    {
        "name": "④ The Verge — 강한 루머 신호 → RUMOR 기대",
        "title": "Reportedly: Google Allegedly Planning to Acquire Anthropic",
        "content": (
            "Unverified reports suggest that Google is allegedly in advanced talks "
            "to acquire AI startup Anthropic. The claim, which remains unverified, "
            "has sparked controversy in the AI community. Misinformation about the "
            "deal has reportedly been circulating on social media."
        ),
        "source": "The Verge",
        "source_type": "media",
    },
    {
        "name": "⑤ VentureBeat — 기본 tier CREDIBLE_LEAK, 신호 없음 → FC/LLM 검증 기대",
        "title": "Meta Releases Llama 4 Scout with 17B Parameters",
        "content": (
            "Meta AI has officially released Llama 4 Scout, a 17 billion parameter "
            "model designed for efficient inference. The model achieves state-of-the-art "
            "results on multiple benchmarks including MMLU and HumanEval. "
            "The weights are available on Hugging Face under the Llama 4 license."
        ),
        "source": "VentureBeat AI",
        "source_type": "media",
    },
]


def run():
    print("=" * 65)
    print("  팩트체크 파이프라인 시뮬레이션")
    print(f"  Google FC API: {'✅ 실제 호출' if not SKIP_FC else '⏭ skip (키 없음)'}")
    print(f"  Gemini LLM   : {'✅ 실제 호출' if not SKIP_LLM else '⏭ skip (키 없음)'}")
    print("=" * 65)

    for case in CASES:
        print(f"\n{case['name']}")
        print(f"  출처  : {case['source']} ({case['source_type']})")
        print(f"  제목  : {case['title'][:70]}")

        result = run_fact_check(
            title       = case["title"],
            content     = case["content"],
            source      = case["source"],
            source_type = case["source_type"],
            skip_fc_api = SKIP_FC,
            skip_llm    = SKIP_LLM,
        )

        label_icon = {
            "FACT":       "✅ FACT",
            "RUMOR":      "🚨 RUMOR",
            "UNVERIFIED": "❓ UNVERIFIED",
            "DROP":       "🗑  DROP",
        }.get(result.fact_label, result.fact_label)

        print(f"  결과  : {label_icon}  (confidence={result.confidence:.2f})")
        print(f"  Step  : {result.step_reached}  |  방법: {result.verification_method}")
        print(f"  Tier  : {result.tier}")
        if result.matched_patterns:
            print(f"  패턴  : {result.matched_patterns[:3]}")
        print(f"  근거  : {result.reasoning_trace[:100]}")

    print("\n" + "=" * 65)
    print("  시뮬레이션 완료")
    print("=" * 65)


if __name__ == "__main__":
    run()
