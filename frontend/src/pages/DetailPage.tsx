import { useEffect, useState, useRef, type MouseEvent } from 'react';
import { articleDisplayTitle, type Article } from '../data/articles';
import { tossOpenURL } from '../lib/toss';

type SummaryTone = 'formal' | 'casual';

interface Props {
  article: Article;
  bookmarked: boolean;
  onBookmark: (id: string, article?: Article) => void;
  onBack: () => void;
}

const JARGON: Record<string, string> = {
  'RAG': '검색 증강 생성(Retrieval-Augmented Generation). LLM이 외부 문서를 검색해 답변을 생성하는 기법',
  'LLM': '대규모 언어 모델(Large Language Model). GPT, Claude 같은 대형 AI 언어 모델',
  'GPU': '그래픽 처리 장치. AI 학습·추론에 핵심적으로 쓰이는 병렬 연산 칩',
  'API': '소프트웨어 간 통신을 위한 인터페이스(Application Programming Interface)',
  'NPU': '신경망 처리 장치(Neural Processing Unit). AI 연산 전용 칩',
  'SLM': '소형 언어 모델(Small Language Model). 온디바이스에서 동작 가능한 경량 AI 모델',
  'MMLU': 'AI 모델의 다분야 언어 이해 능력을 평가하는 벤치마크',
  'AGI': '범용 인공지능(Artificial General Intelligence). 인간 수준의 일반 지능을 갖춘 AI',
  'RLHF': '인간 피드백 강화학습. AI 출력을 사람이 평가해 모델을 개선하는 방법',
  '파인튜닝': '사전학습된 모델을 특정 목적에 맞게 추가 학습하는 과정(Fine-tuning)',
  '임베딩': '텍스트·이미지 등을 수치 벡터로 변환하는 표현 방식(Embedding)',
  '할루시네이션': 'AI가 사실이 아닌 내용을 그럴듯하게 생성하는 현상(Hallucination)',
  'MoE': '혼합 전문가(Mixture of Experts). 여러 전문 네트워크를 조합해 효율을 높이는 구조',
  'CoT': '연쇄적 사고(Chain of Thought). AI가 단계별로 추론 과정을 서술하는 방식',
  '멀티모달': '텍스트·이미지·음성 등 여러 형태의 데이터를 동시에 처리하는 AI 능력',
};

function HighlightedText({ text, onTap }: { text: string; onTap: (word: string, el: HTMLElement) => void }) {
  if (!text) return null;
  const pattern = new RegExp(`(${Object.keys(JARGON).map(k => k.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('|')})`, 'g');
  const parts = text.split(pattern);
  return (
    <>
      {parts.map((part, i) =>
        JARGON[part] ? (
          <span key={i} onClick={e => { e.stopPropagation(); onTap(part, e.currentTarget as HTMLElement); }} style={{
            color: 'var(--color-primary)', borderBottom: '1px dashed var(--color-primary)',
            cursor: 'pointer', fontWeight: 500,
          }}>{part}</span>
        ) : <span key={i}>{part}</span>
      )}
    </>
  );
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

export default function DetailPage({ article, bookmarked, onBookmark, onBack }: Props) {
  const [copiedFormal, setCopiedFormal] = useState(false);
  const [copiedShare,  setCopiedShare]  = useState(false);
  const [summaryTone, setSummaryTone] = useState<SummaryTone>(() =>
    article.summaryFormal.trim() || !article.summaryCasual.trim() ? 'formal' : 'casual',
  );
  const [translationOpen, setTranslationOpen] = useState(false);
  const [tooltip, setTooltip] = useState<{ word: string; top: number } | null>(null);
  const mainRef = useRef<HTMLDivElement>(null);

  const translation = article.translation.trim();
  const summaryFormal = article.summaryFormal.trim();
  const summaryCasual = article.summaryCasual.trim();
  const hasFormalSummary = Boolean(summaryFormal);
  const hasCasualSummary = Boolean(summaryCasual);
  const hasAnySummary = hasFormalSummary || hasCasualSummary;
  const selectedSummary = summaryTone === 'formal' ? summaryFormal : summaryCasual;
  const selectedToneLabel = summaryTone === 'formal' ? '격식체' : '일상체';
  const selectedSummaryMessage = hasAnySummary ? '선택한 스타일의 요약이 아직 없습니다.' : '요약이 아직 없습니다.';

  useEffect(() => {
    if (hasFormalSummary) {
      setSummaryTone('formal');
    } else if (hasCasualSummary) {
      setSummaryTone('casual');
    } else {
      setSummaryTone('formal');
    }
  }, [article.urlHash, hasFormalSummary, hasCasualSummary]);

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

  const handleJargon = (word: string, el: HTMLElement) => {
    const mainEl = mainRef.current;
    if (!mainEl) return;
    const top = el.getBoundingClientRect().bottom - mainEl.getBoundingClientRect().top + mainEl.scrollTop + 6;
    setTooltip(prev => prev?.word === word ? null : { word, top });
  };
  const sourceUrl = (article.sourceUrl || article.url || '').trim();
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
      <main ref={mainRef} onClick={() => setTooltip(null)} style={{ flex: 1, overflowY: 'auto', WebkitOverflowScrolling: 'touch', position: 'relative' }}>

        {/* 제목 */}
        <div style={{ background: 'var(--color-surface)', padding: '20px 20px 16px', marginBottom: 8 }}>
          <span style={{ display: 'inline-block', fontSize: 11, fontWeight: 500, color: 'var(--color-primary)', background: 'var(--color-primary-light)', padding: '3px 8px', borderRadius: 6, marginBottom: 10 }}>
            {article.category}
          </span>
          <h1 style={{ fontSize: 19, fontWeight: 700, lineHeight: 1.42, letterSpacing: '-0.03em', color: 'var(--color-text-primary)' }}>
            {articleDisplayTitle(article)}
          </h1>
        </div>

        {hasAnySummary && (
          <div style={{ background: 'var(--color-surface)', padding: '14px 20px', marginBottom: 8 }}>
            <p style={{ fontSize: 11, fontWeight: 600, color: 'var(--color-text-tertiary)', letterSpacing: '0.04em', textTransform: 'uppercase', marginBottom: 10 }}>요약 스타일</p>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, background: 'var(--color-surface-secondary)', borderRadius: 10, padding: 4 }}>
              {([
                ['formal', '격식체', hasFormalSummary],
                ['casual', '일상체', hasCasualSummary],
              ] as const).map(([tone, label, enabled]) => {
                const active = summaryTone === tone;
                return (
                  <button
                    key={tone}
                    disabled={!enabled}
                    onClick={() => enabled && setSummaryTone(tone)}
                    style={{
                      height: 36,
                      borderRadius: 8,
                      fontSize: 13,
                      fontWeight: active ? 700 : 500,
                      color: !enabled
                        ? 'var(--color-text-tertiary)'
                        : active
                          ? 'var(--color-primary)'
                          : 'var(--color-text-secondary)',
                      background: active ? 'var(--color-surface)' : 'transparent',
                      boxShadow: active ? '0 1px 4px rgba(0,0,0,0.08)' : 'none',
                      opacity: enabled ? 1 : 0.45,
                      cursor: enabled ? 'pointer' : 'not-allowed',
                      transition: 'all 0.15s',
                    }}
                  >
                    {label}
                  </button>
                );
              })}
            </div>
          </div>
        )}

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
              {selectedSummary || selectedSummaryMessage}
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

          {/* 신조어 툴팁 */}
          {translationOpen && tooltip && (
            <div onClick={e => e.stopPropagation()} style={{
              position: 'absolute', left: 16, right: 16, top: tooltip.top,
              background: 'var(--color-surface)', border: '1px solid var(--color-border)',
              borderRadius: 10, padding: '10px 14px', zIndex: 20,
              boxShadow: '0 4px 16px rgba(0,0,0,0.12)', animation: 'tipIn 0.18s ease',
            }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 4 }}>
                <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--color-primary)' }}>{tooltip.word}</span>
                <button onClick={() => setTooltip(null)} style={{ fontSize: 18, color: 'var(--color-text-tertiary)', lineHeight: 1 }}>×</button>
              </div>
              <p style={{ fontSize: 12, color: 'var(--color-text-secondary)', lineHeight: 1.6 }}>{JARGON[tooltip.word]}</p>
            </div>
          )}

          {translationOpen && (
            translation ? (
              <>
                <div style={{ background: 'var(--color-surface-secondary)', borderRadius: 10, padding: '12px 14px', marginBottom: 10 }}>
                  <p style={{ fontSize: 14, lineHeight: 1.78, color: 'var(--color-text-primary)', letterSpacing: '-0.01em', whiteSpace: 'pre-line' }}>
                    <HighlightedText text={translation} onTap={handleJargon} />
                  </p>
                </div>

                <p style={{ fontSize: 11, color: 'var(--color-text-tertiary)' }}>
                  파란색 단어를 탭하면 설명을 볼 수 있어요
                </p>
              </>
            ) : (
              <div style={{ background: 'var(--color-surface-secondary)', borderRadius: 10, padding: '14px', marginBottom: 10 }}>
                <p style={{ fontSize: 13, lineHeight: 1.7, color: 'var(--color-text-tertiary)' }}>
                  번역 전문은 아직 준비 중입니다.
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
