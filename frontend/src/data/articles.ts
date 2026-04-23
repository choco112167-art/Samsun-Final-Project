/**
 * 삼선뉴스 — 기사 타입 정의 + API 어댑터
 *
 * 변경 내역 (개선방안 반영)
 *   - formalTranslation / casualTranslation → translationFormal / translationCasual 로 통일
 *   - summary → summaryKobart / summaryLlm 분리 (KoBART vs LLM 비교 구조 반영)
 *   - sourceUrl 추가 (원문 링크)
 *   - credibilityScore / factLabel / sourceType 추가 (신뢰도 라벨링)
 *   - publishedAt 추가 (ISO) + timeAgo 유틸 분리
 *   - 더미 데이터 제거 — API에서 받아오는 방식으로 전환
 *   - toArticle() 어댑터로 ApiArticle → Article 변환
 */

import type { ApiArticle } from './api';

// ─────────────────────────────────────────────
// 카테고리
// ─────────────────────────────────────────────

export type Category =
  | 'AI 모델'
  | '스타트업'
  | '빅테크'
  | '윤리/정책'
  | '반도체'
  | 'LLM'
  | 'AI 제품'
  | '기타';

// ─────────────────────────────────────────────
// UI용 Article 타입
// ─────────────────────────────────────────────

export interface Article {
  // 식별
  id:          string;
  sourceUrl:   string;      // 원문 링크 (DetailPage "원문 보기" 버튼)

  // 메타
  title:       string;
  source:      string;      // 'TechCrunch' | 'The Verge' | ...
  sourceColor: string;      // 소스별 브랜드 컬러 (어댑터에서 주입)
  sourceType:  'media' | 'community';
  category:    Category;
  publishedAt: string;      // ISO 8601 원본 (정렬·필터용)
  timeAgo:     string;      // "3시간 전" 등 (포맷팅 후)

  // 콘텐츠
  contentEn:   string;      // 영문 원문

  // 번역 — translator.py Translator.translate_both() 결과
  translationFormal: string;    // 격식체 (~하였습니다)
  translationCasual: string;    // 일상체 (~했어요)

  // 요약 — summarizer.py + LLM API 비교
  summaryKobart: string;    // KoBART 파인튜닝 3줄 요약 ("• ...\n• ...\n• ...")
  summaryLlm:    string;    // LLM API 비교 요약

  // 신뢰도 — credibility.py
  credibilityScore: number;               // 0.0 ~ 1.0
  factLabel:        'FACT' | 'UNVERIFIED' | 'RUMOR';

  // UI 상태
  isNew:      boolean;
  isBreaking: boolean;
  views:      number;
}

// ─────────────────────────────────────────────
// 소스별 브랜드 컬러 맵
// credibility.py SOURCE_CREDIBILITY 기준 소스와 일치
// ─────────────────────────────────────────────

const SOURCE_COLORS: Record<string, string> = {
  'TechCrunch':            '#4F46E5',
  'MIT Technology Review': '#0891B2',
  'The Verge':             '#7C3AED',
  'VentureBeat AI':        '#D97706',
  'The Guardian Tech':     '#059669',
  'IEEE Spectrum':         '#0369A1',
  'BBC Technology':        '#DC2626',
  'Nikkei Asia Tech':      '#B45309',
  // 커뮤니티
  'Reddit r/artificial':      '#FF4500',
  'Reddit r/MachineLearning': '#FF4500',
  'Reddit r/LocalLLaMA':      '#FF4500',
  'Product Hunt':             '#DA552F',
};

const DEFAULT_COLOR = '#6B7280';

// ─────────────────────────────────────────────
// 카테고리 정규화
// rss_crawler.py category 필드 → UI Category 타입으로 변환
// ─────────────────────────────────────────────

const CATEGORY_MAP: Record<string, Category> = {
  'AI/스타트업':  'AI 모델',
  'AI 심층':     'AI 모델',
  'AI 비즈니스': '빅테크',
  'AI 윤리':     '윤리/정책',
  'AI/반도체':   '반도체',
  'AI 일반':     'AI 모델',
  'AI 커뮤니티': 'AI 모델',
  'AI 연구':     'AI 모델',
  'LLM 커뮤니티': 'LLM',
  'AI 제품':     'AI 제품',
  '테크 전반':   '기타',
};

function normalizeCategory(raw: string): Category {
  return CATEGORY_MAP[raw] ?? '기타';
}

// ─────────────────────────────────────────────
// timeAgo 포맷터
// publishedAt ISO 문자열 → "3시간 전" 형식
// ─────────────────────────────────────────────

export function formatTimeAgo(publishedAt: string): string {
  if (!publishedAt) return '';
  const diff = Date.now() - new Date(publishedAt).getTime();
  const min  = Math.floor(diff / 60_000);
  const hr   = Math.floor(diff / 3_600_000);
  const day  = Math.floor(diff / 86_400_000);

  if (min < 1)  return '방금';
  if (min < 60) return `${min}분 전`;
  if (hr  < 24) return `${hr}시간 전`;
  return `${day}일 전`;
}

// ─────────────────────────────────────────────
// 어댑터: ApiArticle → Article
// ─────────────────────────────────────────────

/**
 * 백엔드 ApiArticle을 UI용 Article로 변환합니다.
 *
 * @param api       GET /articles 또는 GET /articles/:id 응답 1건
 * @param isBreaking 브레이킹 여부 (API가 플래그를 내리면 교체 예정)
 */
export function toArticle(api: ApiArticle, isBreaking = false): Article {
  const publishedAt = api.published_at ?? '';
  const now = Date.now();
  const publishedMs = publishedAt ? new Date(publishedAt).getTime() : now;
  const isNew = now - publishedMs < 6 * 3_600_000; // 6시간 이내

  return {
    id:          api.id,
    sourceUrl:   api.url,

    title:       api.title,
    source:      api.source,
    sourceColor: SOURCE_COLORS[api.source] ?? DEFAULT_COLOR,
    sourceType:  api.source_type ?? 'media',
    category:    normalizeCategory(api.category),
    publishedAt,
    timeAgo:     formatTimeAgo(publishedAt),

    contentEn:   api.content ?? '',

    translationFormal: api.translation_formal ?? '',
    translationCasual: api.translation_casual ?? '',

    summaryKobart: api.summary_ko  ?? '',
    summaryLlm:    api.summary_llm ?? '',

    credibilityScore: api.credibility_score ?? 0,
    factLabel:        api.fact_label ?? 'UNVERIFIED',

    isNew,
    isBreaking,
    views: 0, // 추후 조회수 API 연동 시 교체
  };
}

/**
 * ApiArticle 배열을 일괄 변환합니다.
 * GET /articles 응답에 바로 사용하세요.
 *
 * @example
 * const raw = await fetchArticles({ limit: 20 });
 * const articles = toArticles(raw);
 */
export function toArticles(raw: ApiArticle[]): Article[] {
  return raw.map((a) => toArticle(a));
}
// 임시 더미 데이터 — API 연동 전까지 사용
export const allArticles: Article[] = [];
export const breakingArticles: Article[] = [];
export const articles: Article[] = [];
