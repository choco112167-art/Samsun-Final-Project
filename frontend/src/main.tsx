import React, { Component, type PropsWithChildren } from 'react';
import { createRoot } from 'react-dom/client';
import './styles/global.css';
import App from './App';

// TDSMobileAITProvider는 토스 앱 WebView 환경에서만 정상 동작.
// 일반 브라우저(Railway 배포 등)에서는 Provider 없이 렌더링.
function AppContainer({ children }: PropsWithChildren) {
  try {
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    const { TDSMobileAITProvider } = require('@toss/tds-mobile-ait');
    return <TDSMobileAITProvider>{children}</TDSMobileAITProvider>;
  } catch {
    return <>{children}</>;
  }
}

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

createRoot(document.getElementById('root')!).render(
  <ErrorBoundary>
    <AppContainer>
      <App />
    </AppContainer>
  </ErrorBoundary>,
);
