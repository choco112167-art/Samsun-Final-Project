import { existsSync, readFileSync } from 'node:fs';
import { resolve } from 'node:path';

const REQUIRED = ['VITE_SUPABASE_URL', 'VITE_SUPABASE_ANON_KEY'];
const ENV_FILES = ['.env.local', '.env.production', '.env'];

function parseEnvFile(path) {
  if (!existsSync(path)) return {};
  const values = {};
  const text = readFileSync(path, 'utf8');
  for (const line of text.split(/\r?\n/)) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith('#')) continue;
    const idx = trimmed.indexOf('=');
    if (idx === -1) continue;
    const key = trimmed.slice(0, idx).trim();
    let value = trimmed.slice(idx + 1).trim();
    if ((value.startsWith('"') && value.endsWith('"')) || (value.startsWith("'") && value.endsWith("'"))) {
      value = value.slice(1, -1);
    }
    values[key] = value;
  }
  return values;
}

const fileEnv = Object.assign(
  {},
  ...ENV_FILES.map(name => parseEnvFile(resolve(process.cwd(), name))),
);

const missing = REQUIRED.filter(key => {
  const value = process.env[key] ?? fileEnv[key] ?? '';
  return !String(value).trim() || String(value).includes('<PASTE_');
});

if (missing.length > 0) {
  console.error('[build-env] Missing required Vite env for Apps in Toss .ait build:');
  for (const key of missing) {
    console.error(`  - ${key}`);
  }
  console.error('');
  console.error('Create frontend/.env.local before building, for example:');
  console.error('  VITE_SUPABASE_URL=https://<project>.supabase.co');
  console.error('  VITE_SUPABASE_ANON_KEY=<anon-key>');
  console.error('  VITE_DEMO_POLISHED_FEED=1');
  console.error('  VITE_HIDE_DEMO_ARTICLES=1');
  process.exit(1);
}

console.log('[build-env] Supabase Vite env OK for .ait build.');
