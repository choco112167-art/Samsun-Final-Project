import { useState, useRef, useCallback } from 'react';
import { searchArticles } from '../data/api';
import { toArticle } from '../data/articles';
import type { Article } from '../data/articles';
import DetailPage from './DetailPage';
import type { BookmarkHook } from '../hooks/useBookmarks';

/** SearchResult를 Article로 변환하되 similarity는 보존 */
type SearchItem = Article & { similarity?: number };

const RECENT_KEY  = 'samsun_recent_searches';
const MAX_RECENT  = 8;
const SUGGESTIONS = ['AI 칩 설계', '오픈소스 LLM', '반도체 공급망', 'AI 규제 동향', '스타트업 투자'];

/** localStorage에서 최근 검색어 목록을 불러온다 */
function loadRecent(): string[] {
  try {
    return JSON.parse(localStorage.getItem(RECENT_KEY) ?? '[]');
  } catch {
    return [];
  }
}

/** 검색어를 최근 검색 목록 맨 앞에 추가하고 저장한다 (중복 제거, 최대 MAX_RECENT개) */
function saveRecent(q: string, prev: string[]): string[] {
  const next = [q, ...prev.filter(s => s !== q)].slice(0, MAX_RECENT);
  try { localStorage.setItem(RECENT_KEY, JSON.stringify(next)); } catch { /* noop */ }
  return next;
}

interface Props { bm: BookmarkHook; }

export default function SearchPage({ bm }: Props) {
  const [query, setQuery]         = useState('');
  const [submitted, setSubmitted] = useState('');
  const [results, setResults]     = useState<SearchItem[]>([]);
  const [loading, setLoading]     = useState(false);
  const [detail, setDetail]       = useState<SearchItem | null>(null);
  const [recent, setRecent]       = useState<string[]>(loadRecent);
  const inputRef = useRef<HTMLInputElement>(null);

  const doSearch = useCallback((q: string) => {
    if (!q.trim()) return;
    const trimmed = q.trim();
    setLoading(true);
    setSubmitted(trimmed);
    // 검색할 때마다 최근 검색 목록 맨 앞에 추가
    setRecent(prev => saveRecent(trimmed, prev));
    searchArticles(trimmed, 15)
      .then(data => {
        // SearchResult(ApiArticle 기반) → Article(camelCase)로 변환하고 similarity 보존
        const items: SearchItem[] = data.map(r => ({ ...toArticle(r), similarity: r.similarity }));
        setResults(items);
        setLoading(false);
      })
      .catch(() => { setResults([]); setLoading(false); });
  }, []);

  /** 최근 검색어 항목 하나 삭제 */
  const removeRecent = (s: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setRecent(prev => {
      const next = prev.filter(r => r !== s);
      try { localStorage.setItem(RECENT_KEY, JSON.stringify(next)); } catch { /* noop */ }
      return next;
    });
  };

  /** 최근 검색어 전체 삭제 */
  const clearRecent = () => {
    setRecent([]);
    try { localStorage.removeItem(RECENT_KEY); } catch { /* noop */ }
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
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden', background: 'var(--color-header-bg)' }}>
      <style>{`
        @keyframes resultIn { from{opacity:0;transform:translateY(10px)} to{opacity:1;transform:translateY(0)} }
        @keyframes spin { to{transform:rotate(360deg)} }
      `}</style>

      <header style={{ flexShrink: 0, padding: '22px 16px 16px' }}>
        <h1 style={{ fontSize: 26, fontWeight: 800, letterSpacing: '-0.04em', color: 'var(--color-header-text)', marginBottom: 14 }}>검색</h1>
        <form onSubmit={e => { e.preventDefault(); doSearch(query); inputRef.current?.blur(); }}>
          <div style={{
            display: 'flex', alignItems: 'center', gap: 10,
            background: 'rgba(0,0,0,0.05)',
            border: '1px solid var(--color-border)',
            borderRadius: 'var(--radius-md)', padding: '10px 14px',
          }}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" style={{ flexShrink: 0 }}>
              <circle cx="11" cy="11" r="6" stroke="var(--color-text-tertiary)" strokeWidth="1.6"/>
              <path d="M16.5 16.5L20 20" stroke="var(--color-text-tertiary)" strokeWidth="1.6" strokeLinecap="round"/>
            </svg>
            <input ref={inputRef} value={query} onChange={e => setQuery(e.target.value)}
              placeholder="자연어로 검색해보세요"
              style={{ flex: 1, background: 'none', border: 'none', outline: 'none', fontSize: 14, color: 'var(--color-text-primary)', fontFamily: 'inherit' }}
            />
            {query && (
              <button type="button" onClick={() => { setQuery(''); setResults([]); setSubmitted(''); }}
                style={{ fontSize: 18, color: 'var(--color-text-tertiary)', lineHeight: 1 }}>×</button>
            )}
          </div>
        </form>
      </header>

      <main style={{ flex: 1, overflowY: 'auto', WebkitOverflowScrolling: 'touch', background: 'var(--color-bg)', borderRadius: '32px 32px 0 0' }}>

        {/* 로딩 */}
        {loading && (
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '60px 0', gap: 12 }}>
            <div style={{ width: 24, height: 24, border: '2.5px solid var(--color-border)', borderTopColor: 'var(--color-primary)', borderRadius: '50%', animation: 'spin 0.7s linear infinite' }} />
            <span style={{ fontSize: 13, color: 'var(--color-text-tertiary)' }}>벡터 검색 중...</span>
          </div>
        )}

        {/* 초기 상태 */}
        {!loading && !submitted && (
          <div style={{ padding: '20px 16px' }}>

            {/* 최근 검색 */}
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10 }}>
              <p style={{ fontSize: 12, fontWeight: 600, color: 'var(--color-text-tertiary)', letterSpacing: '0.04em', textTransform: 'uppercase' }}>최근 검색</p>
              {recent.length > 0 && (
                <button onClick={clearRecent} style={{ fontSize: 11, color: 'var(--color-text-tertiary)' }}>전체 삭제</button>
              )}
            </div>

            {recent.length === 0 ? (
              <p style={{ fontSize: 13, color: 'var(--color-text-tertiary)', padding: '12px 0 8px' }}>최근 검색 기록이 없어요</p>
            ) : (
              recent.map(s => (
                <div key={s} style={{ display: 'flex', alignItems: 'center', gap: 10, borderBottom: '0.5px solid var(--color-border)' }}>
                  <button onClick={() => { setQuery(s); doSearch(s); }} style={{
                    display: 'flex', alignItems: 'center', gap: 10, flex: 1,
                    padding: '11px 4px', textAlign: 'left',
                  }}>
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
                      <path d="M3 12C3 7.03 7.03 3 12 3s9 4.03 9 9-4.03 9-9 9S3 16.97 3 12z" stroke="var(--color-text-tertiary)" strokeWidth="1.5"/>
                      <path d="M12 7v5l3 3" stroke="var(--color-text-tertiary)" strokeWidth="1.5" strokeLinecap="round"/>
                    </svg>
                    <span style={{ fontSize: 14, color: 'var(--color-text-secondary)', flex: 1 }}>{s}</span>
                  </button>
                  {/* 개별 삭제 버튼 */}
                  <button onClick={e => removeRecent(s, e)} style={{
                    padding: '4px 6px', fontSize: 16, color: 'var(--color-text-tertiary)', lineHeight: 1,
                  }}>×</button>
                </div>
              ))
            )}

            {/* 추천 검색어 */}
            <p style={{ fontSize: 12, fontWeight: 600, color: 'var(--color-text-tertiary)', letterSpacing: '0.04em', textTransform: 'uppercase', marginTop: 24, marginBottom: 10 }}>추천 검색어</p>
            <div style={{ display: 'flex', gap: 7, flexWrap: 'wrap' }}>
              {SUGGESTIONS.map(s => (
                <button key={s} onClick={() => { setQuery(s); doSearch(s); }} style={{
                  fontSize: 12, padding: '6px 12px', borderRadius: 20,
                  background: 'var(--color-surface)', border: '0.5px solid var(--color-border)',
                  color: 'var(--color-text-secondary)', boxShadow: 'var(--shadow-card)',
                }}>{s}</button>
              ))}
            </div>
          </div>
        )}

        {/* 검색 결과 */}
        {!loading && submitted && (
          <div style={{ padding: '14px 16px 24px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 12 }}>
              <span style={{ fontSize: 14, fontWeight: 600 }}>"{submitted}"</span>
              <span style={{ fontSize: 12, color: 'var(--color-text-tertiary)' }}>{results.length}건</span>
              <button onClick={() => { setSubmitted(''); setResults([]); setQuery(''); }}
                style={{ marginLeft: 'auto', fontSize: 12, color: 'var(--color-text-tertiary)' }}>← 돌아가기</button>
            </div>
            {results.length === 0 ? (
              <div style={{ textAlign: 'center', padding: '48px 0', color: 'var(--color-text-tertiary)', fontSize: 14 }}>검색 결과가 없어요</div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                {results.map((article, i) => {
                  const simPct = article.similarity !== undefined ? Math.round(article.similarity * 100) : null;
                  return (
                    <button key={article.urlHash} onClick={() => setDetail(article)} style={{
                      background: 'var(--color-surface)', borderRadius: 'var(--radius-lg)',
                      padding: '14px', boxShadow: 'var(--shadow-card)', textAlign: 'left',
                      transition: 'transform 0.12s', animation: `resultIn 0.25s ${i * 0.04}s ease both`,
                    }}
                      onTouchStart={e => { (e.currentTarget as HTMLElement).style.transform = 'scale(0.985)'; }}
                      onTouchEnd={e => { (e.currentTarget as HTMLElement).style.transform = ''; }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 6 }}>
                        <div style={{ width: 5, height: 5, borderRadius: '50%', background: article.sourceColor, flexShrink: 0 }} />
                        <span style={{ fontSize: 11, color: 'var(--color-text-secondary)' }}>{article.source}</span>
                        <span style={{ fontSize: 11, color: 'var(--color-text-tertiary)' }}>{article.timeAgo}</span>
                        {simPct !== null && (
                          <div style={{ marginLeft: 'auto', fontSize: 11, fontWeight: 600, color: 'var(--color-primary)', background: 'var(--color-primary-light)', padding: '2px 8px', borderRadius: 6 }}>
                            유사도 {simPct}%
                          </div>
                        )}
                      </div>
                      <p style={{ fontSize: 13, fontWeight: 600, color: 'var(--color-text-primary)', lineHeight: 1.4, marginBottom: 5 }}>{article.title}</p>
                      <p style={{ fontSize: 12, color: 'var(--color-text-secondary)', lineHeight: 1.5, display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>
                        {article.summaryFormal}
                      </p>
                      <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: 8 }}>
                        <button onClick={e => { e.stopPropagation(); bm.toggle(article.urlHash); }} style={{
                          display: 'flex', alignItems: 'center', gap: 4, fontSize: 11, fontWeight: 500,
                          color: bm.isBookmarked(article.urlHash) ? '#D97706' : 'var(--color-text-tertiary)',
                          background: bm.isBookmarked(article.urlHash) ? '#FEF3C7' : 'var(--color-surface-secondary)',
                          padding: '4px 10px', borderRadius: 6, transition: 'all 0.15s',
                        }}>
                          <svg width="11" height="11" viewBox="0 0 24 24" fill={bm.isBookmarked(article.urlHash) ? '#D97706' : 'none'}>
                            <path d="M19 21L12 16L5 21V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2v16z" stroke={bm.isBookmarked(article.urlHash) ? '#D97706' : 'currentColor'} strokeWidth="1.7" strokeLinejoin="round"/>
                          </svg>
                          {bm.isBookmarked(article.urlHash) ? '저장됨' : '저장'}
                        </button>
                      </div>
                    </button>
                  );
                })}
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  );
}
