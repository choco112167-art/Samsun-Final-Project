import { normalizeFactStatus, type FactStatus } from '../data/articles';
import { Badge } from './Badge';

interface Props {
  label?: string | null;
  size?: 'tiny' | 'small';
}

const META: Record<FactStatus, { text: string; tone: 'blue' | 'red' | 'green' | 'grey' | 'purple' | 'orange'; style: 'fill' | 'weak' }> = {
  VERIFIED: { text: '검증됨', tone: 'blue', style: 'fill' },
  UNVERIFIED: { text: '확인 필요', tone: 'grey', style: 'weak' },
  RUMOR: { text: '루머 주의', tone: 'orange', style: 'weak' },
  HITL_REQUIRED: { text: '전문가 검토', tone: 'purple', style: 'weak' },
  INSIGHT: { text: '분석글', tone: 'blue', style: 'weak' },
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
  const status = normalizeFactStatus(label);
  if (status === 'HITL_REQUIRED') return '전문가 검토 필요';
  return META[status].text;
}

export function factStatusDescription(label?: string | null): string {
  const status = normalizeFactStatus(label);
  if (status === 'VERIFIED') return '신뢰도 높은 출처와 명확한 보도 형식으로 확인된 기사입니다.';
  if (status === 'UNVERIFIED') return '출처는 확인되지만 독립 교차검증 정보가 부족해 추가 확인이 필요한 기사입니다.';
  if (status === 'RUMOR') return '공식 발표보다 추정성 표현이 많아 주의가 필요한 기사입니다.';
  if (status === 'HITL_REQUIRED') return '자동 판정만으로는 판단이 어려워 사람이 추가로 확인해야 하는 기사입니다.';
  return '사실 보도보다 전문가 해설·관점이 중심인 기사입니다.';
}

export function factStatusColor(label?: string | null): string {
  const status = normalizeFactStatus(label);
  if (status === 'VERIFIED' || status === 'INSIGHT') return '#3081FB';
  if (status === 'RUMOR') return '#F97316';
  if (status === 'HITL_REQUIRED') return '#8B5CF6';
  return '#8B95A1';
}
