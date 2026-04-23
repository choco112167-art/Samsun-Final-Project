import { useState, useEffect } from 'react';
import { fetchHot } from '../data/api';
import type { Article } from '../data/articles';
import DetailPage from './DetailPage';
import type { BookmarkHook } from '../hooks/useBookmarks';

const HEAT_COLORS = ['transparent', '#BFDBFE', '#60A5FA', '#1D4ED8'];

interface Props { bm: BookmarkHook; }

type HotArticle = Article & { viewCount: number };

function toYMD(year: number, month: number, day: number): string {
  return `${year}-${String(month).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
}

function daysInMonth(year: number, month: number): number {
  return new Date(year, month, 0).getDate();
}

function firstDayOfWeek(year: number, month: number): number {
  return new Date(year, month - 1, 1).getDay();
}

export default function HotPage({ bm }: Props) {
  const today = new Date();
  const [year, setYear]   = useState(today.getFullYear());
  const [month, setMonth] = useState(today.getMonth() + 1);
  const [day, setDay]     = useState(today.getDate());
  const [hotMap, setHotMap] = useState<Record<string, HotArticle[]>>({});
  const [loading, setLoading] = useState(false);
  const [detail, setDetail] = useState<Article | null>(null);

  const selectedDate = toYMD(year, month, day);
  const tops = hotMap[selectedDate] ?? [];
  const totalDays = daysInMonth(year, month);
  const firstDow  = firstDayOfWeek(year, month);

  // 날짜 선택 시 해당 날짜 핫이슈 로드
  useEffect(() => {
    if (hotMap[selectedDate] !== undefined) return;
    setLoading(true);
    fetchHot(selectedDate)
      .then(data => {
        setHotMap(prev => ({ ...prev, [selectedDate]: data }));
        setLoading(false);
      })
      .catch(() => {
        setHotMap(prev => ({ ...prev, [selectedDate]: [] }));
        setLoading(false);
      });
  }, [selectedDate]);

  const prevMonth = () => {
    if (month === 1) { setYear(y => y - 1); setMonth(12); }
    else setMonth(m => m - 1);
    setDay(1);
  };
  const nextMonth = () => {
    const now = new Date();
    if (year > now.getFullYear() || (year === now.getFullYear() && month >= now.getMonth() + 1)) return;
    if (month === 12) { setYear(y => y + 1); setMonth(1); }
    else setMonth(m => m + 1);
    setDay(1);
  };

  // 히트맵: 조회 데이터 있는 날은 색상 표시
  const heatLevel = (d: number): number => {
    const key = toYMD(year, month, d);
    const data = hotMap[key];
    if (!data || data.length === 0) return 0;
    const maxViews = data[0]?.viewCount ?? 0;
    if (maxViews > 500) return 3;
    if (maxViews > 100) return 2;
    if (maxViews > 0)   return 1;
    return 0;
  };

  const isToday = (d: number) => {
    const t = new Date();
    return d === t.getDate() && month === t.getMonth() + 1 && year === t.getFullYear();
  };

  const isFuture = (d: number) => {
    // 날짜만 비교 (시간 제외) — YYYY-MM-DD 문자열 비교로 오늘 날짜 선택 가능하게
    const t = new Date();
    const todayStr = `${t.getFullYear()}-${String(t.getMonth() + 1).padStart(2, '0')}-${String(t.getDate()).padStart(2, '0')}`;
    return toYMD(year, month, d) > todayStr;
  };

  if (detail) return (
    <DetailPage
      article={detail}
      bookmarked={bm.isBookmarked(detail.urlHash)}
      onBookmark={bm.toggle}
      onBack={() => setDetail(null)}
    />
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
            <button onClick={prevMonth} style={{ padding: '4px 10px', fontSize: 18, color: 'var(--color-text-tertiary)' }}>‹</button>
            <span style={{ fontSize: 14, fontWeight: 600 }}>{year}년 {month}월</span>
            <button onClick={nextMonth} style={{ padding: '4px 10px', fontSize: 18, color: 'var(--color-text-tertiary)' }}>›</button>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(7,1fr)', marginBottom: 6 }}>
            {['일','월','화','수','목','금','토'].map(d => (
              <div key={d} style={{ textAlign: 'center', fontSize: 11, color: 'var(--color-text-tertiary)', paddingBottom: 4 }}>{d}</div>
            ))}
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(7,1fr)', gap: 3 }}>
            {/* 시작 요일 전 빈 셀 */}
            {Array.from({ length: firstDow }).map((_, i) => <div key={`empty-${i}`} />)}

            {Array.from({ length: totalDays }).map((_, i) => {
              const d = i + 1;
              const future = isFuture(d);
              const sel = d === day;
              const today_ = isToday(d);
              const h = future ? 0 : heatLevel(d);
              return (
                <button
                  key={d}
                  onClick={() => !future && setDay(d)}
                  disabled={future}
                  style={{
                    aspectRatio: '1', display: 'flex', flexDirection: 'column',
                    alignItems: 'center', justifyContent: 'center', borderRadius: 8, gap: 2,
                    background: sel ? 'var(--color-primary)' : 'transparent',
                    opacity: future ? 0.25 : 1,
                    cursor: future ? 'default' : 'pointer',
                    outline: today_ && !sel ? '1.5px solid var(--color-primary)' : 'none',
                  }}
                >
                  <span style={{ fontSize: 11, fontWeight: sel || today_ ? 600 : 400, color: sel ? '#fff' : 'var(--color-text-primary)' }}>{d}</span>
                  {!future && !sel && h > 0 && (
                    <div style={{ width: 4, height: 4, borderRadius: '50%', background: HEAT_COLORS[h] }} />
                  )}
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
            <span style={{ fontSize: 15, fontWeight: 700 }}>{month}월 {day}일</span>
            {loading
              ? <span style={{ fontSize: 12, color: 'var(--color-text-tertiary)' }}>불러오는 중...</span>
              : <span style={{ fontSize: 12, color: 'var(--color-text-tertiary)' }}>인기 기사 Top {tops.length}</span>
            }
          </div>

          {!loading && tops.length === 0 && (
            <div style={{ textAlign: 'center', padding: '40px 0', color: 'var(--color-text-tertiary)', fontSize: 14 }}>
              해당 날짜의 조회 기록이 없어요
            </div>
          )}

          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {tops.map((article, i) => {
              const rankColor = i === 0 ? '#B45309' : i === 1 ? '#6B7280' : i === 2 ? '#92400E' : 'var(--color-text-tertiary)';
              const maxV = tops[0]?.viewCount ?? 1;
              return (
                <button
                  key={`${selectedDate}-${article.urlHash}`}
                  onClick={() => setDetail(article)}
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
                      <span style={{ fontSize: 11, color: 'var(--color-text-tertiary)', marginLeft: 'auto' }}>{article.timeAgo}</span>
                    </div>
                    <p style={{ fontSize: 13, fontWeight: 600, color: 'var(--color-text-primary)', lineHeight: 1.4, marginBottom: 8 }}>{article.title}</p>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <div style={{ flex: 1, height: 3, borderRadius: 2, background: 'var(--color-border)', overflow: 'hidden' }}>
                        <div style={{ height: '100%', borderRadius: 2, background: 'var(--color-primary)', width: `${(article.viewCount / maxV) * 100}%` }} />
                      </div>
                      <span style={{ fontSize: 11, color: 'var(--color-text-tertiary)', whiteSpace: 'nowrap' }}>
                        {article.viewCount > 0 ? `${article.viewCount.toLocaleString()} 회` : '발행일 기준'}
                      </span>
                    </div>
                  </div>
                  <button
                    onClick={e => { e.stopPropagation(); bm.toggle(article.urlHash, article); }}
                    style={{
                      width: 28, height: 28, borderRadius: 6, flexShrink: 0,
                      background: bm.isBookmarked(article.urlHash) ? '#FEF3C7' : 'var(--color-surface-secondary)',
                      display: 'flex', alignItems: 'center', justifyContent: 'center', transition: 'all 0.15s',
                    }}
                  >
                    <svg width="12" height="12" viewBox="0 0 24 24" fill={bm.isBookmarked(article.urlHash) ? '#D97706' : 'none'}>
                      <path d="M19 21L12 16L5 21V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2v16z"
                        stroke={bm.isBookmarked(article.urlHash) ? '#D97706' : 'var(--color-text-tertiary)'} strokeWidth="1.7" strokeLinejoin="round"/>
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
