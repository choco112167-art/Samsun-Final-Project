import { useState, useEffect } from 'react';
import { fetchArticles } from '../data/api';
import type { ApiArticle } from '../data/api';
import DetailPage from './DetailPage';
import type { BookmarkHook } from '../hooks/useBookmarks';

const HEAT_COLORS = ['transparent', '#BFDBFE', '#60A5FA', '#1D4ED8'];
const heat = (day: number) => { const s = (day * 37 + 11) % 100; return s > 80 ? 3 : s > 50 ? 2 : s > 20 ? 1 : 0; };

function topForDay(articles: ApiArticle[], day: number): (ApiArticle & { dayViews: number })[] {
  return articles
    .map(a => ({
      ...a,
      dayViews: Math.abs(Math.sin(day * 7 + a.credibility_score * 100) * 15000) | 0,
    }))
    .sort((a, b) => b.dayViews - a.dayViews)
    .slice(0, 5);
}

interface Props { bm: BookmarkHook; }

export default function HotPage({ bm }: Props) {
  const [day, setDay]     = useState(25);
  const [detail, setDetail] = useState<ApiArticle | null>(null);
  const [articles, setArticles] = useState<ApiArticle[]>([]);

  useEffect(() => {
    fetchArticles({ limit: 50 }).then(setArticles).catch(() => {});
  }, []);

  const tops = topForDay(articles, day);

  if (detail) return (
    <DetailPage article={detail} bookmarked={bm.isBookmarked(detail.id)} onBookmark={bm.toggle} onBack={() => setDetail(null)} />
  );

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
      <style>{`@keyframes listIn { from{opacity:0;transform:translateY(8px)} to{opacity:1;transform:translateY(0)} }`}</style>

      <header style={{ background: 'var(--color-surface)', borderBottom: '0.5px solid var(--color-border)', padding: '18px 20px 14px', flexShrink: 0 }}>
        <h1 style={{ fontSize: 20, fontWeight: 700, letterSpacing: '-0.03em', marginBottom: 2 }}>핫이슈</h1>
        <p style={{ fontSize: 12, color: 'var(--color-text-tertiary)' }}>날짜별 가장 많이 읽힌 기사</p>
      </header>

      <main style={{ flex: 1, overflowY: 'auto', WebkitOverflowScrolling: 'touch' }}>

        {/* 캘린더 */}
        <div style={{ background: 'var(--color-surface)', margin: '12px 16px 0', borderRadius: 'var(--radius-lg)', padding: '16px', boxShadow: 'var(--shadow-card)' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 14 }}>
            <button style={{ padding: '4px 8px', fontSize: 16, color: 'var(--color-text-tertiary)' }}>‹</button>
            <span style={{ fontSize: 14, fontWeight: 600 }}>2026년 3월</span>
            <button style={{ padding: '4px 8px', fontSize: 16, color: 'var(--color-text-tertiary)' }}>›</button>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(7,1fr)', marginBottom: 6 }}>
            {['일','월','화','수','목','금','토'].map(d => (
              <div key={d} style={{ textAlign: 'center', fontSize: 11, color: 'var(--color-text-tertiary)', paddingBottom: 4 }}>{d}</div>
            ))}
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(7,1fr)', gap: 3 }}>
            {Array.from({ length: 31 }).map((_, i) => {
              const d = i + 1;
              const future = d > 25;
              const sel = d === day;
              const h = future ? 0 : heat(d);
              return (
                <button key={d} onClick={() => !future && setDay(d)} disabled={future} style={{
                  aspectRatio: '1', display: 'flex', flexDirection: 'column',
                  alignItems: 'center', justifyContent: 'center', borderRadius: 8, gap: 2,
                  background: sel ? 'var(--color-primary)' : 'transparent',
                  opacity: future ? 0.25 : 1, cursor: future ? 'default' : 'pointer',
                }}>
                  <span style={{ fontSize: 11, fontWeight: sel ? 600 : 400, color: sel ? '#fff' : 'var(--color-text-primary)' }}>{d}</span>
                  {!future && !sel && h > 0 && <div style={{ width: 4, height: 4, borderRadius: '50%', background: HEAT_COLORS[h] }} />}
                </button>
              );
            })}
          </div>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: 5, marginTop: 10 }}>
            <span style={{ fontSize: 10, color: 'var(--color-text-tertiary)' }}>조회수</span>
            {HEAT_COLORS.slice(1).map(c => <div key={c} style={{ width: 8, height: 8, borderRadius: 2, background: c }} />)}
            <span style={{ fontSize: 10, color: 'var(--color-text-tertiary)' }}>높음</span>
          </div>
        </div>

        {/* Top 기사 */}
        <div style={{ padding: '16px 16px 24px' }}>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: 6, marginBottom: 12 }}>
            <span style={{ fontSize: 15, fontWeight: 700 }}>3월 {day}일</span>
            <span style={{ fontSize: 12, color: 'var(--color-text-tertiary)' }}>인기 기사 Top {tops.length}</span>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {tops.map((article, i) => {
              const rankColor = i === 0 ? '#B45309' : i === 1 ? '#6B7280' : i === 2 ? '#92400E' : 'var(--color-text-tertiary)';
              const maxV = tops[0]?.dayViews ?? 1;
              return (
                <button key={`${day}-${article.id}`} onClick={() => setDetail(article)} style={{
                  display: 'flex', alignItems: 'flex-start', gap: 12,
                  background: 'var(--color-surface)', borderRadius: 'var(--radius-md)',
                  padding: '13px 14px', boxShadow: 'var(--shadow-card)', textAlign: 'left',
                  transition: 'transform 0.12s', animation: `listIn 0.25s ${i * 0.05}s ease both`,
                }}
                  onTouchStart={e => { (e.currentTarget as HTMLElement).style.transform = 'scale(0.985)'; }}
                  onTouchEnd={e => { (e.currentTarget as HTMLElement).style.transform = ''; }}
                >
                  <span style={{ fontSize: 16, fontWeight: 700, color: rankColor, minWidth: 24, paddingTop: 1 }}>{i + 1}</span>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 5, marginBottom: 4 }}>
                      <div style={{ width: 5, height: 5, borderRadius: '50%', background: article.sourceColor ?? '#6B7280' }} />
                      <span style={{ fontSize: 11, color: 'var(--color-text-secondary)' }}>{article.source}</span>
                    </div>
                    <p style={{ fontSize: 13, fontWeight: 600, color: 'var(--color-text-primary)', lineHeight: 1.4, marginBottom: 8 }}>{article.title}</p>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <div style={{ flex: 1, height: 3, borderRadius: 2, background: 'var(--color-border)', overflow: 'hidden' }}>
                        <div style={{ height: '100%', borderRadius: 2, background: 'var(--color-primary)', width: `${(article.dayViews / maxV) * 100}%` }} />
                      </div>
                      <span style={{ fontSize: 11, color: 'var(--color-text-tertiary)', whiteSpace: 'nowrap' }}>{article.dayViews.toLocaleString()}</span>
                    </div>
                  </div>
                  <button onClick={e => { e.stopPropagation(); bm.toggle(article.id); }} style={{
                    width: 28, height: 28, borderRadius: 6, flexShrink: 0,
                    background: bm.isBookmarked(article.id) ? '#FEF3C7' : 'var(--color-surface-secondary)',
                    display: 'flex', alignItems: 'center', justifyContent: 'center', transition: 'all 0.15s',
                  }}>
                    <svg width="12" height="12" viewBox="0 0 24 24" fill={bm.isBookmarked(article.id) ? '#D97706' : 'none'}>
                      <path d="M19 21L12 16L5 21V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2v16z" stroke={bm.isBookmarked(article.id) ? '#D97706' : 'var(--color-text-tertiary)'} strokeWidth="1.7" strokeLinejoin="round"/>
                    </svg>
                  </button>
                </button>
              );
            })}
          </div>
        </div>
      </main>
    </div>
  );
}
