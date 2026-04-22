import { useState } from 'react';
import { postOnboarding } from '../data/api';

export type Interest = '신규 출시/제품' | '기술 이슈' | '블록체인/양자' | '대기업';

const INTERESTS: { id: Interest; emoji: string; desc: string }[] = [
  { id: '신규 출시/제품', emoji: '🚀', desc: '스냅드래곤, 엑시노스 등 신제품 출시 소식' },
  { id: '기술 이슈',     emoji: '⚡', desc: 'AI·반도체·소프트웨어 핵심 기술 동향' },
  { id: '블록체인/양자', emoji: '🔬', desc: '블록체인, 양자컴퓨팅 관련 뉴스' },
  { id: '대기업',        emoji: '🏢', desc: '구글·MS·애플·Meta·삼성 등 빅테크 동향' },
];

function getOrCreateUserId(): string {
  const key = 'samsun_user_id';
  const existing = localStorage.getItem(key);
  if (existing) return existing;
  const id = `user_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
  localStorage.setItem(key, id);
  return id;
}

interface Props { onDone: (selected: Interest[], userId: string) => void; }

export default function OnboardingPage({ onDone }: Props) {
  const [step, setStep]             = useState<1 | 2>(1);
  const [selected, setSelected]     = useState<Interest[]>([]);
  const [submitting, setSubmitting] = useState(false);

  const toggle = (id: Interest) =>
    setSelected(p => p.includes(id) ? p.filter(i => i !== id) : [...p, id]);

  const handleDone = async () => {
    setSubmitting(true);
    const userId = getOrCreateUserId();
    try {
      await postOnboarding(userId, selected);
    } catch {
      console.warn('[Onboarding] /onboarding API 실패 — 로컬 모드로 진행');
    } finally {
      setSubmitting(false);
      onDone(selected, userId);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', padding: '0 24px', background: 'var(--color-bg)', overflowY: 'auto' }}>
      <style>{`
        @keyframes stepIn { from{opacity:0;transform:translateX(20px)} to{opacity:1;transform:translateX(0)} }
        @keyframes logoIn { from{opacity:0;transform:scale(0.82)} to{opacity:1;transform:scale(1)} }
      `}</style>

      {/* 로고 */}
      <div style={{ paddingTop: 64, paddingBottom: 32, textAlign: 'center' }}>
        <div style={{
          width: 68, height: 68, borderRadius: 20,
          background: 'linear-gradient(135deg,#4F46E5 0%,#7C3AED 100%)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          margin: '0 auto 16px',
          boxShadow: '0 8px 28px rgba(79,70,229,0.32)',
          animation: 'logoIn 0.4s cubic-bezier(0.22,1,0.36,1)',
        }}>
          <span style={{ fontSize: 26, color: '#fff', fontWeight: 700 }}>삼선</span>
        </div>
        <h1 style={{ fontSize: 22, fontWeight: 700, letterSpacing: '-0.04em', marginBottom: 6 }}>
          삼선뉴스에 오신 걸 환영해요
        </h1>
        <p style={{ fontSize: 13, color: 'var(--color-text-secondary)', lineHeight: 1.6 }}>
          AI 뉴스를 추천·요약·번역해드려요
        </p>
      </div>

      {/* 스텝 인디케이터 */}
      <div style={{ display: 'flex', justifyContent: 'center', gap: 6, marginBottom: 32 }}>
        {[1, 2].map(s => (
          <div key={s} style={{
            height: 4, borderRadius: 2,
            width: step === s ? 24 : 8,
            background: step === s ? 'var(--color-primary)' : 'var(--color-border-medium)',
            transition: 'all 0.3s',
          }} />
        ))}
      </div>

      {/* Step 1 */}
      {step === 1 && (
        <div style={{ animation: 'stepIn 0.3s ease', flex: 1 }}>
          <h2 style={{ fontSize: 17, fontWeight: 700, letterSpacing: '-0.03em', marginBottom: 4 }}>어떤 분야가 궁금하세요?</h2>
          <p style={{ fontSize: 12, color: 'var(--color-text-secondary)', marginBottom: 18 }}>
            관심 주제에 맞는 뉴스를 골라서 추천해드려요
          </p>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 9 }}>
            {INTERESTS.map(item => {
              const on = selected.includes(item.id);
              return (
                <button key={item.id} onClick={() => toggle(item.id)} style={{
                  display: 'flex', alignItems: 'center', gap: 14,
                  padding: '13px 16px', borderRadius: 'var(--radius-lg)', textAlign: 'left',
                  background: on ? 'var(--color-primary-light)' : 'var(--color-surface)',
                  border: `1.5px solid ${on ? 'var(--color-primary)' : 'var(--color-border)'}`,
                  boxShadow: on ? '0 0 0 3px rgba(79,70,229,0.08)' : 'var(--shadow-card)',
                  transition: 'all 0.15s',
                }}>
                  <span style={{ fontSize: 20 }}>{item.emoji}</span>
                  <div style={{ flex: 1 }}>
                    <p style={{ fontSize: 14, fontWeight: 600, color: on ? 'var(--color-primary)' : 'var(--color-text-primary)' }}>{item.id}</p>
                    <p style={{ fontSize: 11, color: 'var(--color-text-tertiary)', marginTop: 1 }}>{item.desc}</p>
                  </div>
                  <div style={{
                    width: 20, height: 20, borderRadius: '50%', flexShrink: 0,
                    background: on ? 'var(--color-primary)' : 'transparent',
                    border: `1.5px solid ${on ? 'var(--color-primary)' : 'var(--color-border-medium)'}`,
                    display: 'flex', alignItems: 'center', justifyContent: 'center', transition: 'all 0.15s',
                  }}>
                    {on && <svg width="10" height="10" viewBox="0 0 24 24" fill="none"><path d="M20 6L9 17L4 12" stroke="white" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"/></svg>}
                  </div>
                </button>
              );
            })}
          </div>
        </div>
      )}

      {/* Step 2 */}
      {step === 2 && (
        <div style={{ animation: 'stepIn 0.3s ease', flex: 1, textAlign: 'center' }}>
          <div style={{ fontSize: 52, marginBottom: 14 }}>🎉</div>
          <h2 style={{ fontSize: 20, fontWeight: 700, letterSpacing: '-0.03em', marginBottom: 8 }}>준비 완료!</h2>
          <p style={{ fontSize: 13, color: 'var(--color-text-secondary)', lineHeight: 1.7, marginBottom: 28 }}>
            {selected.length > 0 ? `${selected.join(' · ')} 분야 뉴스를 추천해드릴게요` : '모든 분야의 AI 뉴스를 보여드릴게요'}
          </p>
          <div style={{
            background: 'var(--color-surface)', borderRadius: 'var(--radius-lg)',
            padding: '16px', boxShadow: 'var(--shadow-card)', textAlign: 'left',
            display: 'flex', flexDirection: 'column', gap: 13,
          }}>
            {[
              { icon: '📝', text: '3줄 자동 요약' },
              { icon: '🌐', text: '격식체 / 일상체 번역 동시 비교' },
              { icon: '💡', text: '신조어·전문용어 즉시 설명' },
              { icon: '📋', text: '번역 즉시 복사 · 공유' },
            ].map(f => (
              <div key={f.text} style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <span style={{ fontSize: 18 }}>{f.icon}</span>
                <span style={{ fontSize: 13, color: 'var(--color-text-secondary)' }}>{f.text}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 버튼 */}
      <div style={{ padding: '20px 0 44px' }}>
        <button
          onClick={() => step === 1 ? setStep(2) : handleDone()}
          disabled={(step === 1 && selected.length === 0) || submitting}
          style={{
            width: '100%', padding: '15px', borderRadius: 'var(--radius-md)',
            fontSize: 15, fontWeight: 600, color: '#fff',
            background: (step === 1 && selected.length === 0) || submitting
              ? 'var(--color-text-tertiary)'
              : 'linear-gradient(135deg,#4F46E5 0%,#7C3AED 100%)',
            transition: 'opacity 0.15s',
          }}
        >
          {step === 1 ? `선택 완료 (${selected.length}개)` : submitting ? '저장 중...' : '시작하기'}
        </button>
        {step === 1 && (
          <button
            onClick={() => { setSelected([]); setStep(2); }}
            style={{ width: '100%', marginTop: 10, padding: '10px', fontSize: 13, color: 'var(--color-text-tertiary)' }}
          >
            나중에 설정할게요
          </button>
        )}
      </div>
    </div>
  );
}
