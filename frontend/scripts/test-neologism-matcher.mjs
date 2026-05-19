const STOPWORDS = new Set([
  'the', 'a', 'an', 'and', 'or', 'of', 'for', 'to', 'in', 'on', 'with', 'by', 'from',
  'tech', 'technology', 'news', 'guardian', 'verge', 'decoder', 'spectrum', 'venturebeat',
  'techcrunch', 'meta', 'google', 'openai', 'anthropic', 'nvidia', 'ai', 'ml',
]);

const ALLOWLIST = new Set([
  'rag', 'llm', 'slm', 'fine-tuning', 'lora', 'qlora', 'rlhf', 'dpo',
  'prompt injection', 'jailbreak', 'guardrail', 'hallucination',
  'inference', 'token', 'transformer', 'embedding', 'vector db', 'pgvector',
  're-ranking', 'cove', 'hitl', 'agentic ai', 'ai agent', 'mcp',
  'context engineering', 'vibe coding', 'synthetic data', 'model collapse',
  'quantization', 'reasoning model', 'chain of thought', 'multimodal',
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
  { term: 'MCP', explanation: '도구 연결 프로토콜' },
  { term: 'Vector DB', explanation: '벡터 검색 데이터베이스' },
  { term: 'Agentic AI', explanation: '목표를 수행하는 에이전트형 AI' },
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
  ['MCP connects an AI Agent to tools through a Vector DB workflow.', ['MCP', 'Vector DB']],
  ['Agentic AI systems use reasoning models.', ['Agentic AI']],
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
