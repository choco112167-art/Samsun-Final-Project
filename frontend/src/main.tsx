import React, { Component, type PropsWithChildren } from 'react';
import { createRoot } from 'react-dom/client';
import { TDSMobileProvider } from '@toss/tds-mobile';
import './styles/global.css';
import App from './App';

// 전체 앱 에러 바운더리 — 흰 화면 대신 에러 내용을 표시
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

// TDSMobileProvider: 일반 브라우저용 TDS 컨텍스트 (Overlay/Portal/Theme 등).
// TDSMobileAITProvider(=AppsInToss WebView용)와 달리 토스 앱 외부에서도 정상 렌더링됨.
// CSS 변수는 global.css :root에 별도로 정의돼 있고, Provider는 useOverlay/BottomSheet/
// useToast 등 TDS 컴포넌트가 요구하는 React 컨텍스트만 제공한다.
createRoot(document.getElementById('root')!).render(
  <ErrorBoundary>
    <TDSMobileProvider>
      <App />
    </TDSMobileProvider>
  </ErrorBoundary>,
);
