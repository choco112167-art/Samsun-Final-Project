# Final Architecture

Samsun News is an Apps in Toss `.ait` mini-app backed by Supabase. The frontend does not call Railway or a custom production server.

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
    FactChecks["fact_checks"]
    Neologisms["neologisms"]
    DemoFields["demo readiness fields<br/>is_hidden/demo_visible/demo_priority"]
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

- `.ait` frontend: reads Supabase with anon key only.
- Supabase: production data platform and public read source.
- Local Ollama: demo/backfill only, running on the developer machine.
- Supabase Edge/Cron: cloud automation path using OpenRouter/Gemini, not local Ollama.

## HITL Path

When an article contains ambiguous claims or insufficient evidence, the pipeline can mark:
- `fact_label=HITL_REQUIRED`
- `hitl_required=true` if the optional column exists

The UI displays this as `HITL 검토 필요`, signaling that human review is required before treating the item as verified.
