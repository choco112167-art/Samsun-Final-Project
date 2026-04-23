import { useState } from 'react';
import { postOnboarding } from '../data/api';
import logoImg from '../assets/samsun_blue.png';

export type Interest = 'AI 연구' | 'AI 심층' | 'AI 스타트업' | 'AI 비즈니스' | 'AI 윤리' | 'AI 커뮤니티' | '테크 전반';

const INTERESTS: { id: Interest; emoji: string; desc: string }[] = [
  { id: 'AI 연구',    emoji: '🔬', desc: 'MIT TR · The Decoder — AI 최신 연구 동향' },
  { id: 'AI 심층',    emoji: '📖', desc: 'MIT TR · The Decoder — AI 심층 분석·리포트' },
  { id: 'AI 스타트업', emoji: '🚀', desc: 'TechCrunch · VentureBeat — AI 스타트업·투자 동향' },
  { id: 'AI 비즈니스', emoji: '💼', desc: 'VentureBeat — AI 비즈니스·산업 적용 소식' },
  { id: 'AI 윤리',    emoji: '⚖️', desc: 'The Guardian — AI 윤리·규제·사회적 영향' },
  { id: 'AI 커뮤니티', emoji: '💬', desc: 'Reddit — AI 커뮤니티 토론·트렌드' },
  { id: '테크 전반',  emoji: '💻', desc: 'The Verge — AI를 포함한 테크 업계 전반 소식' },
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
  const [step, setStep]         = useState<1 | 2>(1);
  const [selected, setSelected] = useState<Interest[]>([]);
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
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', background: 'var(--color-header-bg)', overflow: 'hidden' }}>
      <style>{`
        @keyframes stepIn  { from{opacity:0;transform:translateY(16px)} to{opacity:1;transform:translateY(0)} }
        @keyframes logoIn  { from{opacity:0;transform:scale(0.82)} to{opacity:1;transform:scale(1)} }
        @keyframes fadeIn  { from{opacity:0} to{opacity:1} }
      `}</style>

      {/* ── 다크 헤더 영역 */}
      <div style={{ padding: '52px 28px 28px', flexShrink: 0, animation: 'logoIn 0.4s cubic-bezier(0.22,1,0.36,1)' }}>
        {/* 로고 아이콘 */}
        <img
          src={logoImg}
          alt="삼선뉴스 로고"
          style={{
            width: 60, height: 60, borderRadius: 18,
            objectFit: 'cover',
            marginBottom: 20,
            animation: 'logoIn 0.4s cubic-bezier(0.22,1,0.36,1)',
          }}
        />

        <h1 style={{ fontSize: 26, fontWeight: 800, letterSpacing: '-0.04em', color: 'var(--color-header-text)', marginBottom: 6, lineHeight: 1.25 }}>
          {step === 1 ? '삼선뉴스에 온 걸 환영해요' : '준비가 다 됐어요!'}
        </h1>
        <p style={{ fontSize: 13, color: 'var(--color-header-text-secondary)', lineHeight: 1.6 }}>
          {step === 1
            ? 'AI 뉴스를 추천·요약·번역해드려요'
            : selected.length > 0
              ? `${selected.join(' · ')} 분야 뉴스를 추천해드릴게요`
              : '모든 분야의 AI 뉴스를 보여드릴게요'}
        </p>

        {/* 스텝 인디케이터 */}
        <div style={{ display: 'flex', gap: 5, marginTop: 20 }}>
          {[1, 2].map(s => (
            <div key={s} style={{
              height: 3, borderRadius: 2,
              width: step === s ? 22 : 7,
              background: step === s ? '#3081fb' : 'rgba(0,0,0,0.1)',
              transition: 'all 0.3s',
            }} />
          ))}
        </div>
      </div>

      {/* ── 라이트 컨텐츠 영역 */}
      <div style={{
        flex: 1, background: 'var(--color-bg)',
        borderRadius: '32px 32px 0 0',
        padding: '28px 24px 0',
        overflowY: 'auto',
        display: 'flex', flexDirection: 'column',
      }}>

        {/* Step 1 — 관심 주제 선택 */}
        {step === 1 && (
          <div style={{ flex: 1, animation: 'stepIn 0.3s ease' }}>
            <p style={{ fontSize: 14, fontWeight: 700, color: 'var(--color-text-primary)', marginBottom: 4 }}>
              어떤 분야가 궁금해요?
            </p>
            <p style={{ fontSize: 12, color: 'var(--color-text-tertiary)', marginBottom: 18 }}>
              관심 주제에 맞는 뉴스를 골라서 추천해드려요
            </p>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 9 }}>
              {INTERESTS.map(item => {
                const on = selected.includes(item.id);
                return (
                  <button key={item.id} onClick={() => toggle(item.id)} style={{
                    display: 'flex', alignItems: 'center', gap: 14,
                    padding: '14px 16px', borderRadius: 'var(--radius-sm)', textAlign: 'left',
                    background: on ? 'var(--color-primary-light)' : 'var(--color-surface)',
                    border: `1.5px solid ${on ? 'var(--color-primary)' : 'var(--color-border)'}`,
                    boxShadow: on ? `0 0 0 3px rgba(48,129,251,0.1)` : 'var(--shadow-card)',
                    transition: 'all 0.15s',
                  }}>
                    <span style={{ fontSize: 22 }}>{item.emoji}</span>
                    <div style={{ flex: 1 }}>
                      <p style={{ fontSize: 14, fontWeight: 600, color: on ? 'var(--color-primary)' : 'var(--color-text-primary)' }}>
                        {item.id}
                      </p>
                      <p style={{ fontSize: 11, color: 'var(--color-text-tertiary)', marginTop: 2 }}>{item.desc}</p>
                    </div>
                    <div style={{
                      width: 20, height: 20, borderRadius: '50%', flexShrink: 0,
                      background: on ? 'var(--color-primary)' : 'transparent',
                      border: `1.5px solid ${on ? 'var(--color-primary)' : 'var(--color-border-medium)'}`,
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                      transition: 'all 0.15s',
                    }}>
                      {on && (
                        <svg width="10" height="10" viewBox="0 0 24 24" fill="none">
                          <path d="M20 6L9 17L4 12" stroke="white" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"/>
                        </svg>
                      )}
                    </div>
                  </button>
                );
              })}
            </div>
          </div>
        )}

        {/* Step 2 — 기능 소개 */}
        {step === 2 && (
          <div style={{ flex: 1, animation: 'stepIn 0.3s ease' }}>
            <p style={{ fontSize: 14, fontWeight: 700, color: 'var(--color-text-primary)', marginBottom: 4 }}>
              삼선뉴스로 이런 걸 할 수 있어요
            </p>
            <p style={{ fontSize: 12, color: 'var(--color-text-tertiary)', marginBottom: 20 }}>
              지금 바로 시작해봐요
            </p>
            <div style={{
              background: 'var(--color-surface)', borderRadius: 'var(--radius-sm)',
              overflow: 'hidden', boxShadow: 'var(--shadow-card)',
            }}>
              {[
                { icon: '📝', title: '3줄 자동 요약', desc: '핵심만 빠르게 파악해요' },
                { icon: '🌐', title: '격식체·일상체 번역', desc: '상황에 맞게 골라서 읽어요' },
                { icon: '💡', title: '신조어 영문 그대로 유지', desc: 'LoRA, Blackwell 등 원문 표기를 보존해요' },
                { icon: '📋', title: '즉시 복사·공유', desc: '번역 결과를 바로 활용해요' },
                { icon: '🔔', title: '부재중 요약 알림', desc: '오랜만에 접속하면 놓친 기사를 정리해드려요' },
              ].map((f, i, arr) => (
                <div key={f.title} style={{
                  display: 'flex', alignItems: 'center', gap: 14,
                  padding: '15px 16px',
                  borderBottom: i < arr.length - 1 ? '0.5px solid var(--color-border)' : 'none',
                  animation: `fadeIn 0.3s ${i * 0.07}s ease both`,
                }}>
                  <div style={{
                    width: 38, height: 38, borderRadius: 10, flexShrink: 0,
                    background: 'var(--color-primary-light)',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    fontSize: 18,
                  }}>{f.icon}</div>
                  <div>
                    <p style={{ fontSize: 13, fontWeight: 600, color: 'var(--color-text-primary)' }}>{f.title}</p>
                    <p style={{ fontSize: 11, color: 'var(--color-text-tertiary)', marginTop: 2 }}>{f.desc}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ── 버튼 영역 */}
        <div style={{ padding: '20px 0 44px', flexShrink: 0 }}>
          <button
            onClick={() => step === 1 ? setStep(2) : handleDone()}
            disabled={(step === 1 && selected.length === 0) || submitting}
            style={{
              width: '100%', padding: '16px',
              borderRadius: 'var(--radius-md)',
              fontSize: 15, fontWeight: 700, color: '#fff',
              background: (step === 1 && selected.length === 0) || submitting
                ? 'var(--color-text-tertiary)'
                : 'linear-gradient(135deg, #3081fb 0%, #1960ca 100%)',
              transition: 'opacity 0.15s',
              boxShadow: (step === 1 && selected.length === 0) || submitting
                ? 'none'
                : '0 4px 16px rgba(48,129,251,0.35)',
            }}
          >
            {step === 1
              ? selected.length > 0 ? `${selected.length}개 선택했어요 →` : '관심 주제를 선택해주세요'
              : submitting ? '저장 중...' : '시작하기 →'}
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
    </div>
  );
}
