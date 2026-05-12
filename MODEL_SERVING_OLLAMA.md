# Gemma 4 E4B Local Serving

Last checked: 2026-05-12

## Current Model State

The public Hugging Face repository [`mingyu3939/gemma4-e4b-6ep-samsun-lora`](https://huggingface.co/mingyu3939/gemma4-e4b-6ep-samsun-lora) is a PEFT/LoRA adapter, not a merged full model. The model card states that it was fine-tuned from `unsloth/gemma-4-e4b-it-unsloth-bnb-4bit` and that users must load it with the base model.

That means there are two valid local serving paths:

1. **Transformers/PEFT server**: load base model + LoRA adapter in Python and expose `/generate`.
2. **Ollama GGUF server**: merge adapter into the base model, quantize/export to GGUF, then register it in Ollama.

Do not put model files inside `frontend/` or the `.ait` bundle.

## Ollama GGUF Path

If a merged GGUF exists at `models/samsun-gemma4-q8_0.gguf`, create:

```text
FROM ./models/samsun-gemma4-q8_0.gguf
TEMPLATE """{{ .Prompt }}"""
PARAMETER temperature 0.2
PARAMETER num_ctx 4096
```

Save it as `Modelfile`, then run:

```bash
ollama create gemma4-e4b-samsun -f Modelfile
ollama run gemma4-e4b-samsun
```

Check:

```bash
ollama list
```

Backend/batch env:

```text
LOCAL_LLM_CONFIGURED=1
OLLAMA_BASE_URL=http://localhost:11434
MODEL_NAME=gemma4-e4b-samsun
```

One-article test:

```bash
python scripts/backfill_article_ai_outputs.py --limit 1 --provider local --model gemma4-e4b-samsun --run
```

## Transformers / PEFT Server Path

If only the LoRA adapter exists, serve it from Python instead of Ollama.

Minimal contract expected by the batch script:

```text
POST <LOCAL_LLM_ENDPOINT>
{
  "model": "gemma4-e4b-samsun",
  "prompt": "...",
  "text": "...",
  "max_tokens": 4096
}
```

The response should include one of:

```json
{"text": "..."}
```

or

```json
{"translation": "...", "summary_formal": "...", "summary_casual": "..."}
```

Backend/batch env:

```text
LOCAL_LLM_CONFIGURED=1
LOCAL_LLM_ENDPOINT=http://localhost:8001/generate
MODEL_NAME=gemma4-e4b-samsun
```

One-article test:

```bash
python scripts/backfill_article_ai_outputs.py --limit 1 --provider local --model gemma4-e4b-samsun --run
```

## External Access For Demo

If the model is on a local GPU machine but the FastAPI backend runs elsewhere, expose only the backend-to-model route:

```bash
ngrok http 11434
```

or use Cloudflare Tunnel.

Set:

```text
OLLAMA_BASE_URL=https://<tunnel-domain>
```

The frontend must not call Ollama, OpenRouter, Gemini, or a model tunnel directly. It only reads stored `translation`, `summary_formal`, and `summary_casual` from the backend/Supabase path.

## Fallback Policy

Provider behavior must stay explicit:

| Provider | Behavior |
| --- | --- |
| `local` | Use `LOCAL_LLM_ENDPOINT` or `OLLAMA_BASE_URL`; fail with `local provider not configured` if not configured. |
| `openrouter` | Use only `OPENROUTER_API_KEY`. |
| `gemini` | Use only `GOOGLE_API_KEY` or `GEMINI_API_KEY`. |
| `mock` | Generate obvious `[MOCK ...]` test output for DB pipeline checks only. |

`provider=local` must never silently call OpenRouter or Gemini. For demos, use mock fallback only to keep screens alive when the API is unavailable, and clear mock DB outputs before showing real article details.
