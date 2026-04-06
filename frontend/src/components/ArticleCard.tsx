import { useState } from 'react';
import type { Article } from '../data/articles';
import type { ApiArticle } from '../data/api';

/** UI 카드에 올리는 기사: 도메인 Article 또는 API 스키마(ApiArticle) */
export type CardArticle = Article | ApiArticle;

function pickSummary(article: CardArticle): string {
  if ('summaryKobart' in article && article.summaryKobart) return article.summaryKobart;
  if ('summaryLlm' in article && article.summaryLlm) return article.summaryLlm;
  const x = article as ApiArticle;
  return (x.summary_ko || x.summary_llm || '').trim();
}

function pickFactLabel(article: CardArticle): 'FACT' | 'UNVERIFIED' | 'RUMOR' | undefined {
  if ('factLabel' in article && (article as Article).factLabel) return (article as Article).factLabel;
  return (article as ApiArticle).fact_label;
}

function pickSourceColor(article: CardArticle): string {
  return article.sourceColor ?? '#6B7280';
}

interface Props {
  article: CardArticle;
  bookmarked?: boolean;
  onBookmark?: (id: string) => void;
  onClick?: () => void;
  style?: React.CSSProperties;
}

export default function ArticleCard({ article, bookmarked = false, onBookmark, onClick, style }: Props) {
  const [copied, setCopied] = useState(false);

  const summary = pickSummary(article);
  const factLabel = pickFactLabel(article);
  const sourceColor = pickSourceColor(article);

  const handleShare = (e: React.MouseEvent) => {
    e.stopPropagation();
    navigator.clipboard
      .writeText(`[${article.source}] ${article.title}\n\n${summary}`)
      .catch(() => {});
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleBookmark = (e: React.MouseEvent) => {
    e.stopPropagation();
    onBookmark?.(article.id);
  };

  return (
    <article
      onClick={onClick}
      style={{
        background: 'var(--color-surface)',
        borderRadius: 'var(--radius-lg)',
        padding: '16px',
        boxShadow: 'var(--shadow-card)',
        cursor: 'pointer',
        position: 'relative',
        overflow: 'hidden',
        transition: 'transform 0.12s',
        ...style,
      }}
      onTouchStart={e => { (e.currentTarget as HTMLElement).style.transform = 'scale(0.985)'; }}
      onTouchEnd={e => { (e.currentTarget as HTMLElement).style.transform = ''; }}
    >
      {/* 출처 컬러 액센트 바 */}
      <div style={{
        position: 'absolute', left: 0, top: 16, bottom: 16,
        width: 3, borderRadius: '0 3px 3px 0',
        background: sourceColor,
      }} />

      {/* 소스 & 시간 */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 8, paddingLeft: 8 }}>
        <div style={{ width: 6, height: 6, borderRadius: '50%', background: sourceColor, flexShrink: 0 }} />
        <span style={{ fontSize: 12, color: 'var(--color-text-secondary)', fontWeight: 500 }}>{article.source}</span>
        {!!article.isNew && (
          <span style={{ fontSize: 10, fontWeight: 600, color: 'var(--color-primary)', background: 'var(--color-primary-light)', padding: '1px 6px', borderRadius: 4 }}>
            NEW
          </span>
        )}
        {!!article.isBreaking && (
          <span style={{ fontSize: 10, fontWeight: 600, color: '#EF4444', background: '#FEE2E2', padding: '1px 6px', borderRadius: 4 }}>
            속보
          </span>
        )}
        {/* 신뢰도 라벨 */}
        {factLabel === 'FACT' && (
          <span style={{ fontSize: 10, fontWeight: 600, color: '#059669', background: '#D1FAE5', padding: '1px 6px', borderRadius: 4 }}>
            FACT
          </span>
        )}
        {factLabel === 'RUMOR' && (
          <span style={{ fontSize: 10, fontWeight: 600, color: '#DC2626', background: '#FEE2E2', padding: '1px 6px', borderRadius: 4 }}>
            RUMOR
          </span>
        )}
        <span style={{ marginLeft: 'auto', fontSize: 11, color: 'var(--color-text-tertiary)' }}>{article.timeAgo}</span>
      </div>

      {/* 제목 */}
      <h2 style={{
        fontSize: 15, fontWeight: 600, color: 'var(--color-text-primary)',
        lineHeight: 1.45, letterSpacing: '-0.02em',
        marginBottom: 7, paddingLeft: 8,
      }}>
        {article.title}
      </h2>

      {/* 요약 — 첫 번째 줄만 표시 */}
      <p style={{
        fontSize: 13, color: 'var(--color-text-secondary)', lineHeight: 1.6,
        marginBottom: 12, paddingLeft: 8,
        display: '-webkit-box', WebkitLineClamp: 2,
        WebkitBoxOrient: 'vertical', overflow: 'hidden',
      }}>
        {summary}
      </p>

      {/* 하단: 카테고리 + 북마크 + 공유 */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 6, paddingLeft: 8 }}>
        <span style={{
          fontSize: 11, fontWeight: 500, color: 'var(--color-primary)',
          background: 'var(--color-primary-light)', padding: '3px 8px', borderRadius: 6,
        }}>
          {article.category}
        </span>

        <div style={{ marginLeft: 'auto', display: 'flex', gap: 6 }}>
          {/* 북마크 버튼 */}
          <button
            onClick={handleBookmark}
            style={{
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              width: 30, height: 28, borderRadius: 6,
              background: bookmarked ? '#FEF3C7' : 'var(--color-surface-secondary)',
              transition: 'all 0.15s',
            }}
          >
            <svg width="13" height="13" viewBox="0 0 24 24" fill={bookmarked ? '#D97706' : 'none'}>
              <path d="M19 21L12 16L5 21V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2v16z"
                stroke={bookmarked ? '#D97706' : 'var(--color-text-tertiary)'} strokeWidth="1.7" strokeLinejoin="round"/>
            </svg>
          </button>

          {/* 공유(복사) 버튼 */}
          <button
            onClick={handleShare}
            style={{
              display: 'flex', alignItems: 'center', gap: 4,
              fontSize: 11, fontWeight: 500,
              color: copied ? '#16A34A' : 'var(--color-text-tertiary)',
              background: copied ? '#DCFCE7' : 'var(--color-surface-secondary)',
              padding: '4px 10px', borderRadius: 6, transition: 'all 0.18s',
            }}
          >
            {copied ? (
              <>
                <svg width="11" height="11" viewBox="0 0 24 24" fill="none">
                  <path d="M20 6L9 17L4 12" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
                복사됨
              </>
            ) : (
              <>
                <svg width="11" height="11" viewBox="0 0 24 24" fill="none">
                  <rect x="9" y="9" width="13" height="13" rx="2" stroke="currentColor" strokeWidth="1.6"/>
                  <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" stroke="currentColor" strokeWidth="1.6"/>
                </svg>
                공유
              </>
            )}
          </button>
        </div>
      </div>
    </article>
  );
}