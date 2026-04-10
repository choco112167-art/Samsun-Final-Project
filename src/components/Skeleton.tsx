import { useEffect, useState, useRef } from 'react';

interface SkeletonBoxProps {
  width?: string;
  height?: number;
  borderRadius?: number;
  style?: React.CSSProperties;
}

function SkeletonBox({ width = '100%', height = 16, borderRadius = 6, style }: SkeletonBoxProps) {
  return (
    <div style={{
      width,
      height,
      borderRadius,
      background: 'linear-gradient(90deg, #F0F0F0 25%, #E0E0E0 50%, #F0F0F0 75%)',
      backgroundSize: '200% 100%',
      animation: 'shimmer 1.4s infinite',
      ...style,
    }} />
  );
}

export function ArticleCardSkeleton() {
  return (
    <div style={{
      background: 'var(--color-surface)',
      borderRadius: 'var(--radius-lg)',
      padding: '16px',
      boxShadow: 'var(--shadow-card)',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 10 }}>
        <SkeletonBox width="6px" height={6} borderRadius={3} />
        <SkeletonBox width="80px" height={12} />
        <SkeletonBox width="50px" height={12} style={{ marginLeft: 'auto' }} />
      </div>
      <SkeletonBox width="90%" height={18} style={{ marginBottom: 8 }} />
      <SkeletonBox width="70%" height={18} style={{ marginBottom: 12 }} />
      <SkeletonBox width="100%" height={13} style={{ marginBottom: 5 }} />
      <SkeletonBox width="80%" height={13} style={{ marginBottom: 14 }} />
      <div style={{ display: 'flex', gap: 6 }}>
        <SkeletonBox width="72px" height={24} borderRadius={6} />
        <SkeletonBox width="36px" height={24} borderRadius={6} style={{ marginLeft: 'auto' }} />
      </div>
    </div>
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
    <>
      <style>{`
        @keyframes shimmer {
          0% { background-position: 200% 0; }
          100% { background-position: -200% 0; }
        }
      `}</style>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 10, padding: '12px 16px' }}>
        {/* breaking 배너 스켈레톤 */}
        <SkeletonBox height={64} borderRadius={16} />
        {/* 카드 스켈레톤 3장 */}
        <ArticleCardSkeleton />
        <ArticleCardSkeleton />
        <ArticleCardSkeleton />
      </div>
    </>
  );
}
