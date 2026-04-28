// ⚠️ 반드시 첫 번째 import — `@toss/tds-mobile` 의 IIFE 가
//    실행되기 전에 location.hostname / navigator.userAgent 를 모킹해야 한다.
import './lib/tds-bypass';

import React, { Component, useMemo, useSyncExternalStore, type PropsWithChildren } from 'react';
import { createRoot } from 'react-dom/client';
import { TDSMobileProvider } from '@toss/tds-mobile';
import './styles/global.css';
import App from './App';

class ErrorBoundary extends Component<PropsWithChildren, { error: Error | null }> {
  state = { error: null };
  static getDerivedStateFromError(error: Error) { return { error }; }
  render() {
    if (this.state.error) {
      return (
        <div style={{ padding: 24, fontFamily: 'monospace', color: 'red' }}>
          <b>앱 오류:</b>
          <pre style={{ whiteSpace: 'pre-wrap', fontSize: 13 }}>
            {(this.state.error as Error).message}
          </pre>
        </div>
      );
    }
    return this.props.children;
  }
}

// TDSMobileProvider 는 userAgent: UserAgentVariables 가 필수.
// 안 넘기면 내부에서 userAgent.colorPreference 접근 시 throw → 흰 화면.
const isBrowser = typeof window !== 'undefined' && typeof navigator !== 'undefined';
const ua = isBrowser ? navigator.userAgent : '';
const isAndroid = /Android/i.test(ua);
const isIOS = /iPhone|iPad|iPod/i.test(ua);

function getColorPreference(): 'light' | 'dark' {
  if (!isBrowser || typeof window.matchMedia !== 'function') return 'light';
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
}

function subscribeColorPreference(onChange: () => void): () => void {
  if (!isBrowser || typeof window.matchMedia !== 'function') return () => {};
  const mq = window.matchMedia('(prefers-color-scheme: dark)');
  const handler = () => onChange();
  if (typeof mq.addEventListener === 'function') {
    mq.addEventListener('change', handler);
    return () => mq.removeEventListener('change', handler);
  }
  mq.addListener(handler);
  return () => mq.removeListener(handler);
}

function useColorPreference(): 'light' | 'dark' {
  return useSyncExternalStore(
    subscribeColorPreference,
    getColorPreference,
    () => 'light',
  );
}

function Root({ children }: PropsWithChildren) {
  const colorPreference = useColorPreference();
  const userAgent = useMemo(
    () => ({
      isAndroid,
      isIOS,
      fontA11y: undefined,
      fontScale: undefined,
      colorPreference,
      safeAreaBottomTransparency: 'opaque' as const,
    }),
    [colorPreference],
  );

  return (
    <TDSMobileProvider userAgent={userAgent}>
      {children}
    </TDSMobileProvider>
  );
}

createRoot(document.getElementById('root')!).render(
  <ErrorBoundary>
    <Root>
      <App />
    </Root>
  </ErrorBoundary>,
);
