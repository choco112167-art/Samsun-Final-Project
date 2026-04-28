import { useState, useEffect, useRef, useCallback } from 'react';
import { BottomSheet, useToast } from '../components/Overlay';
import ArticleCard from '../components/ArticleCard';
import { FeedSkeleton } from '../components/Skeleton';
import { fetchArticles } from '../data/api';
import { CATEGORIES, filterByCategory } from '../data/articles';
import type { Article, Category, Interest } from '../data/articles';
import type { AbsenceSummaryResponse, AbsenceArticle } from '../data/api';
import DetailPage from './DetailPage';
import type { BookmarkHook } from '../hooks/useBookmarks';

// CategoryPage 와 동일한 데이터 풀 크기를 보장해야 카테고리 칩 별 매핑 결과가
// 두 화면에서 동일하게 나온다 (이슈 #15). 너무 작으면 최신 N개 안에 특정 카테고리가
// 0건 이라 칩 클릭 시 빈 화면이 나오는 사일런트 누락 발생.
const LIMIT = 100;

type Filter = '전체' | Category;

interface Props {
  bm: BookmarkHook;
  userId?: string;
  interests?: Interest[];
  onNavigateToFeed?: () => void;
  onArticleClick?: (urlHash: string) => void;
  absenceData?: AbsenceSummaryResponse | null;
  onAbsenceDismiss?: () => void;
}

export default function HomePage({ bm, onNavigateToFeed, onArticleClick, absenceData, onAbsenceDismiss, interests = [] }: Props) {
  const [articles, setArticles]       = useState<Article[]>([]);
  const [loading, setLoading]         = useState(true);
  const [error, setError]             = useState<string | null>(null);
  const [filter, setFilter]           = useState<Filter>('전체');
  const [detail, setDetail]           = useState<Article | null>(null);
  const [hasMore, setHasMore]         = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const toast = useToast();

  const mainRef         = useRef<HTMLDivElement>(null);
  const sentinelRef     = useRef<HTMLDivElement>(null);
  const scrollPos       = useRef(0);
  const offsetRef       = useRef(0);
  const loadingMoreRef  = useRef(false);
  const hasMoreRef      = useRef(true);
  const initialLoadDone = useRef(false);

  const [absenceModalOpen, setAbsenceModalOpen] = useState(false);

  const handleNotif = () => {
    if (absenceData?.show) {
      setAbsenceModalOpen(true);
    } else {
      toast.openToast('새 기사 알림이 설정됐어요', { duration: 2200 });
    }
  };

  const load = () => {
    setLoading(true);
    setError(null);
    offsetRef.current = 0;
    hasMoreRef.current = true;
    initialLoadDone.current = false; // 문서 13에서 유지
    setHasMore(true);
    fetchArticles({ limit: LIMIT, offset: 0 })
      .then(data => {
        setArticles(data);
        const more = data.length >= LIMIT;
        hasMoreRef.current = more;
        setHasMore(more);
        initialLoadDone.current = true;
        setLoading(false);
      })
      .catch(() => { setError('기사를 불러오지 못했어요'); setLoading(false); });
  };

  const loadMore = useCallback(() => {
    if (!initialLoadDone.current || loadingMoreRef.current || !hasMoreRef.current) return;
    loadingMoreRef.current = true;
    setLoadingMore(true);
    const newOffset = offsetRef.current + LIMIT;
    fetchArticles({ limit: LIMIT, offset: newOffset })
      .then(data => {
        setArticles(prev => [...prev, ...data]);
        offsetRef.current = newOffset;
        const more = data.length >= LIMIT;
        hasMoreRef.current = more;
        setHasMore(more);
        loadingMoreRef.current = false;
        setLoadingMore(false);
      })
      .catch(() => {
        loadingMoreRef.current = false;
        setLoadingMore(false);
      });
  }, []);

  useEffect(() => { load(); }, []);

  // 스크롤 위치 저장
  useEffect(() => {
    const el = mainRef.current;
    if (!el) return;
    const onScroll = () => { scrollPos.current = el.scrollTop; };
    el.addEventListener('scroll', onScroll, { passive: true });
    return () => el.removeEventListener('scroll', onScroll);
  }, []);

  // IntersectionObserver: sentinel 감지 → loadMore
  useEffect(() => {
    const sentinel = sentinelRef.current;
    if (!sentinel) return;
    const observer = new IntersectionObserver(
      entries => { if (entries[0].isIntersecting) loadMore(); },
      { threshold: 0.1 }
    );
    observer.observe(sentinel);
    return () => observer.disconnect();
  }, [loadMore]);

  // 상세 → 목록 복귀 시 스크롤 복원
  useEffect(() => {
    if (!detail && mainRef.current) {
      setTimeout(() => {
        if (mainRef.current) mainRef.current.scrollTop = scrollPos.current;
      }, 50);
    }
  }, [detail]);

  // 필터 규칙
  //   '전체' 선택  → 사용자가 온보딩에서 고른 관심사로 우선 좁힌 개인화 피드
  //                  (관심사 매칭 결과가 0이면 전체 기사로 폴백 — 구버전 라벨 호환)
  //   카테고리 칩 → 관심사를 무시하고 전체 풀에서 해당 카테고리만 매칭
  //                 ↳ filterByCategory(공유 유틸)을 통해 CategoryPage 와 동일 동작 보장
  const interestFiltered = interests.length > 0
    ? articles.filter(a => interests.includes(a.category as Interest))
    : articles;
  const baseArticles = filter === '전체'
    ? (interestFiltered.length > 0 ? interestFiltered : articles)
    : articles;

  const breaking = baseArticles.filter(a => a.isBreaking);
  const filtered  = filterByCategory(baseArticles, filter);
  const newCount  = baseArticles.filter(a => a.isNew).length;

  if (detail) return (
    <DetailPage
      article={detail}
      bookmarked={bm.isBookmarked(detail.urlHash)}
      onBookmark={bm.toggle}
      onBack={() => setDetail(null)}
    />
  );

  if (loading) return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden', background: 'var(--color-header-bg)' }}>
      <header style={{ padding: '22px 20px 20px', flexShrink: 0 }}>
        <h1 style={{ fontSize: 26, fontWeight: 800, letterSpacing: '-0.04em', color: 'var(--color-header-text)' }}>삼선뉴스</h1>
        <p style={{ fontSize: 12, color: 'var(--color-header-text-secondary)', marginTop: 3 }}>불러오는 중...</p>
      </header>
      <div style={{ flex: 1, overflowY: 'auto', background: 'var(--color-bg)', borderRadius: '32px 32px 0 0' }}>
        <FeedSkeleton onDone={() => {}} />
      </div>
    </div>
  );

  if (error) return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden', background: 'var(--color-header-bg)' }}>
      <header style={{ padding: '22px 20px 20px', flexShrink: 0 }}>
        <h1 style={{ fontSize: 26, fontWeight: 800, letterSpacing: '-0.04em', color: 'var(--color-header-text)' }}>삼선뉴스</h1>
      </header>
      <div style={{ flex: 1, background: 'var(--color-bg)', borderRadius: '32px 32px 0 0', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 12 }}>
        <p style={{ fontSize: 15, color: 'var(--color-text-secondary)' }}>😢 {error}</p>
        <button onClick={load} style={{ fontSize: 13, color: 'var(--color-primary)', padding: '8px 18px', border: '1px solid var(--color-primary)', borderRadius: 20 }}>
          다시 시도
        </button>
      </div>
    </div>
  );

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden', background: 'var(--color-header-bg)', animation: 'pageFadeIn 0.3s ease' }}>
      <style>{`
        @keyframes pageFadeIn { from{opacity:0;transform:translateY(8px)} to{opacity:1;transform:translateY(0)} }
        @keyframes cardIn { from{opacity:0;transform:translateY(14px)} to{opacity:1;transform:translateY(0)} }
        @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.55} }
        @keyframes spin { to{transform:rotate(360deg)} }
      `}</style>

      {/* 부재 중 알림 바텀시트 */}
      <BottomSheet
        open={absenceModalOpen && !!absenceData?.show}
        onClose={() => { setAbsenceModalOpen(false); onAbsenceDismiss?.(); }}
        header={<BottomSheet.Header>🔔 {absenceData?.message}</BottomSheet.Header>}
        cta={
          <BottomSheet.CTA>
            확인했어요
          </BottomSheet.CTA>
        }
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10, padding: '0 20px 8px' }}>
          {absenceData?.sub_message && (
            <p style={{ fontSize: 13, color: 'var(--color-text-secondary)', fontWeight: 500, marginBottom: 2 }}>
              {absenceData.sub_message}
            </p>
          )}
          {(absenceData?.articles as AbsenceArticle[] | undefined ?? []).map(article => (
            <div key={article.url_hash} style={{
              background: 'var(--color-surface)', borderRadius: 12,
              padding: '12px 14px', border: '0.5px solid var(--color-border)',
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 6 }}>
                <span style={{
                  fontSize: 10, fontWeight: 600, color: 'var(--color-primary)',
                  background: 'var(--color-primary-light)', padding: '2px 7px', borderRadius: 6,
                }}>{article.category}</span>
                <span style={{ fontSize: 10, color: 'var(--color-text-tertiary)' }}>{article.source}</span>
              </div>
              <p style={{ fontSize: 13, fontWeight: 600, color: 'var(--color-text-primary)', lineHeight: 1.45, marginBottom: 6 }}>
                {article.title}
              </p>
              {article.summary_formal && (
                <p style={{ fontSize: 12, color: 'var(--color-text-secondary)', lineHeight: 1.6 }}>
                  {article.summary_formal}
                </p>
              )}
            </div>
          ))}
        </div>
      </BottomSheet>

      {/* 헤더 */}
      <header style={{ flexShrink: 0, padding: '22px 20px 0' }}>
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between' }}>
          <div>
            <h1 style={{ fontSize: 26, fontWeight: 800, letterSpacing: '-0.04em', color: 'var(--color-header-text)' }}>삼선뉴스</h1>
            <p style={{ fontSize: 12, color: 'var(--color-header-text-secondary)', marginTop: 3 }}>
              AI 뉴스 큐레이션 ·{' '}
              <span style={{ color: 'var(--color-primary)', fontWeight: 600 }}>{newCount}개 새 기사</span>
            </p>
          </div>
          <button
            onClick={handleNotif}
            style={{
              width: 38, height: 38, borderRadius: '50%',
              background: 'rgba(0,0,0,0.05)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              transition: 'background 0.2s', position: 'relative',
            }}
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
              <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" stroke="var(--color-text-tertiary)" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"/>
              <path d="M13.73 21a2 2 0 0 1-3.46 0" stroke="var(--color-text-tertiary)" strokeWidth="1.6" strokeLinecap="round"/>
            </svg>
            {absenceData?.show && (
              <span style={{
                position: 'absolute', top: 6, right: 6,
                width: 8, height: 8, borderRadius: '50%',
                background: '#EF4444', border: '1.5px solid white',
              }} />
            )}
          </button>
        </div>

        {/* 카테고리 필터 — 8개 */}
        <div style={{ display: 'flex', gap: 7, marginTop: 16, paddingBottom: 16, overflowX: 'auto', scrollbarWidth: 'none' }}>
          {(['전체', ...CATEGORIES] as Filter[]).map(f => (
            <button key={f} onClick={() => setFilter(f)} style={{
              flexShrink: 0, fontSize: 12, fontWeight: filter === f ? 700 : 400,
              color: filter === f ? '#FFFFFF' : '#6B7684',
              background: filter === f ? 'var(--color-primary)' : '#F2F4F6',
              border: 'none',
              padding: '6px 14px', borderRadius: 20, transition: 'all 0.15s', whiteSpace: 'nowrap',
            }}>{f}</button>
          ))}
        </div>
      </header>

      {/* 메인 컨텐츠 */}
      <main
        ref={mainRef}
        style={{
          flex: 1, overflowY: 'auto',
          background: 'var(--color-bg)',
          borderRadius: '32px 32px 0 0',
          padding: '16px 16px 20px',
          display: 'flex', flexDirection: 'column', gap: 10,
          WebkitOverflowScrolling: 'touch',
        }}
      >
        {/* 속보 배너 */}
        {breaking.length > 0 && (filter === '전체' || breaking.some(a => a.category === filter)) && (
          <div style={{ background: 'var(--color-surface)', borderRadius: 'var(--radius-md)', border: '0.5px solid var(--color-border)', overflow: 'hidden', animation: 'cardIn 0.3s ease both' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '10px 14px', borderBottom: '0.5px solid var(--color-border)' }}>
              <div style={{ width: 7, height: 7, borderRadius: '50%', background: '#EF4444', animation: 'pulse 1.5s ease-in-out infinite' }} />
              <span style={{ fontSize: 11, fontWeight: 700, color: '#EF4444', letterSpacing: '0.04em' }}>속보</span>
              <span style={{ fontSize: 11, color: 'var(--color-text-tertiary)' }}>최신 기사</span>
            </div>
            <div style={{ display: 'flex', overflowX: 'auto', scrollbarWidth: 'none' }}>
              {breaking
                .filter(a => filter === '전체' || a.category === filter)
                .slice(0, 5)
                .map((a, i, arr) => (
                  <button key={a.urlHash} onClick={() => { onArticleClick?.(a.urlHash); setDetail(a); }} style={{
                    flexShrink: 0, width: 220, padding: '12px 14px', textAlign: 'left',
                    borderRight: i < arr.length - 1 ? '0.5px solid var(--color-border)' : 'none',
                  }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 5, marginBottom: 5 }}>
                      <div style={{ width: 5, height: 5, borderRadius: '50%', background: a.sourceColor }} />
                      <span style={{ fontSize: 10, color: 'var(--color-text-tertiary)' }}>{a.source}</span>
                      <span style={{ fontSize: 10, color: '#EF4444', fontWeight: 600 }}>{a.timeAgo}</span>
                    </div>
                    <p style={{ fontSize: 12, fontWeight: 600, color: 'var(--color-text-primary)', lineHeight: 1.4, display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>
                      {a.title}
                    </p>
                  </button>
                ))}
            </div>
          </div>
        )}

        {/* 관심 주제 추천 배너 — 블루 */}
        <div
          onClick={onNavigateToFeed}
          style={{ background: 'linear-gradient(135deg,#3081fb 0%,#1960ca 100%)', borderRadius: 'var(--radius-md)', padding: '14px 16px', display: 'flex', alignItems: 'center', gap: 12, animation: 'cardIn 0.35s 0.04s ease both', cursor: 'pointer' }}
        >
          <div style={{ width: 36, height: 36, borderRadius: 10, background: 'rgba(255,255,255,0.18)', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
              <path d="M12 2L15.09 8.26L22 9.27L17 14.14L18.18 21.02L12 17.77L5.82 21.02L7 14.14L2 9.27L8.91 8.26L12 2Z" fill="white"/>
            </svg>
          </div>
          <div>
            <p style={{ fontSize: 13, fontWeight: 600, color: '#fff' }}>관심 주제 기반 추천</p>
            <p style={{ fontSize: 11, color: 'rgba(255,255,255,0.72)', marginTop: 1 }}>관심 분야 뉴스를 골라서 보여드려요</p>
          </div>
          <svg style={{ marginLeft: 'auto', flexShrink: 0 }} width="16" height="16" viewBox="0 0 24 24" fill="none">
            <path d="M9 18L15 12L9 6" stroke="rgba(255,255,255,0.8)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
        </div>

        {/* 기사 카드 */}
        {filtered.map((article, i) => (
          <ArticleCard
            key={article.urlHash}
            article={article}
            bookmarked={bm.isBookmarked(article.urlHash)}
            onBookmark={bm.toggle}
            onClick={() => { onArticleClick?.(article.urlHash); setDetail(article); }}
            style={{ animation: `cardIn 0.3s ${0.06 + Math.min(i, 10) * 0.05}s ease both` }}
          />
        ))}

        {/* 로딩 스피너 */}
        {loadingMore && (
          <div style={{ display: 'flex', justifyContent: 'center', padding: '20px 0' }}>
            <div style={{ width: 22, height: 22, border: '2.5px solid var(--color-border)', borderTopColor: 'var(--color-primary)', borderRadius: '50%', animation: 'spin 0.7s linear infinite' }} />
          </div>
        )}

        {/* 더 보기 버튼 */}
        {hasMore && !loadingMore && articles.length > 0 && (
          <button
            onClick={loadMore}
            style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6, margin: '4px auto 8px', padding: '10px 24px', fontSize: 13, color: 'var(--color-primary)', background: 'var(--color-primary-light)', border: '1px solid var(--color-primary-mid)', borderRadius: 20, cursor: 'pointer' }}
          >
            기사 더 보기
          </button>
        )}

        {/* 마지막 도달 */}
        {!hasMore && articles.length > 0 && (
          <div style={{ textAlign: 'center', padding: '20px 0', color: 'var(--color-text-tertiary)', fontSize: 13 }}>
            모든 기사를 불러왔어요 🎉
          </div>
        )}

        {filtered.length === 0 && (
          <div style={{ textAlign: 'center', padding: '60px 0', color: 'var(--color-text-tertiary)', fontSize: 14 }}>
            해당 카테고리의 기사가 없어요
          </div>
        )}

        {/* IntersectionObserver sentinel */}
        <div ref={sentinelRef} style={{ height: 1 }} />
      </main>
    </div>
  );
}