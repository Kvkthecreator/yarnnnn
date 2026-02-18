-- ADR-059: Simplified Context Model
-- Replaces knowledge_profile, knowledge_styles, knowledge_domains, knowledge_entries
-- with a single flat store: user_context
--
-- Schema design:
-- - One row per (user, key). The key encodes what kind of value it is.
-- - key examples: 'name', 'role', 'company', 'timezone', 'summary',
--                 'tone_slack', 'tone_gmail', 'verbosity_slack', 'verbosity_gmail',
--                 'fact:X', 'preference:X', 'instruction:X'
-- - source: 'user_stated' | 'tp_extracted' | 'document'
--   user_stated  = user typed it in Profile form or Context page
--   tp_extracted = TP wrote it during conversation
--   document     = extracted from uploaded document
-- - confidence: 0.0–1.0. user_stated defaults to 1.0. tp_extracted varies.

create table if not exists user_context (
  id              uuid primary key default gen_random_uuid(),
  user_id         uuid not null references auth.users(id) on delete cascade,
  key             text not null,
  value           text not null,
  source          text not null default 'user_stated'
                    check (source in ('user_stated', 'tp_extracted', 'document')),
  confidence      float not null default 1.0
                    check (confidence >= 0.0 and confidence <= 1.0),
  created_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now(),

  constraint user_context_user_key_unique unique (user_id, key)
);

-- Index for working memory builder (SELECT * WHERE user_id = ?)
create index if not exists user_context_user_id_idx on user_context (user_id);

-- Row-level security
alter table user_context enable row level security;

create policy "Users can manage their own context"
  on user_context
  for all
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);
