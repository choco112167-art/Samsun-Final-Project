import { useEffect, useRef } from 'react';
import { Skeleton } from './SkeletonPrimitive';

export function ArticleCardSkeleton() {
  return (
    <Skeleton.Wrapper
      play="show"
      style={{
        background: 'var(--color-surface)',
        borderRadius: 'var(--radius-lg)',
        padding: '16px',
        boxShadow: 'var(--shadow-card)',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 10 }}>
        <Skeleton.Item style={{ width: 6, height: 6, borderRadius: 3 }} />
        <Skeleton.Item style={{ width: 80, height: 12, borderRadius: 6 }} />
        <Skeleton.Item style={{ width: 50, height: 12, borderRadius: 6, marginLeft: 'auto' }} />
      </div>
      <Skeleton.Item style={{ width: '90%', height: 18, borderRadius: 6, marginBottom: 8 }} />
      <Skeleton.Item style={{ width: '70%', height: 18, borderRadius: 6, marginBottom: 12 }} />
      <Skeleton.Item style={{ width: '100%', height: 13, borderRadius: 6, marginBottom: 5 }} />
      <Skeleton.Item style={{ width: '80%', height: 13, borderRadius: 6, marginBottom: 14 }} />
      <div style={{ display: 'flex', gap: 6 }}>
        <Skeleton.Item style={{ width: 72, height: 24, borderRadius: 6 }} />
        <Skeleton.Item style={{ width: 36, height: 24, borderRadius: 6, marginLeft: 'auto' }} />
      </div>
    </Skeleton.Wrapper>
  );
}

interface FeedSkeletonProps {
  onDone: () => void;
}

export function FeedSkeleton({ onDone }: FeedSkeletonProps) {
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    timerRef.current = setTimeout(onDone, 1200);
    return () => { if (timerRef.current) clearTimeout(timerRef.current); };
  }, [onDone]);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 10, padding: '12px 16px' }}>
      {/* breaking 배너 스켈레톤 */}
      <Skeleton.Wrapper play="show" style={{ height: 64, borderRadius: 16 }}>
        <Skeleton.Item style={{ width: '100%', height: '100%', borderRadius: 16 }} />
      </Skeleton.Wrapper>
      {/* 카드 스켈레톤 3장 */}
      <ArticleCardSkeleton />
      <ArticleCardSkeleton />
      <ArticleCardSkeleton />
    </div>
  );
}
