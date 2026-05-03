import {
  Storage,
  generateHapticFeedback,
  getDeviceId,
  openURL,
} from '@apps-in-toss/web-framework';

const USER_ID_KEY = 'samsun_user_id';

function browserFallbackUserId(): string {
  const existing = localStorage.getItem(USER_ID_KEY);
  if (existing) return existing;

  const id =
    typeof crypto !== 'undefined' && 'randomUUID' in crypto
      ? `user_${crypto.randomUUID()}`
      : `user_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
  localStorage.setItem(USER_ID_KEY, id);
  return id;
}

export function getSamsunUserId(): string {
  try {
    const deviceId = getDeviceId();
    if (deviceId) {
      const id = `toss_${deviceId}`;
      localStorage.setItem(USER_ID_KEY, id);
      return id;
    }
  } catch {
    // Toss bridge is only available inside the Toss app sandbox.
  }

  return browserFallbackUserId();
}

export async function tossStorageGet(key: string): Promise<string | null> {
  try {
    return await Storage.getItem(key);
  } catch {
    return localStorage.getItem(key);
  }
}

export async function tossStorageSet(key: string, value: string): Promise<void> {
  try {
    await Storage.setItem(key, value);
  } catch {
    localStorage.setItem(key, value);
  }
}

export async function tossHaptic(type: 'tickWeak' | 'tickMedium' = 'tickWeak'): Promise<void> {
  try {
    await generateHapticFeedback({ type });
  } catch {
    // Haptics are best-effort and unavailable in normal browsers.
  }
}

export async function tossOpenURL(url: string): Promise<void> {
  try {
    await openURL(url);
  } catch {
    window.open(url, '_blank', 'noopener,noreferrer');
  }
}
