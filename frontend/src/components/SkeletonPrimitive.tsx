/**
 * SkeletonPrimitive.tsx — `@toss/tds-mobile` 의 <Skeleton.Wrapper>, <Skeleton.Item> 대체.
 *
 * 호출처 호환을 위해 동일하게 dot-notation 으로 묶어 export:
 *   <Skeleton.Wrapper play="show" style={...}>
 *     <Skeleton.Item style={{ width, height, borderRadius }} />
 *   </Skeleton.Wrapper>
 *
 * 구현은 순수 div + CSS keyframe 한 번 주입.
 */

import type { CSSProperties, PropsWithChildren } from 'react';

const KEYFRAME_INJECTED = '__samsun_skeleton_kf__';

function injectKeyframesOnce() {
  if (typeof document === 'undefined') return;
  if ((document as unknown as { [k: string]: boolean })[KEYFRAME_INJECTED]) return;
  const style = document.createElement('style');
  style.textContent = `
    @keyframes samsunSkeletonShimmer {
      0%   { background-position: -200px 0; }
      100% { background-position: calc(200px + 100%) 0; }
    }
  `;
  document.head.appendChild(style);
  (document as unknown as { [k: string]: boolean })[KEYFRAME_INJECTED] = true;
}

interface WrapperProps {
  /** TDS 와 동일하게 'show' 시 shimmer 활성화. 'hidden' 등 그 외 값은 정적 표시. */
  play?: 'show' | 'hidden' | string;
  style?: CSSProperties;
}

function Wrapper({ play, style, children }: PropsWithChildren<WrapperProps>) {
  injectKeyframesOnce();
  return (
    <div data-skeleton-play={play ?? 'show'} style={style}>
      {children}
    </div>
  );
}

interface ItemProps {
  style?: CSSProperties;
}

function Item({ style }: ItemProps) {
  injectKeyframesOnce();
  return (
    <div
      style={{
        background:
          'linear-gradient(90deg, #EEF1F4 0px, #F7F9FA 80px, #EEF1F4 160px) #EEF1F4',
        backgroundSize: '200px 100%',
        backgroundRepeat: 'no-repeat',
        animation: 'samsunSkeletonShimmer 1.2s ease-in-out infinite',
        borderRadius: 6,
        ...style,
      }}
    />
  );
}

export const Skeleton = { Wrapper, Item };
export default Skeleton;
