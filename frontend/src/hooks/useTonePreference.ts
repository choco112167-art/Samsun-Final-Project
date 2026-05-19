import { useCallback, useState } from 'react';

export type SummaryTone = 'formal' | 'casual';

const TONE_KEY = 'samsun_summary_tone';

function isSummaryTone(value: string | null): value is SummaryTone {
  return value === 'formal' || value === 'casual';
}

export function loadTonePreference(): SummaryTone {
  try {
    const saved = localStorage.getItem(TONE_KEY);
    return isSummaryTone(saved) ? saved : 'formal';
  } catch {
    return 'formal';
  }
}

export function useTonePreference() {
  const [tone, setToneState] = useState<SummaryTone>(loadTonePreference);

  const setTone = useCallback((next: SummaryTone) => {
    setToneState(next);
    try {
      localStorage.setItem(TONE_KEY, next);
    } catch {
      // Preference is still applied for the current session.
    }
  }, []);

  return { tone, setTone };
}

export function toneLabel(tone: SummaryTone): string {
  return tone === 'formal' ? '격식체' : '일상체';
}
