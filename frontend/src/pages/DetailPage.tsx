import { useEffect, useMemo, useState, type MouseEvent } from 'react';
import { articleDisplayTitle, articleSummaryForTone, type Article } from '../data/articles';
import {
  fetchArticleExtras,
  fetchArticleNeologisms,
  fetchNeologismDictionary,
  fetchNeologismsByTerms,
  type NeologismEntry,
} from '../data/api';
import { tossOpenURL } from '../lib/toss';
import NeologismText from '../components/NeologismText';
import TonePreferenceControl from '../components/TonePreferenceControl';
import { toneLabel, type SummaryTone } from '../hooks/useTonePreference';

interface Props {
  article: Article;
  bookmarked: boolean;
  onBookmark: (id: string, article?: Article) => void;
  onBack: () => void;
  tone: SummaryTone;
  onToneChange: (tone: SummaryTone) => void;
}

function CopyBtn({ copied, onClick }: { copied: boolean; onClick: () => void }) {
  return (
    <button onClick={onClick} style={{
      display: 'flex', alignItems: 'center', gap: 4, fontSize: 11, fontWeight: 500,
      color: copied ? '#16A34A' : 'var(--color-text-tertiary)',
      background: copied ? '#DCFCE7' : 'var(--color-surface)',
      padding: '4px 10px', borderRadius: 6, transition: 'all 0.18s', flexShrink: 0,
      border: '0.5px solid var(--color-border)',
    }}>
      {copied
        ? <><svg width="11" height="11" viewBox="0 0 24 24" fill="none"><path d="M20 6L9 17L4 12" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"/></svg>복사됨</>
        : <><svg width="11" height="11" viewBox="0 0 24 24" fill="none"><rect x="9" y="9" width="13" height="13" rx="2" stroke="currentColor" strokeWidth="1.6"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" stroke="currentColor" strokeWidth="1.6"/></svg>복사</>
      }
    </button>
  );
}

function isExternalHttpUrl(url: string): boolean {
  try {
    const parsed = new URL(url);
    return parsed.protocol === 'http:' || parsed.protocol === 'https:';
  } catch {
    return false;
  }
}

function mergeEntries(...groups: NeologismEntry[][]): NeologismEntry[] {
  const byTerm = new Map<string, NeologismEntry>();
  groups.flat().forEach(entry => {
    const key = entry.term.trim().toLocaleLowerCase();
    if (!key || !entry.explanation?.trim()) return;
    if (!byTerm.has(key)) byTerm.set(key, entry);
  });
  return [...byTerm.values()];
}

export default function DetailPage({ article, bookmarked, onBookmark, onBack, tone, onToneChange }: Props) {
  const [copiedFormal, setCopiedFormal] = useState(false);
  const [copiedShare,  setCopiedShare]  = useState(false);
  const [translationOpen, setTranslationOpen] = useState(false);
  const [neologisms, setNeologisms] = useState<NeologismEntry[]>([]);
  const [sourceOverride, setSourceOverride] = useState('');

  const translation = article.translation.trim();
  const selectedSummary = articleSummaryForTone(article, tone);
  const selectedToneLabel = toneLabel(tone);
  const visibleNeologisms = useMemo(() => {
    const haystack = `${selectedSummary}\n${translation}`.toLocaleLowerCase();
    return neologisms.filter(entry => haystack.includes(entry.term.toLocaleLowerCase()));
  }, [neologisms, selectedSummary, translation]);

  useEffect(() => {
    let cancelled = false;
    Promise.all([
      fetchNeologismDictionary(),
      fetchArticleNeologisms(article.urlHash),
      fetchArticleExtras(article.urlHash),
    ])
      .then(async ([dictionary, articleEntries, extras]) => {
        if (cancelled) return;
        const articleTerms = [
          ...(extras.neologism_terms ?? []),
          ...(extras.slang_terms ?? []),
          ...article.slangTerms,
        ];
        const termEntries = await fetchNeologismsByTerms(articleTerms);
        if (cancelled) return;
        setNeologisms(mergeEntries(termEntries, articleEntries, dictionary));
        setSourceOverride((extras.source_url ?? '').trim());
      })
      .catch((err: unknown) => {
        if (import.meta.env.DEV) {
          console.warn('[DetailPage] optional neologism/source lookup failed', err);
        }
        if (!cancelled) {
          setNeologisms([]);
          setSourceOverride('');
        }
      });
    return () => { cancelled = true; };
  }, [article.urlHash, article.slangTerms]);

  const handleShare = () => {
    const lines = [`[${article.source}] ${articleDisplayTitle(article)}`];
    if (selectedSummary) lines.push(`\n${selectedToneLabel} 요약: ${selectedSummary}`);
    navigator.clipboard.writeText(lines.join('\n')).catch(() => {});
    setCopiedShare(true); setTimeout(() => setCopiedShare(false), 2000);
  };
  const handleCopySummary = () => {
    navigator.clipboard.writeText(selectedSummary).catch(() => {});
    setCopiedFormal(true); setTimeout(() => setCopiedFormal(false), 2000);
  };

  const sourceUrl = (sourceOverride || article.sourceUrl || article.url || '').trim();
  const canOpenSource = isExternalHttpUrl(sourceUrl);

  useEffect(() => {
    if (import.meta.env.DEV && !canOpenSource) {
      console.warn('[DetailPage] missing or invalid sourceUrl', {
        urlHash: article.urlHash,
        sourceUrl: article.sourceUrl,
        url: article.url,
      });
    }
  }, [article.sourceUrl, article.url, article.urlHash, canOpenSource]);

  const handleSourceClick = (event: MouseEvent<HTMLAnchorElement>) => {
    if (!canOpenSource) return;
    if (import.meta.env.DEV) {
      event.preventDefault();
      window.location.assign(sourceUrl);
      return;
    }
    event.preventDefault();
    tossOpenURL(sourceUrl).catch(() => {
      window.location.assign(sourceUrl);
    });
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', background: 'var(--color-bg)', animation: 'slideUp 0.28s cubic-bezier(0.22,1,0.36,1)' }}>
      <style>{`
        @keyframes slideUp { from{transform:translateY(100%);opacity:0} to{transform:translateY(0);opacity:1} }
        @keyframes tipIn   { from{opacity:0;transform:translateY(-4px)} to{opacity:1;transform:translateY(0)} }
      `}</style>

      {/* 헤더 */}
      <header style={{ background: 'var(--color-surface)', borderBottom: '0.5px solid var(--color-border)', padding: '14px 16px', display: 'flex', alignItems: 'center', gap: 10, flexShrink: 0 }}>
        <button onClick={onBack} style={{ width: 36, height: 36, borderRadius: '50%', background: 'var(--color-surface-secondary)', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
            <path d="M19 12H5M5 12L12 19M5 12L12 5" stroke="var(--color-text-secondary)" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
        </button>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
            <div style={{ width: 5, height: 5, borderRadius: '50%', background: article.sourceColor, flexShrink: 0 }} />
            <span style={{ fontSize: 12, color: 'var(--color-text-secondary)', fontWeight: 500 }}>{article.source}</span>
            <span style={{ fontSize: 11, color: 'var(--color-text-tertiary)' }}>{article.timeAgo}</span>
          </div>
        </div>
        <button onClick={() => onBookmark(article.urlHash, article)} style={{ width: 36, height: 36, borderRadius: '50%', background: bookmarked ? '#FEF3C7' : 'var(--color-surface-secondary)', display: 'flex', alignItems: 'center', justifyContent: 'center', transition: 'all 0.15s' }}>
          <svg width="16" height="16" viewBox="0 0 24 24" fill={bookmarked ? '#D97706' : 'none'}>
            <path d="M19 21L12 16L5 21V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2v16z" stroke={bookmarked ? '#D97706' : 'var(--color-text-secondary)'} strokeWidth="1.7" strokeLinejoin="round"/>
          </svg>
        </button>
        <button onClick={handleShare} style={{ display: 'flex', alignItems: 'center', gap: 5, fontSize: 12, fontWeight: 500, color: copiedShare ? '#16A34A' : 'var(--color-primary)', background: copiedShare ? '#DCFCE7' : 'var(--color-primary-light)', padding: '7px 12px', borderRadius: 20, transition: 'all 0.2s' }}>
          {copiedShare ? '복사됨' : '공유'}
        </button>
      </header>

      {/* 본문 */}
      <main style={{ flex: 1, overflowY: 'auto', WebkitOverflowScrolling: 'touch', position: 'relative' }}>

        {/* 제목 */}
        <div style={{ background: 'var(--color-surface)', padding: '20px 20px 16px', marginBottom: 8 }}>
          <span style={{ display: 'inline-block', fontSize: 11, fontWeight: 500, color: 'var(--color-primary)', background: 'var(--color-primary-light)', padding: '3px 8px', borderRadius: 6, marginBottom: 10 }}>
            {article.category}
          </span>
          <h1 style={{ fontSize: 19, fontWeight: 700, lineHeight: 1.42, letterSpacing: '-0.03em', color: 'var(--color-text-primary)' }}>
            {articleDisplayTitle(article)}
          </h1>
        </div>

        <div style={{ background: 'var(--color-surface)', padding: '14px 20px', marginBottom: 8 }}>
          <p style={{ fontSize: 11, fontWeight: 600, color: 'var(--color-text-tertiary)', letterSpacing: '0.04em', textTransform: 'uppercase', marginBottom: 10 }}>요약 말투</p>
          <TonePreferenceControl tone={tone} onChange={onToneChange} />
        </div>

        {/* 3줄 요약 */}
        <div style={{ background: 'var(--color-surface)', padding: '16px 20px', marginBottom: 8 }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
            <p style={{ fontSize: 11, fontWeight: 600, color: 'var(--color-text-tertiary)', letterSpacing: '0.04em', textTransform: 'uppercase' }}>3줄 요약</p>
            {selectedSummary && <CopyBtn copied={copiedFormal} onClick={handleCopySummary} />}
          </div>

          <div style={{ background: 'var(--color-surface-secondary)', borderRadius: 10, padding: '14px 14px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 8 }}>
              <span style={{ fontSize: 11, fontWeight: 700, color: 'var(--color-primary)', background: 'var(--color-primary-light)', padding: '3px 8px', borderRadius: 6 }}>{selectedToneLabel}</span>
            </div>
            <p style={{ fontSize: 15, lineHeight: 1.78, color: selectedSummary ? 'var(--color-text-primary)' : 'var(--color-text-tertiary)', letterSpacing: '-0.01em', fontWeight: selectedSummary ? 500 : 400 }}>
              {selectedSummary ? <NeologismText text={selectedSummary} entries={visibleNeologisms} /> : '요약이 아직 없습니다.'}
            </p>
          </div>
        </div>

        {/* 번역 전문 — 신조어 하이라이트 포함 */}
        <div style={{ background: 'var(--color-surface)', padding: '16px 20px', marginBottom: 8, position: 'relative' }}>
          <button
            onClick={() => setTranslationOpen(v => !v)}
            style={{
              width: '100%',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              marginBottom: translationOpen ? 12 : 0,
              textAlign: 'left',
            }}
          >
            <p style={{ fontSize: 11, fontWeight: 600, color: 'var(--color-text-tertiary)', letterSpacing: '0.04em', textTransform: 'uppercase' }}>번역 전문</p>
            <span style={{ fontSize: 12, color: 'var(--color-text-tertiary)' }}>{translationOpen ? '접기' : '펼치기'}</span>
          </button>

          {translationOpen && (
            translation ? (
              <>
                <div style={{ background: 'var(--color-surface-secondary)', borderRadius: 10, padding: '12px 14px', marginBottom: 10 }}>
                  <p style={{ fontSize: 14, lineHeight: 1.78, color: 'var(--color-text-primary)', letterSpacing: '-0.01em', whiteSpace: 'pre-line' }}>
                    <NeologismText text={translation} entries={visibleNeologisms} />
                  </p>
                </div>

                {visibleNeologisms.length > 0 && (
                  <p style={{ fontSize: 11, color: 'var(--color-text-tertiary)' }}>
                    파란색 단어를 탭하거나 마우스를 올리면 설명을 볼 수 있어요
                  </p>
                )}
              </>
            ) : (
              <div style={{ background: 'var(--color-surface-secondary)', borderRadius: 10, padding: '14px', marginBottom: 10 }}>
                <p style={{ fontSize: 13, lineHeight: 1.7, color: 'var(--color-text-tertiary)' }}>
                  번역 전문이 아직 없습니다.
                </p>
              </div>
            )
          )}
        </div>

        {/* 원문 링크 */}
        <div style={{ padding: '0 20px 40px' }}>
          {canOpenSource ? (
            <a
              href={sourceUrl}
              target="_blank"
              rel="noopener noreferrer"
              onClick={handleSourceClick}
              style={{ width: '100%', padding: '12px', background: 'transparent', border: '0.5px solid var(--color-border)', borderRadius: 'var(--radius-md)', fontSize: 13, fontWeight: 500, color: 'var(--color-text-tertiary)', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8, textDecoration: 'none' }}
            >
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none">
                <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round"/>
                <path d="M15 3h6v6M10 14L21 3" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
              원문 보기 — {article.source}
            </a>
          ) : (
            <div
              aria-disabled="true"
              style={{ width: '100%', padding: '14px', background: 'var(--color-surface-secondary)', border: '0.5px dashed var(--color-border)', borderRadius: 'var(--radius-md)', fontSize: 14, fontWeight: 500, color: 'var(--color-text-tertiary)', textAlign: 'center', cursor: 'not-allowed' }}
            >
              원문 링크가 아직 준비되지 않았습니다.
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
