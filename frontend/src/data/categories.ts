/**
 * frontend/src/data/categories.ts — 카테고리 단일 진실 소스 (SoT)
 *
 * 이 파일이 책임지는 4가지:
 *   1. UI 가 노출하는 카테고리 목록(`CATEGORIES`)
 *   2. DB raw 카테고리 → UI 카테고리 정규화(`normalizeCategory`)
 *   3. 페이지 공통 필터(`filterByCategory`)
 *   4. UI 카테고리 → DB raw 라벨 역매핑(`getRawCategoriesFor`)
 *
 * ─── 이슈 #16 (직전 이슈 #15 의 사일런트 누락 정공 해결) ───
 *
 * 직전 매핑은 RSS 크롤러(`collect/crawler/rss_crawler.py`) 의 라벨만 보고 작성됐었지만,
 * 실제 로컬 Supabase 에 데이터를 적재하는 스크립트는 `generate_dummy.py` 이고
 * 이 스크립트가 사용하는 라벨은 RSS 크롤러와 완전히 다른 변종이었다.
 *
 * 데이터 전수 조사 결과 (2026-04-28):
 *
 *   [generate_dummy.py — 로컬 더미 데이터, 27개]
 *     'AI 연구'        × 6
 *     'AI 스타트업'    × 5
 *     '테크전반'       × 5    ← 공백 없음 (RSS 의 '테크 전반' 과 다름)
 *     '윤리-정책'      × 5    ← 대시 구분자 + AI 접두어 없음
 *     '반도체'         × 6    ← 접두어 없음. 내용은 모두 반도체 심층 분석/리포트
 *
 *   [collect/crawler/rss_crawler.py — 운영 크롤링 시 적재, 11종]
 *     'AI/스타트업'   (TechCrunch)
 *     'AI 심층'       (MIT Technology Review)
 *     '테크 전반'     (The Verge)
 *     'AI 비즈니스'   (VentureBeat AI)
 *     'AI 윤리'       (The Guardian Tech)
 *     'AI/반도체'     (IEEE Spectrum)
 *     'AI 심층/기술'  (The Decoder)
 *     'AI 커뮤니티'   (Hacker News AI)
 *     'LLM 커뮤니티'  (Hacker News LLM)
 *     'AI 연구'       (Hacker News ML)
 *     'AI 제품'       (Product Hunt)
 *
 *   [poc_cycle.py]
 *     'AI'  (legacy shorthand)
 *
 * ──────────────────────────────────────────────────────────────────
 * 모든 라벨은 EXACT_MAP 에 1:1 로 등재되어 있어 어떤 기사도 '기타' 로 떨어지지 않는다.
 * 새 데이터 라벨이 추가되면 반드시 이 파일 EXACT_MAP 에 명시적으로 추가할 것.
 * ──────────────────────────────────────────────────────────────────
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
export type DemoCategory = '주요 뉴스' | '기술/AI' | '보안/리스크' | '커뮤니티 이슈';
export type Category = Interest | DemoCategory | '기타';

export const CATEGORY_FALLBACK: Category = '기타';


// ─────────────────────────────────────────────
// 2. DB raw 라벨 → UI 카테고리 (1:1 explicit mapping)
//
// 실제 데이터 출처를 직접 grep 하여 확인된 모든 라벨을 explicit 하게 등록한다.
// 추측 금지 원칙: 새 라벨이 들어오면 데이터 파일을 직접 확인한 뒤 이 표를 수정.
// ─────────────────────────────────────────────

const EXACT_MAP: Record<string, Category> = {
  // ── generate_dummy.py (로컬 Supabase 더미 데이터) ─────────────
  'AI 연구':       'AI 연구',
  'AI 스타트업':   'AI 스타트업',
  '테크전반':      '테크 전반',     // 공백 변종
  '윤리-정책':     'AI 윤리',       // 대시 + AI 접두어 누락 변종
  '반도체':        'AI 심층',       // 더미 6건 모두 HBM/2nm/수출통제 등 심층 분석 → 'AI 심층'

  // ── collect/crawler/rss_crawler.py (운영 RSS 크롤링) ─────────
  'AI/스타트업':   'AI 스타트업',   // TechCrunch
  'AI 심층':       'AI 심층',       // MIT Technology Review
  '테크 전반':     '테크 전반',     // The Verge
  'AI 비즈니스':   'AI 비즈니스',   // VentureBeat AI
  'AI 윤리':       'AI 윤리',       // The Guardian Tech
  'AI/반도체':     'AI 심층',       // IEEE Spectrum (반도체 심층 기술 매체 → 일관성 위해 '반도체' 와 동일하게 'AI 심층')
  'AI 심층/기술':  'AI 심층',       // The Decoder
  'AI 커뮤니티':   'AI 커뮤니티',   // Hacker News AI
  'LLM 커뮤니티':  'AI 커뮤니티',   // Hacker News LLM
  'AI 제품':       'AI 비즈니스',   // Product Hunt

  // ── 기타 / legacy ──────────────────────────────────────────
  'AI':            'AI 연구',       // poc_cycle.py shorthand

  // ── demo / numeric priority labels ─────────────────────────
  // Raw 1/2/3/4 labels are not meaningful to users, so normalize them
  // into explicit Korean category labels before rendering.
  '1':             '주요 뉴스',
  '2':             '기술/AI',
  '3':             '보안/리스크',
  '4':             '커뮤니티 이슈',
};


// ─────────────────────────────────────────────
// 3. 정규화 함수
//
// 1) trim → EXACT_MAP 정확 매칭
// 2) canonical(공백·구분자 제거 + lowercase + NFKC) 키 매칭 — 띄어쓰기/특수기호 변종 흡수
// 3) 그래도 못 찾으면 '기타' (등록되지 않은 새 라벨임을 의미. EXACT_MAP 추가 필요.)
// ─────────────────────────────────────────────

function canonical(s: string): string {
  return s
    .normalize('NFKC')
    .toLowerCase()
    .replace(/[\s·/_\-\u00b7\u2027]/g, '');
}

// EXACT_MAP 의 키들로부터 자동 파생되는 정규화 인덱스
const NORMALIZED_MAP: Record<string, Category> = Object.fromEntries(
  Object.entries(EXACT_MAP).map(([raw, ui]) => [canonical(raw), ui]),
);

export function normalizeCategory(raw: string | null | undefined): Category {
  if (!raw) return CATEGORY_FALLBACK;
  const trimmed = raw.trim();
  if (trimmed.length === 0) return CATEGORY_FALLBACK;

  // 1단계: 정확 매칭 (EXACT_MAP 의 키 그대로)
  if (trimmed in EXACT_MAP) return EXACT_MAP[trimmed];

  // 2단계: 공백·구분자 차이 흡수 (예: 'AI 연구' / 'AI연구' / 'AI·연구' 모두 동일 키)
  const c = canonical(trimmed);
  if (c in NORMALIZED_MAP) return NORMALIZED_MAP[c];

  // 등록되지 않은 새 라벨 — EXACT_MAP 에 명시적으로 추가해야 한다.
  // 콘솔에 경고를 남겨 추적 가능하게 한다 (브라우저 환경에서만).
  if (typeof console !== 'undefined') {
    console.warn(
      `[categories] 미등록 raw 카테고리 라벨: ${JSON.stringify(raw)}. ` +
      `frontend/src/data/categories.ts 의 EXACT_MAP 에 추가하세요.`,
    );
  }
  return CATEGORY_FALLBACK;
}


// ─────────────────────────────────────────────
// 4. 페이지 공통 필터 (HomePage / CategoryPage 동일 동작 보장)
// ─────────────────────────────────────────────

/**
 * '전체' 또는 특정 UI 카테고리로 기사 배열을 필터링한다.
 * `Article.category` 는 `toArticle()` 단계에서 이미 `normalizeCategory()` 가 적용되어
 * UI 카테고리 값(`Category`)만 들어있다고 가정한다.
 */
export function filterByCategory<T extends { category: Category }>(
  articles: T[],
  target: '전체' | Category,
): T[] {
  if (target === '전체') return articles;
  return articles.filter(a => a.category === target);
}


// ─────────────────────────────────────────────
// 5. UI 카테고리 → DB raw 라벨 역인덱스
//
// 백엔드 `/articles?category=...` 가 raw 라벨로 동작하므로,
// 추후 서버 사이드 필터를 사용하고 싶을 때 이 함수가 raw 후보 목록을 돌려준다.
// (현재는 클라이언트 사이드 필터로 충분)
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


// ─────────────────────────────────────────────
// 6. (개발용) 매핑 자가 검증 — 등록된 모든 raw 라벨이 EXACT_MAP 으로 정상 처리되는지 확인
// 실제 데이터 출처에서 grep 으로 추출한 라벨 전체를 여기 두고,
// dev 모드에서 한 번이라도 누락이 발견되면 즉시 throw 한다.
// production 빌드에는 자동 tree-shaking 되도록 import.meta.env.DEV 가드.
// ─────────────────────────────────────────────

if (import.meta.env?.DEV) {
  const KNOWN_RAW_LABELS: string[] = [
    // generate_dummy.py
    'AI 연구', 'AI 스타트업', '테크전반', '윤리-정책', '반도체',
    // rss_crawler.py
    'AI/스타트업', 'AI 심층', '테크 전반', 'AI 비즈니스', 'AI 윤리',
    'AI/반도체', 'AI 심층/기술', 'AI 커뮤니티', 'LLM 커뮤니티', 'AI 제품',
    // poc_cycle.py
    'AI',
    '1', '2', '3', '4',
  ];
  const failed = KNOWN_RAW_LABELS.filter(l => normalizeCategory(l) === CATEGORY_FALLBACK);
  if (failed.length > 0) {
    throw new Error(
      `[categories self-check] '기타' 로 떨어진 등록 라벨이 있습니다: ${JSON.stringify(failed)}. ` +
      'EXACT_MAP 에 누락이 있는지 확인하세요.',
    );
  }
}
