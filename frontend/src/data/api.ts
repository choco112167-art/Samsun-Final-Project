import { toArticle } from './articles';
import type { Article } from './articles';
/**
 * frontend/src/data/api.ts — 삼선뉴스 API 클라이언트
 *
 * 프론트엔드에서 백엔드(FastAPI)로 HTTP 요청을 보내는 함수들을 모아놓은 파일.
 * 모든 API 호출은 이 파일을 통해서 한다.
 *
 * 엔드포인트 맵 (backend/main.py 기준)
 *   GET  /articles          → fetchArticles()      기사 목록 조회
 *   GET  /article/:url_hash → fetchArticleByHash() 기사 상세 조회
 *   POST /onboarding        → postOnboarding()     유저 관심사 등록
 *   GET  /feed/:userId      → fetchFeed()          맞춤 기사 추천
 *   GET  /search?q=         → searchArticles()     벡터 검색
 *   GET  /health            → healthCheck()        서버 상태 확인
 *   POST /translate         → translateArticle()   번역
 *   POST /summarize         → summarizeArticle()   요약
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
// 타입 정의 — DB 컬럼명과 1:1 대응
// ─────────────────────────────────────────────

export interface ApiArticle {
  url_hash:          string;
  url:               string;
  title:             string;
  source:            string;
  source_type:       'media' | 'community';
  category:          string;
  country:           string;
  keywords:          string[];
  published_at:      string;
  collected_at:      string;
  content:           string;
  credibility_score: number;
  fact_label:        'FACT' | 'UNVERIFIED' | 'RUMOR';
  translation:       string;
  summary_formal:    string;
  summary_casual:    string;
  is_new:            boolean;
  is_breaking:       boolean;
  time_ago:          string;
  source_color:      string;
}

export interface FetchArticlesParams {
  category?:    string;
  source?:      string;
  source_type?: 'media' | 'community';
  limit?:       number;
  offset?:      number;
  is_breaking?: boolean;
}

export interface OnboardingRequest  { user_id: string; interest_tags: string[]; }
export interface OnboardingResponse { message: string; }

export interface FeedArticle   extends ApiArticle { similarity?: number; }
export interface SearchResult  extends ApiArticle { similarity?: number; }


// ─────────────────────────────────────────────
// API 함수들
// ─────────────────────────────────────────────

export async function fetchArticles(params: FetchArticlesParams = {}): Promise<Article[]> {
  const qs = new URLSearchParams();
  if (params.category)                  qs.set('category',    params.category);
  if (params.source)                    qs.set('source',      params.source);
  if (params.source_type)               qs.set('source_type', params.source_type);
  if (params.limit)                     qs.set('limit',       String(params.limit));
  if (params.offset !== undefined)      qs.set('offset',      String(params.offset)); // 0도 전송
  if (params.is_breaking !== undefined) qs.set('is_breaking', String(params.is_breaking));

  const query = qs.toString() ? `?${qs}` : '';
  return request<ApiArticle[]>(`/articles${query}`).then(list => list.map(toArticle));
}

export async function fetchArticleByHash(urlHash: string): Promise<ApiArticle> {
  return request<ApiArticle>(`/article/${urlHash}`);
}

export async function postOnboarding(userId: string, interestTags: string[]): Promise<OnboardingResponse> {
  return request<OnboardingResponse>('/onboarding', {
    method: 'POST',
    body: JSON.stringify({ user_id: userId, interest_tags: interestTags }),
  });
}

export async function fetchFeed(userId: string, topK = 10): Promise<(Article & { similarity?: number })[]> {
  const res = await request<{ feed: FeedArticle[] }>(
    `/feed/${encodeURIComponent(userId)}?top_k=${topK}`,
  );
  const list = res.feed ?? [];
  return list.map(f => ({ ...toArticle(f), similarity: f.similarity }));
}

export async function searchArticles(query: string, topK = 10): Promise<(Article & { similarity?: number })[]> {
  const res = await request<{ results: SearchResult[] }>(
    `/search?q=${encodeURIComponent(query)}&top_k=${topK}`,
  );
  const list = res.results ?? [];
  return list.map(r => ({ ...toArticle(r), similarity: r.similarity }));
}

export async function recordArticleView(userId: string, urlHash: string): Promise<void> {
  if (!userId?.trim() || !urlHash) return;
  await request<{ message?: string }>(
    `/article-view/${encodeURIComponent(userId)}/${encodeURIComponent(urlHash)}`,
    { method: 'POST' },
  );
}

export async function healthCheck(): Promise<{ status: string }> {
  return request<{ status: string }>('/health');
}

// ─────────────────────────────────────────────
// 부재 중 요약 알림
// ─────────────────────────────────────────────

export interface AbsenceArticle {
  url_hash:       string;
  title:          string;
  source:         string;
  category:       string;
  published_at:   string;
  summary_formal: string;
  similarity:     number;
  view_count?:    number;
}

export interface AbsenceSummaryResponse {
  show:         boolean;
  message?:     string;
  sub_message?: string;
  days_away?:   number;
  articles?:    AbsenceArticle[];
}

export async function fetchAbsenceSummary(userId: string): Promise<AbsenceSummaryResponse> {
  return request<AbsenceSummaryResponse>(`/absence-summary/${encodeURIComponent(userId)}`);
}

export async function markUserSeen(userId: string): Promise<void> {
  await request<{ message: string }>(`/user-seen/${encodeURIComponent(userId)}`, { method: 'POST' });
}

export async function logArticleView(userId: string, urlHash: string): Promise<void> {
  if (!userId?.trim() || !urlHash) return;
  await request<{ message?: string }>(
    `/logs/view?user_id=${encodeURIComponent(userId)}&url_hash=${encodeURIComponent(urlHash)}`,
    { method: 'POST' },
  );
}

export async function fetchHot(date: string): Promise<(Article & { view_count: number })[]> {
  const list = await request<(ApiArticle & { view_count: number })[]>(`/hot/${date}`);
  return list.map(a => ({ ...toArticle(a), view_count: a.view_count ?? 0 }));
}

/**
 * 영문 원문을 한국어로 번역한다.
 * DetailPage의 "재번역" 버튼에서 호출.
 * 내부적으로 Ollama qwen3.5:4b 모델을 사용한다.
 *
 * @param text 영문 원문 (article.content)
 */
export async function translateArticle(text: string): Promise<{ translation: string }> {
  return request<{ translation: string }>('/translate', {
    method: 'POST',
    body: JSON.stringify({ text }),
  });
}

/**
 * 영문 원문에 대한 격식체·일상체 3줄 요약을 생성한다.
 * DetailPage의 "재요약" 버튼에서 호출.
 * 내부적으로 Ollama qwen3.5:4b 모델을 사용한다.
 *
 * @param text 영문 원문 (article.content)
 */
export async function summarizeArticle(
  text: string,
): Promise<{ summary_formal: string; summary_casual: string }> {
  return request<{ summary_formal: string; summary_casual: string }>('/summarize', {
    method: 'POST',
    body: JSON.stringify({ text }),
  });
}