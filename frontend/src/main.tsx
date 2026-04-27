import React, { Component, type PropsWithChildren } from 'react';
import { createRoot } from 'react-dom/client';
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

// CSS 변수(--color-*, --radius-*, 등)는 global.css :root에 직접 정의돼 있어서
// TDSMobileAITProvider 없이도 정상 렌더링된다.
createRoot(document.getElementById('root')!).render(
  <ErrorBoundary>
    <App />
  </ErrorBoundary>,
);
