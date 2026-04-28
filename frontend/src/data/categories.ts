/**
 * frontend/src/data/categories.ts — 카테고리 단일 진실 소스(SoT)
 *
 * 이 파일은 다음 4가지를 한 곳에서 책임진다.
 *   1. UI 가 노출하는 카테고리 목록(`CATEGORIES`)
 *   2. DB 가 저장하는 raw 카테고리 → UI 카테고리 정규화(`normalizeCategory`)
 *   3. 페이지 간 공통 필터링 로직(`filterByCategory`)
 *   4. UI 카테고리 → DB raw 카테고리 역매핑(`getRawCategoriesFor`)
 *
 * 어디에서든 카테고리를 다룰 때는 반드시 이 모듈을 통해야 한다.
 * 페이지 컴포넌트에 카테고리 문자열을 하드코딩하는 것을 금지한다.
 *
 * 배경 (이슈 #15)
 *   - 기존에는 `articles.ts`, `HomePage.tsx`, `CategoryPage.tsx`, `OnboardingPage.tsx`
 *     네 곳에 카테고리 배열이 분산 하드코딩되어 라벨 추가/변경 시 동기화 누락이 잦았다.
 *   - DB 레이블 `AI 심층/기술` (The Decoder) 이 매핑되지 않아 모든 The Decoder 기사가
 *     '기타' 로 떨어지는 사일런트 데이터 누락이 발생.
 *   - 공백 / `·` / `/` 등 구분자 차이가 정확 매칭을 깨트림.
 */

// ─────────────────────────────────────────────
// 1. UI 카테고리 목록 (단일 진실 소스)
// ─────────────────────────────────────────────

export const CATEGORIES = [
  'AI 연구',
  'AI 심층',
  'AI 스타트업',
  'AI 비즈니스',
  'AI 윤리',
  'AI 커뮤니티',
  '테크 전반',
] as const;

export type Interest = (typeof CATEGORIES)[number];
export type Category = Interest | '기타';

export const CATEGORY_FALLBACK: Category = '기타';


// ─────────────────────────────────────────────
// 2. DB raw → UI 정규화
//
// 정확 매칭 → 키 정규화(공백·구분자 제거) 매칭 → 부분 키워드 매칭 → '기타'
// ─────────────────────────────────────────────

// raw 라벨 그대로의 1:1 매핑
const EXACT_MAP: Record<string, Category> = {
  // 현재 RSS 크롤러에서 적재되는 라벨 (collect/crawler/rss_crawler.py 기준)
  'AI 연구':       'AI 연구',
  'AI 심층':       'AI 심층',
  'AI 심층/기술':  'AI 심층',     // The Decoder — 누락이었다 (이슈 #15)
  'AI/스타트업':   'AI 스타트업',
  'AI 비즈니스':   'AI 비즈니스',
  'AI 윤리':       'AI 윤리',
  'AI 커뮤니티':   'AI 커뮤니티',
  'AI/반도체':     'AI 연구',
  'LLM 커뮤니티':  'AI 커뮤니티',
  'AI 제품':       'AI 비즈니스',
  '테크 전반':     '테크 전반',

  // 구버전·잠재적 변형 호환
  'AI 스타트업':   'AI 스타트업',
  'AI 연구·심층':  'AI 심층',
  'AI 윤리·정책':  'AI 윤리',
  'LLM':           'AI 연구',
  'AI 일반':       'AI 연구',
};

// 공백·구분자 차이를 흡수하기 위한 정규화 키
//   "AI 연구" / "AI연구" / "AI/연구" / "AI·연구" 가 동일 키가 되도록.
function canonical(s: string): string {
  return s
    .normalize('NFKC')
    .toLowerCase()
    .replace(/[\s·/_\-\u00b7\u2027]/g, '');
}

// 정규화 키 매핑 (EXACT_MAP 으로부터 자동 생성)
const NORMALIZED_MAP: Record<string, Category> = Object.fromEntries(
  Object.entries(EXACT_MAP).map(([raw, ui]) => [canonical(raw), ui]),
);

// 키워드 부분 매칭(최후 폴백)
//   완전히 새로운 라벨이 들어와도 핵심 키워드로 분류하기 위함.
//   순서 중요: 더 구체적인 매칭이 위에.
const KEYWORD_RULES: { keys: string[]; ui: Category }[] = [
  { keys: ['스타트업', 'startup'],            ui: 'AI 스타트업' },
  { keys: ['비즈니스', '제품', 'product'],    ui: 'AI 비즈니스' },
  { keys: ['윤리', '정책', '규제'],           ui: 'AI 윤리' },
  { keys: ['커뮤니티', 'reddit', 'forum'],    ui: 'AI 커뮤니티' },
  { keys: ['심층', '리포트', 'analysis'],     ui: 'AI 심층' },
  { keys: ['연구', '논문', 'llm', 'paper'],   ui: 'AI 연구' },
  { keys: ['테크', '일반', 'tech'],           ui: '테크 전반' },
];

export function normalizeCategory(raw: string | null | undefined): Category {
  if (!raw) return CATEGORY_FALLBACK;

  const trimmed = raw.trim();
  if (trimmed.length === 0) return CATEGORY_FALLBACK;

  // 1) 정확 매칭
  if (trimmed in EXACT_MAP) return EXACT_MAP[trimmed];

  // 2) 정규화 키 매칭 (공백·구분자 차이 흡수)
  const c = canonical(trimmed);
  if (c in NORMALIZED_MAP) return NORMALIZED_MAP[c];

  // 3) 키워드 부분 매칭
  for (const rule of KEYWORD_RULES) {
    if (rule.keys.some(k => c.includes(canonical(k)))) return rule.ui;
  }

  return CATEGORY_FALLBACK;
}


// ─────────────────────────────────────────────
// 3. 페이지 공통 필터 (HomePage, CategoryPage 동일 동작 보장)
// ─────────────────────────────────────────────

/**
 * '전체' 또는 특정 UI 카테고리로 기사 배열을 필터링한다.
 * Article.category 는 toArticle() 단계에서 이미 normalizeCategory() 가 적용되어
 * UI 카테고리(`Category`) 값만 들어있다고 가정한다.
 */
export function filterByCategory<T extends { category: Category }>(
  articles: T[],
  target: '전체' | Category,
): T[] {
  if (target === '전체') return articles;
  return articles.filter(a => a.category === target);
}


// ─────────────────────────────────────────────
// 4. UI 카테고리 → DB raw 라벨 역매핑
//
// 백엔드 `/articles?category=...` 가 raw 라벨로 동작하므로,
// 서버 사이드 필터를 사용하고 싶을 때 이 함수로 raw 후보를 얻는다.
// (현재는 클라이언트 사이드 필터로 충분하지만 추후 확장 대비)
// ─────────────────────────────────────────────

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
