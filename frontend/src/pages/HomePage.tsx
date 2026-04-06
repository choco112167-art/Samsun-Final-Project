import { useState, useEffect } from 'react';
import ArticleCard from '../components/ArticleCard';
import { FeedSkeleton } from '../components/Skeleton';
import { fetchArticles } from '../data/api';
import type { ApiArticle } from '../data/api';
import DetailPage from './DetailPage';
import type { BookmarkHook } from '../hooks/useBookmarks';

// 백엔드 category값 → 프론트 필터 매핑
const CATEGORY_MAP: Record<string, string> = {
  'AI/스타트업':   'AI 모델',
  'AI 심층':      'AI 모델',
  'AI 비즈니스':  '빅테크',
  '테크 전반':    '빅테크',
  'AI 윤리':     '윤리/정책',
  'AI 일반':     'AI 모델',
  'AI/반도체':   '반도체',
  'AI 커뮤니티':  'AI 모델',
  'AI 연구':     'AI 모델',
  'LLM 커뮤니티': 'AI 모델',
  'AI 제품':     '스타트업',
};

type Filter = '전체' | 'AI 모델' | '스타트업' | '빅테크' | '윤리/정책' | '반도체';
interface Props { bm: BookmarkHook; }

export default function HomePage({ bm }: Props) {
  const [articles, setArticles]     = useState<ApiArticle[]>([]);
  const [loading, setLoading]       = useState(true);
  const [error, setError]           = useState<string | null>(null);
  const [filter, setFilter]         = useState<Filter>('전체');
  const [detail, setDetail]         = useState<ApiArticle | null>(null);
  const [notifToast, setNotifToast] = useState(false);

  const handleNotif = () => {
    setNotifToast(true);
    setTimeout(() => setNotifToast(false), 2200);
  };

  const load = () => {
    setLoading(true);
    setError(null);
    fetchArticles({ limit: 50 })
      .then(data => { setArticles(data); setLoading(false); })
      .catch(() => { setError('기사를 불러오지 못했어요'); setLoading(false); });
  };

  useEffect(() => {
    // 초기 데이터 로드 (load는 재시도 버튼에서도 사용)
    // eslint-disable-next-line react-hooks/set-state-in-effect -- mount 시 fetch 후 setState
    load();
  }, []);

  const mapped = articles.map(a => ({
    ...a,
    _filterCategory: CATEGORY_MAP[a.category] ?? '빅테크',
  }));

  const breaking = mapped.filter(a => a.isNew);
  const filtered  = filter === '전체'
    ? mapped
    : mapped.filter(a => a._filterCategory === filter);
  const newCount = articles.filter(a => a.isNew).length;

  if (detail) return (
    <DetailPage
      article={detail}
      bookmarked={bm.isBookmarked(detail.id)}
      onBookmark={bm.toggle}
      onBack={() => setDetail(null)}
    />
  );

  if (loading) return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
      <header style={{ background: 'var(--color-surface)', borderBottom: '0.5px solid var(--color-border)', padding: '18px 20px 14px', flexShrink: 0 }}>
        <h1 style={{ fontSize: 22, fontWeight: 700, letterSpacing: '-0.04em' }}>삼선뉴스</h1>
        <p style={{ fontSize: 12, color: 'var(--color-text-tertiary)', marginTop: 2 }}>불러오는 중...</p>
      </header>
      <div style={{ flex: 1, overflowY: 'auto' }}><FeedSkeleton onDone={() => {}} /></div>
    </div>
  );

  if (error) return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%', gap: 12 }}>
      <p style={{ fontSize: 15, color: 'var(--color-text-secondary)' }}>😢 {error}</p>
      <button
        onClick={load}
        style={{ fontSize: 13, color: 'var(--color-primary)', padding: '8px 18px', border: '1px solid var(--color-primary)', borderRadius: 20 }}
      >
        다시 시도
      </button>
    </div>
  );

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden', animation: 'pageFadeIn 0.3s ease' }}>
      <style>{`
        @keyframes pageFadeIn { from{opacity:0;transform:translateY(8px)} to{opacity:1;transform:translateY(0)} }
        @keyframes cardIn { from{opacity:0;transform:translateY(14px)} to{opacity:1;transform:translateY(0)} }
        @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.55} }
        @keyframes toastIn { from{opacity:0;transform:translateY(12px)} to{opacity:1;transform:translateY(0)} }
      `}</style>

      {/* 알림 토스트 */}
      {notifToast && (
        <div style={{
          position: 'fixed', bottom: 80, left: '50%', transform: 'translateX(-50%)',
          background: 'rgba(30,30,35,0.92)', color: '#fff',
          fontSize: 13, fontWeight: 500, padding: '10px 18px',
          borderRadius: 20, zIndex: 999, whiteSpace: 'nowrap',
          animation: 'toastIn 0.22s ease', backdropFilter: 'blur(8px)',
        }}>
          🔔 새 기사 알림이 설정되었어요
        </div>
      )}

      {/* 헤더 */}
      <header style={{ background: 'var(--color-surface)', borderBottom: '0.5px solid var(--color-border)', flexShrink: 0 }}>
        <div style={{ padding: '18px 20px 0' }}>
          <div style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between' }}>
            <div>
              <h1 style={{ fontSize: 22, fontWeight: 700, letterSpacing: '-0.04em' }}>삼선뉴스</h1>
              <p style={{ fontSize: 12, color: 'var(--color-text-tertiary)', marginTop: 2 }}>
                AI 뉴스 큐레이션 ·
                <span style={{ color: 'var(--color-primary)', fontWeight: 600, marginLeft: 4 }}>{newCount}개 새 기사</span>
              </p>
            </div>
            <button
              onClick={handleNotif}
              style={{ width: 38, height: 38, borderRadius: '50%', background: notifToast ? 'var(--color-primary-light)' : 'var(--color-surface-secondary)', display: 'flex', alignItems: 'center', justifyContent: 'center', transition: 'background 0.2s' }}
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
                <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" stroke={notifToast ? 'var(--color-primary)' : 'var(--color-text-secondary)'} strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"/>
                <path d="M13.73 21a2 2 0 0 1-3.46 0" stroke={notifToast ? 'var(--color-primary)' : 'var(--color-text-secondary)'} strokeWidth="1.6" strokeLinecap="round"/>
              </svg>
            </button>
          </div>

          {/* 카테고리 필터 */}
          <div style={{ display: 'flex', gap: 7, marginTop: 14, paddingBottom: 14, overflowX: 'auto', scrollbarWidth: 'none' }}>
            {(['전체','AI 모델','스타트업','빅테크','윤리/정책','반도체'] as Filter[]).map(f => (
              <button key={f} onClick={() => setFilter(f)} style={{
                flexShrink: 0, fontSize: 12, fontWeight: filter === f ? 600 : 400,
                color: filter === f ? 'var(--color-primary)' : 'var(--color-text-tertiary)',
                background: filter === f ? 'var(--color-primary-light)' : 'transparent',
                border: `1px solid ${filter === f ? 'var(--color-primary-mid)' : 'var(--color-border)'}`,
                padding: '6px 13px', borderRadius: 20, transition: 'all 0.15s', whiteSpace: 'nowrap',
              }}>{f}</button>
            ))}
          </div>
        </div>
      </header>

      {/* 피드 */}
      <main style={{ flex: 1, overflowY: 'auto', padding: '12px 16px 20px', display: 'flex', flexDirection: 'column', gap: 10, WebkitOverflowScrolling: 'touch' }}>

        {/* 속보 배너 */}
        {breaking.length > 0 && (filter === '전체' || breaking.some(a => a._filterCategory === filter)) && (
          <div style={{ background: 'var(--color-surface)', borderRadius: 'var(--radius-lg)', border: '0.5px solid var(--color-border)', overflow: 'hidden', animation: 'cardIn 0.3s ease both' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '10px 14px', borderBottom: '0.5px solid var(--color-border)' }}>
              <div style={{ width: 7, height: 7, borderRadius: '50%', background: '#EF4444', animation: 'pulse 1.5s ease-in-out infinite' }} />
              <span style={{ fontSize: 11, fontWeight: 700, color: '#EF4444', letterSpacing: '0.04em' }}>속보</span>
              <span style={{ fontSize: 11, color: 'var(--color-text-tertiary)' }}>최신 기사</span>
            </div>
            <div style={{ display: 'flex', overflowX: 'auto', scrollbarWidth: 'none' }}>
              {breaking
                .filter(a => filter === '전체' || a._filterCategory === filter)
                .slice(0, 5)
                .map((a, i, arr) => (
                  <button key={a.id} onClick={() => setDetail(a)} style={{
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

        {/* 관심 주제 추천 배너 */}
        <div
          onClick={() => setFilter('전체')}
          style={{ background: 'linear-gradient(135deg,#4F46E5 0%,#7C3AED 100%)', borderRadius: 'var(--radius-lg)', padding: '14px 16px', display: 'flex', alignItems: 'center', gap: 12, animation: 'cardIn 0.35s 0.04s ease both', cursor: 'pointer' }}>
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
            key={article.id}
            article={article}
            bookmarked={bm.isBookmarked(article.id)}
            onBookmark={bm.toggle}
            onClick={() => setDetail(article)}
            style={{ animation: `cardIn 0.3s ${0.06 + i * 0.05}s ease both` }}
          />
        ))}

        {filtered.length === 0 && (
          <div style={{ textAlign: 'center', padding: '60px 0', color: 'var(--color-text-tertiary)', fontSize: 14 }}>
            해당 카테고리의 기사가 없습니다
          </div>
        )}
      </main>
    </div>
  );
}