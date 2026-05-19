# Final Architecture

Samsun News is an Apps in Toss `.ait` mini-app backed by Supabase. The frontend does not call a custom production server.

```mermaid
flowchart TD
  subgraph Sources
    RSS["RSS Feeds"]
    SQLite["Sangjun SQLite DB<br/>May 1-May 18 only"]
    DemoSeed["Safe DEMO Seed<br/>rumor/unverified/HITL"]
  end

  subgraph LocalProcessing["Local Processing / Demo Backfill"]
    AuditSQLite["audit_sangjun_sqlite.py"]
    Ollama["Ollama<br/>samsun-gemma4"]
    ProcessSQLite["process_sangjun_sqlite_with_ollama.py"]
  end

  subgraph CloudRefresh["Cloud Refresh"]
    Cron["Supabase Cron"]
    Edge["Supabase Edge Function"]
    CloudLLM["OpenRouter / Gemini"]
  end

  subgraph AIStages["AI Preprocessing"]
    Crawl["Crawling / Body Extraction"]
    Preprocess["Preprocessing<br/>quality/date filtering"]
    Translate["Korean title + full translation"]
    Summaries["Formal + casual 3-line summaries"]
    Fact["Fact status<br/>verified/unverified/rumor/HITL"]
    Neo["Neologism detection"]
  end

  subgraph Supabase["Supabase"]
    Articles["articles"]
    Embedding["embedding vector(1024)"]
    Users["users.user_vector"]
    FactChecks["fact_checks"]
    Neologisms["neologisms"]
    DemoFields["demo readiness fields<br/>is_hidden/demo_visible/demo_priority"]
  end

  subgraph RagPoc["Personalized Recommendation"]
    QwenEmbedding["Qwen3-Embedding-0.6B<br/>via Ollama"]
    MatchArticles["match_articles RPC<br/>pgvector candidates"]
    ClickUpdate["click log<br/>user_vector update"]
    FallbackRecommend["interest/recent-click<br/>fallback"]
    OptionalRerank["optional Gemma4/OpenRouter<br/>LLM rerank extension"]
  end

  subgraph App["Apps in Toss .ait Frontend"]
    Feed["Korean-first feed"]
    Detail["Detail page<br/>translation/source"]
    Tone["Tone preference<br/>localStorage"]
    Badges["Fact badges + trust UI"]
    NeoUI["Neologism bottom sheet"]
  end

  RSS --> Crawl --> Preprocess --> CloudRefresh
  Cron --> Edge --> CloudLLM --> Translate
  CloudLLM --> Summaries
  CloudLLM --> Fact
  SQLite --> AuditSQLite --> ProcessSQLite --> Ollama
  Ollama --> Translate
  Ollama --> Summaries
  Ollama --> Fact
  Translate --> Articles
  Summaries --> Articles
  Fact --> Articles
  Fact --> FactChecks
  Neo --> Neologisms
  QwenEmbedding --> Embedding
  Articles --> MatchArticles
  Users --> MatchArticles
  MatchArticles --> OptionalRerank
  MatchArticles --> FallbackRecommend
  Articles --> ClickUpdate --> Users
  ProcessSQLite --> Articles
  DemoSeed --> Articles
  DemoSeed --> FactChecks
  DemoSeed --> Neologisms
  Articles --> Feed
  Articles --> Detail
  Articles --> Badges
  Neologisms --> NeoUI
  FactChecks --> Badges
  DemoFields --> Feed
```

## Runtime Boundaries

- `.ait` frontend: reads Supabase with anon key only, records onboarding interests and article clicks, and calls Supabase recommendation RPC when available.
- Supabase: production data platform and public read source.
- Local Ollama: demo/backfill only, running on the developer machine.
- Supabase Edge/Cron: cloud automation path using OpenRouter/Gemini, not local Ollama.
- Qwen3-Embedding-0.6B: article/user embedding model for pgvector recommendation through `backend/embedder.py`; article writes store 1024-dimensional vectors in `articles.embedding`.

## Embedding And RAG Implementation

- Schema: `supabase_schema.sql` creates `articles.embedding VECTOR(1024)`, `users.user_vector VECTOR(1024)`, and `match_articles(...)`.
- Embedding adapter: `backend/embedder.py` uses `LOCAL_EMBEDDING_MODEL=qwen3-embedding:0.6b` in local mode and fits all vectors to 1024 dimensions.
- Article upsert: `backend/save_articles.py` embeds `title_ko + translation` and writes `articles.embedding`.
- Frontend recommendation: `frontend/src/data/api.ts` stores `interest_tags`, records `user_logs`, updates `users.user_vector` with `old*0.6 + clicked*0.4` when embeddings exist, calls `match_articles`, and falls back to interest/recent-click/latest article ranking.
- Admin endpoints: `backend/main.py` exposes `/onboarding`, `/feed/{user_id}`, and `/users/{user_id}/click/{url_hash}` for local/admin testing.
- Optional reranking: `backend/rag.py` has a disabled-by-default reranking hook. Final demo messaging should describe it as a Gemma4/OpenRouter extension, not the default path.

## HITL Path

When an article contains ambiguous claims or insufficient evidence, the pipeline can mark:
- `fact_label=HITL_REQUIRED`
- `hitl_required=true` if the optional column exists

The UI displays this as `HITL 검토 필요`, signaling that human review is required before treating the item as verified.
