/**
 * frontend/src/data/categories.ts — final 7-category normalization and colors.
 */

export const CATEGORIES = [
  'AI 연구',
  'AI 심층',
  'AI 스타트업',
  'AI 윤리',
  'AI 비즈니스',
  'AI 커뮤니티',
  '테크 전반',
] as const;

export type Interest = (typeof CATEGORIES)[number];
export type DemoCategory = '주요 뉴스' | '기술/AI' | '보안/리스크' | '커뮤니티 이슈';
export type Category = Interest | DemoCategory;

export const CATEGORY_FALLBACK: Interest = '테크 전반';

const SOURCE_FALLBACK: Record<string, Interest> = {
  'TechCrunch': 'AI 스타트업',
  'MIT Technology Review': 'AI 심층',
  'The Guardian Tech': 'AI 윤리',
  'IEEE Spectrum': '테크 전반',
  'The Decoder': 'AI 심층',
  'VentureBeat AI': 'AI 비즈니스',
  'The Verge': '테크 전반',
  'Medium': '테크 전반',
  'Quanta Magazine': 'AI 연구',
};

const EXACT_MAP: Record<string, Category> = {
  'AI 연구': 'AI 연구',
  'AI 연구/기술': 'AI 연구',
  'AI 심층': 'AI 심층',
  'AI 심층/기술': 'AI 심층',
  'AI/스타트업': 'AI 스타트업',
  'AI 스타트업': 'AI 스타트업',
  'AI 윤리': 'AI 윤리',
  'AI 윤리/정책': 'AI 윤리',
  '윤리-정책': 'AI 윤리',
  'AI 비즈니스': 'AI 비즈니스',
  'AI 커뮤니티': 'AI 커뮤니티',
  'LLM 커뮤니티': 'AI 커뮤니티',
  'LLM/생성AI': 'AI 심층',
  'AI 제품': 'AI 비즈니스',
  'AI 제품/서비스': 'AI 비즈니스',
  'AI 인프라': '테크 전반',
  'AI/반도체': '테크 전반',
  '반도체': '테크 전반',
  '로보틱스/자율주행': '테크 전반',
  '테크 전반': '테크 전반',
  '테크전반': '테크 전반',
  '기타 테크': '테크 전반',
  '카테고리 없음': '테크 전반',
  'AI': 'AI 심층',
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

function looksLikeStartup(source: string, text: string): boolean {
  return source === 'TechCrunch'
    && /startup|funding|funded|raises|raised|acquire|acquired|acquisition|seed round|series [ab]/i.test(text);
}

export function fallbackCategoryForSource(source: string | null | undefined, text = ''): Interest {
  const raw = (source ?? '').trim();
  if (!raw) return CATEGORY_FALLBACK;
  if (/reddit|hacker news|\bhn\b|lemmy/i.test(raw)) return 'AI 커뮤니티';
  if (looksLikeStartup(raw, text)) return 'AI 스타트업';
  return SOURCE_FALLBACK[raw] ?? CATEGORY_FALLBACK;
}

export function normalizeCategory(raw: string | null | undefined, source?: string | null, text = ''): Category {
  if (!raw || raw.trim().length === 0) return fallbackCategoryForSource(source, text);
  const trimmed = raw.trim();
  if (trimmed in EXACT_MAP) return EXACT_MAP[trimmed];
  const c = canonical(trimmed);
  if (c in NORMALIZED_MAP) return NORMALIZED_MAP[c];
  return fallbackCategoryForSource(source, text);
}

export interface CategoryStyle {
  color: string;
  background: string;
  border: string;
}

export const CATEGORY_STYLES: Record<Category, CategoryStyle> = {
  'AI 연구': { color: '#0F766E', background: '#CCFBF1', border: '#99F6E4' },
  'AI 심층': { color: '#7E22CE', background: '#F3E8FF', border: '#E9D5FF' },
  'AI 스타트업': { color: '#BE123C', background: '#FFE4E6', border: '#FECDD3' },
  'AI 윤리': { color: '#7C2D12', background: '#FFEDD5', border: '#FED7AA' },
  'AI 비즈니스': { color: '#1D4ED8', background: '#DBEAFE', border: '#BFDBFE' },
  'AI 커뮤니티': { color: '#B45309', background: '#FEF3C7', border: '#FDE68A' },
  '테크 전반': { color: '#334155', background: '#E2E8F0', border: '#CBD5E1' },
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
