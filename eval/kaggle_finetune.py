"""
Qwen3.5-4B QLoRA 파인튜닝 — Kaggle P100 (16GB)
======================================================
세션 분리 실행 (Kaggle 12시간 제한 대응):

  SESSION = 1  →  epoch 1 학습 (8~10시간 예상)
  SESSION = 2  →  epoch 2~3 학습, 체크포인트 이어받기 (8~10시간 예상)
  SESSION = 3  →  파인튜닝 후 추론 + BLEU 비교 (2~3시간 예상)

Kaggle 셀 상단에 실행:
    !pip install -q transformers peft trl bitsandbytes datasets sacrebleu accelerate

업로드할 Kaggle Dataset (이름: samseon-dataset):
    trainset_chat.jsonl
    testset_chat.jsonl

파인튜닝 전(before) 평가는 로컬에서 완료 → results_300.csv 존재
Kaggle에서는 after 추론만 진행
"""

import os
import csv
import json
import re
import time
import torch
from datetime import datetime

# ══════════════════════════════════════════════════════════
# ★ 세션 설정 — 실행 전 여기만 바꾸세요
# ══════════════════════════════════════════════════════════
SESSION = 1   # 1, 2, 3 중 선택

# ── 경로 설정 (Kaggle 환경) ───────────────────────────────
BASE_DIR    = "/kaggle/working"
DATA_DIR    = "/kaggle/input/datasets/huemayi/samseon-dataset"
TRAIN_JSONL = os.path.join(DATA_DIR, "trainset_chat.jsonl")
TEST_JSONL  = os.path.join(DATA_DIR, "testset_chat.jsonl")
MODEL_ID    = "Qwen/Qwen3.5-4B"
OUTPUT_DIR  = os.path.join(BASE_DIR, "qwen3_5-finetuned")
CKPT_DIR    = os.path.join(BASE_DIR, "checkpoints")   # 세션 간 체크포인트

# 결과 파일
AFTER_CSV    = os.path.join(BASE_DIR, "after_results.csv")
TRAINING_LOG = os.path.join(BASE_DIR, "training_log.csv")

# ── QLoRA 하이퍼파라미터 ──────────────────────────────────
LORA_CONFIG = dict(
    r=16,
    lora_alpha=32,
    target_modules=[
        "q_proj", "k_proj", "v_proj", "o_proj",
        "gate_proj", "up_proj", "down_proj",
    ],
    lora_dropout=0.05,
    bias="none",
    task_type="CAUSAL_LM",
)

# 세션별 epoch 설정
SESSION_EPOCHS = {
    1: 1,   # Session 1: epoch 1만
    2: 3,   # Session 2: epoch 3까지 (1에서 이어받아 2~3 진행)
}

TRAIN_CONFIG = dict(
    per_device_train_batch_size=4,
    gradient_accumulation_steps=4,   # 유효 배치 = 16
    learning_rate=2e-4,
    lr_scheduler_type="cosine",
    warmup_ratio=0.05,
    fp16=True,
    logging_steps=50,
    save_steps=300,          # 자주 저장 (세션 끊김 대비)
    save_total_limit=3,
    output_dir=CKPT_DIR,
    report_to="none",
)

MAX_SEQ_LEN = 1024

SUMMARY_SYSTEM = """You are a professional AI news summarizer.
Summarize the given English news article into Korean formal style (격식체, ~습니다/~됩니다).

Rules:
- Summarize in exactly 3 sentences. Each sentence must cover a DIFFERENT aspect.
- Keep abbreviations like RAG, LLM, GPU, API, NPU in English.
- Keep ALL proper nouns in English (Anthropic, OpenAI, Google, Meta, Nvidia, etc.).
- Output ONLY the Korean summary. No explanation, no preamble."""


# ══════════════════════════════════════════════════════════
# 1. 유틸리티
# ══════════════════════════════════════════════════════════

def load_jsonl(path: str) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def strip_think(text: str) -> str:
    """Qwen3 <think>...</think> 태그 제거"""
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    return text.strip()


def calc_bleu(hypothesis: str, reference: str) -> float:
    try:
        import sacrebleu
        return round(sacrebleu.sentence_bleu(hypothesis, [reference]).score, 2)
    except Exception:
        return 0.0


def init_csv(path: str, headers: list):
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        csv.DictWriter(f, fieldnames=headers).writeheader()


def append_csv(path: str, row: dict):
    with open(path, "a", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(row.keys()))
        writer.writerow(row)


def find_latest_checkpoint(ckpt_dir: str):
    """가장 최근 체크포인트 경로 반환"""
    if not os.path.exists(ckpt_dir):
        return None
    ckpts = [
        os.path.join(ckpt_dir, d)
        for d in os.listdir(ckpt_dir)
        if d.startswith("checkpoint-")
    ]
    return max(ckpts, key=os.path.getmtime) if ckpts else None


# ══════════════════════════════════════════════════════════
# 2. 모델 로드
# ══════════════════════════════════════════════════════════

def load_base_model(model_id: str):
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
    )

    model = AutoModelForCausalLM.from_pretrained(
        model_id,
        quantization_config=bnb_config,
        device_map="auto",
        trust_remote_code=True,
    )
    model.config.use_cache = False
    return model, tokenizer


def load_finetuned_model(model_dir: str):
    """파인튜닝 완료 모델 로드 (Session 3용)"""
    from transformers import AutoTokenizer
    from peft import AutoPeftModelForCausalLM

    print(f"[파인튜닝 모델 로드] {model_dir}")
    tokenizer = AutoTokenizer.from_pretrained(model_dir, trust_remote_code=True)
    model = AutoPeftModelForCausalLM.from_pretrained(
        model_dir,
        device_map="auto",
        torch_dtype=torch.float16,
    )
    model.eval()
    return model, tokenizer


# ══════════════════════════════════════════════════════════
# 3. 추론
# ══════════════════════════════════════════════════════════

def generate_text(model, tokenizer, messages: list[dict], max_new_tokens: int = 512) -> str:
    prompt = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True,
    )
    inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
    with torch.no_grad():
        output_ids = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            temperature=0.3,
            do_sample=True,
            pad_token_id=tokenizer.eos_token_id,
        )
    new_ids = output_ids[0][inputs["input_ids"].shape[1]:]
    raw = tokenizer.decode(new_ids, skip_special_tokens=True)
    return strip_think(raw)   # think 태그 제거


def run_inference(model, tokenizer, test_data: list[dict], out_csv: str):
    """testset 전체 추론 → CSV 저장"""
    headers = ["id", "en_text", "ko_gt", "translation", "summary_formal", "bleu", "elapsed_sec"]
    init_csv(out_csv, headers)

    model.eval()
    total = len(test_data)

    for i, item in enumerate(test_data, 1):
        messages = item["messages"]
        en_text  = messages[1]["content"]
        ko_gt    = messages[2]["content"]

        t0 = time.time()

        translation = generate_text(model, tokenizer, messages[:-1])
        summary_formal = generate_text(
            model, tokenizer,
            [{"role": "system", "content": SUMMARY_SYSTEM},
             {"role": "user",   "content": en_text}],
            max_new_tokens=256,
        )

        elapsed = round(time.time() - t0, 2)
        bleu    = calc_bleu(translation, ko_gt)

        append_csv(out_csv, {
            "id":             i,
            "en_text":        en_text[:500],
            "ko_gt":          ko_gt[:500],
            "translation":    translation[:500],
            "summary_formal": summary_formal[:300],
            "bleu":           bleu,
            "elapsed_sec":    elapsed,
        })

        if i % 50 == 0 or i == total:
            with open(out_csv, encoding="utf-8-sig") as f:
                rows = list(csv.DictReader(f))
            vals = [float(r["bleu"]) for r in rows if r["bleu"]]
            avg = sum(vals) / len(vals) if vals else 0.0
            print(f"  [{i}/{total}] BLEU 누적 평균: {avg:.2f}")

    print(f"추론 완료 → {out_csv}")


# ══════════════════════════════════════════════════════════
# 4. 파인튜닝
# ══════════════════════════════════════════════════════════

def finetune(model, tokenizer, train_data: list[dict], num_epochs: int, resume: bool = False):
    from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
    from trl import SFTTrainer, SFTConfig
    from transformers import TrainerCallback
    from datasets import Dataset

    print(f"\n[파인튜닝] epochs={num_epochs}, resume={resume}")

    model = prepare_model_for_kbit_training(model)
    lora_config = LoraConfig(**LORA_CONFIG)
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()

    formatted = [{"text": tokenizer.apply_chat_template(
        item["messages"], tokenize=False, add_generation_prompt=False
    )} for item in train_data]
    dataset = Dataset.from_list(formatted)

    # 학습 로그 콜백
    class CsvLogCallback(TrainerCallback):
        def on_log(self, args, state, control, logs=None, **kwargs):
            if logs and "loss" in logs:
                append_csv(TRAINING_LOG, {
                    "step":          state.global_step,
                    "loss":          round(logs.get("loss", 0), 4),
                    "learning_rate": logs.get("learning_rate", 0),
                    "epoch":         round(logs.get("epoch", 0), 2),
                    "timestamp":     datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                })

    if not resume:
        init_csv(TRAINING_LOG, ["step", "loss", "learning_rate", "epoch", "timestamp"])

    config = {**TRAIN_CONFIG, "num_train_epochs": num_epochs}
    sft_config = SFTConfig(max_seq_length=MAX_SEQ_LEN, **config)

    trainer = SFTTrainer(
        model=model,
        tokenizer=tokenizer,
        train_dataset=dataset,
        args=sft_config,
        callbacks=[CsvLogCallback()],
    )

    # 체크포인트 이어받기
    checkpoint = find_latest_checkpoint(CKPT_DIR) if resume else None
    if checkpoint:
        print(f"체크포인트 이어받기: {checkpoint}")
    trainer.train(resume_from_checkpoint=checkpoint)

    trainer.save_model(OUTPUT_DIR)
    tokenizer.save_pretrained(OUTPUT_DIR)
    print(f"모델 저장 완료: {OUTPUT_DIR}")
    return model


# ══════════════════════════════════════════════════════════
# 5. 세션별 실행
# ══════════════════════════════════════════════════════════

def session_1():
    """Session 1 — epoch 1 학습 (8~10시간 예상)"""
    print("=" * 60)
    print("SESSION 1: epoch 1 학습 시작")
    print("=" * 60)

    train_data = load_jsonl(TRAIN_JSONL)
    print(f"trainset: {len(train_data)}건\n")

    model, tokenizer = load_base_model(MODEL_ID)
    finetune(model, tokenizer, train_data, num_epochs=1, resume=False)

    print("\nSession 1 완료. 체크포인트 저장됨.")
    print(f"다음 세션: SESSION = 2 로 변경 후 실행")


def session_2():
    """Session 2 — epoch 2~3 이어받기 (8~10시간 예상)"""
    print("=" * 60)
    print("SESSION 2: epoch 2~3 이어받기 학습")
    print("=" * 60)

    ckpt = find_latest_checkpoint(CKPT_DIR)
    if not ckpt:
        print("오류: 체크포인트 없음. Session 1을 먼저 실행하세요.")
        return

    print(f"이어받을 체크포인트: {ckpt}")
    train_data = load_jsonl(TRAIN_JSONL)
    print(f"trainset: {len(train_data)}건\n")

    model, tokenizer = load_base_model(MODEL_ID)
    finetune(model, tokenizer, train_data, num_epochs=3, resume=True)

    print("\nSession 2 완료. 파인튜닝 최종 모델 저장됨.")
    print(f"다음 세션: SESSION = 3 으로 변경 후 실행")


def session_3():
    """Session 3 — 파인튜닝 후 추론 + BLEU 비교 (2~3시간 예상)"""
    print("=" * 60)
    print("SESSION 3: 파인튜닝 후 추론 및 평가")
    print("=" * 60)

    if not os.path.exists(OUTPUT_DIR):
        print("오류: 파인튜닝 모델 없음. Session 1~2를 먼저 실행하세요.")
        return

    test_data = load_jsonl(TEST_JSONL)
    print(f"testset: {len(test_data)}건\n")

    model, tokenizer = load_finetuned_model(OUTPUT_DIR)
    run_inference(model, tokenizer, test_data, AFTER_CSV)

    # BLEU 비교 출력
    with open(AFTER_CSV, encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    after_bleu = sum(float(r["bleu"]) for r in rows if r["bleu"]) / len(rows)

    print("\n" + "=" * 40)
    print("최종 결과")
    print("=" * 40)
    print(f"파인튜닝 전 BLEU (로컬 결과): 1.57")
    print(f"파인튜닝 후 BLEU:             {after_bleu:.2f}")
    print(f"BLEU 개선:                   +{after_bleu - 1.57:.2f}")
    print(f"\n저장 파일: {AFTER_CSV}")


# ══════════════════════════════════════════════════════════
# 6. 메인
# ══════════════════════════════════════════════════════════

if __name__ == "__main__":
    print(f"GPU: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU'}")
    print(f"VRAM: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f}GB\n" if torch.cuda.is_available() else "")

    if SESSION == 1:
        session_1()
    elif SESSION == 2:
        session_2()
    elif SESSION == 3:
        session_3()
    else:
        print("SESSION 값을 1, 2, 3 중 하나로 설정하세요.")
