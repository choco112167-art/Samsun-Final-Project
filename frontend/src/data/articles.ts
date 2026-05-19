/**
 * frontend/src/data/articles.ts — 기사 타입 + UI 어댑터
 *
 * 역할:
 *   1. UI에서 사용하는 Article 타입을 정의한다 (camelCase)
 *   2. 백엔드 응답(ApiArticle, snake_case)을 UI용 Article(camelCase)로 변환한다
 *
 * 왜 두 가지 타입이 필요한가?
 *   - 백엔드(Python) 관례: published_at, source_type (snake_case)
 *   - 프론트(JS/React) 관례: publishedAt, sourceType (camelCase)
 *   이 파일의 toArticle() 함수가 그 간격을 이어준다.
 */

import type { ApiArticle } from './api';
import { normalizeCategory } from './categories';
import type { Category } from './categories';
import type { SummaryTone } from '../hooks/useTonePreference';

// 카테고리 분류 체계는 ./categories.ts 가 단일 진실 소스다.
// 기존 import 호환을 위해 여기서도 재내보낸다.
export {
  CATEGORIES,
  normalizeCategory,
  filterByCategory,
  getRawCategoriesFor,
} from './categories';
export type { Interest, Category } from './categories';


// ─────────────────────────────────────────────
// UI용 Article 타입
// React 컴포넌트(ArticleCard, DetailPage 등)에서 사용하는 타입
// camelCase 관례를 따른다
// ─────────────────────────────────────────────

export interface Article {
  // 식별
  urlHash:     string;   // DB의 url_hash (PK) — 상세 페이지 이동 시 사용
  url:         string;   // 원문 URL — 기존 컴포넌트 호환용
  sourceUrl:   string;   // 원문 URL — 상세 페이지 "원문 보기" 표준 필드
  originalUrl: string;
  slangTerms:  string[];

  // 메타 정보 (표시 제목은 articleDisplayTitle() 사용 권장)
  /** 영문 RSS 헤드라인 등 원본 제목 */
  title:       string;
  /** 한국어 번역 제목 — 없으면 UI 에서 title 로 폴백 */
  titleKo?:    string;
  source:      string;
  sourceColor: string;   // 소스별 브랜드 컬러 — 카드 왼쪽 액센트 바, 점 색상
  sourceType:  'media' | 'community';
  category:    Category; // 정규화된 카테고리 (아래 CATEGORY_MAP으로 변환)
  country:     string;
  keywords:    string[];
  publishedAt: string;   // ISO 8601 원본 (정렬/필터용)
  timeAgo:     string;   // "3시간 전" 포맷 (화면 표시용)

  // 콘텐츠
  content:     string;   // 영문 원문 본문

  // 신뢰도
  credibilityScore: number;
  factLabel:        'FACT' | 'VERIFIED' | 'UNVERIFIED' | 'RUMOR' | 'HITL_REQUIRED' | 'INSIGHT' | 'FACT_INSIGHT';
  factConfidence?:  number;
  factStatus?:      string;
  factReason?:      string;
  factInsight?:     string;

  // 번역 / 요약
  translation:   string;   // 한국어 번역 전문 — DetailPage 신조어 하이라이트에 사용
  summaryFormal: string;   // 격식체 3줄 요약 — ArticleCard 미리보기, DetailPage 표시
  summaryCasual: string;   // 일상체 3줄 요약 — DetailPage 표시
  aiStatus?:     'pending' | 'processing' | 'completed' | 'failed' | 'skipped';
  aiProvider?:   string;
  aiModel?:      string;
  aiError?:      string;
  isDemo?:       boolean;
  isHidden?:     boolean;
  demoVisible?:  boolean;
  demoPriority?: number;

  // UI 상태
  isNew:      boolean;   // true면 "NEW" 뱃지 표시
  isBreaking: boolean;   // true면 "속보" 뱃지 + 상단 배너에 포함
}


// ─────────────────────────────────────────────
// 소스별 브랜드 컬러 맵
// 각 언론사의 대표 컬러를 HEX로 정의한다
// ArticleCard의 왼쪽 액센트 바와 소스 점 색상에 사용
// ─────────────────────────────────────────────

const SOURCE_COLORS: Record<string, string> = {
  'TechCrunch':            '#4F46E5',   // 인디고
  'MIT Technology Review': '#0891B2',   // 시안
  'The Verge':             '#7C3AED',   // 바이올렛
  'VentureBeat AI':        '#D97706',   // 앰버
  'The Guardian Tech':     '#059669',   // 에메랄드
  'IEEE Spectrum':         '#0369A1',   // 블루
  'The Decoder':           '#DC2626',   // 레드
  // 커뮤니티 소스
  'Lemmy Technology': '#B45309',
  'Hacker News AI':   '#B45309',
  'Hacker News LLM':  '#B45309',
  'Hacker News ML':   '#B45309',
  'DEMO':             '#6B7280',
};

// 목록에 없는 소스의 기본 컬러 (회색)
const DEFAULT_COLOR = '#6B7280';


// 카테고리 정규화는 ./categories.ts 의 normalizeCategory 가 담당한다.

// ─────────────────────────────────────────────
// timeAgo 포맷터
// ISO 8601 시간 문자열을 "3시간 전" 형식으로 변환한다
// ArticleCard의 우측 상단 시간 표시에 사용
// ─────────────────────────────────────────────

/** 목록·상세에서 보여 줄 한국어 우선 제목 (레거시 행 폴백 포함). */
export function articleDisplayTitle(a: Pick<Article, 'title' | 'titleKo'>): string {
  const ko = (a.titleKo ?? '').trim();
  return ko || '제목 번역 중입니다.';
}

export function hasKoreanTitle(a: Pick<Article, 'titleKo'>): boolean {
  return Boolean((a.titleKo ?? '').trim());
}

function cleanGeneratedText(value: string | null | undefined): string {
  return (value ?? '').replace(/\r\n/g, '\n').trim();
}

function isPlaceholderGeneratedText(value: string): boolean {
  return /\[MOCK|\(파싱 실패\)|parsing failed|translation unavailable|summary unavailable/i.test(value);
}

function sentenceCount(value: string): number {
  const normalized = value
    .replace(/\n+/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
  if (!normalized) return 0;
  const numbered = normalized.match(/(?:^|\s)\d+\.\s+/g)?.length ?? 0;
  const punctuation = normalized.split(/[.!?。！？]|[.!?]\s|[다요죠음함됨임]\./).filter(part => part.trim().length > 5).length;
  return Math.max(numbered, punctuation);
}

export function isValidSummary(value: string | null | undefined): boolean {
  const text = cleanGeneratedText(value);
  if (text.length < 55 || isPlaceholderGeneratedText(text)) return false;
  return sentenceCount(text) >= 2;
}

export function isValidTranslation(value: string | null | undefined): boolean {
  const text = cleanGeneratedText(value);
  if (text.length < 140 || isPlaceholderGeneratedText(text)) return false;
  return /[가-힣]/.test(text);
}

export function articleSummaryForTone(
  article: Pick<Article, 'summaryFormal' | 'summaryCasual'>,
  tone: SummaryTone,
): string {
  const selected = tone === 'formal' ? article.summaryFormal : article.summaryCasual;
  return isValidSummary(selected) ? cleanGeneratedText(selected) : '';
}

export function articleTranslationForDisplay(article: Pick<Article, 'translation'>): string {
  return isValidTranslation(article.translation) ? cleanGeneratedText(article.translation) : '';
}

export function articleCompletenessScore(
  article: Pick<Article, 'titleKo' | 'summaryFormal' | 'summaryCasual' | 'translation'>,
): number {
  return (hasKoreanTitle(article) ? 3 : 0)
    + (isValidSummary(article.summaryFormal) ? 2 : 0)
    + (isValidSummary(article.summaryCasual) ? 2 : 0)
    + (isValidTranslation(article.translation) ? 3 : 0);
}

export type FactStatus = 'VERIFIED' | 'UNVERIFIED' | 'RUMOR' | 'HITL_REQUIRED' | 'INSIGHT';

export function normalizeFactStatus(label: string | null | undefined): FactStatus {
  const value = (label ?? '').trim().toUpperCase();
  if (value === 'FACT' || value === 'VERIFIED' || value === 'FACT_INSIGHT') return 'VERIFIED';
  if (value === 'RUMOR') return 'RUMOR';
  if (value === 'HITL_REQUIRED' || value === 'HITL' || value === 'HUMAN_REVIEW_REQUIRED') return 'HITL_REQUIRED';
  if (value === 'INSIGHT') return 'INSIGHT';
  return 'UNVERIFIED';
}

export function isDemoArticle(article: Pick<Article, 'source' | 'title' | 'titleKo' | 'isDemo'>): boolean {
  return article.source.trim().toUpperCase() === 'DEMO'
    || article.isDemo === true
    || (article.titleKo ?? '').includes('[시연용]')
    || article.title.includes('[DEMO]');
}

export function factStatusWeight(label: string | null | undefined): number {
  const status = normalizeFactStatus(label);
  if (status === 'VERIFIED' || status === 'INSIGHT') return 4;
  if (status === 'UNVERIFIED') return 3;
  if (status === 'HITL_REQUIRED') return 2;
  if (status === 'RUMOR') return 1;
  return 0;
}

export function demoFeedRankScore(article: Article): number {
  const demoBoost = isDemoArticle(article) ? 1000 : 0;
  const quality = articleCompletenessScore(article) * 20;
  const status = factStatusWeight(article.factLabel) * 8;
  const recencyDays = Math.max(0, (Date.now() - new Date(article.publishedAt).getTime()) / 86_400_000);
  const recency = Math.max(0, 30 - Math.min(recencyDays, 30));
  return demoBoost + quality + status + recency + (article.credibilityScore ?? 0);
}

export function isOldIncompleteDemoFeedArticle(article: Article): boolean {
  const ageDays = (Date.now() - new Date(article.publishedAt).getTime()) / 86_400_000;
  return ageDays > 30 && articleCompletenessScore(article) < 10 && !isDemoArticle(article);
}


export function formatTimeAgo(publishedAt: string): string {
  if (!publishedAt) return '';

  // 현재 시각과의 차이를 밀리초로 계산
  const diff = Date.now() - new Date(publishedAt).getTime();

  // 밀리초 → 분, 시간, 일로 변환
  const min  = Math.floor(diff / 60_000);       // 60 * 1000
  const hr   = Math.floor(diff / 3_600_000);    // 60 * 60 * 1000
  const day  = Math.floor(diff / 86_400_000);   // 24 * 60 * 60 * 1000

  if (min < 1)  return '방금';
  if (min < 60) return `${min}분 전`;
  if (hr  < 24) return `${hr}시간 전`;
  return `${day}일 전`;
}


// ─────────────────────────────────────────────
// 어댑터: ApiArticle → Article
// 백엔드 응답(snake_case)을 UI 타입(camelCase)으로 변환한다
// 이 함수 덕분에 컴포넌트에서는 article.publishedAt 처럼 깔끔하게 쓸 수 있다
// ─────────────────────────────────────────────

export function toArticle(api: ApiArticle): Article {
  const publishedAt = api.published_at ?? '';
  const now = Date.now();
  const publishedMs = publishedAt ? new Date(publishedAt).getTime() : now;

  return {
    // snake_case → camelCase 변환
    urlHash:     api.url_hash,
    url:         api.url,
    sourceUrl:   api.source_url ?? api.original_url ?? api.url,
    originalUrl: api.original_url ?? '',
    slangTerms:  api.neologism_terms ?? api.slang_terms ?? [],

    title:       api.title,
    titleKo:     api.title_ko ?? '',
    source:      api.source,
    sourceColor: SOURCE_COLORS[api.source] ?? DEFAULT_COLOR,  // 소스명으로 컬러 주입
    sourceType:  api.source_type ?? 'media',
    category:    normalizeCategory(api.category, api.source, `${api.title ?? ''} ${api.title_ko ?? ''} ${api.content ?? ''}`),  // 카테고리 정규화 + source/text fallback
    country:     api.country ?? '',
    keywords:    api.keywords ?? [],
    publishedAt,
    // 백엔드가 time_ago를 내려주면 사용, 없으면 직접 계산
    timeAgo:     api.time_ago ?? formatTimeAgo(publishedAt),

    content:     api.content ?? '',

    credibilityScore: api.credibility_score ?? 0,
    factLabel:        (api.fact_label ?? normalizeFactStatus(api.fact_status)) as Article['factLabel'],
    factConfidence:   api.fact_confidence,
    factStatus:       api.fact_status,
    factReason:       api.fact_reason,
    factInsight:      api.fact_insight,

    translation:   api.translation    ?? '',
    summaryFormal: api.summary_formal ?? '',
    summaryCasual: api.summary_casual ?? '',
    aiStatus:      api.ai_status,
    aiProvider:    api.ai_provider,
    aiModel:       api.ai_model,
    aiError:       api.ai_error,
    isDemo:        api.is_demo,
    isHidden:      api.is_hidden,
    demoVisible:   api.demo_visible,
    demoPriority:  api.demo_priority,

    // 백엔드가 is_new를 내려주면 사용, 없으면 6시간 이내인지 직접 판단
    isNew:      api.is_new      ?? (now - publishedMs < 6 * 3_600_000),
    isBreaking: api.is_breaking ?? false,
  };
}

/**
 * ApiArticle 배열을 한 번에 변환한다.
 * fetchArticles() 결과를 컴포넌트에 넘기기 전에 사용.
 *
 * @example
 * const raw = await fetchArticles({ limit: 20 });
 * const articles = toArticles(raw);  // ArticleCard에 바로 사용 가능
 */
export function toArticles(raw: ApiArticle[]): Article[] {
  return raw.map(toArticle);
}
