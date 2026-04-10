/**
 * 삼선뉴스 — API 클라이언트
 *
 * 엔드포인트 맵 (app.py — SQLite 기반)
 *   GET  /articles              → fetchArticles()
 *   GET  /articles/:id          → fetchArticleById()
 *   POST /translation/          → translateArticle()
 *   POST /translation/both      → translateBoth()
 *   GET  /translation/health    → translationHealth()
 *
 * 엔드포인트 맵 (rag_app.py — Supabase RAG 기반)
 *   POST /onboarding            → postOnboarding()
 *   GET  /feed/:userId          → fetchFeed()
 *   GET  /search?q=             → searchArticles()
 */

const BASE_URL = (import.meta.env.VITE_API_BASE_URL as string | undefined)
  ?? 'http://localhost:8000';

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...init,
  });
  if (!res.ok) {
    const body = await res.text().catch(() => '');
    throw new ApiError(res.status, body || res.statusText);
  }
  return res.json() as Promise<T>;
}

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
    this.name = 'ApiError';
  }
}

// ─────────────────────────────────────────────
// 타입
// ─────────────────────────────────────────────

export interface ApiArticle {
  id:                  string;
  title:               string;
  url:                 string;
  source:              string;
  source_type:         'media' | 'community';
  category:            string;
  country:             string;
  published_at:        string;
  content:             string;
  credibility_score:   number;
  translation_formal:  string;
  translation_casual:  string;
  translation_llm:     string;
  summary_ko:          string;
  summary_llm:         string;
  fact_label:          'FACT' | 'UNVERIFIED' | 'RUMOR';

  // app.py row_to_dict가 추가로 내려주는 필드
  isNew:        boolean;
  isBreaking:   boolean;
  timeAgo:      string;
  sourceColor:  string;
  views:        number;
}

export interface FetchArticlesParams {
  category?:    string;
  source?:      string;
  source_type?: 'media' | 'community';
  limit?:       number;
  offset?:      number;
  is_breaking?: boolean;
}

export interface TranslateRequest  { text: string; style: 'formal' | 'casual'; }
export interface TranslateResponse { original: string; translated: string; style: 'formal' | 'casual'; model: string; }
export interface TranslateBothResponse { original: string; formal: string; casual: string; model: string; }
export interface TranslationHealth { status: 'ok' | 'error'; model: string; }

export interface OnboardingRequest  { user_id: string; interest_tags: string[]; }
export interface OnboardingResponse { message: string; }

export interface FeedArticle extends ApiArticle { similarity?: number; }
export interface SearchResult extends ApiArticle { similarity?: number; }

// ─────────────────────────────────────────────
// app.py 함수
// ─────────────────────────────────────────────

export async function fetchArticles(params: FetchArticlesParams = {}): Promise<ApiArticle[]> {
  const qs = new URLSearchParams();
  if (params.category)    qs.set('category',    params.category);
  if (params.source)      qs.set('source',      params.source);
  if (params.source_type) qs.set('source_type', params.source_type);
  if (params.limit)       qs.set('limit',       String(params.limit));
  if (params.offset)      qs.set('offset',      String(params.offset));
  if (params.is_breaking !== undefined) qs.set('is_breaking', String(params.is_breaking));
  const query = qs.toString() ? `?${qs}` : '';
  return request<ApiArticle[]>(`/articles${query}`);
}

export async function fetchArticleById(id: string): Promise<ApiArticle> {
  return request<ApiArticle>(`/articles/${id}`);
}

export async function translateArticle(text: string, style: 'formal' | 'casual'): Promise<TranslateResponse> {
  return request<TranslateResponse>('/translation/', {
    method: 'POST',
    body: JSON.stringify({ text, style } satisfies TranslateRequest),
  });
}

export async function translateBoth(text: string): Promise<TranslateBothResponse> {
  return request<TranslateBothResponse>('/translation/both', {
    method: 'POST',
    body: JSON.stringify({ text, style: 'formal' } satisfies TranslateRequest),
  });
}

export async function translationHealth(): Promise<TranslationHealth> {
  return request<TranslationHealth>('/translation/health');
}

// ─────────────────────────────────────────────
// RAG 함수 (rag_app.py)
// ─────────────────────────────────────────────

export async function postOnboarding(userId: string, interestTags: string[]): Promise<OnboardingResponse> {
  return request<OnboardingResponse>('/onboarding', {
    method: 'POST',
    body: JSON.stringify({ user_id: userId, interest_tags: interestTags } satisfies OnboardingRequest),
  });
}

export async function fetchFeed(userId: string, topK = 10): Promise<FeedArticle[]> {
  const res = await request<{ feed: FeedArticle[] }>(
    `/feed/${encodeURIComponent(userId)}?top_k=${topK}`,
  );
  return res.feed ?? [];
}

export async function searchArticles(query: string, topK = 10): Promise<SearchResult[]> {
  const res = await request<{ results: SearchResult[] }>(
    `/search?q=${encodeURIComponent(query)}&top_k=${topK}`,
  );
  return res.results ?? [];
}
