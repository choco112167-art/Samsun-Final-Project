"""
Term Preservation Rate (TPR)
AI 신조어·고유명사가 번역 출력에 영문 그대로 유지되는지 룰 기반 체크.

목표: TPR ≥ 95%
"""

# 보존해야 할 AI 신조어·고유명사 목록
# 프롬프트 규칙과 동일한 기준으로 관리
AI_TERMS = [
    # 모델·회사명
    "Anthropic", "OpenAI", "Google", "Meta", "Microsoft",
    "Nvidia", "Apple", "Amazon", "Samsung", "DeepMind",
    "xAI", "Mistral", "Cohere", "Stability AI",
    # 모델명
    "GPT-4", "GPT-4o", "GPT-5", "Claude", "Gemini", "Llama",
    "Grok", "Qwen", "DeepSeek", "Falcon", "Mixtral",
    # 기술 용어 (약어)
    "RAG", "LLM", "GPU", "NPU", "API", "RLHF", "SFT",
    "LoRA", "QLoRA", "PEFT", "vLLM",
    # 제품·서비스명
    "ChatGPT", "Copilot", "Alexa", "Siri", "Bard",
    "Slack", "GitHub", "Hugging Face",
    # 하드웨어
    "Blackwell", "Hopper", "H100", "A100", "B200",
]


def check_term_preservation(translation: str, source: str = "", terms: list[str] = None) -> dict:
    """
    번역 출력에서 AI 용어 영문 보존 여부 체크.

    Args:
        translation : 모델 번역 출력 텍스트
        source      : 원본 영어 텍스트 (용어 등장 여부 판단 기준)
                      없으면 translation에서 찾는 방식으로 fallback (비권장)
        terms       : 체크할 용어 리스트 (기본: AI_TERMS)

    Returns:
        {
            "tpr": float,           # Term Preservation Rate (0.0~1.0)
            "preserved": list,      # 보존된 용어
            "missing": list,        # 누락된 용어 (번역됨)
            "checked": list,        # 원문에 등장한 용어 (체크 대상)
        }
    """
    if terms is None:
        terms = AI_TERMS

    # 원문(source)에 등장하는 용어만 체크 대상으로 선정
    # source가 없으면 translation에서 fallback (TPR 과대평가 주의)
    base = source if source else translation
    checked   = [t for t in terms if t.lower() in base.lower()]
    preserved = [t for t in checked if t in translation]
    missing   = [t for t in checked if t not in translation]

    tpr = len(preserved) / len(checked) if checked else 1.0

    return {
        "tpr":       round(tpr, 4),
        "preserved": preserved,
        "missing":   missing,
        "checked":   checked,
    }


def batch_tpr(translations: list[str], terms: list[str] = None) -> dict:
    """
    여러 번역 출력의 평균 TPR 계산.

    Returns:
        {"tpr_mean": float, "scores": list[float]}
    """
    scores = [check_term_preservation(t, terms=terms)["tpr"] for t in translations]
    tpr_mean = sum(scores) / len(scores) if scores else 0.0

    return {
        "tpr_mean": round(tpr_mean, 4),
        "scores":   [round(s, 4) for s in scores],
    }
