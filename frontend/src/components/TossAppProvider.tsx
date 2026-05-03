import type { ReactNode } from 'react';
import { TDSMobileAITProvider } from '@toss/tds-mobile-ait';

interface Props {
  children: ReactNode;
}

const ENABLE_TDS_PROVIDER = import.meta.env.VITE_ENABLE_TDS_PROVIDER === '1';

export default function TossAppProvider({ children }: Props) {
  if (!ENABLE_TDS_PROVIDER) {
    return <>{children}</>;
  }

  return (
    <TDSMobileAITProvider brandPrimaryColor="#3182F6">
      {children}
    </TDSMobileAITProvider>
  );
}
