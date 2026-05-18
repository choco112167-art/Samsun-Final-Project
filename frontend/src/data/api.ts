import { supabase, isSupabaseConfigured, getSupabaseConfigIssue } from '../lib/supabase';
import {
  articleCompletenessScore,
  articleSummaryForTone,
  articleTranslationForDisplay,
  toArticle,
  normalizeCategory,
} from './articles';
import type { Article } from './articles';

/**
 * Samsun News frontend data adapter.
 *
 * Runtime policy:
 * - No Railway/FastAPI dependency in the Apps in Toss bundle.
 * - No live LLM calls from the frontend.
 * - Read public article rows from Supabase with the anon key only.
 * - If Supabase has no rows, return an empty list so the UI can show an empty state.
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
  source_url?: string;
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
  slang_terms?: string[];
  neologism_terms?: string[];
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

export interface NeologismEntry {
  term: string;
  explanation?: string | null;
  ko_suggestion?: string | null;
  occurrence_count?: number | null;
  confirmed?: boolean | null;
  first_seen_url_hash?: string | null;
}

export interface OnboardingRequest { user_id: string; interest_tags: string[]; }
export interface OnboardingResponse { message: string; }
export interface SearchResult extends ApiArticle { similarity?: number; }

function requireSupabase(): void {
  if (!isSupabaseConfigured()) {
    throw new ApiError(0, getSupabaseConfigIssue() ?? 'Supabase env is not configured');
  }
}

function supabaseErrorMessage(action: string, error: { message?: string; code?: string; details?: string; hint?: string }): string {
  const parts = [
    action,
    error.code ? `code=${error.code}` : '',
    error.message ?? '',
    error.details ? `details=${error.details}` : '',
    error.hint ? `hint=${error.hint}` : '',
  ].filter(Boolean);
  return parts.join(' · ');
}

function buildArticleQuery(params: FetchArticlesParams = {}) {
  let query = supabase
    .from('articles')
    .select(ARTICLE_FIELDS)
    .order('published_at', { ascending: false });

  if (params.source) query = query.eq('source', params.source);
  if (params.source_type) query = query.eq('source_type', params.source_type);

  const limit = params.limit ?? 20;
  const offset = params.offset ?? 0;
  query = query.range(offset, offset + Math.max(limit, 1) - 1);
  return query;
}

function toArticleList(rows: ApiArticle[] | null): Article[] {
  return (rows ?? []).map(toArticle);
}

function polishedFeedSort(a: Article, b: Article): number {
  const qualityDelta = articleCompletenessScore(b) - articleCompletenessScore(a);
  if (qualityDelta !== 0) return qualityDelta;
  return new Date(b.publishedAt).getTime() - new Date(a.publishedAt).getTime();
}

export async function fetchArticles(params: FetchArticlesParams = {}): Promise<Article[]> {
  requireSupabase();
  const { data, error } = await buildArticleQuery(params);
  if (error) throw new ApiError(500, supabaseErrorMessage('Supabase articles query failed', error));
  const articles = toArticleList(data as unknown as ApiArticle[]);
  if (import.meta.env.DEV) {
    console.info('[api] fetched articles', {
      count: articles.length,
      limit: params.limit ?? 20,
      offset: params.offset ?? 0,
      category: params.category ?? 'all',
    });
  }
  const filtered = params.category
    ? articles.filter(article => article.category === normalizeCategory(params.category))
    : articles;
  return filtered.sort(polishedFeedSort);
}

export async function fetchArticleByHash(urlHash: string): Promise<ApiArticle> {
  requireSupabase();
  const { data, error } = await supabase
    .from('articles')
    .select(ARTICLE_FIELDS)
    .eq('url_hash', urlHash)
    .maybeSingle();
  if (error) throw new ApiError(500, supabaseErrorMessage('Supabase article detail query failed', error));
  if (!data) throw new ApiError(404, 'Article not found');
  return data as unknown as ApiArticle;
}

export async function fetchArticleExtras(urlHash: string): Promise<Partial<ApiArticle>> {
  requireSupabase();
  const extras: Partial<ApiArticle> = {};

  const sourceResult = await supabase
    .from('articles')
    .select('source_url')
    .eq('url_hash', urlHash)
    .maybeSingle();
  if (!sourceResult.error && sourceResult.data) {
    extras.source_url = (sourceResult.data as Partial<ApiArticle>).source_url;
  } else if (sourceResult.error && import.meta.env.DEV) {
    console.warn('[api] optional source_url unavailable', sourceResult.error.message);
  }

  const slangResult = await supabase
    .from('articles')
    .select('slang_terms,neologism_terms')
    .eq('url_hash', urlHash)
    .maybeSingle();
  if (!slangResult.error && slangResult.data) {
    const data = slangResult.data as Partial<ApiArticle>;
    extras.slang_terms = data.slang_terms;
    extras.neologism_terms = data.neologism_terms;
  } else if (slangResult.error && import.meta.env.DEV) {
    console.warn('[api] optional slang fields unavailable', slangResult.error.message);
  }

  return extras;
}

export async function fetchNeologismDictionary(limit = 300): Promise<NeologismEntry[]> {
  requireSupabase();
  const { data, error } = await supabase
    .from('neologisms')
    .select('term,explanation,ko_suggestion,occurrence_count,confirmed,first_seen_url_hash')
    .not('explanation', 'is', null)
    .order('occurrence_count', { ascending: false })
    .limit(limit);
  if (error) {
    if (import.meta.env.DEV) {
      console.warn('[api] neologism dictionary unavailable', error.message);
    }
    return [];
  }
  return ((data ?? []) as NeologismEntry[]).filter(entry => entry.term?.trim() && entry.explanation?.trim());
}

export async function fetchArticleNeologisms(urlHash: string): Promise<NeologismEntry[]> {
  requireSupabase();
  const { data, error } = await supabase
    .from('neologisms')
    .select('term,explanation,ko_suggestion,occurrence_count,confirmed,first_seen_url_hash')
    .eq('first_seen_url_hash', urlHash)
    .not('explanation', 'is', null)
    .limit(50);
  if (error) {
    if (import.meta.env.DEV) {
      console.warn('[api] article neologisms unavailable', error.message);
    }
    return [];
  }
  return ((data ?? []) as NeologismEntry[]).filter(entry => entry.term?.trim() && entry.explanation?.trim());
}

export async function fetchNeologismsByTerms(terms: string[]): Promise<NeologismEntry[]> {
  requireSupabase();
  const uniqueTerms = [...new Set(terms.map(term => term.trim()).filter(Boolean))].slice(0, 50);
  if (uniqueTerms.length === 0) return [];
  const { data, error } = await supabase
    .from('neologisms')
    .select('term,explanation,ko_suggestion,occurrence_count,confirmed,first_seen_url_hash')
    .in('term', uniqueTerms)
    .not('explanation', 'is', null)
    .limit(50);
  if (error) {
    if (import.meta.env.DEV) {
      console.warn('[api] per-article neologism lookup unavailable', error.message);
    }
    return [];
  }
  return ((data ?? []) as NeologismEntry[]).filter(entry => entry.term?.trim() && entry.explanation?.trim());
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
  const haystack = `${article.category} ${article.title} ${article.titleKo ?? ''} ${articleSummaryForTone(article, 'formal')}`.toLowerCase();
  const matches = interests.filter(interest => haystack.includes(interest.toLowerCase())).length;
  return matches + (article.credibilityScore || 0);
}

export async function fetchFeed(
  userId: string,
  topK = 10,
): Promise<(Article & { similarity?: number; reason?: string })[]> {
  let interests: string[] = [];
  try {
    interests = JSON.parse(localStorage.getItem(`samsun_interests_${userId}`) ?? localStorage.getItem('samsun_interests') ?? '[]');
  } catch {
    interests = [];
  }
  const articles = await fetchArticles({ limit: Math.max(topK * 4, 40) });
  const feed = articles
    .map(article => ({
      ...article,
      similarity: Math.min(1, scoreByInterests(article, interests) / 2),
      reason: interests.length ? '관심 주제와 제목/요약이 가까운 기사입니다' : '최신 기사 기반 추천입니다',
    }))
    .sort((a, b) => (b.similarity ?? 0) - (a.similarity ?? 0))
    .slice(0, topK)
    .map(article => articleToApiLike(article, article.similarity, article.reason));

  return feed.map(f => ({
    ...toArticle(f),
    similarity: f.similarity,
    ...(f.reason ? { reason: f.reason } : {}),
  }));
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
    articleSummaryForTone(article, 'formal'),
    articleSummaryForTone(article, 'casual'),
    articleTranslationForDisplay(article),
    article.content,
    article.factLabel,
  ].join(' '));
  if (!q) return 0;
  if (haystack.includes(q)) return 1;
  const tokenHits = tokens.filter(token => haystack.includes(token)).length;
  return tokenHits / Math.max(tokens.length, 1);
}

export async function searchArticles(query: string, topK = 10): Promise<(Article & { similarity?: number })[]> {
  const articles = await fetchArticles({ limit: 250 });
  return articles
    .map(article => ({ article, similarity: articleSearchScore(article, query) }))
    .filter(item => item.similarity > 0)
    .sort((a, b) => b.similarity - a.similarity)
    .slice(0, topK)
    .map(item => ({ ...item.article, similarity: item.similarity }));
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
  requireSupabase();
  const { error } = await supabase.from('articles').select('url_hash').limit(1);
  if (error) throw new ApiError(500, supabaseErrorMessage('Supabase health query failed', error));
  return { status: 'ok' };
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
      summary_formal: articleSummaryForTone(article, 'formal'),
      similarity: 0.7,
    })),
  };
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
  requireSupabase();
  const start = `${date}T00:00:00`;
  const end = `${date}T23:59:59`;
  const { data, error } = await supabase
    .from('articles')
    .select(ARTICLE_FIELDS)
    .gte('published_at', start)
    .lte('published_at', end)
    .order('credibility_score', { ascending: false })
    .limit(20);
  if (error) throw new ApiError(500, supabaseErrorMessage('Supabase hot articles query failed', error));
  return (data as unknown as ApiArticle[]).map((article, index) => ({
    ...toArticle(article),
    view_count: Math.max(0, 100 - index * 7),
  }));
}

function articleToApiLike(article: Article, similarity?: number, reason?: string): SearchResult & { reason?: string } {
  return {
    url_hash: article.urlHash,
    url: article.url,
    source_url: article.sourceUrl,
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
    slang_terms: article.slangTerms,
    neologism_terms: article.slangTerms,
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
