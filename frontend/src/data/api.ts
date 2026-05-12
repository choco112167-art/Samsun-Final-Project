import { supabase, isSupabaseConfigured } from '../lib/supabase';
import { toArticle, normalizeCategory } from './articles';
import type { Article } from './articles';

/**
 * Samsun News frontend data adapter.
 *
 * Runtime policy:
 * - No Railway/FastAPI dependency in the Apps in Toss bundle.
 * - No live LLM calls from the frontend.
 * - Read public article rows from Supabase with the anon key only.
 * - If Supabase is unavailable, keep the presentation alive with dev mock data.
 */

const ARTICLE_FIELDS = [
  'url_hash',
  'url',
  'title',
  'title_ko',
  'source',
  'source_type',
  'category',
  'country',
  'keywords',
  'published_at',
  'collected_at',
  'content',
  'credibility_score',
  'fact_label',
  'translation',
  'summary_formal',
  'summary_casual',
  'is_breaking',
].join(',');

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
    this.name = 'ApiError';
  }
}

export interface ApiArticle {
  id?: string | number;
  url_hash: string;
  url: string;
  title: string;
  title_ko?: string;
  source: string;
  source_type: 'media' | 'community';
  category: string;
  country: string;
  keywords: string[];
  published_at: string;
  collected_at: string;
  content: string;
  credibility_score: number;
  fact_label: 'FACT' | 'UNVERIFIED' | 'RUMOR';
  translation: string;
  summary_formal: string;
  summary_casual: string;
  ai_status?: 'pending' | 'processing' | 'completed' | 'failed' | 'skipped';
  ai_provider?: 'mock' | 'openrouter' | 'gemini' | 'local' | string;
  ai_model?: string;
  ai_generated_at?: string;
  ai_error?: string;
  is_new: boolean;
  is_breaking: boolean;
  time_ago: string;
  source_color: string;
}

export interface FetchArticlesParams {
  category?: string;
  source?: string;
  source_type?: 'media' | 'community';
  limit?: number;
  offset?: number;
  is_breaking?: boolean;
}

export interface OnboardingRequest { user_id: string; interest_tags: string[]; }
export interface OnboardingResponse { message: string; }
export interface FeedArticle extends ApiArticle { similarity?: number; reason?: string }
export interface SearchResult extends ApiArticle { similarity?: number; }

async function withMockFallback<T>(
  path: string,
  method: string,
  work: () => Promise<T>,
): Promise<T> {
  try {
    if (!isSupabaseConfigured()) {
      throw new ApiError(0, 'Supabase env is not configured');
    }
    return await work();
  } catch (err) {
    try {
      const mod = await import('./mock-articles');
      const fallback = mod.getMockFallback<T>(path, method);
      if (fallback !== undefined) {
        const reason = err instanceof Error ? err.message : 'Supabase query failed';
        console.warn(`[api] mock fallback for ${method} ${path} (${reason})`);
        return fallback;
      }
    } catch {
      // ignore mock import failure and rethrow the original error
    }
    throw err;
  }
}

function buildArticleQuery(params: FetchArticlesParams = {}) {
  let query = supabase
    .from('articles')
    .select(ARTICLE_FIELDS)
    .order('published_at', { ascending: false });

  if (params.source) query = query.eq('source', params.source);
  if (params.source_type) query = query.eq('source_type', params.source_type);
  if (params.is_breaking !== undefined) query = query.eq('is_breaking', params.is_breaking);

  const limit = params.limit ?? 20;
  const offset = params.offset ?? 0;
  query = query.range(offset, offset + Math.max(limit, 1) - 1);
  return query;
}

function toArticleList(rows: ApiArticle[] | null): Article[] {
  return (rows ?? []).map(toArticle);
}

function queryString(params: object): string {
  const qs = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') qs.set(key, String(value));
  });
  return qs.toString();
}

export async function fetchArticles(params: FetchArticlesParams = {}): Promise<Article[]> {
  const query = queryString(params);
  return withMockFallback<ApiArticle[]>(
    `/articles${query ? `?${query}` : ''}`,
    'GET',
    async () => {
      const { data, error } = await buildArticleQuery(params);
      if (error) throw new ApiError(500, error.message);
      const articles = toArticleList(data as unknown as ApiArticle[]);
      const filtered = params.category
        ? articles.filter(article => article.category === normalizeCategory(params.category))
        : articles;
      return filtered.map(article => articleToApiLike(article));
    },
  ).then(toArticleList);
}

export async function fetchArticleByHash(urlHash: string): Promise<ApiArticle> {
  return withMockFallback<ApiArticle>(
    `/article/${urlHash}`,
    'GET',
    async () => {
      const { data, error } = await supabase
        .from('articles')
        .select(ARTICLE_FIELDS)
        .eq('url_hash', urlHash)
        .maybeSingle();
      if (error) throw new ApiError(500, error.message);
      if (!data) throw new ApiError(404, 'Article not found');
      return data as unknown as ApiArticle;
    },
  );
}

export async function postOnboarding(userId: string, interestTags: string[]): Promise<OnboardingResponse> {
  try {
    localStorage.setItem(`samsun_interests_${userId}`, JSON.stringify(interestTags));
  } catch {
    // local persistence is a convenience only
  }
  return { message: 'saved locally' };
}

function scoreByInterests(article: Article, interests: string[]): number {
  if (interests.length === 0) return article.credibilityScore || 0.1;
  const haystack = `${article.category} ${article.title} ${article.titleKo ?? ''} ${article.summaryFormal}`.toLowerCase();
  const matches = interests.filter(interest => haystack.includes(interest.toLowerCase())).length;
  return matches + (article.credibilityScore || 0);
}

export async function fetchFeed(
  userId: string,
  topK = 10,
): Promise<(Article & { similarity?: number; reason?: string })[]> {
  return withMockFallback<{ feed: FeedArticle[] }>(
    `/feed/${encodeURIComponent(userId)}?top_k=${topK}`,
    'GET',
    async () => {
      let interests: string[] = [];
      try {
        interests = JSON.parse(localStorage.getItem('samsun_interests') ?? '[]');
      } catch {
        interests = [];
      }
      const articles = await fetchArticles({ limit: Math.max(topK * 4, 40) });
      const ranked = articles
        .map(article => ({
          ...article,
          similarity: Math.min(1, scoreByInterests(article, interests) / 2),
          reason: interests.length ? '관심 주제와 제목/요약이 가까운 기사입니다' : '최신 기사 기반 추천입니다',
        }))
        .sort((a, b) => (b.similarity ?? 0) - (a.similarity ?? 0))
        .slice(0, topK);
      return { feed: ranked.map(article => articleToApiLike(article, article.similarity, article.reason)) };
    },
  ).then(res => (res.feed ?? []).map(f => ({
    ...toArticle(f),
    similarity: f.similarity,
    ...(f.reason ? { reason: f.reason } : {}),
  })));
}

function normalizeSearchText(value: string): string {
  return value
    .normalize('NFKC')
    .toLowerCase()
    .replace(/[^\p{L}\p{N}]+/gu, ' ')
    .trim();
}

function articleSearchScore(article: Article, query: string): number {
  const q = normalizeSearchText(query);
  const tokens = q.split(/\s+/).filter(Boolean);
  const haystack = normalizeSearchText([
    article.title,
    article.titleKo,
    article.source,
    article.category,
    article.summaryFormal,
    article.summaryCasual,
    article.translation,
    article.content,
    article.factLabel,
  ].join(' '));
  if (!q) return 0;
  if (haystack.includes(q)) return 1;
  const tokenHits = tokens.filter(token => haystack.includes(token)).length;
  return tokenHits / Math.max(tokens.length, 1);
}

export async function searchArticles(query: string, topK = 10): Promise<(Article & { similarity?: number })[]> {
  return withMockFallback<{ results: SearchResult[] }>(
    `/search?q=${encodeURIComponent(query)}&top_k=${topK}`,
    'GET',
    async () => {
      const articles = await fetchArticles({ limit: 250 });
      const results = articles
        .map(article => ({ article, similarity: articleSearchScore(article, query) }))
        .filter(item => item.similarity > 0)
        .sort((a, b) => b.similarity - a.similarity)
        .slice(0, topK)
        .map(item => articleToApiLike(item.article, item.similarity));
      return { results };
    },
  ).then(res => (res.results ?? []).map(r => ({ ...toArticle(r), similarity: r.similarity })));
}

export async function recordArticleView(userId: string, urlHash: string): Promise<void> {
  if (!userId?.trim() || !urlHash) return;
  try {
    const key = `samsun_view_log_${userId}`;
    const prev = JSON.parse(localStorage.getItem(key) ?? '[]') as string[];
    localStorage.setItem(key, JSON.stringify([urlHash, ...prev].slice(0, 200)));
  } catch {
    // no-op; runtime has no backend writer
  }
}

export async function healthCheck(): Promise<{ status: string }> {
  return withMockFallback<{ status: string }>('/health', 'GET', async () => {
    const { error } = await supabase.from('articles').select('url_hash').limit(1);
    if (error) throw new ApiError(500, error.message);
    return { status: 'ok' };
  });
}

export interface AbsenceArticle {
  url_hash: string;
  title: string;
  title_ko?: string;
  source: string;
  category: string;
  published_at: string;
  summary_formal: string;
  similarity: number;
  view_count?: number;
}

export interface AbsenceSummaryResponse {
  show: boolean;
  message?: string;
  sub_message?: string;
  days_away?: number;
  articles?: AbsenceArticle[];
}

export async function fetchAbsenceSummary(userId: string): Promise<AbsenceSummaryResponse> {
  return withMockFallback<AbsenceSummaryResponse>(
    `/absence-summary/${encodeURIComponent(userId)}`,
    'GET',
    async () => {
      const lastSeen = Number(localStorage.getItem(`samsun_last_seen_${userId}`) ?? '0');
      if (!lastSeen) return { show: false };
      const daysAway = Math.floor((Date.now() - lastSeen) / 86_400_000);
      if (daysAway < 1) return { show: false };
      const articles = await fetchArticles({ limit: 5 });
      return {
        show: articles.length > 0,
        message: `${daysAway}일 동안 놓친 AI 뉴스가 있어요`,
        sub_message: 'Supabase에 저장된 최신 요약을 모아봤어요',
        days_away: daysAway,
        articles: articles.map(article => ({
          url_hash: article.urlHash,
          title: article.title,
          title_ko: article.titleKo,
          source: article.source,
          category: article.category,
          published_at: article.publishedAt,
          summary_formal: article.summaryFormal,
          similarity: 0.7,
        })),
      };
    },
  );
}

export async function markUserSeen(userId: string): Promise<void> {
  try {
    localStorage.setItem(`samsun_last_seen_${userId}`, String(Date.now()));
  } catch {
    // no-op
  }
}

export async function logArticleView(userId: string, urlHash: string): Promise<void> {
  await recordArticleView(userId, urlHash);
}

export async function fetchHot(date: string): Promise<(Article & { view_count: number })[]> {
  return withMockFallback<(ApiArticle & { view_count: number })[]>(
    `/hot/${date}`,
    'GET',
    async () => {
      const start = `${date}T00:00:00`;
      const end = `${date}T23:59:59`;
      const { data, error } = await supabase
        .from('articles')
        .select(ARTICLE_FIELDS)
        .gte('published_at', start)
        .lte('published_at', end)
        .order('credibility_score', { ascending: false })
        .limit(20);
      if (error) throw new ApiError(500, error.message);
      return (data as unknown as ApiArticle[]).map((article, index) => ({
        ...article,
        view_count: Math.max(0, 100 - index * 7),
      }));
    },
  ).then(list => list.map(a => ({ ...toArticle(a), view_count: a.view_count ?? 0 })));
}

function articleToApiLike(article: Article, similarity?: number, reason?: string): SearchResult & { reason?: string } {
  return {
    url_hash: article.urlHash,
    url: article.url,
    title: article.title,
    title_ko: article.titleKo,
    source: article.source,
    source_type: article.sourceType,
    category: article.category,
    country: article.country,
    keywords: article.keywords,
    published_at: article.publishedAt,
    collected_at: article.publishedAt,
    content: article.content,
    credibility_score: article.credibilityScore,
    fact_label: article.factLabel,
    translation: article.translation,
    summary_formal: article.summaryFormal,
    summary_casual: article.summaryCasual,
    ai_status: article.aiStatus,
    ai_provider: article.aiProvider,
    ai_model: article.aiModel,
    ai_error: article.aiError,
    is_new: article.isNew,
    is_breaking: article.isBreaking,
    time_ago: article.timeAgo,
    source_color: article.sourceColor,
    similarity,
    reason,
  };
}
