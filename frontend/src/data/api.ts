import { supabase, isSupabaseConfigured, getSupabaseConfigIssue } from '../lib/supabase';
import {
  articleCompletenessScore,
  articleSummaryForTone,
  articleTranslationForDisplay,
  demoFeedRankScore,
  factStatusWeight,
  hasKoreanTitle,
  isDemoArticle,
  isValidSummary,
  isValidTranslation,
  toArticle,
  normalizeCategory,
} from './articles';
import type { Article } from './articles';

/**
 * Samsun News frontend data adapter.
 *
 * Runtime policy:
 * - No custom server dependency in the Apps in Toss bundle.
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

const DEMO_POLISHED_FEED = import.meta.env.VITE_DEMO_POLISHED_FEED === '1';
const HIDE_DEMO_ARTICLES = import.meta.env.VITE_HIDE_DEMO_ARTICLES === '1' || DEMO_POLISHED_FEED;
const DEMO_RANGE_START = new Date('2026-05-01T00:00:00+09:00').getTime();
const DEMO_RANGE_END = new Date('2026-05-18T23:59:59+09:00').getTime();

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
  original_url?: string;
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
  fact_confidence?: number;
  fact_status?: string;
  fact_reason?: string;
  fact_insight?: string;
  fact_label: 'FACT' | 'VERIFIED' | 'UNVERIFIED' | 'RUMOR' | 'HITL_REQUIRED' | 'INSIGHT' | 'FACT_INSIGHT';
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
  is_demo?: boolean;
  is_hidden?: boolean;
  demo_visible?: boolean;
  demo_priority?: number;
  embedding?: unknown;
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
interface UserProfileRow {
  user_id: string;
  interest_tags?: string[] | null;
  user_vector?: unknown;
}

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

async function attachOptionalPresentationFields(rows: ApiArticle[]): Promise<ApiArticle[]> {
  if (rows.length === 0) return rows;
  const hashes = rows.map(row => row.url_hash).filter(Boolean).slice(0, 500);
  if (hashes.length === 0) return rows;

  const result = await supabase
    .from('articles')
    .select('url_hash,is_demo,is_hidden,demo_visible,demo_priority')
    .in('url_hash', hashes);

  if (result.error) {
    if (import.meta.env.DEV) {
      console.warn('[api] optional presentation fields unavailable', result.error.message);
    }
    return rows;
  }

  const extras = new Map<string, Partial<ApiArticle>>();
  for (const row of (result.data ?? []) as Partial<ApiArticle>[]) {
    if (row.url_hash) extras.set(row.url_hash, row);
  }
  return rows.map(row => ({ ...row, ...(extras.get(row.url_hash) ?? {}) }));
}

function polishedFeedSort(a: Article, b: Article): number {
  if (DEMO_POLISHED_FEED) {
    const demoDelta = Number(isDemoArticle(b)) - Number(isDemoArticle(a));
    if (demoDelta !== 0) return demoDelta;
    const demoRankDelta = demoFeedRankScore(b) - demoFeedRankScore(a);
    if (demoRankDelta !== 0) return demoRankDelta;
    const statusDelta = factStatusWeight(b.factLabel) - factStatusWeight(a.factLabel);
    if (statusDelta !== 0) return statusDelta;
  }
  const qualityDelta = articleCompletenessScore(b) - articleCompletenessScore(a);
  if (qualityDelta !== 0) return qualityDelta;
  return new Date(b.publishedAt).getTime() - new Date(a.publishedAt).getTime();
}

function isCompletePresentationArticle(article: Article): boolean {
  return hasKoreanTitle(article)
    && isValidTranslation(article.translation)
    && (isValidSummary(article.summaryFormal) || isValidSummary(article.summaryCasual))
    && Boolean(article.factLabel)
    && Boolean(article.source.trim())
    && Boolean(article.url.trim());
}

function isPresentationHidden(article: Article): boolean {
  if (article.isHidden === true || article.demoVisible === false) return true;
  if (HIDE_DEMO_ARTICLES && isDemoArticle(article)) return true;
  return false;
}

function isDemoRangeArticle(article: Article): boolean {
  if (isDemoArticle(article)) return true;
  const published = new Date(article.publishedAt).getTime();
  if (!Number.isFinite(published)) return false;
  return published >= DEMO_RANGE_START && published <= DEMO_RANGE_END;
}

export async function fetchArticles(params: FetchArticlesParams = {}): Promise<Article[]> {
  requireSupabase();
  const { data, error } = await buildArticleQuery(params);
  if (error) throw new ApiError(500, supabaseErrorMessage('Supabase articles query failed', error));
  const rowsWithExtras = await attachOptionalPresentationFields(data as unknown as ApiArticle[]);
  const articles = toArticleList(rowsWithExtras);
  if (import.meta.env.DEV) {
    console.info('[api] fetched articles', {
      count: articles.length,
      limit: params.limit ?? 20,
      offset: params.offset ?? 0,
      category: params.category ?? 'all',
    });
  }
  const visible = articles.filter(article => !isPresentationHidden(article));
  const filtered = params.category
    ? visible.filter(article => article.category === normalizeCategory(params.category))
    : visible;
  const sorted = filtered.sort(polishedFeedSort);
  if (!DEMO_POLISHED_FEED) return sorted;
  const demoScoped = sorted.filter(isDemoRangeArticle);
  const ready = demoScoped.filter(isCompletePresentationArticle);
  if (ready.length === 0) return [];
  return ready;
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
    .select('source_url,original_url')
    .eq('url_hash', urlHash)
    .maybeSingle();
  if (!sourceResult.error && sourceResult.data) {
    const data = sourceResult.data as Partial<ApiArticle>;
    extras.source_url = data.source_url;
    extras.original_url = data.original_url;
  } else if (sourceResult.error && import.meta.env.DEV) {
    console.warn('[api] optional source_url unavailable', sourceResult.error.message);
  }

  const factResult = await supabase
    .from('articles')
    .select('fact_status,fact_confidence,fact_reason,fact_insight')
    .eq('url_hash', urlHash)
    .maybeSingle();
  if (!factResult.error && factResult.data) {
    const data = factResult.data as Partial<ApiArticle>;
    extras.fact_status = data.fact_status;
    extras.fact_confidence = data.fact_confidence;
    extras.fact_reason = data.fact_reason;
    extras.fact_insight = data.fact_insight;
  } else if (factResult.error && import.meta.env.DEV) {
    console.warn('[api] optional fact insight fields unavailable', factResult.error.message);
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
  if (!isSupabaseConfigured()) return { message: 'saved locally' };

  try {
    await upsertUserProfile(userId, interestTags);
  } catch (error) {
    if (import.meta.env.DEV) {
      console.warn('[api] onboarding Supabase sync failed', error);
    }
    return { message: 'saved locally; supabase sync skipped' };
  }

  return { message: 'saved' };
}

function parsePgVector(raw: unknown): number[] | null {
  if (!raw) return null;
  if (Array.isArray(raw)) return raw.map(Number).filter(Number.isFinite);
  if (typeof raw !== 'string') return null;
  const text = raw.trim();
  if (!text) return null;
  try {
    const parsed = JSON.parse(text);
    if (Array.isArray(parsed)) return parsed.map(Number).filter(Number.isFinite);
  } catch {
    // pgvector often returns "[0.1,0.2,...]"; JSON parsing covers that shape.
  }
  const values = text
    .replace(/^\[/, '')
    .replace(/\]$/, '')
    .split(',')
    .map(value => Number(value.trim()))
    .filter(Number.isFinite);
  return values.length > 0 ? values : null;
}

function serializePgVector(vector: number[]): string {
  return `[${vector.map(value => Number.isFinite(value) ? Number(value.toFixed(8)) : 0).join(',')}]`;
}

function blendUserVector(current: number[] | null, clicked: number[], clickWeight = 0.4): number[] {
  const dim = Math.min(clicked.length, current?.length ?? clicked.length);
  if (!current || current.length === 0) return clicked.slice(0, dim);
  return Array.from({ length: dim }, (_, index) => current[index] * (1 - clickWeight) + clicked[index] * clickWeight);
}

function localInterestsFor(userId: string): string[] {
  try {
    return JSON.parse(localStorage.getItem(`samsun_interests_${userId}`) ?? localStorage.getItem('samsun_interests') ?? '[]');
  } catch {
    return [];
  }
}

async function upsertUserProfile(userId: string, interestTags: string[]): Promise<void> {
  const now = new Date().toISOString();
  const base = {
    user_id: userId,
    interest_tags: interestTags,
    last_seen_at: now,
  };
  const result = await supabase
    .from('users')
    .upsert({ ...base, updated_at: now }, { onConflict: 'user_id' });
  if (!result.error) return;
  if (result.error.code === 'PGRST204' || result.error.message?.includes('updated_at')) {
    const fallback = await supabase.from('users').upsert(base, { onConflict: 'user_id' });
    if (!fallback.error) return;
    throw fallback.error;
  }
  throw result.error;
}

async function updateUserVector(userId: string, vector: number[]): Promise<void> {
  const now = new Date().toISOString();
  const base = {
    user_vector: serializePgVector(vector),
    last_seen_at: now,
  };
  const result = await supabase
    .from('users')
    .update({ ...base, updated_at: now })
    .eq('user_id', userId);
  if (!result.error) return;
  if (result.error.code === 'PGRST204' || result.error.message?.includes('updated_at')) {
    const fallback = await supabase.from('users').update(base).eq('user_id', userId);
    if (!fallback.error) return;
    throw fallback.error;
  }
  throw result.error;
}

async function fetchUserProfile(userId: string): Promise<UserProfileRow | null> {
  if (!isSupabaseConfigured()) return null;
  const { data, error } = await supabase
    .from('users')
    .select('user_id,interest_tags,user_vector')
    .eq('user_id', userId)
    .maybeSingle();
  if (error) {
    if (import.meta.env.DEV) console.warn('[api] user profile unavailable', error.message);
    return null;
  }
  return data as UserProfileRow | null;
}

async function fetchRecentClickCategories(userId: string): Promise<string[]> {
  if (!isSupabaseConfigured()) return [];
  const { data, error } = await supabase
    .from('user_logs')
    .select('url_hash')
    .eq('user_id', userId)
    .order('created_at', { ascending: false })
    .limit(20);
  if (error || !data?.length) return [];
  const hashes = data.map(row => row.url_hash).filter(Boolean);
  if (hashes.length === 0) return [];
  const articles = await supabase
    .from('articles')
    .select('category,source,title,title_ko')
    .in('url_hash', hashes);
  if (articles.error) return [];
  return [...new Set((articles.data ?? []).map(row =>
    normalizeCategory(row.category, row.source, `${row.title ?? ''} ${row.title_ko ?? ''}`),
  ))];
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
  const profile = await fetchUserProfile(userId);
  const interests = (profile?.interest_tags?.length ? profile.interest_tags : localInterestsFor(userId)).map(String);
  const recentCategories = await fetchRecentClickCategories(userId);
  const userVector = parsePgVector(profile?.user_vector);

  if (userVector?.length) {
    const rpc = await supabase.rpc('match_articles', {
      query_vector: serializePgVector(userVector),
      top_k: Math.max(topK * 4, 40),
    });
    if (!rpc.error && rpc.data?.length) {
      const rows = await attachOptionalPresentationFields(rpc.data as unknown as ApiArticle[]);
      const vectorArticles = toArticleList(rows)
        .filter(article => !isPresentationHidden(article))
        .filter(article => !DEMO_POLISHED_FEED || (isDemoRangeArticle(article) && isCompletePresentationArticle(article)))
        .slice(0, Math.max(topK * 2, topK));
      if (vectorArticles.length > 0) {
        return vectorArticles
          .slice(0, topK)
          .map(article => ({
            ...article,
            similarity: typeof (rows.find(row => row.url_hash === article.urlHash) as SearchResult | undefined)?.similarity === 'number'
              ? (rows.find(row => row.url_hash === article.urlHash) as SearchResult).similarity
              : undefined,
            reason: '사용자 관심 벡터와 유사도가 높은 기사입니다.',
          }));
      }
    } else if (rpc.error && import.meta.env.DEV) {
      console.warn('[api] match_articles RPC failed; using fallback feed', rpc.error.message);
    }
  }

  const articles = await fetchArticles({ limit: Math.max(topK * 4, 40) });
  const feed = articles
    .map(article => ({
      ...article,
      similarity: Math.min(1, (scoreByInterests(article, interests) + (recentCategories.includes(article.category) ? 1 : 0)) / 3),
      reason: recentCategories.includes(article.category)
        ? `최근 읽은 기사와 같은 '${article.category}' 분야 기사입니다.`
        : interests.includes(article.category)
          ? `선택한 관심사 '${article.category}'와 맞는 기사입니다.`
          : interests.length
            ? '선택한 관심사와 제목/요약이 가까운 기사입니다.'
            : '최근 업데이트된 완성 기사입니다.',
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
    // local fallback only
  }

  if (!isSupabaseConfigured()) return;

  try {
    const now = new Date().toISOString();
    await upsertUserProfile(userId, localInterestsFor(userId));

    const logResult = await supabase
      .from('user_logs')
      .insert({ user_id: userId, url_hash: urlHash, action: 'view', created_at: now });
    if (logResult.error && import.meta.env.DEV) {
      console.warn('[api] user_logs insert failed', logResult.error.message);
    }

    const articleResult = await supabase
      .from('articles')
      .select('embedding')
      .eq('url_hash', urlHash)
      .maybeSingle();
    const clickedVector = parsePgVector((articleResult.data as Partial<ApiArticle> | null)?.embedding);
    if (!clickedVector?.length) return;

    const user = await fetchUserProfile(userId);
    const currentVector = parsePgVector(user?.user_vector);
    const nextVector = blendUserVector(currentVector, clickedVector);
    await updateUserVector(userId, nextVector);
  } catch (error) {
    if (import.meta.env.DEV) {
      console.warn('[api] recordArticleView failed; UI continues', error);
    }
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
  if (!userId?.trim() || !urlHash) return;
  try {
    const key = `samsun_view_log_${userId}`;
    const prev = JSON.parse(localStorage.getItem(key) ?? '[]') as string[];
    localStorage.setItem(key, JSON.stringify([urlHash, ...prev].slice(0, 200)));
  } catch {
    // no-op
  }
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

  const datedRows = await attachOptionalPresentationFields(data as unknown as ApiArticle[]);
  const dated = toArticleList(datedRows)
    .filter(article => !isPresentationHidden(article))
    .filter(article => !DEMO_POLISHED_FEED || (isDemoRangeArticle(article) && isCompletePresentationArticle(article)))
    .map((article, index) => ({ ...article, view_count: Math.max(0, 100 - index * 7) }));
  if (dated.length >= 5) return dated;

  const yesterday = new Date(Date.now() - 86_400_000).toISOString();
  const logResult = await supabase
    .from('user_logs')
    .select('url_hash,created_at')
    .gte('created_at', yesterday)
    .limit(500);
  if (!logResult.error && logResult.data?.length) {
    const counts = new Map<string, number>();
    for (const row of logResult.data as { url_hash?: string }[]) {
      if (row.url_hash) counts.set(row.url_hash, (counts.get(row.url_hash) ?? 0) + 1);
    }
    const hashes = [...counts.keys()].slice(0, 50);
    if (hashes.length) {
      const articlesResult = await supabase
        .from('articles')
        .select(ARTICLE_FIELDS)
        .in('url_hash', hashes);
      if (!articlesResult.error) {
        const rows = await attachOptionalPresentationFields(articlesResult.data as unknown as ApiArticle[]);
        const hotByLogs = toArticleList(rows)
          .filter(article => !isPresentationHidden(article))
          .filter(article => !DEMO_POLISHED_FEED || (isDemoRangeArticle(article) && isCompletePresentationArticle(article)))
          .map(article => ({ ...article, view_count: counts.get(article.urlHash) ?? 0 }))
          .sort((a, b) => b.view_count - a.view_count)
          .slice(0, 20);
        if (hotByLogs.length >= 5) return hotByLogs;
      }
    }
  }

  const fallback = await fetchArticles({ limit: 40 });
  return fallback
    .sort((a, b) => {
      const statusDelta = factStatusWeight(b.factLabel) - factStatusWeight(a.factLabel);
      if (statusDelta !== 0) return statusDelta;
      const scoreDelta = (b.credibilityScore ?? 0) - (a.credibilityScore ?? 0);
      if (scoreDelta !== 0) return scoreDelta;
      return new Date(b.publishedAt).getTime() - new Date(a.publishedAt).getTime();
    })
    .slice(0, 20)
    .map((article, index) => ({ ...article, view_count: Math.max(0, 80 - index * 4) }));
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
