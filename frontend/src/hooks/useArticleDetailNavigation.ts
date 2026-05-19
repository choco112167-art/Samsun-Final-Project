import { useEffect, useRef } from 'react';
import type { RefObject } from 'react';

type ScrollRef = RefObject<HTMLElement | HTMLDivElement | null>;

export function restoreArticleListScroll(scrollRef: ScrollRef, scrollTop: number) {
  const apply = () => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollTop;
    }
  };
  requestAnimationFrame(() => {
    apply();
    requestAnimationFrame(apply);
  });
  window.setTimeout(apply, 80);
}

export function useArticleDetailNavigation(isOpen: boolean, onSystemBack: () => void) {
  const isOpenRef = useRef(isOpen);
  const closeRef = useRef(onSystemBack);
  const pushedRef = useRef(false);

  useEffect(() => {
    isOpenRef.current = isOpen;
    closeRef.current = onSystemBack;
  }, [isOpen, onSystemBack]);

  useEffect(() => {
    if (!isOpen || pushedRef.current) return;
    window.history.pushState({ samsunDetailOpen: true }, '', window.location.href);
    pushedRef.current = true;
    if (import.meta.env.DEV) {
      console.log('[detail-nav] push detail history marker');
    }
  }, [isOpen]);

  useEffect(() => {
    if (isOpen || !pushedRef.current) return;
    if (window.history.state?.samsunDetailOpen) {
      window.history.replaceState({ samsunDetailClosed: true }, '', window.location.href);
    }
    pushedRef.current = false;
  }, [isOpen]);

  useEffect(() => {
    const handlePopState = () => {
      if (!isOpenRef.current) return;
      pushedRef.current = false;
      if (import.meta.env.DEV) {
        console.log('[detail-nav] system back closes article detail');
      }
      closeRef.current();
    };
    window.addEventListener('popstate', handlePopState);
    return () => window.removeEventListener('popstate', handlePopState);
  }, []);
}
