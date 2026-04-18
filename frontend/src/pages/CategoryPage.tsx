import { useState, useEffect, useCallback, useRef } from 'react';
import { SegmentedControl } from '@toss/tds-mobile';
import { fetchArticles } from '../data/api';
import type { Article, Category } from '../data/articles';
import DetailPage from './DetailPage';
import type { BookmarkHook } from '../hooks/useBookmarks';

const PAGE_SIZE = 50;

type SubTab = '전체' | Category;
const CATEGORY_TABS: SubTab[] = ['전체', 'AI 연구', 'AI 스타트업', '테크 전반', '윤리·정책', '반도체'];

interface Props { bm: BookmarkHook; }

export default function CategoryPage({ bm }: Props) {
  const [tab, setTab]       = useState<SubTab>('전체');
  const [detail, setDetail] = useState<Article | null>(null);
  const [articles, setArticles] = useState<Article[]>([]);
  const [hasMore, setHasMore] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const loadingMoreRef = useRef(false);

  const loadInitial = useCallback(() => {
    fetchArticles({ limit: PAGE_SIZE, offset: 0 })
      .then(data => {
        setArticles(data);
        setHasMore(data.length >= PAGE_SIZE);
      })
      .catch(() => {});
  }, []);

  const loadMore = useCallback(() => {
    if (loadingMoreRef.current || !hasMore) return;
    loadingMoreRef.current = true;
    setLoadingMore(true);
    fetchArticles({ limit: PAGE_SIZE, offset: articles.length })
      .then(data => {
        setArticles(prev => [...prev, ...data]);
        setHasMore(data.length >= PAGE_SIZE);
      })
      .catch(() => { setHasMore(false); })
      .finally(() => {
        loadingMoreRef.current = false;
        setLoadingMore(false);
      });
  }, [articles.length, hasMore]);

  useEffect(() => {
    loadInitial();
  }, [loadInitial]);

  const handleScroll = useCallback((e: React.UIEvent<HTMLElement>) => {
    const el = e.currentTarget;
    if (el.scrollHeight - el.scrollTop - el.clientHeight < 160) {
      loadMore();
    }
  }, [loadMore]);

  const filtered = tab === '전체' ? articles : articles.filter(a => a.category === tab);
  const sorted   = [...filtered].sort((a, b) => (b.credibilityScore ?? 0) - (a.credibilityScore ?? 0));

  if (detail) return (
    <DetailPage article={detail} bookmarked={bm.isBookmarked(detail.urlHash)} onBookmark={bm.toggle} onBack={() => setDetail(null)} />
  );

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden', background: 'var(--color-header-bg)' }}>
      <style>{`
        @keyframes rankIn { from{opacity:0;transform:translateX(-8px)} to{opacity:1;transform:translateX(0)} }
      `}</style>

      <header style={{ background: 'var(--color-header-bg)', flexShrink: 0, padding: '22px 20px 0' }}>
        <h1 style={{ fontSize: 26, fontWeight: 800, letterSpacing: '-0.04em', color: 'var(--color-header-text)', marginBottom: 3 }}>카테고리</h1>
        <p style={{ fontSize: 12, color: 'var(--color-header-text-secondary)', marginBottom: 10 }}>분야별 기사 모아보기</p>
        <div style={{ paddingBottom: 14, borderRadius: 0, minHeight: 44 }}>
          <SegmentedControl
            alignment="fluid"
            size="small"
            value={tab}
            onChange={(v) => setTab(v as SubTab)}
          >
            {CATEGORY_TABS.map(t => (
              <SegmentedControl.Item key={t} value={t}>{t}</SegmentedControl.Item>
            ))}
          </SegmentedControl>
        </div>
      </header>

      <main
        onScroll={handleScroll}
        style={{ flex: 1, overflowY: 'auto', WebkitOverflowScrolling: 'touch', background: 'var(--color-bg)', borderRadius: '32px 32px 0 0', padding: '16px 16px 24px', display: 'flex', flexDirection: 'column', gap: 8 }}
      >
        {sorted.map((article, i) => {
          const rankColor = i === 0 ? '#B45309' : i === 1 ? '#6B7280' : i === 2 ? '#92400E' : 'var(--color-text-tertiary)';
          const maxScore  = sorted[0]?.credibilityScore ?? 1;
          return (
            <button key={article.urlHash} onClick={() => setDetail(article)} style={{
              display: 'flex', alignItems: 'flex-start', gap: 12,
              background: 'var(--color-surface)', borderRadius: 'var(--radius-lg)',
              padding: '14px', boxShadow: 'var(--shadow-card)', textAlign: 'left',
              transition: 'transform 0.12s', animation: `rankIn 0.25s ${i * 0.04}s ease both`,
            }}
              onTouchStart={e => { (e.currentTarget as HTMLElement).style.transform = 'scale(0.985)'; }}
              onTouchEnd={e => { (e.currentTarget as HTMLElement).style.transform = ''; }}
            >
              <span style={{ fontSize: 16, fontWeight: 700, color: rankColor, minWidth: 24, paddingTop: 2, fontVariantNumeric: 'tabular-nums' }}>{i + 1}</span>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 5, marginBottom: 5 }}>
                  <div style={{ width: 5, height: 5, borderRadius: '50%', background: article.sourceColor ?? '#6B7280', flexShrink: 0 }} />
                  <span style={{ fontSize: 11, color: 'var(--color-text-secondary)' }}>{article.source}</span>
                  {article.isBreaking && <span style={{ fontSize: 10, fontWeight: 600, color: '#EF4444' }}>속보</span>}
                  <span style={{ fontSize: 11, color: 'var(--color-text-tertiary)', marginLeft: 'auto' }}>{article.timeAgo ?? ''}</span>
                </div>
                <p style={{ fontSize: 13, fontWeight: 600, color: 'var(--color-text-primary)', lineHeight: 1.4, marginBottom: 8 }}>{article.title}</p>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <div style={{ flex: 1, height: 3, borderRadius: 2, background: 'var(--color-border)', overflow: 'hidden' }}>
                    <div style={{ height: '100%', borderRadius: 2, background: i < 3 ? 'var(--color-primary)' : 'var(--color-text-tertiary)', width: `${((article.credibilityScore ?? 0) / maxScore) * 100}%`, opacity: i < 3 ? 1 : 0.4 }} />
                  </div>
                  <span style={{ fontSize: 11, color: 'var(--color-text-tertiary)', whiteSpace: 'nowrap' }}>신뢰도 {Math.round((article.credibilityScore ?? 0) * 100)}%</span>
                </div>
              </div>
              <button onClick={e => { e.stopPropagation(); bm.toggle(article.urlHash, article); }} style={{
                width: 30, height: 30, borderRadius: 8, flexShrink: 0, marginTop: -2,
                background: bm.isBookmarked(article.urlHash) ? '#FEF3C7' : 'var(--color-surface-secondary)',
                display: 'flex', alignItems: 'center', justifyContent: 'center', transition: 'all 0.15s',
              }}>
                <svg width="13" height="13" viewBox="0 0 24 24" fill={bm.isBookmarked(article.urlHash) ? '#D97706' : 'none'}>
                  <path d="M19 21L12 16L5 21V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2v16z" stroke={bm.isBookmarked(article.urlHash) ? '#D97706' : 'var(--color-text-tertiary)'} strokeWidth="1.7" strokeLinejoin="round"/>
                </svg>
              </button>
            </button>
          );
        })}
        {loadingMore && (
          <p style={{ textAlign: 'center', fontSize: 12, color: 'var(--color-text-tertiary)', padding: '8px 0' }}>더 불러오는 중…</p>
        )}
        {sorted.length === 0 && (
          <div style={{ textAlign: 'center', padding: '60px 0', color: 'var(--color-text-tertiary)', fontSize: 14 }}>
            해당 카테고리의 기사가 없습니다
          </div>
        )}
      </main>
    </div>
  );
}
