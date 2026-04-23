import { useState, useRef } from 'react';
import type { Article } from '../data/articles';
import { translateArticle, summarizeArticle } from '../data/api';

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

export default function DetailPage({ article, bookmarked, onBookmark, onBack }: Props) {
  const [copiedFormal, setCopiedFormal] = useState(false);
  const [copiedCasual, setCopiedCasual] = useState(false);
  const [copiedShare,  setCopiedShare]  = useState(false);
  const [tooltip, setTooltip] = useState<{ word: string; top: number } | null>(null);
  const mainRef = useRef<HTMLDivElement>(null);

  // 번역·요약 API 호출 상태
  const [translation,   setTranslation]   = useState(article.translation);
  const [summaryFormal, setSummaryFormal] = useState(article.summaryFormal);
  const [summaryCasual, setSummaryCasual] = useState(article.summaryCasual);
  const [loadingTranslate,  setLoadingTranslate]  = useState(false);
  const [loadingSummarize,  setLoadingSummarize]  = useState(false);
  const [translateError,    setTranslateError]    = useState<string | null>(null);
  const [summarizeError,    setSummarizeError]    = useState<string | null>(null);

  const handleTranslate = async () => {
    setLoadingTranslate(true);
    setTranslateError(null);
    try {
      const res = await translateArticle(article.content);
      setTranslation(res.translation || translation);
    } catch {
      setTranslateError('번역 중 오류가 발생했어요. 잠시 후 다시 시도해주세요.');
    } finally {
      setLoadingTranslate(false);
    }
  };

  const handleSummarize = async () => {
    setLoadingSummarize(true);
    setSummarizeError(null);
    try {
      const res = await summarizeArticle(article.content);
      setSummaryFormal(res.summary_formal || summaryFormal);
      setSummaryCasual(res.summary_casual || summaryCasual);
    } catch {
      setSummarizeError('요약 중 오류가 발생했어요. 잠시 후 다시 시도해주세요.');
    } finally {
      setLoadingSummarize(false);
    }
  };

  const handleShare = () => {
    navigator.clipboard.writeText(`[${article.source}] ${article.title}\n\n格식체 요약: ${summaryFormal}\n\n일상체 요약: ${summaryCasual}`).catch(() => {});
    setCopiedShare(true); setTimeout(() => setCopiedShare(false), 2000);
  };
  const handleCopyFormal = () => {
    navigator.clipboard.writeText(summaryFormal).catch(() => {});
    setCopiedFormal(true); setTimeout(() => setCopiedFormal(false), 2000);
  };
  const handleCopyCasual = () => {
    navigator.clipboard.writeText(summaryCasual).catch(() => {});
    setCopiedCasual(true); setTimeout(() => setCopiedCasual(false), 2000);
  };

  const handleJargon = (word: string, el: HTMLElement) => {
    const mainEl = mainRef.current;
    if (!mainEl) return;
    const top = el.getBoundingClientRect().bottom - mainEl.getBoundingClientRect().top + mainEl.scrollTop + 6;
    setTooltip(prev => prev?.word === word ? null : { word, top });
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', background: 'var(--color-bg)', animation: 'slideUp 0.28s cubic-bezier(0.22,1,0.36,1)' }}>
      <style>{`
        @keyframes slideUp { from{transform:translateY(100%);opacity:0} to{transform:translateY(0);opacity:1} }
        @keyframes tipIn   { from{opacity:0;transform:translateY(-4px)} to{opacity:1;transform:translateY(0)} }
        @keyframes spin    { from{transform:rotate(0deg)} to{transform:rotate(360deg)} }
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
            {article.title}
          </h1>
        </div>

        {/* 번역 전문 — 신조어 하이라이트 포함 */}
        <div style={{ background: 'var(--color-surface)', padding: '16px 20px', marginBottom: 8, position: 'relative' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
            <p style={{ fontSize: 11, fontWeight: 600, color: 'var(--color-text-tertiary)', letterSpacing: '0.04em', textTransform: 'uppercase' }}>번역 전문</p>
            <button
              onClick={handleTranslate}
              disabled={loadingTranslate}
              style={{
                display: 'flex', alignItems: 'center', gap: 4,
                fontSize: 11, fontWeight: 500,
                color: loadingTranslate ? 'var(--color-text-tertiary)' : 'var(--color-primary)',
                background: 'var(--color-primary-light)',
                padding: '4px 10px', borderRadius: 6,
                border: '0.5px solid var(--color-border)',
                opacity: loadingTranslate ? 0.6 : 1,
                transition: 'all 0.18s',
              }}
            >
              {loadingTranslate
                ? <><span style={{ display: 'inline-block', animation: 'spin 1s linear infinite' }}>⟳</span> 번역 중…</>
                : <>🔄 재번역</>
              }
            </button>
          </div>

          {translateError && (
            <p style={{ fontSize: 12, color: '#DC2626', marginBottom: 10, padding: '8px 12px', background: '#FEF2F2', borderRadius: 8 }}>
              {translateError}
            </p>
          )}

          {/* 신조어 툴팁 */}
          {tooltip && (
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

          <div style={{ background: 'var(--color-surface-secondary)', borderRadius: 10, padding: '12px 14px', marginBottom: 10 }}>
            <p style={{ fontSize: 14, lineHeight: 1.78, color: 'var(--color-text-primary)', letterSpacing: '-0.01em' }}>
              <HighlightedText text={translation} onTap={handleJargon} />
            </p>
          </div>

          <p style={{ fontSize: 11, color: 'var(--color-text-tertiary)' }}>
            💡 파란색 단어를 탭하면 설명을 볼 수 있어요
          </p>
        </div>

        {/* 3줄 요약 — 격식체 · 일상체 */}
        <div style={{ background: 'var(--color-surface)', padding: '16px 20px', marginBottom: 8 }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
            <p style={{ fontSize: 11, fontWeight: 600, color: 'var(--color-text-tertiary)', letterSpacing: '0.04em', textTransform: 'uppercase' }}>3줄 요약</p>
            <button
              onClick={handleSummarize}
              disabled={loadingSummarize}
              style={{
                display: 'flex', alignItems: 'center', gap: 4,
                fontSize: 11, fontWeight: 500,
                color: loadingSummarize ? 'var(--color-text-tertiary)' : 'var(--color-primary)',
                background: 'var(--color-primary-light)',
                padding: '4px 10px', borderRadius: 6,
                border: '0.5px solid var(--color-border)',
                opacity: loadingSummarize ? 0.6 : 1,
                transition: 'all 0.18s',
              }}
            >
              {loadingSummarize
                ? <><span style={{ display: 'inline-block', animation: 'spin 1s linear infinite' }}>⟳</span> 요약 중…</>
                : <>✨ 재요약</>
              }
            </button>
          </div>

          {summarizeError && (
            <p style={{ fontSize: 12, color: '#DC2626', marginBottom: 10, padding: '8px 12px', background: '#FEF2F2', borderRadius: 8 }}>
              {summarizeError}
            </p>
          )}

          {/* 격식체 요약 */}
          <div style={{ background: 'var(--color-surface-secondary)', borderRadius: 10, padding: '12px 14px', marginBottom: 10 }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
              <span style={{ fontSize: 11, fontWeight: 600, color: 'var(--color-text-tertiary)', letterSpacing: '0.04em' }}>격식체</span>
              <CopyBtn copied={copiedFormal} onClick={handleCopyFormal} />
            </div>
            <p style={{ fontSize: 14, lineHeight: 1.78, color: 'var(--color-text-primary)', letterSpacing: '-0.01em' }}>
              {summaryFormal}
            </p>
          </div>

          {/* 일상체 요약 */}
          <div style={{ background: 'var(--color-surface-secondary)', borderRadius: 10, padding: '12px 14px', marginBottom: 10 }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
              <span style={{ fontSize: 11, fontWeight: 600, color: 'var(--color-text-tertiary)', letterSpacing: '0.04em' }}>일상체</span>
              <CopyBtn copied={copiedCasual} onClick={handleCopyCasual} />
            </div>
            <p style={{ fontSize: 14, lineHeight: 1.78, color: 'var(--color-text-primary)', letterSpacing: '-0.01em' }}>
              {summaryCasual}
            </p>
          </div>
        </div>

        {/* 원문 링크 */}
        <div style={{ padding: '0 20px 40px' }}>
          <button
            onClick={() => window.open(article.url, '_blank', 'noopener,noreferrer')}
            style={{ width: '100%', padding: '14px', background: 'var(--color-surface)', border: '0.5px solid var(--color-border-medium)', borderRadius: 'var(--radius-md)', fontSize: 14, fontWeight: 500, color: 'var(--color-text-secondary)', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8 }}
          >
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none">
              <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round"/>
              <path d="M15 3h6v6M10 14L21 3" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
            원문 보기 — {article.source}
          </button>
        </div>
      </main>
    </div>
  );
}