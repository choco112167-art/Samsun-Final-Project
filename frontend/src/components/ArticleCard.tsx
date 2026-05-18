import { useState } from 'react';
import { Badge } from './Badge';
import type { Article } from '../data/articles';
import type { ApiArticle } from '../data/api';

export type CardArticle = Article | ApiArticle;

/** 카드가 Article 또는 원본 ApiArticle 일 때 한국어 제목 우선 */
function cardHeadline(article: CardArticle): string {
  let ko = '';
  if ('titleKo' in article) ko = ((article as Article).titleKo ?? '').trim();
  else ko = ((article as ApiArticle).title_ko ?? '').trim();
  const fb = (article.title ?? '').trim();
  return ko || fb;
}

function pickSummary(article: CardArticle): string {
  if ('summaryFormal' in article && article.summaryFormal?.trim()) return article.summaryFormal.trim();
  if ('summary_formal' in article && article.summary_formal?.trim()) return article.summary_formal.trim();
  return '';
}

function pickFactLabel(article: CardArticle): 'FACT' | 'UNVERIFIED' | 'RUMOR' | undefined {
  if ('factLabel' in article && article.factLabel) return article.factLabel;
  if ('fact_label' in article) return article.fact_label;
  return undefined;
}

function pickSourceColor(article: CardArticle): string {
  if ('sourceColor' in article && article.sourceColor) return article.sourceColor;
  if ('source_color' in article && article.source_color) return article.source_color;
  return '#6B7280';
}

function pickTimeAgo(article: CardArticle): string {
  if ('timeAgo' in article && article.timeAgo) return article.timeAgo;
  if ('time_ago' in article && article.time_ago) return article.time_ago;
  return '';
}

interface Props {
  article: CardArticle;
  bookmarked?: boolean;
  onBookmark?: (id: string, article?: Article) => void;
  onClick?: () => void;
  style?: React.CSSProperties;
}

export default function ArticleCard({ article, bookmarked = false, onBookmark, onClick, style }: Props) {
  const [copied, setCopied] = useState(false);

  const summary = pickSummary(article);
  const factLabel = pickFactLabel(article);
  const sourceColor = pickSourceColor(article);
  const urlHash = 'urlHash' in article && article.urlHash
    ? article.urlHash
    : (article as ApiArticle).url_hash;

  const asArticle = (): Article | undefined => {
    if ('urlHash' in article && article.urlHash) return article as Article;
    return undefined;
  };

  const handleShare = (e: React.MouseEvent) => {
    e.stopPropagation();
    navigator.clipboard
      .writeText(`[${article.source}] ${cardHeadline(article)}\n\n${summary}`)
      .catch(() => {});
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleBookmark = (e: React.MouseEvent) => {
    e.stopPropagation();
    const full = asArticle();
    onBookmark?.(urlHash, full);
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
        transition: 'transform 0.12s',
        ...style,
      }}
      onTouchStart={e => { (e.currentTarget as HTMLElement).style.transform = 'scale(0.985)'; }}
      onTouchEnd={e => { (e.currentTarget as HTMLElement).style.transform = ''; }}
    >
      <div style={{
        position: 'absolute', left: 0, top: 16, bottom: 16,
        width: 3, borderRadius: '0 3px 3px 0',
        background: sourceColor,
      }} />

      <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 8, paddingLeft: 8 }}>
        <div style={{ width: 6, height: 6, borderRadius: '50%', background: sourceColor, flexShrink: 0 }} />
        <span style={{
          fontSize: 12, color: 'var(--color-text-secondary)', fontWeight: 500,
          maxWidth: 90, overflow: 'hidden', textOverflow: 'ellipsis',
          whiteSpace: 'nowrap', minWidth: 0,
        }}>{article.source}</span>
        {!!('isNew' in article ? article.isNew : article.is_new) && (
          <Badge badgeStyle="fill" type="blue" size="tiny">NEW</Badge>
        )}
        {!!('isBreaking' in article ? article.isBreaking : article.is_breaking) && (
          <Badge badgeStyle="fill" type="red" size="tiny">속보</Badge>
        )}
        {factLabel === 'FACT' && (
          <Badge badgeStyle="fill" type="green" size="tiny">FACT</Badge>
        )}
        {factLabel === 'RUMOR' && (
          <Badge badgeStyle="weak" type="red" size="tiny">RUMOR</Badge>
        )}
        <span style={{
          marginLeft: 'auto', fontSize: 11, color: 'var(--color-text-tertiary)',
          flexShrink: 0, whiteSpace: 'nowrap',
        }}>{pickTimeAgo(article)}</span>
      </div>

      <h2 style={{
        fontSize: 15, fontWeight: 600, color: 'var(--color-text-primary)',
        lineHeight: 1.45, letterSpacing: '-0.02em',
        marginBottom: 7, paddingLeft: 8,
      }}>
        {cardHeadline(article)}
      </h2>

      {summary ? (
        <p style={{
          fontSize: 13, color: 'var(--color-text-secondary)', lineHeight: 1.6,
          marginBottom: 12, paddingLeft: 8,
          display: '-webkit-box', WebkitLineClamp: 2,
          WebkitBoxOrient: 'vertical', overflow: 'hidden',
        }}>
          {summary}
        </p>
      ) : (
        <p style={{
          fontSize: 13, color: 'var(--color-text-tertiary)', lineHeight: 1.6,
          marginBottom: 12, paddingLeft: 8,
        }}>
          요약이 아직 없습니다.
        </p>
      )}

      <div style={{ display: 'flex', alignItems: 'center', paddingLeft: 8 }}>
        <span style={{
          fontSize: 11, fontWeight: 500, color: 'var(--color-primary)',
          background: 'var(--color-primary-light)', padding: '3px 8px', borderRadius: 6,
        }}>
          {'category' in article ? article.category : ''}
        </span>

        <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 6 }}>
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

          <button
            onClick={handleShare}
            style={{
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              height: 28, padding: '0 10px', borderRadius: 6, fontSize: 12, fontWeight: 500,
              background: copied ? 'var(--color-primary-light)' : 'var(--color-surface-secondary)',
              color: copied ? 'var(--color-primary)' : 'var(--color-text-secondary)',
              border: '1px solid',
              borderColor: copied ? 'var(--color-primary-mid)' : 'var(--color-border)',
              transition: 'all 0.15s',
            }}
          >
            {copied ? '복사됨' : '공유'}
          </button>
        </div>
      </div>
    </article>
  );
}
