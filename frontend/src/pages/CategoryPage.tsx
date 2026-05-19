import { useState, useEffect, useRef, useCallback } from 'react';
import { ApiError, fetchArticles } from '../data/api';
import { CATEGORIES, filterByCategory, articleCompletenessScore, articleDisplayTitle, factStatusWeight, hasKoreanTitle, normalizeFactStatus, type Article, type Category } from '../data/articles';
import { FactStatusBadge } from '../components/FactStatusBadge';
import DetailPage from './DetailPage';
import type { BookmarkHook } from '../hooks/useBookmarks';
import type { SummaryTone } from '../hooks/useTonePreference';
import { restoreArticleListScroll, useArticleDetailNavigation } from '../hooks/useArticleDetailNavigation';

type SubTab = '전체' | Category;
const CATEGORY_TABS: SubTab[] = ['전체', ...CATEGORIES];

interface Props {
  bm: BookmarkHook;
  onArticleClick?: (urlHash: string) => void;
  tone: SummaryTone;
  onToneChange: (tone: SummaryTone) => void;
}

export default function CategoryPage({ bm, onArticleClick, tone, onToneChange }: Props) {
  const [tab, setTab]           = useState<SubTab>('전체');
  const [detail, setDetail]     = useState<Article | null>(null);
  const [articles, setArticles] = useState<Article[]>([]);
  const [error, setError]       = useState<string | null>(null);
  const mainRef = useRef<HTMLElement | null>(null);
  const scrollPos = useRef(0);

  useEffect(() => {
    fetchArticles({ limit: 250 })
      .then(data => {
        setArticles(data);
        setError(null);
      })
      .catch((err: unknown) => {
        const message = err instanceof ApiError || err instanceof Error
          ? err.message
          : '기사를 불러오지 못했어요';
        setError(message);
      });
  }, []);

  // Article.category는 toArticle()에서 이미 normalizeCategory() 가 적용된 UI 카테고리.
  // HomePage 와 동일한 공유 유틸을 통해 두 화면의 결과가 완전히 일치하도록 보장한다.
  const filtered = filterByCategory(articles, tab);
  const sorted   = [...filtered].sort((a, b) => {
    const dateDelta = new Date(b.publishedAt).getTime() - new Date(a.publishedAt).getTime();
    if (dateDelta !== 0) return dateDelta;
    const qualityDelta = articleCompletenessScore(b) - articleCompletenessScore(a);
    if (qualityDelta !== 0) return qualityDelta;
    const statusDelta = factStatusWeight(b.factLabel) - factStatusWeight(a.factLabel);
    if (statusDelta !== 0) return statusDelta;
    return (b.credibilityScore ?? 0) - (a.credibilityScore ?? 0);
  });

  const openDetail = (article: Article) => {
    scrollPos.current = mainRef.current?.scrollTop ?? 0;
    onArticleClick?.(article.urlHash);
    setDetail(article);
  };

  const closeDetail = useCallback(() => {
    setDetail(null);
    restoreArticleListScroll(mainRef, scrollPos.current);
  }, []);

  useArticleDetailNavigation(Boolean(detail), closeDetail);

  if (detail) return (
    <DetailPage article={detail} bookmarked={bm.isBookmarked(detail.urlHash)} onBookmark={bm.toggle} onBack={closeDetail} tone={tone} onToneChange={onToneChange} />
  );

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden', background: 'var(--color-header-bg)' }}>
      <style>{`@keyframes rankIn { from{opacity:0;transform:translateX(-8px)} to{opacity:1;transform:translateX(0)} }`}</style>

      {/* 헤더 */}
      <header style={{ flexShrink: 0, padding: '22px 20px 0' }}>
        <h1 style={{ fontSize: 26, fontWeight: 800, letterSpacing: '-0.04em', color: 'var(--color-header-text)', marginBottom: 3 }}>카테고리</h1>
        <p style={{ fontSize: 12, color: 'var(--color-header-text-secondary)', marginBottom: 0 }}>분야별 기사 모아보기</p>
        {/* 언더라인 탭 */}
        <div style={{ display: 'flex', overflowX: 'auto', scrollbarWidth: 'none', marginTop: 10 }}>
          {CATEGORY_TABS.map(t => (
            <button key={t} onClick={() => setTab(t)} style={{
              flexShrink: 0, padding: '10px 14px', fontSize: 13,
              fontWeight: tab === t ? 600 : 400,
              color: tab === t ? 'var(--color-primary)' : 'var(--color-header-text-secondary)',
              borderBottom: `2px solid ${tab === t ? 'var(--color-primary)' : 'transparent'}`,
              whiteSpace: 'nowrap', transition: 'all 0.15s',
            }}>{t}</button>
          ))}
        </div>
      </header>

      {/* 메인 컨텐츠 */}
      <main ref={mainRef} style={{
        flex: 1, overflowY: 'auto', WebkitOverflowScrolling: 'touch',
        background: 'var(--color-bg)', borderRadius: '32px 32px 0 0',
        padding: '16px 16px 24px', display: 'flex', flexDirection: 'column', gap: 8,
      }}>
        <p style={{ fontSize: 11, color: 'var(--color-text-tertiary)', lineHeight: 1.55, padding: '0 2px 6px' }}>
          신뢰도 순위는 출처, 교차검증 여부, AI 판별 결과를 종합한 참고 지표입니다.
        </p>
        {sorted.map((article, i) => {
          const status = normalizeFactStatus(article.factLabel);
          const rankColor = i < 3 ? 'var(--color-primary)' : 'var(--color-text-tertiary)';
          const barColor = status === 'RUMOR'
            ? '#F59E0B'
            : status === 'HITL_REQUIRED'
              ? '#8B5CF6'
              : status === 'UNVERIFIED'
              ? '#8B95A1'
              : i < 3 ? 'var(--color-primary)' : 'var(--color-text-tertiary)';
          const maxScore  = sorted[0]?.credibilityScore ?? 1;
          return (
            <button
              key={article.urlHash}
              onClick={() => openDetail(article)}
              style={{
                display: 'flex', alignItems: 'flex-start', gap: 12,
                background: 'var(--color-surface)', borderRadius: 'var(--radius-lg)',
                padding: '14px', boxShadow: 'var(--shadow-card)', textAlign: 'left',
                transition: 'transform 0.12s', animation: `rankIn 0.25s ${i * 0.04}s ease both`,
              }}
              onTouchStart={e => { (e.currentTarget as HTMLElement).style.transform = 'scale(0.985)'; }}
              onTouchEnd={e => { (e.currentTarget as HTMLElement).style.transform = ''; }}
            >
              <span aria-label={`신뢰도 순위 ${i + 1}위`} style={{ fontSize: 11, fontWeight: 800, color: rankColor, minWidth: 30, paddingTop: 2, fontVariantNumeric: 'tabular-nums', lineHeight: 1.2 }}>
                {i + 1}위
              </span>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 5, marginBottom: 5 }}>
                  <div style={{ width: 5, height: 5, borderRadius: '50%', background: article.sourceColor, flexShrink: 0 }} />
                  <span style={{ fontSize: 11, color: 'var(--color-text-secondary)' }}>{article.source}</span>
                  <FactStatusBadge label={article.factLabel} />
                  {article.isBreaking && <span style={{ fontSize: 10, fontWeight: 600, color: '#EF4444' }}>속보</span>}
                  <span style={{ fontSize: 11, color: 'var(--color-text-tertiary)', marginLeft: 'auto' }}>{article.timeAgo}</span>
                </div>
                <p style={{ fontSize: 13, fontWeight: hasKoreanTitle(article) ? 600 : 500, color: hasKoreanTitle(article) ? 'var(--color-text-primary)' : 'var(--color-text-secondary)', lineHeight: 1.4, marginBottom: 8 }}>{articleDisplayTitle(article)}</p>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <div style={{ flex: 1, height: 3, borderRadius: 2, background: 'var(--color-border)', overflow: 'hidden' }}>
                    <div style={{ height: '100%', borderRadius: 2, background: barColor, width: `${((article.credibilityScore ?? 0) / maxScore) * 100}%`, opacity: i < 3 ? 1 : 0.45 }} />
                  </div>
                  <span style={{ fontSize: 11, color: 'var(--color-text-tertiary)', whiteSpace: 'nowrap' }}>신뢰도 {Math.round((article.credibilityScore ?? 0) * 100)}%</span>
                </div>
              </div>
              <div
                role="button"
                onClick={e => { e.stopPropagation(); bm.toggle(article.urlHash, article); }}
                style={{
                  width: 30, height: 30, borderRadius: 8, flexShrink: 0, marginTop: -2,
                  background: bm.isBookmarked(article.urlHash) ? '#FEF3C7' : 'var(--color-surface-secondary)',
                  display: 'flex', alignItems: 'center', justifyContent: 'center', transition: 'all 0.15s',
                  cursor: 'pointer',
                }}
              >
                <svg width="13" height="13" viewBox="0 0 24 24" fill={bm.isBookmarked(article.urlHash) ? '#D97706' : 'none'}>
                  <path d="M19 21L12 16L5 21V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2v16z" stroke={bm.isBookmarked(article.urlHash) ? '#D97706' : 'var(--color-text-tertiary)'} strokeWidth="1.7" strokeLinejoin="round"/>
                </svg>
              </div>
            </button>
          );
        })}

        {error && (
          <div style={{ textAlign: 'center', padding: '48px 14px', color: 'var(--color-text-tertiary)', fontSize: 13, lineHeight: 1.6, wordBreak: 'break-word' }}>
            <p style={{ color: 'var(--color-text-primary)', fontWeight: 700, marginBottom: 6 }}>카테고리 기사를 불러오지 못했어요</p>
            <p>{error}</p>
          </div>
        )}

        {!error && sorted.length === 0 && (
          <div style={{ textAlign: 'center', padding: '60px 14px', color: 'var(--color-text-tertiary)', fontSize: 14, lineHeight: 1.65 }}>
            {articles.length === 0 ? 'Supabase 연결은 성공했지만 articles 조회 결과가 0건입니다.' : '해당 카테고리의 기사가 없습니다'}
          </div>
        )}
      </main>
    </div>
  );
}
