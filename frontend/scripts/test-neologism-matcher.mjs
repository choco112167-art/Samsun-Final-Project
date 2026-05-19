const STOPWORDS = new Set([
  'the', 'a', 'an', 'and', 'or', 'of', 'for', 'to', 'in', 'on', 'with', 'by', 'from',
  'tech', 'technology', 'news', 'guardian', 'verge', 'decoder', 'spectrum', 'venturebeat',
  'meta', 'google', 'openai', 'ai', 'ml',
]);

const ALLOWLIST = new Set([
  'rag', 'llm', 'fine-tuning', 'prompt injection', 'guardrail', 'hallucination',
  'inference', 'token', 'transformer', 'embedding', 'hitl', 'cove', 're-ranking',
  'pgvector', 'lora',
]);

const entries = [
  { term: 'The', explanation: '잘못 잡히면 안 되는 일반 단어' },
  { term: 'Meta', explanation: '회사명은 발표 모드에서 제외' },
  { term: 'Tech', explanation: '출처명 일부는 제외' },
  { term: 'AI', explanation: '너무 일반적인 단어는 제외' },
  { term: 'RAG', explanation: '검색 증강 생성' },
  { term: 'Prompt Injection', explanation: '프롬프트 주입 공격' },
  { term: 'LLM', explanation: '대규모 언어 모델' },
  { term: 'Guardrail', explanation: '안전 장치' },
  { term: 'Hallucination', explanation: '환각 현상' },
];

function norm(value) {
  return String(value || '').trim().replace(/\s+/g, ' ').toLowerCase();
}

function isBoundaryChar(value) {
  return !/[A-Za-z0-9_가-힣]/u.test(value);
}

function hasBoundary(text, start, end) {
  const prev = start > 0 ? text[start - 1] : '';
  const next = end < text.length ? text[end] : '';
  return (!prev || isBoundaryChar(prev)) && (!next || isBoundaryChar(next));
}

function escapeRegExp(value) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

function variants(term) {
  const out = new Set([term]);
  if (/^[A-Za-z][A-Za-z\s-]+$/.test(term) && !term.toLowerCase().endsWith('s')) out.add(`${term}s`);
  return [...out];
}

function matchTerms(text) {
  const candidates = entries
    .filter(entry => entry.term.length >= 3 && entry.explanation && !STOPWORDS.has(norm(entry.term)) && ALLOWLIST.has(norm(entry.term)))
    .flatMap(entry => variants(entry.term).map(variant => ({ entry, variant })))
    .sort((a, b) => b.variant.length - a.variant.length);
  const found = [];
  const used = new Set();
  for (const candidate of candidates) {
    if (used.has(norm(candidate.entry.term))) continue;
    for (const hit of text.matchAll(new RegExp(escapeRegExp(candidate.variant), 'giu'))) {
      const start = hit.index;
      const end = start + hit[0].length;
      if (!hasBoundary(text, start, end)) continue;
      if (found.some(existing => start < existing.end && end > existing.start)) continue;
      found.push({ term: candidate.entry.term, text: hit[0], start, end });
      used.add(norm(candidate.entry.term));
      break;
    }
  }
  return found.sort((a, b) => a.start - b.start).map(item => item.term);
}

const cases = [
  ['The Guardian Tech reported that Meta released a new model.', []],
  ['This article explains RAG and prompt injection.', ['RAG', 'Prompt Injection']],
  ['LLM guardrails reduce hallucination.', ['LLM', 'Guardrail', 'Hallucination']],
  ['AI is changing the tech industry.', []],
];

for (const [text, expected] of cases) {
  const actual = matchTerms(text);
  if (JSON.stringify(actual) !== JSON.stringify(expected)) {
    console.error('[neologism-matcher-test] failed');
    console.error({ text, expected, actual });
    process.exit(1);
  }
}

console.log('[neologism-matcher-test] passed');
