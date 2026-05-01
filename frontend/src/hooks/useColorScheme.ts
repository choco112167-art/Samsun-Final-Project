import { useSyncExternalStore } from 'react';

/**
 * useColorScheme — `prefers-color-scheme` 미디어 쿼리를 구독해 'light' | 'dark' 를 반환.
 *
 * - SSR-safe: window 부재 시 'light' 폴백.
 * - React 18 의 `useSyncExternalStore` 사용 → 외부 OS/브라우저 테마 변경에 즉시 리렌더.
 * - 프로젝트는 현재 라이트 테마 단일이지만, 자산(`samsun_dark.png`) 과 향후 다크모드 도입을 위해
 *   훅을 미리 두고 진입점에서 조건부 렌더한다.
 */
export type ColorScheme = 'light' | 'dark';

const QUERY = '(prefers-color-scheme: dark)';

function subscribe(onChange: () => void): () => void {
  if (typeof window === 'undefined' || !window.matchMedia) return () => {};
  const mql = window.matchMedia(QUERY);
  // Safari < 14 fallback: addListener / removeListener
  if (mql.addEventListener) {
    mql.addEventListener('change', onChange);
    return () => mql.removeEventListener('change', onChange);
  }
  mql.addListener(onChange);
  return () => mql.removeListener(onChange);
}

function getSnapshot(): ColorScheme {
  if (typeof window === 'undefined' || !window.matchMedia) return 'light';
  return window.matchMedia(QUERY).matches ? 'dark' : 'light';
}

function getServerSnapshot(): ColorScheme {
  return 'light';
}

export function useColorScheme(): ColorScheme {
  return useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);
}
