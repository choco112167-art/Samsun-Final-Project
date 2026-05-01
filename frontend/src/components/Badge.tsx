/**
 * Badge.tsx — `@toss/tds-mobile` 의 <Badge> 대체.
 *
 * 호출처 호환을 위해 동일한 props 시그니처 유지:
 *   <Badge badgeStyle="fill"|"weak" type="blue"|"red"|"green" size="tiny"|"small">…</Badge>
 */

import type { PropsWithChildren } from 'react';

type Tone = 'blue' | 'red' | 'green' | 'grey';
type Style = 'fill' | 'weak';
type Size = 'tiny' | 'small';

interface Props {
  badgeStyle?: Style;
  type?: Tone;
  size?: Size;
}

const PALETTE: Record<Tone, { fillBg: string; fillFg: string; weakBg: string; weakFg: string }> = {
  blue:  { fillBg: '#3081FB', fillFg: '#FFFFFF', weakBg: '#E8F2FE', weakFg: '#1B64DA' },
  red:   { fillBg: '#F04452', fillFg: '#FFFFFF', weakBg: '#FEEAEC', weakFg: '#D5283A' },
  green: { fillBg: '#21C284', fillFg: '#FFFFFF', weakBg: '#E0F7EE', weakFg: '#138759' },
  grey:  { fillBg: '#8B95A1', fillFg: '#FFFFFF', weakBg: '#F2F4F6', weakFg: '#4E5968' },
};

export function Badge({
  badgeStyle = 'fill',
  type = 'grey',
  size = 'tiny',
  children,
}: PropsWithChildren<Props>) {
  const c = PALETTE[type];
  const isFill = badgeStyle === 'fill';

  const fontSize = size === 'tiny' ? 10 : 11;
  const padY     = size === 'tiny' ? 2 : 3;
  const padX     = size === 'tiny' ? 6 : 8;

  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        flexShrink: 0,
        fontSize,
        fontWeight: 700,
        lineHeight: 1.2,
        letterSpacing: '0.02em',
        padding: `${padY}px ${padX}px`,
        borderRadius: 4,
        background: isFill ? c.fillBg : c.weakBg,
        color:      isFill ? c.fillFg : c.weakFg,
        whiteSpace: 'nowrap',
      }}
    >
      {children}
    </span>
  );
}

export default Badge;
