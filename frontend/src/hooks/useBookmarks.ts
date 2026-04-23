import { useState, useCallback } from 'react';

export function useBookmarks(initial: string[] = []) {
  const [bookmarked, setBookmarked] = useState<Set<string>>(new Set(initial));

  const toggle = useCallback((id: string) => {
    setBookmarked(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }, []);

  const isBookmarked = useCallback((id: string) => bookmarked.has(id), [bookmarked]);

  return { bookmarked, toggle, isBookmarked };
}

export type BookmarkHook = ReturnType<typeof useBookmarks>;
