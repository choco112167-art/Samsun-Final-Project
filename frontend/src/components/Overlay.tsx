/**
 * Overlay.tsx — `@toss/tds-mobile` 의존 제거 후 자체 구현한 web-safe Overlay 시스템.
 *
 * 제공 API (TDS 와 거의 동일하게 맞춰 호출처 변경을 최소화):
 *   - <OverlayProvider>           : 토스트/시트가 portal 로 렌더되는 루트
 *   - useToast()                  : { openToast(message, { duration }) }
 *   - useOverlay()                : { open(node), close() } imperative — TDS useOverlay 호환
 *   - <BottomSheet open onClose header cta>...</BottomSheet>
 *       하위: <BottomSheet.Header>, <BottomSheet.CTA>
 *
 * 모든 구현은 순수 React + 인라인 스타일이며 외부 라이브러리/CSS 변수 의존 없음.
 */

import React, {
  Component,
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type PropsWithChildren,
  type ReactNode,
} from 'react';
import { createPortal } from 'react-dom';

/* ─────────────────────────── 1. Toast ─────────────────────────── */

interface Toast {
  id: number;
  message: string;
  duration: number;
}

interface ToastCtx {
  openToast: (message: string, opts?: { duration?: number }) => void;
}

const ToastContext = createContext<ToastCtx | null>(null);

export function useToast(): ToastCtx {
  const ctx = useContext(ToastContext);
  if (!ctx) {
    // Provider 가 없어도 앱이 죽지 않도록 noop 반환 (TDS 의 hard-throw 와 다른 점)
    if (typeof console !== 'undefined') {
      console.warn('[useToast] OverlayProvider 외부에서 호출됨 — toast 가 무시됩니다.');
    }
    return { openToast: () => {} };
  }
  return ctx;
}

/* ─────────────────────────── 2. Overlay (imperative) ─────────────────────────── */

interface OverlayCtx {
  open: (node: ReactNode, key?: string) => string;
  close: (key: string) => void;
}

const OverlayContext = createContext<OverlayCtx | null>(null);

export function useOverlay(): OverlayCtx {
  const ctx = useContext(OverlayContext);
  if (!ctx) {
    if (typeof console !== 'undefined') {
      console.warn('[useOverlay] OverlayProvider 외부에서 호출됨 — open/close 가 무시됩니다.');
    }
    return { open: () => '', close: () => {} };
  }
  return ctx;
}

/* ─────────────────────────── 3. Provider ─────────────────────────── */

let toastSeq = 0;
let overlaySeq = 0;

export function OverlayProvider({ children }: PropsWithChildren) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const [overlays, setOverlays] = useState<Array<{ key: string; node: ReactNode }>>([]);
  const timersRef = useRef<Map<number, ReturnType<typeof setTimeout>>>(new Map());

  const openToast = useCallback<ToastCtx['openToast']>((message, opts) => {
    const id = ++toastSeq;
    const duration = opts?.duration ?? 2200;
    setToasts(prev => [...prev, { id, message, duration }]);
    const timer = setTimeout(() => {
      setToasts(prev => prev.filter(t => t.id !== id));
      timersRef.current.delete(id);
    }, duration);
    timersRef.current.set(id, timer);
  }, []);

  const open = useCallback<OverlayCtx['open']>((node, key) => {
    const k = key ?? `o-${++overlaySeq}`;
    setOverlays(prev => [...prev.filter(o => o.key !== k), { key: k, node }]);
    return k;
  }, []);

  const close = useCallback<OverlayCtx['close']>((key) => {
    setOverlays(prev => prev.filter(o => o.key !== key));
  }, []);

  useEffect(() => () => {
    timersRef.current.forEach(t => clearTimeout(t));
    timersRef.current.clear();
  }, []);

  const toastValue = useMemo(() => ({ openToast }), [openToast]);
  const overlayValue = useMemo(() => ({ open, close }), [open, close]);

  return (
    <OverlayContext.Provider value={overlayValue}>
      <ToastContext.Provider value={toastValue}>
        {children}
        {typeof document !== 'undefined' && createPortal(
          <ToastViewport toasts={toasts} />,
          document.body,
        )}
        {typeof document !== 'undefined' && overlays.length > 0 && createPortal(
          <>{overlays.map(o => <React.Fragment key={o.key}>{o.node}</React.Fragment>)}</>,
          document.body,
        )}
      </ToastContext.Provider>
    </OverlayContext.Provider>
  );
}

function ToastViewport({ toasts }: { toasts: Toast[] }) {
  if (toasts.length === 0) return null;
  return (
    <div
      style={{
        position: 'fixed',
        left: 0,
        right: 0,
        bottom: 'calc(env(safe-area-inset-bottom) + 96px)',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        gap: 8,
        pointerEvents: 'none',
        zIndex: 10000,
      }}
    >
      {toasts.map(t => (
        <div
          key={t.id}
          role="status"
          style={{
            background: 'rgba(25, 31, 40, 0.92)',
            color: '#fff',
            fontSize: 13,
            fontWeight: 500,
            padding: '10px 18px',
            borderRadius: 12,
            boxShadow: '0 6px 24px rgba(0,0,0,0.18)',
            maxWidth: 'min(86vw, 420px)',
            textAlign: 'center',
            animation: 'samsunToastIn 0.18s ease',
          }}
        >
          {t.message}
        </div>
      ))}
      <style>{`@keyframes samsunToastIn { from { opacity:0; transform: translateY(8px) } to { opacity:1; transform: translateY(0) } }`}</style>
    </div>
  );
}

/* ─────────────────────────── 4. BottomSheet ─────────────────────────── */

const BottomSheetCloseContext = createContext<(() => void) | null>(null);

interface BottomSheetProps {
  open: boolean;
  onClose: () => void;
  header?: ReactNode;
  cta?: ReactNode;
  children?: ReactNode;
}

interface BottomSheetSubComponents {
  Header: React.FC<PropsWithChildren>;
  CTA: React.FC<PropsWithChildren<{ onClick?: () => void }>>;
}

const BottomSheetImpl: React.FC<BottomSheetProps> = ({ open, onClose, header, cta, children }) => {
  // mounting flag for exit animation
  const [mounted, setMounted] = useState(open);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    if (open) {
      setMounted(true);
      // next tick: trigger enter animation
      const id = requestAnimationFrame(() => setVisible(true));
      return () => cancelAnimationFrame(id);
    } else {
      setVisible(false);
      const t = setTimeout(() => setMounted(false), 220);
      return () => clearTimeout(t);
    }
  }, [open]);

  // prevent body scroll while open
  useEffect(() => {
    if (!mounted) return;
    const prev = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => { document.body.style.overflow = prev; };
  }, [mounted]);

  // ESC to close
  useEffect(() => {
    if (!mounted) return;
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [mounted, onClose]);

  if (!mounted || typeof document === 'undefined') return null;

  return createPortal(
    <BottomSheetCloseContext.Provider value={onClose}>
    <div
      role="dialog"
      aria-modal="true"
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 9000,
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'flex-end',
      }}
    >
      <div
        onClick={onClose}
        style={{
          position: 'absolute',
          inset: 0,
          background: 'rgba(0,0,0,0.45)',
          opacity: visible ? 1 : 0,
          transition: 'opacity 0.2s ease',
        }}
      />
      <div
        style={{
          position: 'relative',
          background: '#fff',
          borderRadius: '20px 20px 0 0',
          paddingBottom: 'env(safe-area-inset-bottom)',
          maxHeight: '85vh',
          display: 'flex',
          flexDirection: 'column',
          transform: visible ? 'translateY(0)' : 'translateY(100%)',
          transition: 'transform 0.22s cubic-bezier(0.32, 0.72, 0, 1)',
          boxShadow: '0 -8px 32px rgba(0,0,0,0.12)',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <div
          aria-hidden
          style={{
            margin: '10px auto 4px',
            width: 36,
            height: 4,
            borderRadius: 2,
            background: '#E5E8EB',
            flexShrink: 0,
          }}
        />
        {header && <div style={{ flexShrink: 0 }}>{header}</div>}
        <div style={{ flex: 1, overflowY: 'auto', WebkitOverflowScrolling: 'touch' }}>
          {children}
        </div>
        {cta && <div style={{ flexShrink: 0 }}>{cta}</div>}
      </div>
    </div>
    </BottomSheetCloseContext.Provider>,
    document.body,
  );
};

const BottomSheetHeader: React.FC<PropsWithChildren> = ({ children }) => (
  <div
    style={{
      padding: '12px 20px 8px',
      fontSize: 17,
      fontWeight: 700,
      color: '#191f28',
      letterSpacing: '-0.02em',
    }}
  >
    {children}
  </div>
);

const BottomSheetCTA: React.FC<PropsWithChildren<{ onClick?: () => void }>> = ({ children, onClick }) => {
  const sheetClose = useContext(BottomSheetCloseContext);
  // onClick 이 명시 안 된 경우 시트의 onClose 를 자동 트리거 (TDS 동등 동작)
  const handle = onClick ?? sheetClose ?? undefined;
  return (
  <div style={{ padding: '12px 16px 16px' }}>
    <button
      type="button"
      onClick={handle}
      style={{
        width: '100%',
        height: 52,
        borderRadius: 12,
        border: 'none',
        background: '#3081FB',
        color: '#fff',
        fontSize: 16,
        fontWeight: 700,
        letterSpacing: '-0.01em',
        cursor: 'pointer',
      }}
    >
      {children}
    </button>
  </div>
  );
};

export const BottomSheet = Object.assign(BottomSheetImpl, {
  Header: BottomSheetHeader,
  CTA: BottomSheetCTA,
}) as React.FC<BottomSheetProps> & BottomSheetSubComponents;

/* ─────────────────────────── 5. ErrorBoundary 재export(편의) ─────────────────────────── */

export class ErrorBoundary extends Component<PropsWithChildren, { error: Error | null }> {
  state: { error: Error | null } = { error: null };
  static getDerivedStateFromError(error: Error) { return { error }; }
  render() {
    if (this.state.error) {
      return (
        <div style={{ padding: 24, fontFamily: 'monospace', color: 'red' }}>
          <b>앱 오류:</b>
          <pre style={{ whiteSpace: 'pre-wrap', fontSize: 13 }}>
            {this.state.error.message}
          </pre>
        </div>
      );
    }
    return this.props.children;
  }
}
