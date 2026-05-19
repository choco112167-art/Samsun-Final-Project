import type { SummaryTone } from '../hooks/useTonePreference';

interface Props {
  tone: SummaryTone;
  onChange: (tone: SummaryTone) => void;
  compact?: boolean;
}

export default function TonePreferenceControl({ tone, onChange, compact = false }: Props) {
  return (
    <div
      role="group"
      aria-label="요약 말투 선택"
      style={{
        display: 'grid',
        gridTemplateColumns: '1fr 1fr',
        gap: 4,
        background: compact ? 'rgba(0,0,0,0.05)' : 'var(--color-surface-secondary)',
        borderRadius: 12,
        padding: 4,
        minWidth: compact ? 154 : '100%',
      }}
    >
      {([
        ['formal', '격식체'],
        ['casual', '일상체'],
      ] as const).map(([value, label]) => {
        const active = tone === value;
        return (
          <button
            key={value}
            type="button"
            onClick={() => onChange(value)}
            aria-pressed={active}
            style={{
              minHeight: 34,
              borderRadius: 9,
              padding: compact ? '0 10px' : '0 14px',
              fontSize: compact ? 12 : 13,
              fontWeight: active ? 700 : 500,
              color: active ? 'var(--color-primary)' : 'var(--color-text-secondary)',
              background: active ? 'var(--color-surface)' : 'transparent',
              boxShadow: active ? '0 1px 4px rgba(0,0,0,0.08)' : 'none',
              transition: 'all 0.15s',
              whiteSpace: 'nowrap',
            }}
          >
            {label}
          </button>
        );
      })}
    </div>
  );
}
