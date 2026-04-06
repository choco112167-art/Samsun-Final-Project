import { useState, useRef } from 'react';
import { searchArticles } from '../data/api';
import type { SearchResult } from '../data/api';
import DetailPage from './DetailPage';
import type { BookmarkHook } from '../hooks/useBookmarks';

const RECENT      = ['GPT-5 출시', 'TSMC 반도체', '오픈소스 모델', 'EU AI 규제'];
const SUGGESTIONS = ['AI 칩 설계', '오픈소스 LLM', '반도체 공급망', 'AI 규제 동향', '스타트업 투자'];

interface Props { bm: BookmarkHook; }

export default function SearchPage({ bm }: Props) {
  const [query, setQuery]         = useState('');
  const [submitted, setSubmitted] = useState('');
  const [results, setResults]     = useState<SearchResult[]>([]);
  const [loading, setLoading]     = useState(false);
  const [detail, setDetail]       = useState<SearchResult | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const doSearch = (q: string) => {
    if (!q.trim()) return;
    setLoading(true);
    setSubmitted(q);
    searchArticles(q, 15)
      .then(data => { setResults(data); setLoading(false); })
      .catch(() => { setResults([]); setLoading(false); });
  };

  if (detail) return (
    <DetailPage
      article={detail}
      bookmarked={bm.isBookmarked(detail.id)}
      onBookmark={bm.toggle}
      onBack={() => setDetail(null)}
    />
  );

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
      <style>{`
        @keyframes resultIn { from{opacity:0;transform:translateY(10px)} to{opacity:1;transform:translateY(0)} }
        @keyframes spin { to{transform:rotate(360deg)} }
      `}</style>

      <header style={{ background: 'var(--color-surface)', borderBottom: '0.5px solid var(--color-border)', padding: '18px 16px 14px', flexShrink: 0 }}>
        <h1 style={{ fontSize: 20, fontWeight: 700, letterSpacing: '-0.03em', marginBottom: 12 }}>검색</h1>
        <form onSubmit={e => { e.preventDefault(); doSearch(query); inputRef.current?.blur(); }}>
          <div style={{
            display: 'flex', alignItems: 'center', gap: 10,
            background: 'var(--color-surface-secondary)',
            border: '1px solid var(--color-border-medium)',
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
            {query && <button type="button" onClick={() => { setQuery(''); setResults([]); setSubmitted(''); }} style={{ fontSize: 18, color: 'var(--color-text-tertiary)', lineHeight: 1 }}>×</button>}
          </div>
        </form>
        <div style={{ display: 'flex', alignItems: 'center', gap: 5, marginTop: 10 }}>
          <div style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--color-primary)' }} />
          <span style={{ fontSize: 11, color: 'var(--color-text-tertiary)' }}>pgvector 유사도 검색 · Qwen3-Embedding-4B</span>
        </div>
      </header>

      <main style={{ flex: 1, overflowY: 'auto', WebkitOverflowScrolling: 'touch' }}>

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
            <p style={{ fontSize: 12, fontWeight: 600, color: 'var(--color-text-tertiary)', letterSpacing: '0.04em', textTransform: 'uppercase', marginBottom: 10 }}>최근 검색</p>
            {RECENT.map(s => (
              <button key={s} onClick={() => { setQuery(s); doSearch(s); }} style={{
                display: 'flex', alignItems: 'center', gap: 10, width: '100%',
                padding: '11px 4px', borderBottom: '0.5px solid var(--color-border)', textAlign: 'left',
              }}>
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
                  <path d="M3 12C3 7.03 7.03 3 12 3s9 4.03 9 9-4.03 9-9 9S3 16.97 3 12z" stroke="var(--color-text-tertiary)" strokeWidth="1.5"/>
                  <path d="M12 7v5l3 3" stroke="var(--color-text-tertiary)" strokeWidth="1.5" strokeLinecap="round"/>
                </svg>
                <span style={{ fontSize: 14, color: 'var(--color-text-secondary)', flex: 1 }}>{s}</span>
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none">
                  <path d="M7 17L17 7M7 7h10v10" stroke="var(--color-text-tertiary)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
              </button>
            ))}
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
            <div style={{ display: 'flex', alignItems: 'baseline', gap: 6, marginBottom: 12 }}>
              <span style={{ fontSize: 14, fontWeight: 600 }}>"{submitted}"</span>
              <span style={{ fontSize: 12, color: 'var(--color-text-tertiary)' }}>{results.length}건</span>
            </div>
            {results.length === 0 ? (
              <div style={{ textAlign: 'center', padding: '48px 0', color: 'var(--color-text-tertiary)', fontSize: 14 }}>검색 결과가 없어요</div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                {results.map((article, i) => {
                  const summary = article.summary_ko || article.summary_llm;
                  const simPct  = article.similarity !== undefined ? Math.round(article.similarity * 100) : null;
                  return (
                    <button key={article.id} onClick={() => setDetail(article)} style={{
                      background: 'var(--color-surface)', borderRadius: 'var(--radius-lg)',
                      padding: '14px', boxShadow: 'var(--shadow-card)', textAlign: 'left',
                      transition: 'transform 0.12s', animation: `resultIn 0.25s ${i * 0.04}s ease both`,
                    }}
                      onTouchStart={e => { (e.currentTarget as HTMLElement).style.transform = 'scale(0.985)'; }}
                      onTouchEnd={e => { (e.currentTarget as HTMLElement).style.transform = ''; }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 6 }}>
                        <div style={{ width: 5, height: 5, borderRadius: '50%', background: article.sourceColor ?? '#6B7280', flexShrink: 0 }} />
                        <span style={{ fontSize: 11, color: 'var(--color-text-secondary)' }}>{article.source}</span>
                        <span style={{ fontSize: 11, color: 'var(--color-text-tertiary)' }}>{article.timeAgo ?? ''}</span>
                        {simPct !== null && (
                          <div style={{ marginLeft: 'auto', fontSize: 11, fontWeight: 600, color: 'var(--color-primary)', background: 'var(--color-primary-light)', padding: '2px 8px', borderRadius: 6 }}>
                            유사도 {simPct}%
                          </div>
                        )}
                      </div>
                      <p style={{ fontSize: 13, fontWeight: 600, color: 'var(--color-text-primary)', lineHeight: 1.4, marginBottom: 5 }}>{article.title}</p>
                      <p style={{ fontSize: 12, color: 'var(--color-text-secondary)', lineHeight: 1.5, display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>
                        {summary}
                      </p>
                      <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: 8 }}>
                        <button onClick={e => { e.stopPropagation(); bm.toggle(article.id); }} style={{
                          display: 'flex', alignItems: 'center', gap: 4, fontSize: 11, fontWeight: 500,
                          color: bm.isBookmarked(article.id) ? '#D97706' : 'var(--color-text-tertiary)',
                          background: bm.isBookmarked(article.id) ? '#FEF3C7' : 'var(--color-surface-secondary)',
                          padding: '4px 10px', borderRadius: 6, transition: 'all 0.15s',
                        }}>
                          <svg width="11" height="11" viewBox="0 0 24 24" fill={bm.isBookmarked(article.id) ? '#D97706' : 'none'}>
                            <path d="M19 21L12 16L5 21V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2v16z" stroke={bm.isBookmarked(article.id) ? '#D97706' : 'currentColor'} strokeWidth="1.7" strokeLinejoin="round"/>
                          </svg>
                          {bm.isBookmarked(article.id) ? '저장됨' : '저장'}
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
