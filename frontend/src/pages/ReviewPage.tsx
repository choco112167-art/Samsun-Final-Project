import { useEffect, useMemo, useState } from 'react';
import { fetchArticles } from '../data/api';
import { articleDisplayTitle, normalizeFactStatus, type Article } from '../data/articles';
import { FactStatusBadge, factStatusDescription, factStatusText } from '../components/FactStatusBadge';
import { tossOpenURL } from '../lib/toss';

const REVIEW_STATUSES = new Set(['HITL_REQUIRED', 'UNVERIFIED', 'RUMOR', 'INSIGHT']);

function sourceUrl(article: Article): string {
  return (article.url || article.sourceUrl || article.originalUrl || '').trim();
}

function canOpen(url: string): boolean {
  return url.startsWith('http://') || url.startsWith('https://');
}

export default function ReviewPage() {
  const [articles, setArticles] = useState<Article[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    fetchArticles({ limit: 200 })
      .then(rows => setArticles(rows))
      .catch(() => setError('검토 대상 목록을 불러오지 못했습니다.'))
      .finally(() => setLoading(false));
  }, []);

  const reviewItems = useMemo(
    () => articles.filter(article => REVIEW_STATUSES.has(normalizeFactStatus(article.factLabel))),
    [articles],
  );

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100dvh', maxWidth: 480, margin: '0 auto', background: 'var(--color-bg)' }}>
      <header style={{ padding: '22px 20px 16px', background: 'var(--color-header-bg)' }}>
        <p style={{ fontSize: 12, fontWeight: 700, color: 'var(--color-header-text-secondary)', marginBottom: 5 }}>
          발표용 POC
        </p>
        <h1 style={{ fontSize: 24, fontWeight: 800, color: 'var(--color-header-text)', letterSpacing: '-0.03em' }}>
          검토 대상 보기
        </h1>
        <p style={{ marginTop: 8, fontSize: 12, lineHeight: 1.55, color: 'var(--color-header-text-secondary)' }}>
          AI 자동 판정 결과 중 전문가 검토·확인 필요·루머·분석글 후보를 읽기 전용으로 모아 보여줍니다. 이 화면은 DB를 수정하지 않습니다.
        </p>
      </header>

      <main style={{ flex: 1, overflowY: 'auto', WebkitOverflowScrolling: 'touch', padding: '14px 16px 28px' }}>
        {loading && <p style={{ padding: '40px 0', textAlign: 'center', color: 'var(--color-text-tertiary)', fontSize: 13 }}>검토 대상 불러오는 중...</p>}
        {!loading && error && <p style={{ padding: '40px 0', textAlign: 'center', color: '#DC2626', fontSize: 13 }}>{error}</p>}
        {!loading && !error && reviewItems.length === 0 && (
          <p style={{ padding: '40px 0', textAlign: 'center', color: 'var(--color-text-tertiary)', fontSize: 13 }}>
            현재 노출 가능한 검토 대상이 없습니다.
          </p>
        )}

        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {reviewItems.map(article => {
            const url = sourceUrl(article);
            const explanation = article.factInsight || article.factReason || factStatusDescription(article.factLabel);
            return (
              <article key={article.urlHash} style={{
                background: 'var(--color-surface)',
                border: '1px solid var(--color-border)',
                borderRadius: 'var(--radius-sm)',
                padding: 14,
                boxShadow: 'var(--shadow-card)',
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 7, marginBottom: 9, flexWrap: 'wrap' }}>
                  <FactStatusBadge label={article.factLabel} size="small" />
                  <span style={{ fontSize: 11, color: 'var(--color-text-tertiary)' }}>{article.source}</span>
                  <span style={{ fontSize: 11, color: 'var(--color-text-tertiary)' }}>{article.timeAgo}</span>
                </div>
                <h2 style={{ fontSize: 15, fontWeight: 700, lineHeight: 1.45, color: 'var(--color-text-primary)', letterSpacing: '-0.02em' }}>
                  {articleDisplayTitle(article)}
                </h2>
                <p style={{ marginTop: 8, fontSize: 12, lineHeight: 1.6, color: 'var(--color-text-secondary)' }}>
                  <strong>{factStatusText(article.factLabel)}</strong> · {explanation}
                </p>
                {canOpen(url) && (
                  <button
                    onClick={() => tossOpenURL(url).catch(() => window.location.assign(url))}
                    style={{
                      marginTop: 10,
                      minHeight: 36,
                      padding: '0 12px',
                      borderRadius: 18,
                      background: 'var(--color-surface-secondary)',
                      color: 'var(--color-text-secondary)',
                      fontSize: 12,
                      fontWeight: 600,
                    }}
                  >
                    원문 열기
                  </button>
                )}
              </article>
            );
          })}
        </div>
      </main>
    </div>
  );
}
