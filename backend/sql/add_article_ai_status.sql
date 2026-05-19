-- Optional AI output worker status columns for articles.
-- Run this in Supabase SQL Editor before enabling ai_status-based operations.

alter table public.articles
  add column if not exists ai_status text not null default 'pending'
    check (ai_status in ('pending', 'processing', 'completed', 'failed', 'skipped')),
  add column if not exists ai_provider text,
  add column if not exists ai_model text,
  add column if not exists ai_generated_at timestamptz,
  add column if not exists ai_error text,
  add column if not exists content_source text,
  add column if not exists content_chars integer,
  add column if not exists translation_chars integer;

update public.articles
set
  ai_status = case
    when coalesce(nullif(trim(translation), ''), '') <> ''
     and coalesce(nullif(trim(summary_formal), ''), '') <> ''
     and coalesce(nullif(trim(summary_casual), ''), '') <> ''
      then 'completed'
    else 'pending'
  end,
  content_chars = length(coalesce(content, '')),
  translation_chars = length(coalesce(translation, ''))
where ai_status is null
   or content_chars is null
   or translation_chars is null;

create index if not exists idx_articles_ai_status_published_at
  on public.articles (ai_status, published_at desc);
