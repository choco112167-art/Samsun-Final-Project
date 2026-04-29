/**
 * frontend/src/data/mock-articles.ts — DEV ONLY 더미 응답 폴백
 *
 * 용도:
 *   로컬 `npm run dev` 중 백엔드(`http://localhost:8000`) 가 떠있지 않거나
 *   네트워크 오류로 fetch 가 실패할 때, `data/api.ts` 의 `request()` 가
 *   이 모듈을 동적 import 하여 mock 응답을 돌려준다.
 *
 * 보장:
 *   - 카테고리 라벨은 **운영 RSS 크롤러(`collect/crawler/rss_crawler.py`)** 와
 *     **로컬 `generate_dummy.py`** 양쪽에 등장하는 실제 raw 문자열 그대로 사용.
 *     → `data/categories.ts` 의 정규화 파이프라인을 우회하지 않고
 *       그대로 통과시켜 매핑 동작까지 함께 검증한다.
 *   - 7개 UI 카테고리 (AI 연구 / AI 심층 / AI 스타트업 / AI 비즈니스 /
 *     AI 윤리 / AI 커뮤니티 / 테크 전반) 각각에 최소 1건 이상 분포.
 *
 * Tree-shaking:
 *   `api.ts` 에서 `import.meta.env.DEV` 가드 + 동적 `import()` 로만 로드.
 *   → production 빌드에는 이 파일 내용이 일체 포함되지 않는다.
 */

import type { ApiArticle, AbsenceSummaryResponse, OnboardingResponse } from './api';

// ─────────────────────────────────────────────
// 10건 mock — 7 UI 카테고리 전부 ≥1, 라벨 변종 5종 검증
// ─────────────────────────────────────────────

const NOW = Date.now();
const hoursAgo = (h: number): string =>
  new Date(NOW - h * 3_600_000).toISOString();

export const MOCK_API_ARTICLES: ApiArticle[] = [
  // 1) AI 연구 — MIT Technology Review
  {
    url_hash:          'mock0001aa11bb22cc33dd44ee55ff6601',
    url:               'https://www.technologyreview.com/mock/gpt5-architecture',
    title:             'OpenAI, GPT-5 아키텍처 공개 — Mixture-of-Depths 도입',
    source:            'MIT Technology Review',
    source_type:       'media',
    category:          'AI 연구',          // raw → UI: 'AI 연구'
    country:           'US',
    keywords:          ['GPT-5', 'MoD', 'OpenAI', '아키텍처'],
    published_at:      hoursAgo(2),
    collected_at:      hoursAgo(1),
    content:           'OpenAI revealed details of the GPT-5 architecture featuring Mixture-of-Depths routing for adaptive compute allocation per token.',
    credibility_score: 0.95,
    fact_label:        'FACT',
    translation:       'OpenAI 가 토큰별 적응적 연산 할당이 가능한 Mixture-of-Depths 라우팅을 채택한 GPT-5 아키텍처 상세를 공개했다.',
    summary_formal:    'OpenAI 가 GPT-5 의 Mixture-of-Depths 기반 적응형 연산 아키텍처를 공식 발표했다.',
    summary_casual:    'GPT-5 안에 토큰마다 연산량 다르게 쓰는 새 구조 들어갔어!',
    is_new:            true,
    is_breaking:       false,
    time_ago:          '2시간 전',
    source_color:      '#0891B2',
  },

  // 2) AI 심층 — The Decoder (라벨 변종 검증: 'AI 심층/기술')
  {
    url_hash:          'mock0002aa11bb22cc33dd44ee55ff6602',
    url:               'https://the-decoder.com/mock/transformer-scaling-limits',
    title:             '트랜스포머 스케일링 한계 분석: 데이터 vs 파라미터 트레이드오프',
    source:            'The Decoder',
    source_type:       'media',
    category:          'AI 심층/기술',      // raw → UI: 'AI 심층'
    country:           'EU',
    keywords:          ['Transformer', 'Scaling Law', 'Chinchilla', '심층분석'],
    published_at:      hoursAgo(5),
    collected_at:      hoursAgo(4),
    content:           'A deep analysis of transformer scaling limits, comparing parameter scaling vs data scaling regimes.',
    credibility_score: 0.88,
    fact_label:        'FACT',
    translation:       '트랜스포머 스케일링 한계에 대한 심층 분석으로, 파라미터 확장과 데이터 확장 체제를 비교한다.',
    summary_formal:    'Chinchilla 법칙 이후 트랜스포머 스케일링의 한계와 데이터·파라미터 트레이드오프를 정밀 분석한 리포트.',
    summary_casual:    '모델 크기만 키운다고 안되고 데이터도 같이 늘려야 한다는 분석!',
    is_new:            true,
    is_breaking:       false,
    time_ago:          '5시간 전',
    source_color:      '#DC2626',
  },

  // 3) AI 스타트업 — TechCrunch (라벨 변종 검증: 'AI/스타트업')
  {
    url_hash:          'mock0003aa11bb22cc33dd44ee55ff6603',
    url:               'https://techcrunch.com/mock/anthropic-series-e',
    title:             'Anthropic, Series E 라운드 80억 달러 마감 — 엔터프라이즈 시장 본격 공략',
    source:            'TechCrunch',
    source_type:       'media',
    category:          'AI/스타트업',       // raw → UI: 'AI 스타트업'
    country:           'US',
    keywords:          ['Anthropic', 'Series E', '투자', '엔터프라이즈'],
    published_at:      hoursAgo(8),
    collected_at:      hoursAgo(7),
    content:           'Anthropic closed an $8B Series E led by Lightspeed and Sequoia, valuing the company at $180B.',
    credibility_score: 0.93,
    fact_label:        'FACT',
    translation:       'Anthropic 이 Lightspeed·Sequoia 주도로 Series E 80억 달러를 마감했으며 기업가치는 1,800억 달러로 평가됐다.',
    summary_formal:    'Anthropic 이 80억 달러 Series E 마감으로 1,800억 달러 기업가치를 인정받으며 엔터프라이즈 AI 시장 확장에 나선다.',
    summary_casual:    'Anthropic 80억 달러 또 투자받았어! 기업가치 1,800억 달러래.',
    is_new:            true,
    is_breaking:       true,
    time_ago:          '8시간 전',
    source_color:      '#4F46E5',
  },

  // 4) AI 비즈니스 — VentureBeat AI
  {
    url_hash:          'mock0004aa11bb22cc33dd44ee55ff6604',
    url:               'https://venturebeat.com/mock/enterprise-ai-adoption-2026',
    title:             '엔터프라이즈 AI 도입률 73% 돌파 — Gartner 2026 리포트',
    source:            'VentureBeat AI',
    source_type:       'media',
    category:          'AI 비즈니스',       // raw → UI: 'AI 비즈니스'
    country:           'US',
    keywords:          ['엔터프라이즈', '도입률', 'Gartner', 'ROI'],
    published_at:      hoursAgo(12),
    collected_at:      hoursAgo(11),
    content:           'Gartner reports 73% of enterprises now use AI in production, up from 47% a year ago. ROI median: 3.2x.',
    credibility_score: 0.89,
    fact_label:        'FACT',
    translation:       'Gartner 에 따르면 기업의 73% 가 AI 를 운영 환경에 도입(전년 47%) 했으며 중앙값 ROI 는 3.2배에 달했다.',
    summary_formal:    '엔터프라이즈 AI 운영 도입률이 1년 만에 47% 에서 73% 로 급증, 중앙값 ROI 3.2배를 기록했다.',
    summary_casual:    '회사 73% 가 이미 AI 쓴대 — 1년 전 47% 에서 확 늘었어. 평균 3배 이상 남는 장사래.',
    is_new:            false,
    is_breaking:       false,
    time_ago:          '12시간 전',
    source_color:      '#D97706',
  },

  // 5) AI 비즈니스 — Product Hunt (라벨 변종 검증: 'AI 제품')
  {
    url_hash:          'mock0005aa11bb22cc33dd44ee55ff6605',
    url:               'https://www.producthunt.com/mock/notion-ai-blocks',
    title:             'Notion AI Blocks 정식 출시 — 문서별 자동 워크플로우 구성',
    source:            'Product Hunt',
    source_type:       'media',
    category:          'AI 제품',          // raw → UI: 'AI 비즈니스'
    country:           'US',
    keywords:          ['Notion', 'AI Blocks', '워크플로우', 'SaaS'],
    published_at:      hoursAgo(18),
    collected_at:      hoursAgo(17),
    content:           'Notion launched AI Blocks, allowing users to compose document-specific AI workflows without code.',
    credibility_score: 0.78,
    fact_label:        'FACT',
    translation:       'Notion 이 코드 없이 문서별 AI 워크플로우를 구성할 수 있는 AI Blocks 를 정식 출시했다.',
    summary_formal:    'Notion AI Blocks 출시로 문서 단위의 코드 프리 AI 워크플로우 구성이 가능해졌다.',
    summary_casual:    '노션에서 코드 없이도 AI 워크플로우 짤 수 있게 됐어!',
    is_new:            false,
    is_breaking:       false,
    time_ago:          '18시간 전',
    source_color:      '#DA552F',
  },

  // 6) AI 윤리 — The Guardian Tech
  {
    url_hash:          'mock0006aa11bb22cc33dd44ee55ff6606',
    url:               'https://www.theguardian.com/mock/eu-ai-act-enforcement',
    title:             'EU AI Act 본격 시행 1년 — 27개 조사 케이스 분석',
    source:            'The Guardian Tech',
    source_type:       'media',
    category:          'AI 윤리',          // raw → UI: 'AI 윤리'
    country:           'EU',
    keywords:          ['EU AI Act', '규제', '시행', '조사'],
    published_at:      hoursAgo(20),
    collected_at:      hoursAgo(19),
    content:           'One year into EU AI Act enforcement, 27 active investigations span hiring algorithms, biometric ID, and generative content.',
    credibility_score: 0.92,
    fact_label:        'FACT',
    translation:       'EU AI Act 시행 1년이 경과한 가운데 채용 알고리즘·생체 인증·생성형 콘텐츠 분야에서 27건의 조사가 진행 중이다.',
    summary_formal:    'EU AI Act 시행 첫 해 동안 27건의 능동 조사가 채용·생체·생성 AI 영역에서 진행됐다.',
    summary_casual:    'EU 가 AI 규제 시작한 지 1년 됐는데, 벌써 27건 조사 중이래.',
    is_new:            false,
    is_breaking:       false,
    time_ago:          '20시간 전',
    source_color:      '#059669',
  },

  // 7) AI 커뮤니티 — Hacker News AI
  {
    url_hash:          'mock0007aa11bb22cc33dd44ee55ff6607',
    url:               'https://news.ycombinator.com/mock/local-llm-thread',
    title:             '[HN 인기글] 로컬 LLM 으로 RAG 운영 후기 — 비용 92% 절감',
    source:            'Reddit r/MachineLearning',
    source_type:       'community',
    category:          'AI 커뮤니티',       // raw → UI: 'AI 커뮤니티'
    country:           'US',
    keywords:          ['로컬LLM', 'RAG', 'Ollama', '비용절감'],
    published_at:      hoursAgo(24),
    collected_at:      hoursAgo(23),
    content:           'A community thread reports 92% cost reduction by replacing GPT-4 RAG with local Llama 3.1 70B on a single A100.',
    credibility_score: 0.55,
    fact_label:        'UNVERIFIED',
    translation:       '커뮤니티 글에 따르면 GPT-4 RAG 를 단일 A100 위 로컬 Llama 3.1 70B 로 대체해 92% 비용 절감을 달성했다고 한다.',
    summary_formal:    '로컬 Llama 3.1 70B 기반 RAG 로 전환 후 GPT-4 대비 92% 비용 절감을 보고한 커뮤니티 사례.',
    summary_casual:    'GPT-4 대신 로컬 Llama 70B 로 바꿨더니 비용 92% 줄었대 — 진짜?',
    is_new:            false,
    is_breaking:       false,
    time_ago:          '1일 전',
    source_color:      '#FF4500',
  },

  // 8) AI 커뮤니티 — Hacker News LLM (라벨 변종 검증: 'LLM 커뮤니티')
  {
    url_hash:          'mock0008aa11bb22cc33dd44ee55ff6608',
    url:               'https://news.ycombinator.com/mock/llm-eval-debate',
    title:             '[HN 토론] LLM 평가 벤치마크 신뢰성 논쟁 격화',
    source:            'Reddit r/LocalLLaMA',
    source_type:       'community',
    category:          'LLM 커뮤니티',      // raw → UI: 'AI 커뮤니티'
    country:           'US',
    keywords:          ['벤치마크', 'MMLU', '평가', '논쟁'],
    published_at:      hoursAgo(30),
    collected_at:      hoursAgo(29),
    content:           'A heated HN debate on LLM benchmark contamination and the case for held-out evaluation.',
    credibility_score: 0.42,
    fact_label:        'UNVERIFIED',
    translation:       'LLM 벤치마크 오염과 비공개 평가 셋의 필요성을 둘러싼 HN 의 격론.',
    summary_formal:    'LLM 벤치마크 오염 문제와 held-out 평가 도입 필요성을 둘러싼 커뮤니티 토론이 격화되고 있다.',
    summary_casual:    'LLM 벤치마크 점수 너무 믿지 말라는 글이 인기야.',
    is_new:            false,
    is_breaking:       false,
    time_ago:          '1일 전',
    source_color:      '#FF4500',
  },

  // 9) 테크 전반 — The Verge
  {
    url_hash:          'mock0009aa11bb22cc33dd44ee55ff6609',
    url:               'https://www.theverge.com/mock/apple-vision-pro-2',
    title:             'Apple Vision Pro 2 발표 — 무게 35% 감소, 가격 동결',
    source:            'The Verge',
    source_type:       'media',
    category:          '테크 전반',         // raw → UI: '테크 전반'
    country:           'US',
    keywords:          ['Apple', 'Vision Pro 2', 'XR', '발표'],
    published_at:      hoursAgo(36),
    collected_at:      hoursAgo(35),
    content:           'Apple unveiled Vision Pro 2 with 35% weight reduction and same $3,499 price.',
    credibility_score: 0.91,
    fact_label:        'FACT',
    translation:       '애플이 무게를 35% 줄이고 가격을 동결한 Vision Pro 2 를 공개했다.',
    summary_formal:    '애플 Vision Pro 2 가 무게 35% 절감과 3,499 달러 가격 동결로 공개됐다.',
    summary_casual:    'Vision Pro 2 나왔는데 더 가벼워지고 가격 그대로래!',
    is_new:            false,
    is_breaking:       false,
    time_ago:          '1일 전',
    source_color:      '#7C3AED',
  },

  // 10) AI 심층 — IEEE Spectrum (라벨 변종 검증: 'AI/반도체')
  {
    url_hash:          'mock0010aa11bb22cc33dd44ee55ff6610',
    url:               'https://spectrum.ieee.org/mock/ai-accelerator-survey',
    title:             '2026 AI 가속기 종합 비교: H200 vs MI400 vs TPU v6',
    source:            'IEEE Spectrum',
    source_type:       'media',
    category:          'AI/반도체',         // raw → UI: 'AI 심층'
    country:           'US',
    keywords:          ['H200', 'MI400', 'TPU v6', '가속기', '심층비교'],
    published_at:      hoursAgo(48),
    collected_at:      hoursAgo(47),
    content:           'A technical survey of 2026 AI accelerators: NVIDIA H200, AMD MI400, Google TPU v6 — performance, memory, software stack.',
    credibility_score: 0.94,
    fact_label:        'FACT',
    translation:       '2026년 AI 가속기 기술 종합 비교 — NVIDIA H200, AMD MI400, Google TPU v6 의 성능·메모리·소프트웨어 스택을 분석한다.',
    summary_formal:    '2026 주요 AI 가속기 3종(H200·MI400·TPU v6) 의 성능, 메모리 대역폭, 소프트웨어 스택을 정밀 비교한 심층 리포트.',
    summary_casual:    'NVIDIA·AMD·구글 AI 칩 3대장 비교 리포트 나왔어!',
    is_new:            false,
    is_breaking:       false,
    time_ago:          '2일 전',
    source_color:      '#0369A1',
  },
];


// ─────────────────────────────────────────────
// path 패턴 → mock 응답 매처
//   - api.ts 의 `request()` 가 fetch 실패 시 호출.
//   - 매칭 안 되면 `undefined` 반환 → 호출자가 원래 에러를 throw.
// ─────────────────────────────────────────────

interface ParsedPath {
  pathname: string;
  params: URLSearchParams;
}

function parsePath(path: string): ParsedPath {
  const [pathname, search = ''] = path.split('?');
  return { pathname, params: new URLSearchParams(search) };
}

function filterArticles(params: URLSearchParams): ApiArticle[] {
  let list: ApiArticle[] = MOCK_API_ARTICLES.slice();
  const cat = params.get('category');
  if (cat && cat !== '전체') {
    list = list.filter(a => a.category === cat);
  }
  const src = params.get('source');
  if (src) list = list.filter(a => a.source === src);
  const stype = params.get('source_type');
  if (stype) list = list.filter(a => a.source_type === stype);
  const isBreaking = params.get('is_breaking');
  if (isBreaking !== null) {
    const want = isBreaking === 'true';
    list = list.filter(a => a.is_breaking === want);
  }

  list = list.sort(
    (a, b) => new Date(b.published_at).getTime() - new Date(a.published_at).getTime(),
  );

  const offset = Number(params.get('offset') ?? 0);
  const limit  = Number(params.get('limit')  ?? list.length);
  return list.slice(offset, offset + limit);
}

export function getMockFallback<T>(
  path: string,
  method: string = 'GET',
): T | undefined {
  const { pathname, params } = parsePath(path);
  const m = method.toUpperCase();

  // GET /articles
  if (pathname === '/articles' && m === 'GET') {
    return filterArticles(params) as unknown as T;
  }

  // GET /article/:hash
  if (pathname.startsWith('/article/') && m === 'GET') {
    const hash = pathname.slice('/article/'.length);
    const found = MOCK_API_ARTICLES.find(a => a.url_hash === hash);
    return (found ?? MOCK_API_ARTICLES[0]) as unknown as T;
  }

  // GET /hot/:date
  if (pathname.startsWith('/hot/') && m === 'GET') {
    const list = MOCK_API_ARTICLES
      .slice()
      .sort((a, b) => b.credibility_score - a.credibility_score)
      .map((a, i) => ({ ...a, view_count: 1000 - i * 80 }));
    return list as unknown as T;
  }

  // GET /feed/:userId
  if (pathname.startsWith('/feed/') && m === 'GET') {
    const feed = MOCK_API_ARTICLES.slice(0, 5).map((a, i) => ({
      ...a,
      similarity: 0.9 - i * 0.05,
    }));
    return { feed } as unknown as T;
  }

  // GET /search
  if (pathname === '/search' && m === 'GET') {
    const q = (params.get('q') ?? '').toLowerCase();
    const matches = q
      ? MOCK_API_ARTICLES.filter(a =>
          (a.title_ko ?? '').toLowerCase().includes(q) ||
          a.title.toLowerCase().includes(q) ||
          a.translation.toLowerCase().includes(q) ||
          a.keywords.some(k => k.toLowerCase().includes(q)),
        )
      : MOCK_API_ARTICLES.slice(0, 5);
    const results = matches.map((a, i) => ({ ...a, similarity: 0.85 - i * 0.05 }));
    return { results } as unknown as T;
  }

  // GET /health
  if (pathname === '/health' && m === 'GET') {
    return { status: 'mock-dev' } as unknown as T;
  }

  // POST /onboarding
  if (pathname === '/onboarding' && m === 'POST') {
    return { message: 'mock onboarding ok' } as OnboardingResponse as unknown as T;
  }

  // GET /absence-summary/:userId, GET /api/users/:userId/absence-summary
  if (
    m === 'GET' &&
    (pathname.startsWith('/absence-summary/') ||
     /^\/api\/users\/[^/]+\/absence-summary$/.test(pathname))
  ) {
    const res: AbsenceSummaryResponse = { show: false };
    return res as unknown as T;
  }

  // POST /article-view/:userId/:hash, /user-seen/:userId, /api/users/:userId/seen, /logs/view
  if (
    (pathname.startsWith('/article-view/') && m === 'POST') ||
    (pathname.startsWith('/user-seen/')    && m === 'POST') ||
    (pathname.startsWith('/api/users/')    && pathname.endsWith('/seen') && m === 'POST') ||
    (pathname.startsWith('/logs/view')     && m === 'POST')
  ) {
    return { message: 'mock-ok' } as unknown as T;
  }

  // POST /translate, /summarize — body 파싱 없이 빈 응답
  if (pathname === '/translate' && m === 'POST') {
    return { translation: '' } as unknown as T;
  }
  if (pathname === '/summarize' && m === 'POST') {
    return { summary_formal: '', summary_casual: '' } as unknown as T;
  }

  return undefined;
}
