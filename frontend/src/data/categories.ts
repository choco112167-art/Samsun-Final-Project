/**
 * frontend/src/data/categories.ts — category normalization and colors.
 */

export const CATEGORIES = [
  'AI 연구/기술',
  'AI 비즈니스',
  'AI 제품/서비스',
  'AI 윤리/정책',
  'AI 인프라',
  'LLM/생성AI',
  '로보틱스/자율주행',
  '기타 테크',
  'AI 심층',
  'AI 스타트업',
  '테크 전반',
  'AI 커뮤니티',
  '카테고리 없음',
] as const;

export type Interest = (typeof CATEGORIES)[number];
export type DemoCategory = '주요 뉴스' | '기술/AI' | '보안/리스크' | '커뮤니티 이슈';
export type Category = Interest | DemoCategory;

export const CATEGORY_FALLBACK: Category = '카테고리 없음';

const SOURCE_FALLBACK: Record<string, Category> = {
  'TechCrunch': 'AI 비즈니스',
  'MIT Technology Review': 'AI 연구/기술',
  'The Guardian Tech': 'AI 윤리/정책',
  'IEEE Spectrum': 'AI 인프라',
  'The Decoder': 'LLM/생성AI',
  'VentureBeat AI': 'AI 비즈니스',
  'The Verge': '기타 테크',
  'Medium': '기타 테크',
  'Quanta Magazine': 'AI 연구/기술',
};

const EXACT_MAP: Record<string, Category> = {
  'AI 연구/기술': 'AI 연구/기술',
  'AI 연구': 'AI 연구/기술',
  'AI 심층/기술': 'AI 연구/기술',
  'AI 비즈니스': 'AI 비즈니스',
  'AI/스타트업': 'AI 스타트업',
  'AI 스타트업': 'AI 스타트업',
  'AI 제품': 'AI 제품/서비스',
  'AI 제품/서비스': 'AI 제품/서비스',
  'AI 윤리': 'AI 윤리/정책',
  'AI 윤리/정책': 'AI 윤리/정책',
  '윤리-정책': 'AI 윤리/정책',
  'AI 인프라': 'AI 인프라',
  'AI/반도체': 'AI 인프라',
  '반도체': 'AI 인프라',
  'LLM/생성AI': 'LLM/생성AI',
  'LLM 커뮤니티': 'LLM/생성AI',
  '로보틱스/자율주행': '로보틱스/자율주행',
  'AI 심층': 'AI 심층',
  '테크 전반': '테크 전반',
  '테크전반': '테크 전반',
  '기타 테크': '기타 테크',
  'AI 커뮤니티': 'AI 커뮤니티',
  '카테고리 없음': '카테고리 없음',
  'AI': 'AI 연구/기술',
  '1': '주요 뉴스',
  '2': '기술/AI',
  '3': '보안/리스크',
  '4': '커뮤니티 이슈',
};

function canonical(s: string): string {
  return s
    .normalize('NFKC')
    .toLowerCase()
    .replace(/[\s·/_\-\u00b7\u2027]/g, '');
}

const NORMALIZED_MAP: Record<string, Category> = Object.fromEntries(
  Object.entries(EXACT_MAP).map(([raw, ui]) => [canonical(raw), ui]),
);

export function fallbackCategoryForSource(source: string | null | undefined): Category {
  const raw = (source ?? '').trim();
  if (!raw) return CATEGORY_FALLBACK;
  if (/reddit|hacker news|\bhn\b/i.test(raw)) return 'AI 커뮤니티';
  return SOURCE_FALLBACK[raw] ?? CATEGORY_FALLBACK;
}

export function normalizeCategory(raw: string | null | undefined, source?: string | null): Category {
  if (!raw || raw.trim().length === 0) return fallbackCategoryForSource(source);
  const trimmed = raw.trim();
  if (trimmed in EXACT_MAP) return EXACT_MAP[trimmed];
  const c = canonical(trimmed);
  if (c in NORMALIZED_MAP) return NORMALIZED_MAP[c];
  return fallbackCategoryForSource(source);
}

export interface CategoryStyle {
  color: string;
  background: string;
  border: string;
}

export const CATEGORY_STYLES: Record<Category, CategoryStyle> = {
  'AI 연구/기술': { color: '#0F766E', background: '#CCFBF1', border: '#99F6E4' },
  'AI 비즈니스': { color: '#1D4ED8', background: '#DBEAFE', border: '#BFDBFE' },
  'AI 제품/서비스': { color: '#047857', background: '#D1FAE5', border: '#A7F3D0' },
  'AI 윤리/정책': { color: '#7C2D12', background: '#FFEDD5', border: '#FED7AA' },
  'AI 인프라': { color: '#4338CA', background: '#E0E7FF', border: '#C7D2FE' },
  'LLM/생성AI': { color: '#6D28D9', background: '#EDE9FE', border: '#DDD6FE' },
  '로보틱스/자율주행': { color: '#0E7490', background: '#CFFAFE', border: '#A5F3FC' },
  '기타 테크': { color: '#475569', background: '#F1F5F9', border: '#E2E8F0' },
  'AI 심층': { color: '#7E22CE', background: '#F3E8FF', border: '#E9D5FF' },
  'AI 스타트업': { color: '#BE123C', background: '#FFE4E6', border: '#FECDD3' },
  '테크 전반': { color: '#334155', background: '#E2E8F0', border: '#CBD5E1' },
  'AI 커뮤니티': { color: '#B45309', background: '#FEF3C7', border: '#FDE68A' },
  '카테고리 없음': { color: '#4B5563', background: '#F3F4F6', border: '#E5E7EB' },
  '주요 뉴스': { color: '#1D4ED8', background: '#DBEAFE', border: '#BFDBFE' },
  '기술/AI': { color: '#0F766E', background: '#CCFBF1', border: '#99F6E4' },
  '보안/리스크': { color: '#991B1B', background: '#FEE2E2', border: '#FECACA' },
  '커뮤니티 이슈': { color: '#B45309', background: '#FEF3C7', border: '#FDE68A' },
};

export function categoryStyle(category: Category): CategoryStyle {
  return CATEGORY_STYLES[category] ?? CATEGORY_STYLES[CATEGORY_FALLBACK];
}

export function filterByCategory<T extends { category: Category }>(
  articles: T[],
  target: '전체' | Category,
): T[] {
  if (target === '전체') return articles;
  return articles.filter(a => a.category === target);
}

const REVERSE_INDEX: Record<Category, string[]> = (() => {
  const idx: Partial<Record<Category, string[]>> = {};
  for (const [raw, ui] of Object.entries(EXACT_MAP)) {
    (idx[ui] ??= []).push(raw);
  }
  return idx as Record<Category, string[]>;
})();

export function getRawCategoriesFor(ui: Category): string[] {
  return REVERSE_INDEX[ui] ?? [];
}
