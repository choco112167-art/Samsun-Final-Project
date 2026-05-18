import { normalizeFactStatus, type FactStatus } from '../data/articles';
import { Badge } from './Badge';

interface Props {
  label?: string | null;
  size?: 'tiny' | 'small';
}

const META: Record<FactStatus, { text: string; tone: 'blue' | 'red' | 'green' | 'grey'; style: 'fill' | 'weak' }> = {
  VERIFIED: { text: '검증됨', tone: 'green', style: 'fill' },
  UNVERIFIED: { text: '미검증', tone: 'grey', style: 'weak' },
  RUMOR: { text: '루머 의심', tone: 'red', style: 'weak' },
  HITL_REQUIRED: { text: 'HITL 검토 필요', tone: 'blue', style: 'weak' },
  INSIGHT: { text: '분석', tone: 'blue', style: 'weak' },
};

export function FactStatusBadge({ label, size = 'tiny' }: Props) {
  const status = normalizeFactStatus(label);
  const meta = META[status];
  return (
    <Badge badgeStyle={meta.style} type={meta.tone} size={size}>
      {meta.text}
    </Badge>
  );
}

export function factStatusText(label?: string | null): string {
  return META[normalizeFactStatus(label)].text;
}

