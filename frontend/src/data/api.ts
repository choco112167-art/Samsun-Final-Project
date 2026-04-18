import { toArticle } from './articles';
import type { Article } from './articles';
/**
 * frontend/src/data/api.ts — 삼선뉴스 API 클라이언트
 *
 * 프론트엔드에서 백엔드(FastAPI)로 HTTP 요청을 보내는 함수들을 모아놓은 파일.
 * 모든 API 호출은 이 파일을 통해서 한다.
 *
 * 엔드포인트 맵 (backend/main.py 기준)
 *   GET  /articles          → fetchArticles()    기사 목록 조회
 *   GET  /article/:url_hash → fetchArticleByHash() 기사 상세 조회
 *   POST /onboarding        → postOnboarding()   유저 관심사 등록
 *   GET  /feed/:userId      → fetchFeed()        맞춤 기사 추천
 *   GET  /search?q=         → searchArticles()   벡터 검색
 *   GET  /health            → healthCheck()      서버 상태 확인
 */

// 백엔드 서버 주소를 환경변수에서 읽는다
// .env 파일의 VITE_API_BASE_URL 값을 사용하고, 없으면 로컬호스트를 기본값으로
const BASE_URL = (import.meta.env.VITE_API_BASE_URL as string | undefined)
  ?? 'http://localhost:8000';

/**
 * 모든 API 요청의 공통 처리를 담당하는 내부 함수.
 * 직접 호출하지 않고 아래 함수들이 내부적으로 사용한다.
 *
 * @param path  엔드포인트 경로 (예: "/articles", "/feed/user_123")
 * @param init  fetch 옵션 (method, body 등)
 */
async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { 'Content-Type': 'application/json' },   // 모든 요청에 JSON 헤더 추가
    ...init,   // 추가 옵션이 있으면 덮어쓴다 (예: POST의 body)
  });

  // HTTP 에러(4xx, 5xx)가 있으면 ApiError를 던진다
  if (!res.ok) {
    const body = await res.text().catch(() => '');
    throw new ApiError(res.status, body || res.statusText);
  }

  return res.json() as Promise<T>;   // 응답 JSON을 타입 T로 파싱해서 반환
}

/**
 * API 에러 클래스 — 일반 Error에 HTTP 상태 코드를 추가한 버전
 * 화면에서 "404 기사 없음" 같은 에러를 구분해서 처리할 때 사용
 */
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
// 백엔드에서 내려오는 JSON의 구조를 타입으로 선언해둔다
// ─────────────────────────────────────────────

/** articles 테이블 컬럼과 동일한 구조 */
export interface ApiArticle {
  // 식별
  url_hash:          string;   // MD5(url) — DB의 PK, 기사 고유 ID
  url:               string;   // 원문 URL (DetailPage "원문 보기" 버튼에 사용)

  // 메타 정보
  title:             string;   // 기사 제목 (영문)
  source:            string;   // 언론사명 (TechCrunch, MIT TR 등)
  source_type:       'media' | 'community';  // 미디어 vs 커뮤니티
  category:          string;   // 카테고리 (AI 모델, 반도체 등)
  country:           string;   // 발행 국가
  keywords:          string[]; // 키워드 배열 — 태그 UI, 검색 필터에 사용
  published_at:      string;   // 기사 발행 시각 (ISO 8601 형식)
  collected_at:      string;   // 파이프라인 수집 시각 (ISO 8601)

  // 콘텐츠
  content:           string;   // 영문 원문 본문

  // 신뢰도
  credibility_score: number;   // 출처 신뢰도 (0.0~1.0)
  fact_label:        'FACT' | 'UNVERIFIED' | 'RUMOR';  // 자동 분류된 팩트 라벨

  // 번역 / 요약 (이동우님 파이프라인 결과)
  translation:       string;   // 한국어 번역 전문
  summary_formal:    string;   // 격식체 3줄 요약 (~습니다)
  summary_casual:    string;   // 일상체 3줄 요약 (~해요)

  // 프론트 전용 필드 (백엔드에서 계산해서 내려줌)
  is_new:            boolean;  // 6시간 이내 기사 여부 → "NEW" 뱃지 표시
  is_breaking:       boolean;  // 속보 여부 → "속보" 뱃지 표시
  time_ago:          string;   // "3시간 전" 포맷으로 변환된 시간
  source_color:      string;   // 소스별 브랜드 컬러 (HEX) — 카드 액센트 바에 사용
}

/** fetchArticles()에 넘길 수 있는 필터 파라미터 */
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

/** 피드 추천 결과 — 유사도 점수가 추가된 기사 */
export interface FeedArticle  extends ApiArticle { similarity?: number; }

/** 검색 결과 — 유사도 점수가 추가된 기사 */
export interface SearchResult extends ApiArticle { similarity?: number; }


// ─────────────────────────────────────────────
// API 함수들
// ─────────────────────────────────────────────

/**
 * 기사 목록을 가져온다.
 * HomePage, CategoryPage, HotPage에서 사용.
 */
export async function fetchArticles(params: FetchArticlesParams = {}): Promise<Article[]> {
  // 쿼리 파라미터 조립 — 있는 것만 추가한다
  const qs = new URLSearchParams();
  if (params.category)    qs.set('category',    params.category);
  if (params.source)      qs.set('source',      params.source);
  if (params.source_type) qs.set('source_type', params.source_type);
  if (params.limit)       qs.set('limit',       String(params.limit));
  if (params.offset)      qs.set('offset',      String(params.offset));
  if (params.is_breaking !== undefined) qs.set('is_breaking', String(params.is_breaking));

  // 파라미터가 있으면 "?category=AI+모델&limit=20" 형태로 붙인다
  const query = qs.toString() ? `?${qs}` : '';
  return request<ApiArticle[]>(`/articles${query}`).then(list => list.map(toArticle));
}

/**
 * 기사 하나의 상세 내용을 가져온다.
 * DetailPage에서 사용.
 *
 * @param urlHash MD5로 해시된 기사 고유 ID
 */
export async function fetchArticleByHash(urlHash: string): Promise<ApiArticle> {
  return request<ApiArticle>(`/article/${urlHash}`);
}

/**
 * 온보딩 — 유저의 관심 주제를 백엔드에 저장한다.
 * OnboardingPage에서 "시작하기" 버튼을 눌렀을 때 호출.
 *
 * @param userId       localStorage에서 생성된 유저 ID
 * @param interestTags 유저가 선택한 관심 주제 배열
 */
export async function postOnboarding(userId: string, interestTags: string[]): Promise<OnboardingResponse> {
  return request<OnboardingResponse>('/onboarding', {
    method: 'POST',
    body: JSON.stringify({ user_id: userId, interest_tags: interestTags }),
  });
}

/**
 * 유저 맞춤 기사 피드를 가져온다.
 * MyFeedPage의 "추천 피드" 탭에서 사용.
 * 내부적으로 pgvector RAG 추천이 이루어진다.
 *
 * @param userId 유저 ID
 * @param topK   가져올 기사 수 (기본 10개)
 */
export async function fetchFeed(userId: string, topK = 10): Promise<(Article & { similarity?: number })[]> {
  const res = await request<{ feed: FeedArticle[] }>(
    `/feed/${encodeURIComponent(userId)}?top_k=${topK}`,
  );
  const list = res.feed ?? [];
  return list.map(f => ({ ...toArticle(f), similarity: f.similarity }));
}

/**
 * 자연어 검색을 수행한다.
 * SearchPage에서 사용.
 * 키워드 매칭이 아닌 벡터 유사도 검색 — 의미가 비슷한 기사를 찾는다.
 *
 * @param query 검색어
 * @param topK  가져올 결과 수 (기본 10개)
 */
export async function searchArticles(query: string, topK = 10): Promise<(Article & { similarity?: number })[]> {
  const res = await request<{ results: SearchResult[] }>(
    `/search?q=${encodeURIComponent(query)}&top_k=${topK}`,
  );
  const list = res.results ?? [];
  return list.map(r => ({ ...toArticle(r), similarity: r.similarity }));
}

/**
 * 기사 카드·목록에서 조회 시 호출 — Hot/추천 통계용 user_logs 적재
 */
export async function recordArticleView(userId: string, urlHash: string): Promise<void> {
  if (!userId?.trim() || !urlHash) return;
  await request<{ message?: string }>(
    `/article-view/${encodeURIComponent(userId)}/${encodeURIComponent(urlHash)}`,
    { method: 'POST' },
  );
}

/**
 * 서버 상태를 확인한다.
 * 앱 초기 로드 시 백엔드가 살아있는지 확인하는 용도.
 */
export async function healthCheck(): Promise<{ status: string }> {
  return request<{ status: string }>('/health');
}
