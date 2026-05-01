import { createRoot } from 'react-dom/client';
import './styles/global.css';
import App from './App';
import { OverlayProvider, ErrorBoundary } from './components/Overlay';

// `@toss/tds-mobile` 의존을 100% 제거 (이슈 #13). hostname 기반 환경 차단을
// 브라우저 보안 정책상 우회할 수 없으므로 자체 OverlayProvider 로 대체.

createRoot(document.getElementById('root')!).render(
  <ErrorBoundary>
    <OverlayProvider>
      <App />
    </OverlayProvider>
  </ErrorBoundary>,
);
