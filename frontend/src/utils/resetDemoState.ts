const DIRECT_KEYS = [
  'samsun_onboarded',
  'samsun_interests',
  'samsun_user_id',
  'user_id',
  'interest_tags',
  'onboarding_completed',
  'onboarded',
  'selectedInterests',
  'preferredTone',
];

const KEY_PATTERNS = [
  'samsun',
  'onboard',
  'interest',
  'user',
  'feed',
  'recommend',
  'article',
  'preferred',
];

export interface DemoResetResult {
  localStorageKeys: string[];
  sessionStorageCleared: boolean;
  indexedDbDeleted: string[];
}

function shouldDeleteKey(key: string): boolean {
  const lowered = key.toLowerCase();
  return DIRECT_KEYS.includes(key) || KEY_PATTERNS.some(pattern => lowered.includes(pattern));
}

async function clearIndexedDb(): Promise<string[]> {
  if (!('indexedDB' in window) || typeof indexedDB.databases !== 'function') return [];

  const deleted: string[] = [];
  try {
    const databases = await indexedDB.databases();
    await Promise.all(databases.map(db => new Promise<void>(resolve => {
      if (!db.name || !shouldDeleteKey(db.name)) {
        resolve();
        return;
      }

      const request = indexedDB.deleteDatabase(db.name);
      request.onsuccess = () => {
        deleted.push(db.name as string);
        resolve();
      };
      request.onerror = () => resolve();
      request.onblocked = () => resolve();
    })));
  } catch (error) {
    console.warn('[SamsunNews] IndexedDB demo reset skipped', error);
  }

  return deleted;
}

export async function resetDemoState(): Promise<DemoResetResult> {
  const beforeKeys = Array.from({ length: localStorage.length }, (_, index) => localStorage.key(index))
    .filter((key): key is string => Boolean(key));
  const keysToDelete = Array.from(new Set([...DIRECT_KEYS, ...beforeKeys.filter(shouldDeleteKey)]));

  console.log('[SamsunNews] demo reset localStorage before', beforeKeys);
  keysToDelete.forEach(key => {
    try {
      localStorage.removeItem(key);
    } catch {
      // Ignore storage access errors in restricted WebView contexts.
    }
  });

  let sessionStorageCleared = false;
  try {
    sessionStorage.clear();
    sessionStorageCleared = true;
  } catch {
    // Ignore storage access errors in restricted WebView contexts.
  }

  const indexedDbDeleted = await clearIndexedDb();
  console.log('[SamsunNews] demo reset removed', {
    localStorageKeys: keysToDelete,
    sessionStorageCleared,
    indexedDbDeleted,
  });
  console.log('[SamsunNews] demo reset localStorage after', Array.from({ length: localStorage.length }, (_, index) => localStorage.key(index)).filter(Boolean));

  return {
    localStorageKeys: keysToDelete,
    sessionStorageCleared,
    indexedDbDeleted,
  };
}

export function goToOnboardingResetUrl(): void {
  const basePath = `${window.location.pathname || '/'}?resetOnboarding=1&t=${Date.now()}`;
  window.location.replace(basePath);
}
