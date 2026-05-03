import { createRoot } from 'react-dom/client';
import './styles/global.css';
import App from './App';
import { OverlayProvider, ErrorBoundary } from './components/Overlay';
import TossAppProvider from './components/TossAppProvider';

// TDS provider is opt-in via VITE_ENABLE_TDS_PROVIDER=1 so normal browser dev
// stays stable while Apps in Toss/TDS wiring is available for sandbox builds.

createRoot(document.getElementById('root')!).render(
  <ErrorBoundary>
    <TossAppProvider>
      <OverlayProvider>
        <App />
      </OverlayProvider>
    </TossAppProvider>
  </ErrorBoundary>,
);
