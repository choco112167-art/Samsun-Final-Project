import { useState, useCallback } from 'react';
import type { Article } from '../data/articles';

const IDS_KEY      = 'samsun_bookmarks';
const ARTICLES_KEY = 'samsun_bookmarked_articles';

/** localStorage에서 북마크 ID Set 불러오기 */
function loadIds(): Set<string> {
  try {
    const raw = JSON.parse(localStorage.getItem(IDS_KEY) ?? '[]') as string[];
    return new Set(raw.filter(id => id && id !== 'undefined'));
  } catch {
    return new Set();
  }
}

/** localStorage에서 북마크된 기사 Map 불러오기 */
function loadArticles(): Map<string, Article> {
  try {
    const list = JSON.parse(localStorage.getItem(ARTICLES_KEY) ?? '[]') as Article[];
    return new Map(list.map(a => [a.urlHash, a]));
  } catch {
    return new Map();
  }
}

export function useBookmarks() {
  const [ids, setIds]           = useState<Set<string>>(loadIds);
  const [cache, setCache]       = useState<Map<string, Article>>(loadArticles);

  /**
   * 북마크 토글.
   * @param id       기사 urlHash
   * @param article  (선택) 기사 전체 객체 — 북마크 탭 독립 동작을 위해 캐시에 저장됨
   */
  const toggle = useCallback((id: string, article?: Article) => {
    if (!id || id === 'undefined') return;
    setIds(prev => {
      const next = new Set(prev);
      if (next.has(id)) {
        // ── 북마크 해제
        next.delete(id);
        setCache(prevC => {
          const nextC = new Map(prevC);
          nextC.delete(id);
          try {
            localStorage.setItem(ARTICLES_KEY, JSON.stringify([...nextC.values()]));
          } catch {}
          return nextC;
        });
      } else {
        // ── 북마크 추가
        next.add(id);
        if (article) {
          setCache(prevC => {
            const nextC = new Map(prevC);
            nextC.set(id, article);
            try {
              localStorage.setItem(ARTICLES_KEY, JSON.stringify([...nextC.values()]));
            } catch {}
            return nextC;
          });
        }
      }
      try {
        localStorage.setItem(IDS_KEY, JSON.stringify([...next]));
      } catch {}
      return next;
    });
  }, []);

  const isBookmarked = useCallback((id: string) => ids.has(id), [ids]);

  /**
   * 북마크된 기사 목록 — feedArticles 없이도 독립적으로 동작.
   * localStorage 캐시 기반이므로 새로고침·API 실패 시에도 유지됨.
   */
  const bookmarkedList = [...cache.values()].filter(a => ids.has(a.urlHash));

  return { bookmarked: ids, bookmarkedList, toggle, isBookmarked };
}

export type BookmarkHook = ReturnType<typeof useBookmarks>;
