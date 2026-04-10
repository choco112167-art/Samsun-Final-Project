import { useState, useEffect } from 'react';
import { fetchArticles } from '../data/api';
import type { ApiArticle } from '../data/api';
import DetailPage from './DetailPage';
import type { BookmarkHook } from '../hooks/useBookmarks';

type SubTab = '전체' | 'AI 연구' | 'AI 스타트업' | '테크 전반' | '윤리·정책' | '반도체';
const SUBTABS: SubTab[] = ['전체', 'AI 연구', 'AI 스타트업', '테크 전반', '윤리·정책', '반도체'];

const CATEGORY_MAP: Record<string, SubTab> = {
  'AI/스타트업':  'AI 스타트업',
  'AI 심층':     'AI 연구',
  'AI 비즈니스': 'AI 스타트업',
  '테크 전반':   '테크 전반',
  'AI 윤리':     '윤리·정책',
  'AI 일반':     'AI 연구',
  'AI/반도체':   '반도체',
  'AI 커뮤니티': 'AI 연구',
  'AI 연구':     'AI 연구',
  'LLM 커뮤니티':'AI 연구',
  'AI 제품':     'AI 스타트업',
};

interface Props { bm: BookmarkHook; }

export default function CategoryPage({ bm }: Props) {
  const [tab, setTab]       = useState<SubTab>('전체');
  const [detail, setDetail] = useState<ApiArticle | null>(null);
  const [articles, setArticles] = useState<ApiArticle[]>([]);

  useEffect(() => {
    fetchArticles({ limit: 100 }).then(setArticles).catch(() => {});
  }, []);

  const mapped = articles.map(a => ({
    ...a,
    _sub: CATEGORY_MAP[a.category] ?? '빅테크',
  }));

  const filtered = tab === '전체' ? mapped : mapped.filter(a => a._sub === tab);
  const sorted   = [...filtered].sort((a, b) => (b.credibility_score ?? 0) - (a.credibility_score ?? 0));

  if (detail) return (
    <DetailPage article={detail} bookmarked={bm.isBookmarked(detail.id)} onBookmark={bm.toggle} onBack={() => setDetail(null)} />
  );

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden', background: 'var(--color-header-bg)' }}>
      <style>{`@keyframes rankIn { from{opacity:0;transform:translateX(-8px)} to{opacity:1;transform:translateX(0)} }`}</style>

      <header style={{ background: 'var(--color-header-bg)', flexShrink: 0, padding: '22px 20px 0' }}>
        <h1 style={{ fontSize: 26, fontWeight: 800, letterSpacing: '-0.04em', color: 'var(--color-header-text)', marginBottom: 3 }}>카테고리</h1>
        <p style={{ fontSize: 12, color: 'var(--color-header-text-secondary)', marginBottom: 14 }}>분야별 기사 모아보기</p>
        <div style={{ display: 'flex', overflowX: 'auto', scrollbarWidth: 'none', gap: 7, paddingBottom: 16 }}>
          {SUBTABS.map(t => (
            <button key={t} onClick={() => setTab(t)} style={{
              flexShrink: 0, fontSize: 12,
              fontWeight: tab === t ? 700 : 400,
              color: tab === t ? '#FFFFFF' : '#6B7684',
              background: tab === t ? '#111111' : '#F2F4F6',
              border: 'none',
              padding: '6px 14px', borderRadius: 20, transition: 'all 0.15s', whiteSpace: 'nowrap',
            }}>{t}</button>
          ))}
        </div>
      </header>

      <main style={{ flex: 1, overflowY: 'auto', WebkitOverflowScrolling: 'touch', background: 'var(--color-bg)', borderRadius: '32px 32px 0 0', padding: '16px 16px 24px', display: 'flex', flexDirection: 'column', gap: 8 }}>
        {sorted.map((article, i) => {
          const rankColor = i === 0 ? '#B45309' : i === 1 ? '#6B7280' : i === 2 ? '#92400E' : 'var(--color-text-tertiary)';
          const maxScore  = sorted[0]?.credibility_score ?? 1;
          return (
            <button key={article.id} onClick={() => setDetail(article)} style={{
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
                    <div style={{ height: '100%', borderRadius: 2, background: i < 3 ? 'var(--color-primary)' : 'var(--color-text-tertiary)', width: `${((article.credibility_score ?? 0) / maxScore) * 100}%`, opacity: i < 3 ? 1 : 0.4 }} />
                  </div>
                  <span style={{ fontSize: 11, color: 'var(--color-text-tertiary)', whiteSpace: 'nowrap' }}>신뢰도 {Math.round((article.credibility_score ?? 0) * 100)}%</span>
                </div>
              </div>
              <button onClick={e => { e.stopPropagation(); bm.toggle(article.id); }} style={{
                width: 30, height: 30, borderRadius: 8, flexShrink: 0, marginTop: -2,
                background: bm.isBookmarked(article.id) ? '#FEF3C7' : 'var(--color-surface-secondary)',
                display: 'flex', alignItems: 'center', justifyContent: 'center', transition: 'all 0.15s',
              }}>
                <svg width="13" height="13" viewBox="0 0 24 24" fill={bm.isBookmarked(article.id) ? '#D97706' : 'none'}>
                  <path d="M19 21L12 16L5 21V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2v16z" stroke={bm.isBookmarked(article.id) ? '#D97706' : 'var(--color-text-tertiary)'} strokeWidth="1.7" strokeLinejoin="round"/>
                </svg>
              </button>
            </button>
          );
        })}
        {sorted.length === 0 && (
          <div style={{ textAlign: 'center', padding: '60px 0', color: 'var(--color-text-tertiary)', fontSize: 14 }}>
            해당 카테고리의 기사가 없습니다
          </div>
        )}
      </main>
    </div>
  );
}
