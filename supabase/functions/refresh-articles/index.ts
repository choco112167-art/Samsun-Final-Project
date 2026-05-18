import { createHash } from "node:crypto";
import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

type RefreshMode = "queue" | "direct";

type FeedConfig = {
  source: string;
  url: string;
  country: string;
  category: string;
  source_type: "media" | "community";
  ai_only: boolean;
};

type FeedArticle = {
  title: string;
  url: string;
  source: string;
  source_type: "media" | "community";
  category: string;
  country: string;
  published_at: string;
  content: string;
};

type AiOutput = {
  title: string;
  translation: string;
  summary_formal: string;
  summary_casual: string;
};

const jsonHeaders = {
  "Content-Type": "application/json",
};

const feeds: FeedConfig[] = [
  {
    source: "TechCrunch",
    url: "https://techcrunch.com/category/artificial-intelligence/feed/",
    country: "미국",
    category: "AI/스타트업",
    source_type: "media",
    ai_only: true,
  },
  {
    source: "MIT Technology Review",
    url: "https://www.technologyreview.com/feed/",
    country: "미국",
    category: "AI 심층",
    source_type: "media",
    ai_only: false,
  },
  {
    source: "The Verge",
    url: "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml",
    country: "미국",
    category: "테크 전반",
    source_type: "media",
    ai_only: true,
  },
  {
    source: "VentureBeat AI",
    url: "https://venturebeat.com/feed",
    country: "미국",
    category: "AI 비즈니스",
    source_type: "media",
    ai_only: false,
  },
  {
    source: "The Guardian Tech",
    url: "https://www.theguardian.com/technology/artificialintelligenceai/rss",
    country: "영국",
    category: "AI 윤리",
    source_type: "media",
    ai_only: true,
  },
  {
    source: "IEEE Spectrum",
    url: "https://spectrum.ieee.org/feeds/topic/artificial-intelligence.rss",
    country: "글로벌",
    category: "AI/반도체",
    source_type: "media",
    ai_only: true,
  },
  {
    source: "The Decoder",
    url: "https://the-decoder.com/feed/",
    country: "독일/글로벌",
    category: "AI 심층/기술",
    source_type: "media",
    ai_only: true,
  },
  {
    source: "Hacker News AI",
    url: "https://hnrss.org/newest?q=artificial+intelligence",
    country: "글로벌",
    category: "AI 커뮤니티",
    source_type: "community",
    ai_only: true,
  },
  {
    source: "Hacker News LLM",
    url: "https://hnrss.org/newest?q=LLM",
    country: "글로벌",
    category: "LLM 커뮤니티",
    source_type: "community",
    ai_only: true,
  },
];

const aiKeywords = [
  "ai",
  "artificial intelligence",
  "machine learning",
  "llm",
  "large language model",
  "openai",
  "chatgpt",
  "anthropic",
  "claude",
  "gemini",
  "deepmind",
  "nvidia",
  "gpu",
  "agent",
  "robot",
  "model",
  "neural",
];

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), { status, headers: jsonHeaders });
}

function decodeXml(value: string): string {
  return value
    .replace(/<!\[CDATA\[([\s\S]*?)\]\]>/g, "$1")
    .replace(/&amp;/g, "&")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'")
    .replace(/&#x27;/g, "'")
    .trim();
}

function stripHtml(value: string): string {
  return decodeXml(value)
    .replace(/<script[\s\S]*?<\/script>/gi, " ")
    .replace(/<style[\s\S]*?<\/style>/gi, " ")
    .replace(/<[^>]+>/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function tag(block: string, name: string): string {
  const escaped = name.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const match = block.match(new RegExp(`<${escaped}(?:\\s[^>]*)?>([\\s\\S]*?)<\\/${escaped}>`, "i"));
  return match ? decodeXml(match[1]) : "";
}

function atomLink(block: string): string {
  const alternate = block.match(/<link[^>]+rel=["']alternate["'][^>]+href=["']([^"']+)["'][^>]*>/i);
  if (alternate) return decodeXml(alternate[1]);
  const href = block.match(/<link[^>]+href=["']([^"']+)["'][^>]*>/i);
  return href ? decodeXml(href[1]) : "";
}

function normalizeDate(value: string): string {
  const parsed = value ? new Date(value) : new Date();
  if (Number.isNaN(parsed.getTime())) return new Date().toISOString();
  return parsed.toISOString();
}

function isAiRelated(article: FeedArticle): boolean {
  const haystack = `${article.title} ${article.content}`.toLowerCase();
  return aiKeywords.some((keyword) => haystack.includes(keyword));
}

function parseFeed(xml: string, config: FeedConfig): FeedArticle[] {
  const blocks = [...xml.matchAll(/<item[\s\S]*?<\/item>/gi)].map((match) => match[0]);
  const entries = blocks.length > 0
    ? blocks
    : [...xml.matchAll(/<entry[\s\S]*?<\/entry>/gi)].map((match) => match[0]);

  const articles = entries.map((entry) => {
    const title = stripHtml(tag(entry, "title"));
    const url = tag(entry, "link") || atomLink(entry);
    const content = stripHtml(
      tag(entry, "content:encoded") ||
        tag(entry, "content") ||
        tag(entry, "description") ||
        tag(entry, "summary"),
    );
    const published_at = normalizeDate(
      tag(entry, "pubDate") || tag(entry, "published") || tag(entry, "updated") || tag(entry, "dc:date"),
    );
    return {
      title,
      url,
      source: config.source,
      source_type: config.source_type,
      category: config.category,
      country: config.country,
      published_at,
      content,
    };
  }).filter((article) => article.title && article.url);

  return config.ai_only ? articles : articles.filter(isAiRelated);
}

async function fetchText(url: string, timeoutMs: number): Promise<string> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(url, {
      signal: controller.signal,
      headers: {
        "User-Agent": "samsun-news-edge-refresh/1.0",
        "Accept": "text/html,application/rss+xml,application/xml,text/xml;q=0.9,*/*;q=0.8",
      },
    });
    if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
    return await response.text();
  } finally {
    clearTimeout(timer);
  }
}

async function crawlArticleText(article: FeedArticle): Promise<string> {
  try {
    const html = await fetchText(article.url, 12000);
    const main =
      html.match(/<article[\s\S]*?<\/article>/i)?.[0] ||
      html.match(/<main[\s\S]*?<\/main>/i)?.[0] ||
      html;
    const text = stripHtml(main);
    if (text.length >= 500) return text.slice(0, 14000);
  } catch {
    // RSS summary fallback below.
  }
  return (article.content || article.title).slice(0, 8000);
}

async function collectArticles(limit: number): Promise<FeedArticle[]> {
  const out: FeedArticle[] = [];
  for (const feed of feeds) {
    if (out.length >= limit) break;
    try {
      const xml = await fetchText(feed.url, 12000);
      out.push(...parseFeed(xml, feed));
    } catch (error) {
      console.warn(`[feed] ${feed.source} failed: ${error instanceof Error ? error.message : String(error)}`);
    }
  }
  return out
    .sort((a, b) => new Date(b.published_at).getTime() - new Date(a.published_at).getTime())
    .slice(0, limit);
}

function summarySentences(text: string, max = 3): number {
  const count = text.trim().split(/(?<=[a-zA-Z]{2})[.!?]\s+/).filter(Boolean).length;
  return Math.min(Math.max(count, 1), max);
}

function systemPrompt(lines: number): string {
  return `You are a professional Korean news translator and summarizer.
Return ONLY valid JSON with these required keys:
{
  "title": "<Korean headline>",
  "translation": "<full Korean translation of the BODY, not a summary>",
  "summary_formal": "1. <formal Korean summary sentence>\\n2. ...",
  "summary_casual": "1. <casual Korean summary sentence>\\n2. ..."
}
Rules:
- translation must cover the full BODY in Korean and preserve paragraph flow.
- summary_formal must contain exactly ${lines} numbered line(s), using formal tone (~습니다/~됩니다).
- summary_casual must contain exactly ${lines} numbered line(s), using casual polite tone (~해요/~예요).
- Do not add markdown or text outside JSON.
- Keep AI technical abbreviations like RAG, LLM, GPU, NPU, API, RLHF, SFT, LoRA, QLoRA in English.`;
}

function extractJsonObject(value: string): AiOutput {
  const cleaned = value.replace(/```json|```/gi, "").trim();
  const start = cleaned.indexOf("{");
  const end = cleaned.lastIndexOf("}");
  const jsonText = start >= 0 && end > start ? cleaned.slice(start, end + 1) : cleaned;
  const direct = JSON.parse(jsonText);
  return {
    title: String(direct.title ?? ""),
    translation: String(direct.translation ?? ""),
    summary_formal: String(direct.summary_formal ?? ""),
    summary_casual: String(direct.summary_casual ?? ""),
  };
}

async function translateWithOpenRouter(title: string, body: string, lines: number): Promise<AiOutput> {
  const apiKey = Deno.env.get("OPENROUTER_API_KEY") ?? "";
  if (!apiKey) throw new Error("missing_openrouter_api_key");
  const model = Deno.env.get("OPENROUTER_TRANSLATION_MODEL") ?? "google/gemini-2.5-flash";
  const response = await fetch("https://openrouter.ai/api/v1/chat/completions", {
    method: "POST",
    headers: {
      "Authorization": `Bearer ${apiKey}`,
      "Content-Type": "application/json",
      "HTTP-Referer": "https://samsun-news.supabase.co",
      "X-Title": "Samsun News",
    },
    body: JSON.stringify({
      model,
      messages: [
        { role: "system", content: systemPrompt(lines) },
        { role: "user", content: `[TITLE]\n${title}\n\n[BODY]\n${body}` },
      ],
      temperature: 0.1,
      max_tokens: 4096,
    }),
  });
  if (!response.ok) {
    throw new Error(`openrouter_${response.status}: ${await response.text()}`);
  }
  const jsonBody = await response.json();
  return extractJsonObject(jsonBody.choices?.[0]?.message?.content ?? "");
}

async function translateWithGemini(title: string, body: string, lines: number): Promise<AiOutput> {
  const apiKey = Deno.env.get("GEMINI_API_KEY") ?? Deno.env.get("GOOGLE_API_KEY") ?? "";
  if (!apiKey) throw new Error("missing_gemini_api_key");
  const model = Deno.env.get("GEMINI_TRANSLATION_MODEL") ?? "gemini-2.5-flash";
  const response = await fetch(
    `https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent?key=${apiKey}`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        systemInstruction: { parts: [{ text: systemPrompt(lines) }] },
        contents: [{ role: "user", parts: [{ text: `[TITLE]\n${title}\n\n[BODY]\n${body}` }] }],
        generationConfig: { temperature: 0.1, maxOutputTokens: 4096 },
      }),
    },
  );
  if (!response.ok) {
    throw new Error(`gemini_${response.status}: ${await response.text()}`);
  }
  const jsonBody = await response.json();
  const text = jsonBody.candidates?.[0]?.content?.parts?.map((part: { text?: string }) => part.text ?? "").join("") ?? "";
  return extractJsonObject(text);
}

async function translateArticle(title: string, body: string): Promise<AiOutput> {
  const lines = summarySentences(body, 3);
  const provider = (Deno.env.get("EDGE_LLM_PROVIDER") ?? Deno.env.get("LLM_PROVIDER") ?? "openrouter").toLowerCase();
  if (provider === "gemini") return translateWithGemini(title, body, lines);
  return translateWithOpenRouter(title, body, lines);
}

function detectTerms(text: string): string[] {
  const matches = text.match(/\b(?:[A-Z][A-Za-z0-9-]{2,}|[A-Z]{2,})(?:\s+(?:[A-Z][A-Za-z0-9-]{2,}|[A-Z]{2,})){0,3}\b/g) ?? [];
  return [...new Set(matches.filter((term) => term.length >= 3))].slice(0, 18);
}

function factLabel(article: FeedArticle): string {
  if (article.source_type === "media" && article.source !== "Hacker News AI") return "FACT";
  return "UNVERIFIED";
}

async function markRequest(
  supabase: ReturnType<typeof createClient>,
  requestId: string | null,
  status: "running" | "completed" | "failed",
  error?: string,
) {
  if (!requestId) return;
  const patch: Record<string, unknown> = { status };
  if (status === "running") patch.started_at = new Date().toISOString();
  if (status === "completed" || status === "failed") patch.finished_at = new Date().toISOString();
  if (error) patch.error = error.slice(0, 2000);
  await supabase.from("pipeline_refresh_requests").update(patch).eq("id", requestId);
}

async function createRequest(
  supabase: ReturnType<typeof createClient>,
  reason: string,
  requestedLimit: number,
  status: "queued" | "running",
): Promise<Record<string, unknown> | null> {
  const { data, error } = await supabase
    .from("pipeline_refresh_requests")
    .insert({
      reason,
      requested_limit: requestedLimit,
      status,
      started_at: status === "running" ? new Date().toISOString() : null,
    })
    .select("id, reason, requested_limit, status, requested_at")
    .single();
  if (error) throw error;
  return data;
}

async function availableArticleColumns(supabase: ReturnType<typeof createClient>): Promise<Set<string>> {
  const base = new Set([
    "url_hash",
    "url",
    "title",
    "title_ko",
    "source",
    "source_type",
    "category",
    "country",
    "keywords",
    "published_at",
    "collected_at",
    "content",
    "credibility_score",
    "fact_label",
    "translation",
    "summary_formal",
    "summary_casual",
  ]);
  const optional = [
    "source_url",
    "crawled_text",
    "slang_terms",
    "neologism_terms",
    "slang_processed_at",
    "fact_status",
    "updated_at",
    "ai_status",
    "ai_provider",
    "ai_model",
    "ai_generated_at",
    "ai_error",
    "content_source",
    "content_chars",
    "translation_chars",
  ];
  for (const column of optional) {
    const { error } = await supabase.from("articles").select(column).limit(1);
    if (!error) base.add(column);
  }
  return base;
}

function stripUnavailableColumns(row: Record<string, unknown>, columns: Set<string>): Record<string, unknown> {
  return Object.fromEntries(Object.entries(row).filter(([key]) => columns.has(key)));
}

async function runDirectRefresh(
  supabase: ReturnType<typeof createClient>,
  reason: string,
  requestedLimit: number,
) {
  const limit = Math.min(Math.max(requestedLimit, 1), 5);
  const request = await createRequest(supabase, reason, limit, "running");
  const requestId = typeof request?.id === "string" ? request.id : null;
  const errors: string[] = [];
  let saved = 0;

  try {
    const collected = await collectArticles(limit);
    const columns = await availableArticleColumns(supabase);
    const rows = [];
    const neologismRows = [];

    for (const article of collected) {
      try {
        const body = await crawlArticleText(article);
        const processed = await translateArticle(article.title, body);
        const urlHash = createHash("md5").update(article.url).digest("hex");
        const terms = detectTerms(`${article.title}\n${body}\n${processed.translation}`);
        rows.push(stripUnavailableColumns({
          url_hash: urlHash,
          url: article.url,
          source_url: article.url,
          title: article.title,
          title_ko: processed.title || null,
          source: article.source,
          source_type: article.source_type,
          category: article.category,
          country: article.country,
          keywords: terms,
          published_at: article.published_at,
          collected_at: new Date().toISOString(),
          content: body,
          crawled_text: body,
          credibility_score: factLabel(article) === "FACT" ? 0.85 : 0.5,
          fact_label: factLabel(article),
          fact_status: factLabel(article),
          translation: processed.translation,
          summary_formal: processed.summary_formal,
          summary_casual: processed.summary_casual,
          slang_terms: terms,
          neologism_terms: terms,
          slang_processed_at: new Date().toISOString(),
          ai_status: "completed",
          ai_provider: (Deno.env.get("EDGE_LLM_PROVIDER") ?? Deno.env.get("LLM_PROVIDER") ?? "openrouter").toLowerCase(),
          ai_model: Deno.env.get("OPENROUTER_TRANSLATION_MODEL") ?? Deno.env.get("GEMINI_TRANSLATION_MODEL") ?? null,
          ai_generated_at: new Date().toISOString(),
          ai_error: null,
          content_source: "edge_direct_refresh",
          content_chars: body.length,
          translation_chars: processed.translation.length,
          updated_at: new Date().toISOString(),
        }, columns));
        for (const term of terms) {
          neologismRows.push({
            term,
            first_seen_url_hash: urlHash,
            occurrence_count: 1,
            confirmed: false,
            created_at: new Date().toISOString(),
          });
        }
      } catch (error) {
        errors.push(`${article.source}: ${article.title.slice(0, 80)}: ${error instanceof Error ? error.message : String(error)}`);
      }
    }

    if (rows.length > 0) {
      const { error } = await supabase.from("articles").upsert(rows, { onConflict: "url_hash" });
      if (error) throw error;
      saved = rows.length;
    }

    if (neologismRows.length > 0) {
      await supabase.from("neologisms").upsert(neologismRows, { onConflict: "term", ignoreDuplicates: true });
    }

    await markRequest(supabase, requestId, errors.length === collected.length ? "failed" : "completed", errors.join("\n"));

    const newest = await supabase
      .from("articles")
      .select("published_at,collected_at")
      .order("published_at", { ascending: false })
      .limit(1)
      .maybeSingle();

    return {
      mode: "direct",
      request,
      requested_limit: requestedLimit,
      effective_limit: limit,
      collected: collected.length,
      saved,
      errors,
      newest: newest.data ?? null,
    };
  } catch (error) {
    await markRequest(supabase, requestId, "failed", error instanceof Error ? error.message : String(error));
    throw error;
  }
}

Deno.serve(async (req) => {
  if (req.method !== "POST") {
    return json({ error: "method_not_allowed" }, 405);
  }

  const refreshSecret = Deno.env.get("REFRESH_SECRET") ?? "";
  const auth = req.headers.get("Authorization") ?? "";
  if (!refreshSecret || auth !== `Bearer ${refreshSecret}`) {
    return json({ error: "unauthorized" }, 401);
  }

  const supabaseUrl = Deno.env.get("SUPABASE_URL") ?? "";
  const serviceRoleKey = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY") ?? "";
  if (!supabaseUrl || !serviceRoleKey) {
    return json({ error: "missing_supabase_function_secrets" }, 500);
  }

  const body = await req.json().catch(() => ({}));
  const requestedLimit = Math.min(Math.max(Number(body.limit ?? 10), 1), 100);
  const reason = String(body.reason ?? "manual").slice(0, 200);
  const mode = String(body.mode ?? Deno.env.get("REFRESH_MODE") ?? "queue").toLowerCase() as RefreshMode;

  const supabase = createClient(supabaseUrl, serviceRoleKey, {
    auth: { persistSession: false },
  });

  try {
    if (mode === "direct") {
      const result = await runDirectRefresh(supabase, reason, requestedLimit);
      return json(result, 200);
    }

    const request = await createRequest(supabase, reason, requestedLimit, "queued");
    return json({ mode: "queue", queued: true, request }, 202);
  } catch (error) {
    return json({ error: error instanceof Error ? error.message : String(error) }, 500);
  }
});
