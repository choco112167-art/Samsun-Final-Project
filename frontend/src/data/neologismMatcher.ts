import type { NeologismEntry } from './api';

export const NEOLOGISM_STOPWORDS = [
  'the',
  'a',
  'an',
  'and',
  'or',
  'of',
  'for',
  'to',
  'in',
  'on',
  'with',
  'by',
  'from',
  'tech',
  'technology',
  'news',
  'guardian',
  'verge',
  'decoder',
  'spectrum',
  'venturebeat',
  'meta',
  'google',
  'openai',
  'ai',
  'ml',
];

export const DEMO_NEOLOGISM_ALLOWLIST = [
  'RAG',
  'LLM',
  'Fine-tuning',
  'Prompt Injection',
  'Guardrail',
  'Hallucination',
  'Inference',
  'Token',
  'Transformer',
  'Embedding',
  'HITL',
  'CoVe',
  'Re-ranking',
  'pgvector',
  'LoRA',
];

const SOURCE_PHRASE_BLACKLIST = [
  'The Guardian Tech',
  'The Verge',
  'MIT Technology Review',
  'IEEE Spectrum',
  'VentureBeat AI',
  'TechCrunch',
  'The Decoder',
  'Hacker News',
];

const DEMO_ALLOWLIST_KEYS = new Set(DEMO_NEOLOGISM_ALLOWLIST.map(normalizeKey));
const STOPWORD_KEYS = new Set(NEOLOGISM_STOPWORDS.map(normalizeKey));
const SOURCE_PHRASE_KEYS = new Set(SOURCE_PHRASE_BLACKLIST.map(normalizeKey));

export interface NeologismMatch {
  start: number;
  end: number;
  text: string;
  entry: NeologismEntry;
}

export interface NeologismSegment {
  text: string;
  entry?: NeologismEntry;
}

export interface NeologismMatchOptions {
  demoMode?: boolean;
  maxMatches?: number;
}

function normalizeKey(value: string): string {
  return value.trim().replace(/\s+/g, ' ').toLocaleLowerCase();
}

function displayExplanation(entry: NeologismEntry): string {
  return entry.explanation?.trim() ?? '';
}

function isBoundaryChar(value: string): boolean {
  return !/[A-Za-z0-9_가-힣]/u.test(value);
}

function hasWordBoundary(text: string, start: number, end: number): boolean {
  const prev = start > 0 ? text[start - 1] : '';
  const next = end < text.length ? text[end] : '';
  return (!prev || isBoundaryChar(prev)) && (!next || isBoundaryChar(next));
}

function escapeRegExp(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

function termVariants(term: string): string[] {
  const normalized = term.trim().replace(/\s+/g, ' ');
  if (!normalized) return [];
  const variants = new Set([normalized]);
  if (/^[A-Za-z][A-Za-z\s-]+$/.test(normalized) && !normalized.toLocaleLowerCase().endsWith('s')) {
    variants.add(`${normalized}s`);
  }
  return [...variants];
}

export function isHighlightableNeologism(entry: NeologismEntry, demoMode = false): boolean {
  const term = entry.term?.trim() ?? '';
  const key = normalizeKey(term);
  if (!term || term.length < 3) return false;
  if (!displayExplanation(entry)) return false;
  if (STOPWORD_KEYS.has(key)) return false;
  if (SOURCE_PHRASE_KEYS.has(key)) return false;
  if (demoMode && !DEMO_ALLOWLIST_KEYS.has(key)) return false;
  return true;
}

export function buildNeologismMatches(
  text: string,
  entries: NeologismEntry[],
  options: NeologismMatchOptions = {},
): NeologismMatch[] {
  const maxMatches = Math.max(0, options.maxMatches ?? 4);
  if (!text || maxMatches === 0) return [];

  const byTerm = new Map<string, NeologismEntry>();
  for (const entry of entries) {
    if (!isHighlightableNeologism(entry, options.demoMode)) continue;
    const key = normalizeKey(entry.term);
    if (!byTerm.has(key)) byTerm.set(key, entry);
  }

  const candidates = [...byTerm.values()]
    .flatMap(entry => termVariants(entry.term).map(variant => ({ entry, variant })))
    .sort((a, b) => b.variant.length - a.variant.length);

  const matches: NeologismMatch[] = [];
  const usedTerms = new Set<string>();

  for (const candidate of candidates) {
    if (matches.length >= maxMatches) break;
    const termKey = normalizeKey(candidate.entry.term);
    if (usedTerms.has(termKey)) continue;
    const pattern = new RegExp(escapeRegExp(candidate.variant), 'giu');
    for (const match of text.matchAll(pattern)) {
      const start = match.index ?? -1;
      if (start < 0) continue;
      const matchedText = match[0];
      const end = start + matchedText.length;
      if (!hasWordBoundary(text, start, end)) continue;
      const overlaps = matches.some(existing => start < existing.end && end > existing.start);
      if (overlaps) continue;
      matches.push({ start, end, text: matchedText, entry: candidate.entry });
      usedTerms.add(termKey);
      break;
    }
  }

  return matches.sort((a, b) => a.start - b.start);
}

export function segmentNeologismText(
  text: string,
  entries: NeologismEntry[],
  options: NeologismMatchOptions = {},
): NeologismSegment[] {
  const matches = buildNeologismMatches(text, entries, options);
  if (matches.length === 0) return [{ text }];

  const segments: NeologismSegment[] = [];
  let cursor = 0;
  for (const match of matches) {
    if (match.start > cursor) segments.push({ text: text.slice(cursor, match.start) });
    segments.push({ text: text.slice(match.start, match.end), entry: match.entry });
    cursor = match.end;
  }
  if (cursor < text.length) segments.push({ text: text.slice(cursor) });
  return segments;
}
