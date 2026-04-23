"""
번역 평가 지표
- BLEU  : sacrebleu (n-gram 표면 일치율)
- COMET : unbabel-comet (의미 보존 품질)

설치:
    pip install sacrebleu unbabel-comet
"""

from typing import Optional


def calc_bleu(hypotheses: list[str], references: list[str]) -> dict:
    """
    BLEU 점수 계산.

    Args:
        hypotheses: 모델 번역 출력 리스트
        references: GT 번역 리스트

    Returns:
        {"bleu": float, "detail": str}
    """
    try:
        import sacrebleu
    except ImportError:
        raise ImportError("pip install sacrebleu")

    result = sacrebleu.corpus_bleu(hypotheses, [references])
    return {
        "bleu":   round(result.score, 2),
        "detail": str(result),
    }


def calc_bleu_sentence(hypothesis: str, reference: str) -> float:
    """문장 단위 BLEU (개별 행 저장용)"""
    try:
        import sacrebleu
    except ImportError:
        raise ImportError("pip install sacrebleu")

    result = sacrebleu.sentence_bleu(hypothesis, [reference])
    return round(result.score, 2)


def load_comet_model(model_name: str = "Unbabel/wmt22-comet-da"):
    """COMET 모델을 한 번만 로드해서 반환 (run_eval에서 재사용용)"""
    try:
        from comet import download_model, load_from_checkpoint
    except ImportError:
        raise ImportError("pip install unbabel-comet")
    return load_from_checkpoint(download_model(model_name))


def calc_comet(
    sources: list[str],
    hypotheses: list[str],
    references: list[str],
    model_name: str = "Unbabel/wmt22-comet-da",
    batch_size: int = 8,
    gpus: int = 1,
    model=None,
) -> dict:
    """
    COMET 점수 계산.

    Args:
        sources    : 영어 원문 리스트
        hypotheses : 모델 번역 출력 리스트
        references : GT 번역 리스트
        model_name : COMET 모델 (기본: wmt22-comet-da)
        batch_size : 배치 크기
        gpus       : GPU 수 (0=CPU)

    Returns:
        {"comet_mean": float, "scores": list[float]}
    """
    try:
        from comet import download_model, load_from_checkpoint
    except ImportError:
        raise ImportError("pip install unbabel-comet")

    if model is None:
        from comet import download_model, load_from_checkpoint
        model = load_from_checkpoint(download_model(model_name))

    data = [
        {"src": s, "mt": h, "ref": r}
        for s, h, r in zip(sources, hypotheses, references)
    ]

    output = model.predict(data, batch_size=batch_size, gpus=gpus)
    scores = [round(float(s), 4) for s in output.scores]

    return {
        "comet_mean": round(float(output.system_score), 4),
        "scores":     scores,
    }
