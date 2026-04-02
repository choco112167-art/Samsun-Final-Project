"""
Qwen3-4B-Instruct QLoRA 파인튜닝 — Kaggle P100 (16GB)
======================================================
실행 순서:
  1. before 추론 → before_results.csv
  2. QLoRA 파인튜닝 → 체크포인트 저장
  3. after 추론  → after_results.csv
  4. 학습 로그   → training_log.csv

Kaggle 설치:
    !pip install -q transformers peft trl bitsandbytes datasets sacrebleu accelerate

업로드할 파일:
    trainset_chat.jsonl
    testset_chat.jsonl
"""

import os
import csv
import json
import time
import torch
from datetime import datetime

# ── 경로 설정 (Kaggle 환경) ───────────────────────────────
BASE_DIR     = "/kaggle/working"
DATA_DIR     = "/kaggle/input/samseon-dataset"   # Kaggle Dataset 이름에 맞게 수정
TRAIN_JSONL  = os.path.join(DATA_DIR, "trainset_chat.jsonl")
TEST_JSONL   = os.path.join(DATA_DIR, "testset_chat.jsonl")
MODEL_ID     = "Qwen/Qwen3-4B-Instruct"
OUTPUT_DIR   = os.path.join(BASE_DIR, "qwen3-finetuned")

# CSV 기록 파일
BEFORE_CSV      = os.path.join(BASE_DIR, "before_results.csv")
AFTER_CSV       = os.path.join(BASE_DIR, "after_results.csv")
TRAINING_LOG    = os.path.join(BASE_DIR, "training_log.csv")

# ── QLoRA 하이퍼파라미터 ──────────────────────────────────
LORA_CONFIG = dict(
    r=16,                    # LoRA rank
    lora_alpha=32,           # scaling = alpha/r = 2
    target_modules=[         # Qwen3 어텐션 레이어
        "q_proj", "k_proj", "v_proj", "o_proj",
        "gate_proj", "up_proj", "down_proj",
    ],
    lora_dropout=0.05,
    bias="none",
    task_type="CAUSAL_LM",
)

TRAIN_CONFIG = dict(
    num_train_epochs=3,
    per_device_train_batch_size=4,
    gradient_accumulation_steps=4,   # 유효 배치 = 4×4 = 16
    learning_rate=2e-4,
    lr_scheduler_type="cosine",
    warmup_ratio=0.05,
    fp16=True,
    logging_steps=50,
    save_steps=500,
    save_total_limit=2,
    output_dir=OUTPUT_DIR,
    report_to="none",
)

MAX_SEQ_LEN = 1024   # 최대 토큰 길이


# ══════════════════════════════════════════════════════════
# 1. 유틸리티
# ══════════════════════════════════════════════════════════

def load_jsonl(path: str) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def calc_bleu(hypothesis: str, reference: str) -> float:
    """문장 단위 BLEU"""
    try:
        import sacrebleu
        return round(sacrebleu.sentence_bleu(hypothesis, [reference]).score, 2)
    except Exception:
        return 0.0


def init_csv(path: str, headers: list):
    """CSV 파일 초기화 (헤더 작성)"""
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        csv.DictWriter(f, fieldnames=headers).writeheader()


def append_csv(path: str, row: dict):
    """CSV 한 행 추가"""
    with open(path, "a", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(row.keys()))
        writer.writerow(row)


# ══════════════════════════════════════════════════════════
# 2. 모델 로드
# ══════════════════════════════════════════════════════════

def load_model_tokenizer(model_id: str, use_4bit: bool = True):
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

    print(f"[모델 로드] {model_id}")
    tokenizer = AutoTokenizer.from_pretrained(model_id, trust_remote_code=True)
    tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "right"

    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.float16,
        bnb_4bit_use_double_quant=True,
    ) if use_4bit else None

    model = AutoModelForCausalLM.from_pretrained(
        model_id,
        quantization_config=bnb_config,
        device_map="auto",
        trust_remote_code=True,
    )
    model.config.use_cache = False
    return model, tokenizer


# ══════════════════════════════════════════════════════════
# 3. 추론 (번역 생성)
# ══════════════════════════════════════════════════════════

def run_inference(model, tokenizer, test_data: list[dict], out_csv: str):
    """
    testset 전체 추론 → CSV 저장
    컬럼: id, en_text, ko_gt, translation, bleu, elapsed_sec
    """
    headers = ["id", "en_text", "ko_gt", "translation", "bleu", "elapsed_sec"]
    init_csv(out_csv, headers)

    model.eval()
    total = len(test_data)

    for i, item in enumerate(test_data, 1):
        messages = item["messages"]
        en_text  = messages[1]["content"]   # user 역할 = 영어 원문
        ko_gt    = messages[2]["content"]   # assistant 역할 = 한국어 GT

        # 채팅 템플릿 적용
        prompt = tokenizer.apply_chat_template(
            messages[:-1],   # system + user 만 입력 (assistant 제외)
            tokenize=False,
            add_generation_prompt=True,
        )
        inputs = tokenizer(prompt, return_tensors="pt").to(model.device)

        t0 = time.time()
        with torch.no_grad():
            output_ids = model.generate(
                **inputs,
                max_new_tokens=512,
                temperature=0.3,
                do_sample=True,
                pad_token_id=tokenizer.eos_token_id,
            )
        elapsed = round(time.time() - t0, 2)

        # 생성된 부분만 추출
        new_ids = output_ids[0][inputs["input_ids"].shape[1]:]
        translation = tokenizer.decode(new_ids, skip_special_tokens=True).strip()

        bleu = calc_bleu(translation, ko_gt)

        row = {
            "id":           i,
            "en_text":      en_text[:500],
            "ko_gt":        ko_gt[:500],
            "translation":  translation[:500],
            "bleu":         bleu,
            "elapsed_sec":  elapsed,
        }
        append_csv(out_csv, row)

        if i % 50 == 0 or i == total:
            avg_bleu = _running_bleu(out_csv)
            print(f"  [{i}/{total}] BLEU 누적 평균: {avg_bleu:.2f}")

    print(f"추론 완료 → {out_csv}")


def _running_bleu(csv_path: str) -> float:
    """현재까지 저장된 CSV에서 BLEU 평균 계산"""
    with open(csv_path, encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    vals = [float(r["bleu"]) for r in rows if r["bleu"]]
    return sum(vals) / len(vals) if vals else 0.0


# ══════════════════════════════════════════════════════════
# 4. 파인튜닝
# ══════════════════════════════════════════════════════════

def finetune(model, tokenizer, train_data: list[dict]):
    from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
    from trl import SFTTrainer, SFTConfig
    from datasets import Dataset

    print("\n[파인튜닝 시작]")

    # QLoRA 준비
    model = prepare_model_for_kbit_training(model)
    lora_config = LoraConfig(**LORA_CONFIG)
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()

    # Dataset 변환
    def format_sample(item):
        return tokenizer.apply_chat_template(
            item["messages"],
            tokenize=False,
            add_generation_prompt=False,
        )

    formatted = [{"text": format_sample(item)} for item in train_data]
    dataset = Dataset.from_list(formatted)

    # 학습 로그 CSV 초기화
    log_headers = ["step", "loss", "learning_rate", "epoch", "timestamp"]
    init_csv(TRAINING_LOG, log_headers)

    class CsvLogCallback:
        """학습 로그 → CSV 기록 콜백"""
        def on_log(self, args, state, control, logs=None, **kwargs):
            if logs and "loss" in logs:
                append_csv(TRAINING_LOG, {
                    "step":          state.global_step,
                    "loss":          round(logs.get("loss", 0), 4),
                    "learning_rate": logs.get("learning_rate", 0),
                    "epoch":         round(logs.get("epoch", 0), 2),
                    "timestamp":     datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                })

    sft_config = SFTConfig(
        max_seq_length=MAX_SEQ_LEN,
        **TRAIN_CONFIG,
    )

    trainer = SFTTrainer(
        model=model,
        tokenizer=tokenizer,
        train_dataset=dataset,
        args=sft_config,
        callbacks=[CsvLogCallback()],
    )

    trainer.train()
    trainer.save_model(OUTPUT_DIR)
    tokenizer.save_pretrained(OUTPUT_DIR)
    print(f"모델 저장 완료: {OUTPUT_DIR}")
    print(f"학습 로그 저장: {TRAINING_LOG}")

    return model


# ══════════════════════════════════════════════════════════
# 5. 메인 실행
# ══════════════════════════════════════════════════════════

def main():
    print("=" * 60)
    print("삼선뉴스 Qwen3-4B-Instruct QLoRA 파인튜닝")
    print("=" * 60)

    # 데이터 로드
    train_data = load_jsonl(TRAIN_JSONL)
    test_data  = load_jsonl(TEST_JSONL)
    print(f"train: {len(train_data)}건 / test: {len(test_data)}건\n")

    # ── Step 1: 파인튜닝 전 추론 ──
    print("=" * 40)
    print("Step 1. 파인튜닝 전 추론 (before)")
    print("=" * 40)
    model, tokenizer = load_model_tokenizer(MODEL_ID)
    run_inference(model, tokenizer, test_data, BEFORE_CSV)

    # ── Step 2: QLoRA 파인튜닝 ──
    print("\n" + "=" * 40)
    print("Step 2. QLoRA 파인튜닝")
    print("=" * 40)
    model = finetune(model, tokenizer, train_data)

    # ── Step 3: 파인튜닝 후 추론 ──
    print("\n" + "=" * 40)
    print("Step 3. 파인튜닝 후 추론 (after)")
    print("=" * 40)
    run_inference(model, tokenizer, test_data, AFTER_CSV)

    # ── 최종 BLEU 비교 출력 ──
    before_bleu = _running_bleu(BEFORE_CSV)
    after_bleu  = _running_bleu(AFTER_CSV)
    print("\n" + "=" * 40)
    print("최종 결과 요약")
    print("=" * 40)
    print(f"파인튜닝 전 BLEU: {before_bleu:.2f}")
    print(f"파인튜닝 후 BLEU: {after_bleu:.2f}")
    print(f"BLEU 개선:       +{after_bleu - before_bleu:.2f}")
    print(f"\n저장 파일:")
    print(f"  {BEFORE_CSV}")
    print(f"  {AFTER_CSV}")
    print(f"  {TRAINING_LOG}")


if __name__ == "__main__":
    main()
