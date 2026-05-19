import { useMemo, useState } from 'react';
import { BottomSheet } from './Overlay';
import type { NeologismEntry } from '../data/api';
import { segmentNeologismText } from '../data/neologismMatcher';

interface Props {
  text: string;
  entries: NeologismEntry[];
}

function displayExplanation(entry: NeologismEntry): string {
  return entry.explanation?.trim() ?? '';
}

export default function NeologismText({ text, entries }: Props) {
  const [sheetEntry, setSheetEntry] = useState<NeologismEntry | null>(null);
  const [hoverEntry, setHoverEntry] = useState<NeologismEntry | null>(null);

  const segments = useMemo(() => {
    const demoMode = import.meta.env.VITE_DEMO_POLISHED_FEED === '1'
      || import.meta.env.VITE_HIDE_DEMO_ARTICLES === '1';
    return segmentNeologismText(text, entries, { demoMode, maxMatches: 4 });
  }, [entries, text]);

  if (!text) return null;
  if (segments.length === 1 && !segments[0].entry) return <>{text}</>;

  return (
    <>
      {segments.map((segment, index) => {
        const { entry } = segment;
        const part = segment.text;
        if (!entry) return <span key={`${part}-${index}`}>{part}</span>;
        const explanation = displayExplanation(entry);
        if (!explanation) return <span key={`${part}-${index}`}>{part}</span>;
        return (
          <span
            key={`${part}-${index}`}
            style={{
              position: 'relative',
              display: 'inline-block',
            }}
            onMouseEnter={() => setHoverEntry(entry)}
            onMouseLeave={() => setHoverEntry(prev => (prev?.term === entry.term ? null : prev))}
          >
            <button
              type="button"
              onClick={event => {
                event.stopPropagation();
                setSheetEntry(entry);
              }}
              style={{
                display: 'inline',
                minHeight: 30,
                padding: '0 1px',
                color: 'var(--color-primary)',
                borderBottom: '1px dashed var(--color-primary)',
                font: 'inherit',
                fontWeight: 700,
                lineHeight: 'inherit',
                verticalAlign: 'baseline',
              }}
            >
              {part}
            </button>
            {hoverEntry?.term === entry.term && (
              <span
                role="tooltip"
                style={{
                  position: 'absolute',
                  left: 0,
                  bottom: 'calc(100% + 8px)',
                  width: 220,
                  maxWidth: '72vw',
                  padding: '10px 12px',
                  borderRadius: 10,
                  background: '#191F28',
                  color: '#fff',
                  boxShadow: '0 8px 24px rgba(0,0,0,0.18)',
                  zIndex: 30,
                  pointerEvents: 'none',
                }}
              >
                <strong style={{ display: 'block', fontSize: 12, marginBottom: 3 }}>{entry.term}</strong>
                {entry.ko_suggestion && (
                  <span style={{ display: 'block', fontSize: 11, color: 'rgba(255,255,255,0.72)', marginBottom: 4 }}>
                    {entry.ko_suggestion}
                  </span>
                )}
                <span style={{ display: 'block', fontSize: 12, lineHeight: 1.55 }}>{explanation}</span>
              </span>
            )}
          </span>
        );
      })}

      <BottomSheet
        open={!!sheetEntry}
        onClose={() => setSheetEntry(null)}
        header={sheetEntry && <BottomSheet.Header>{sheetEntry.term}</BottomSheet.Header>}
        cta={<BottomSheet.CTA>확인</BottomSheet.CTA>}
      >
        {sheetEntry && (
          <div style={{ padding: '0 20px 8px' }}>
            {sheetEntry.ko_suggestion && (
              <p style={{ fontSize: 13, color: 'var(--color-primary)', fontWeight: 700, marginBottom: 8 }}>
                {sheetEntry.ko_suggestion}
              </p>
            )}
            <p style={{ fontSize: 14, color: 'var(--color-text-primary)', lineHeight: 1.7 }}>
              {displayExplanation(sheetEntry)}
            </p>
          </div>
        )}
      </BottomSheet>
    </>
  );
}
