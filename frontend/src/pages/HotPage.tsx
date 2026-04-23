import { useState, useEffect } from 'react';
import { fetchHot } from '../data/api';
import type { Article } from '../data/articles';
import DetailPage from './DetailPage';
import type { BookmarkHook } from '../hooks/useBookmarks';

interface Props {
  bm: BookmarkHook;
  userId?: string;
  onArticleClick?: (urlHash: string) => void;
}

export default function HotPage({ bm, userId, onArticleClick }: Props) {
  const today = new Date();
  const [year, setYear]   = useState(today.getFullYear());
  const [month, setMonth] = useState(today.getMonth());
  const [day, setDay]     = useState(today.getDate());
  const [detail, setDetail] = useState<Article | null>(null);
  const [tops, setTops]     = useState<Article[]>([]);
  const [loading, setLoading] = useState(false);

  const daysInMonth = new Date(year, month + 1, 0).getDate();
  const firstDay    = new Date(year, month, 1).getDay();

  const dateStr = `${year}-${String(month + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;

  useEffect(() => {
    setLoading(true);
    fetchHot(dateStr)
      .then(data => { setTops(data); setLoading(false); })
      .catch(() => setLoading(false));
  }, [dateStr]);

  const prevMonth = () => {
    if (month === 0) { setYear(y => y - 1); setMonth(11); } else setMonth(m => m - 1);
    setDay(1);
  };
  const nextMonth = () => {
    const now = new Date();
    if (year === now.getFullYear() && month === now.getMonth()) return;
    if (month === 11) { setYear(y => y + 1); setMonth(0); } else setMonth(m => m + 1);
    setDay(1);
  };

  const isToday = (d: number) => {
    const n = new Date();
    return d === n.getDate() && month === n.getMonth() && year === n.getFullYear();
  };
  const isFuture = (d: number) => {
    const n = new Date(); n.setHours(0,0,0,0);
    return new Date(year, month, d) > n;
  };

  if (detail) return (
    <DetailPage article={detail} bookmarked={bm.isBookmarked(detail.urlHash)} onBookmark={bm.toggle} onBack={() => setDetail(null)} />
  );

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden', background: 'var(--color-header-bg)' }}>
      <style>{`@keyframes listIn { from{opacity:0;transform:translateY(8px)} to{opacity:1;transform:translateY(0)} }`}</style>

      <header style={{ flexShrink: 0, padding: '22px 20px 20px' }}>
        <h1 style={{ fontSize: 26, fontWeight: 800, letterSpacing: '-0.04em', color: 'var(--color-header-text)', marginBottom: 3 }}>핫이슈</h1>
        <p style={{ fontSize: 12, color: 'var(--color-header-text-secondary)' }}>날짜별 가장 많이 읽힌 기사</p>
      </header>

      <main style={{ flex: 1, overflowY: 'auto', WebkitOverflowScrolling: 'touch', background: 'var(--color-bg)', borderRadius: '32px 32px 0 0' }}>

        {/* 캘린더 */}
        <div style={{ background: 'var(--color-surface)', margin: '12px 16px 0', borderRadius: 'var(--radius-lg)', padding: '16px', boxShadow: 'var(--shadow-card)' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 14 }}>
            <button onClick={prevMonth} style={{ padding: '4px 8px', fontSize: 16, color: 'var(--color-text-tertiary)' }}>‹</button>
            <span style={{ fontSize: 14, fontWeight: 600 }}>{year}년 {month + 1}월</span>
            <button onClick={nextMonth} style={{ padding: '4px 8px', fontSize: 16, color: 'var(--color-text-tertiary)' }}>›</button>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(7,1fr)', marginBottom: 6 }}>
            {['일','월','화','수','목','금','토'].map(d => (
              <div key={d} style={{ textAlign: 'center', fontSize: 11, color: 'var(--color-text-tertiary)', paddingBottom: 4 }}>{d}</div>
            ))}
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(7,1fr)', gap: 3 }}>
            {Array.from({ length: firstDay }).map((_, i) => <div key={`e${i}`} />)}
            {Array.from({ length: daysInMonth }).map((_, i) => {
              const d = i + 1;
              const future = isFuture(d);
              const sel = d === day;
              const todayDay = isToday(d);
              return (
                <button key={d} onClick={() => !future && setDay(d)} disabled={future} style={{
                  aspectRatio: '1', display: 'flex', flexDirection: 'column',
                  alignItems: 'center', justifyContent: 'center', borderRadius: 8, gap: 2,
                  background: sel ? 'var(--color-primary)' : todayDay ? 'var(--color-primary-light)' : 'transparent',
                  opacity: future ? 0.25 : 1, cursor: future ? 'default' : 'pointer',
                }}>
                  <span style={{ fontSize: 11, fontWeight: sel || todayDay ? 600 : 400, color: sel ? '#fff' : 'var(--color-text-primary)' }}>{d}</span>
                </button>
              );
            })}
          </div>
        </div>

        {/* Top 기사 */}
        <div style={{ padding: '16px 16px 24px' }}>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: 6, marginBottom: 12 }}>
            <span style={{ fontSize: 15, fontWeight: 700 }}>{month + 1}월 {day}일</span>
            <span style={{ fontSize: 12, color: 'var(--color-text-tertiary)' }}>인기 기사 Top {tops.length}</span>
          </div>

          {loading && (
            <div style={{ textAlign: 'center', padding: '40px 0', color: 'var(--color-text-tertiary)', fontSize: 13 }}>
              불러오는 중...
            </div>
          )}

          {!loading && tops.length === 0 && (
            <div style={{ textAlign: 'center', padding: '40px 0' }}>
              <div style={{ fontSize: 32, marginBottom: 8 }}>📭</div>
              <p style={{ fontSize: 14, color: 'var(--color-text-tertiary)' }}>해당 날짜 기사가 없어요</p>
            </div>
          )}

          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {tops.map((article, i) => {
              const rankColor = i === 0 ? '#B45309' : i === 1 ? '#6B7280' : i === 2 ? '#92400E' : 'var(--color-text-tertiary)';
              const viewCount = (article as any).view_count ?? 0;
              const maxV = ((tops[0] as any).view_count ?? 1) || 1;
              return (
                <button
                  key={article.urlHash}
                  onClick={() => { onArticleClick?.(article.urlHash); setDetail(article); }}
                  style={{
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
                        <div style={{ height: '100%', borderRadius: 2, background: 'var(--color-primary)', width: viewCount > 0 ? `${(viewCount / maxV) * 100}%` : '20%' }} />
                      </div>
                      <span style={{ fontSize: 11, color: 'var(--color-text-tertiary)', whiteSpace: 'nowrap' }}>
                        {viewCount > 0 ? `${viewCount.toLocaleString()} 조회` : '발행일 기준'}
                      </span>
                    </div>
                  </div>
                  {/* 북마크 — div로 감싸서 button 중첩 방지 */}
                  <div
                    role="button"
                    onClick={e => { e.stopPropagation(); bm.toggle(article.urlHash); }}
                    style={{
                      width: 28, height: 28, borderRadius: 6, flexShrink: 0,
                      background: bm.isBookmarked(article.urlHash) ? '#FEF3C7' : 'var(--color-surface-secondary)',
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                      transition: 'all 0.15s', cursor: 'pointer',
                    }}
                  >
                    <svg width="12" height="12" viewBox="0 0 24 24" fill={bm.isBookmarked(article.urlHash) ? '#D97706' : 'none'}>
                      <path d="M19 21L12 16L5 21V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2v16z" stroke={bm.isBookmarked(article.urlHash) ? '#D97706' : 'var(--color-text-tertiary)'} strokeWidth="1.7" strokeLinejoin="round"/>
                    </svg>
                  </div>
                </button>
              );
            })}
          </div>
        </div>
      </main>
    </div>
  );
}
