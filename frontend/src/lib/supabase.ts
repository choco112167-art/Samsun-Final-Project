import { createClient } from '@supabase/supabase-js';

const SUPABASE_URL = import.meta.env.VITE_SUPABASE_URL as string | undefined;
const SUPABASE_ANON_KEY = import.meta.env.VITE_SUPABASE_ANON_KEY as string | undefined;

function isPlaceholder(value: string | undefined): boolean {
  const v = (value ?? '').trim();
  return !v || v.startsWith('<') || /PASTE_|_HERE|example\.supabase|not-configured/i.test(v);
}

function isLikelySupabaseUrl(value: string | undefined): boolean {
  const v = (value ?? '').trim();
  return /^https:\/\/[a-z0-9-]+\.supabase\.co$/i.test(v);
}

export function getSupabaseConfigIssue(): string | null {
  if (isPlaceholder(SUPABASE_URL)) {
    return 'VITE_SUPABASE_URL이 빌드 시점에 설정되지 않았습니다.';
  }
  if (!isLikelySupabaseUrl(SUPABASE_URL)) {
    return 'VITE_SUPABASE_URL 형식이 올바르지 않습니다. https://<project-ref>.supabase.co 형태여야 합니다.';
  }
  if (isPlaceholder(SUPABASE_ANON_KEY)) {
    return 'VITE_SUPABASE_ANON_KEY가 빌드 시점에 설정되지 않았습니다.';
  }
  return null;
}

const configIssue = getSupabaseConfigIssue();

if (configIssue) {
  console.warn(
    `[supabase] ${configIssue} Supabase reads will fail until env is configured.`,
  );
}

const clientUrl = SUPABASE_URL || 'https://example.supabase.co';
const clientKey = SUPABASE_ANON_KEY || 'anon-key-not-configured';

export const supabase = createClient(clientUrl, clientKey, {
  auth: {
    persistSession: false,
    autoRefreshToken: false,
    detectSessionInUrl: false,
  },
});

export function isSupabaseConfigured(): boolean {
  return !getSupabaseConfigIssue();
}
