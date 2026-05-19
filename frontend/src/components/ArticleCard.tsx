import { useState } from 'react';
import { Badge } from './Badge';
import { isValidSummary, hasKoreanTitle, type Article } from '../data/articles';
import type { ApiArticle } from '../data/api';
import type { SummaryTone } from '../hooks/useTonePreference';
import { FactStatusBadge, factStatusColor } from './FactStatusBadge';
import { categoryStyle, normalizeCategory } from '../data/categories';

export type CardArticle = Article | ApiArticle;

/** 카드가 Article 또는 원본 ApiArticle 일 때 한국어 제목 우선 */
function cardHeadline(article: CardArticle): string {
  let ko = '';
  if ('titleKo' in article) ko = ((article as Article).titleKo ?? '').trim();
  else ko = ((article as ApiArticle).title_ko ?? '').trim();
  return ko || '제목 번역 중입니다.';
}

function pickSummary(article: CardArticle, tone: SummaryTone): string {
  if ('summaryFormal' in article) {
    const selected = tone === 'formal' ? article.summaryFormal : article.summaryCasual;
    return isValidSummary(selected) ? selected.trim() : '';
  }
  const selected = tone === 'formal' ? article.summary_formal : article.summary_casual;
  return isValidSummary(selected) ? selected.trim() : '';
}

function hasLocalizedHeadline(article: CardArticle): boolean {
  if ('titleKo' in article) return hasKoreanTitle(article);
  return Boolean(((article as ApiArticle).title_ko ?? '').trim());
}

function pickFactLabel(article: CardArticle): string | undefined {
  if ('factLabel' in article && article.factLabel) return article.factLabel;
  if ('fact_label' in article) return article.fact_label;
  return undefined;
}

function pickTimeAgo(article: CardArticle): string {
  if ('timeAgo' in article && article.timeAgo) return article.timeAgo;
  if ('time_ago' in article && article.time_ago) return article.time_ago;
  return '';
}

function sourceTone(source: string) {
  const palette: Record<string, { color: string; background: string; border: string }> = {
    'TechCrunch': { color: '#1D4ED8', background: '#EFF6FF', border: '#BFDBFE' },
    'MIT Technology Review': { color: '#0F766E', background: '#ECFDF5', border: '#A7F3D0' },
    'The Guardian Tech': { color: '#9A3412', background: '#FFF7ED', border: '#FED7AA' },
    'IEEE Spectrum': { color: '#4338CA', background: '#EEF2FF', border: '#C7D2FE' },
    'The Decoder': { color: '#6D28D9', background: '#F5F3FF', border: '#DDD6FE' },
    'VentureBeat AI': { color: '#BE123C', background: '#FFF1F2', border: '#FECDD3' },
    'The Verge': { color: '#334155', background: '#F8FAFC', border: '#CBD5E1' },
  };
  if (/reddit|hacker news/i.test(source)) return { color: '#B45309', background: '#FFFBEB', border: '#FDE68A' };
  return palette[source] ?? { color: '#4E5968', background: '#F2F4F6', border: '#E5E8EB' };
}

interface Props {
  article: CardArticle;
  bookmarked?: boolean;
  onBookmark?: (id: string, article?: Article) => void;
  onClick?: () => void;
  style?: React.CSSProperties;
  tone?: SummaryTone;
}

export default function ArticleCard({ article, bookmarked = false, onBookmark, onClick, style, tone = 'formal' }: Props) {
  const [copied, setCopied] = useState(false);

  const summary = pickSummary(article, tone);
  const factLabel = pickFactLabel(article);
  const sourceColor = factStatusColor(factLabel);
  const localizedHeadline = hasLocalizedHeadline(article);
  const category = normalizeCategory(article.category, article.source);
  const categoryTone = categoryStyle(category);
  const sourceBadgeTone = sourceTone(article.source);
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
          fontSize: 11,
          color: sourceBadgeTone.color,
          fontWeight: 800,
          background: sourceBadgeTone.background,
          border: `1px solid ${sourceBadgeTone.border}`,
          padding: '3px 7px',
          borderRadius: 999,
          maxWidth: 90, overflow: 'hidden', textOverflow: 'ellipsis',
          whiteSpace: 'nowrap', minWidth: 0,
        }}>{article.source}</span>
        {!!('isNew' in article ? article.isNew : article.is_new) && (
          <Badge badgeStyle="fill" type="blue" size="tiny">NEW</Badge>
        )}
        {!!('isBreaking' in article ? article.isBreaking : article.is_breaking) && (
          <Badge badgeStyle="fill" type="red" size="tiny">속보</Badge>
        )}
        <FactStatusBadge label={factLabel} />
        <span style={{
          marginLeft: 'auto', fontSize: 11, color: 'var(--color-text-tertiary)',
          flexShrink: 0, whiteSpace: 'nowrap',
        }}>{pickTimeAgo(article)}</span>
      </div>
      <p style={{
        fontSize: 10,
        color: 'var(--color-text-tertiary)',
        lineHeight: 1.45,
        margin: '-2px 0 7px',
        paddingLeft: 8,
      }}>
        신뢰도는 출처, 교차검증 여부, AI 판별 결과를 종합한 참고 지표입니다.
      </p>

      <h2 style={{
        fontSize: 15, fontWeight: localizedHeadline ? 600 : 500,
        color: localizedHeadline ? 'var(--color-text-primary)' : 'var(--color-text-secondary)',
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
          요약 생성 중입니다.
        </p>
      )}

      <div style={{ display: 'flex', alignItems: 'center', paddingLeft: 8 }}>
        <span style={{
          fontSize: 11,
          fontWeight: 800,
          color: categoryTone.color,
          background: categoryTone.background,
          border: `1px solid ${categoryTone.border}`,
          padding: '4px 9px',
          borderRadius: 999,
          boxShadow: '0 3px 8px rgba(49,130,246,0.08)',
        }}>
          {category}
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
