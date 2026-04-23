import type { PropsWithChildren } from 'react';
import { createRoot } from 'react-dom/client';
import { TDSMobileAITProvider } from '@toss/tds-mobile-ait';
import './styles/global.css';
import App from './App';

function AppContainer({ children }: PropsWithChildren) {
  return <TDSMobileAITProvider>{children}</TDSMobileAITProvider>;
}

createRoot(document.getElementById('root')!).render(
  <AppContainer>
    <App />
  </AppContainer>,
);
