-- ADR-059: Data migration
-- Migrate stated fields from knowledge_profile → user_context
-- Migrate user_stated entries from knowledge_entries → user_context
-- Migrate stated_preferences from knowledge_styles → user_context
--
-- Inferred fields are NOT migrated — they were unreliable anyway (see ADR-059).
-- knowledge_domains is NOT migrated — it's a UI concept, not data.

-- ─── 1. Migrate knowledge_profile → user_context ─────────────────────────────
-- Only stated_* fields. Skip nulls.

insert into user_context (user_id, key, value, source, confidence)
select user_id, 'name', stated_name, 'user_stated', 1.0
from knowledge_profile
where stated_name is not null and stated_name <> ''
on conflict (user_id, key) do update
  set value = excluded.value,
      source = excluded.source,
      updated_at = now();

insert into user_context (user_id, key, value, source, confidence)
select user_id, 'role', stated_role, 'user_stated', 1.0
from knowledge_profile
where stated_role is not null and stated_role <> ''
on conflict (user_id, key) do update
  set value = excluded.value,
      source = excluded.source,
      updated_at = now();

insert into user_context (user_id, key, value, source, confidence)
select user_id, 'company', stated_company, 'user_stated', 1.0
from knowledge_profile
where stated_company is not null and stated_company <> ''
on conflict (user_id, key) do update
  set value = excluded.value,
      source = excluded.source,
      updated_at = now();

insert into user_context (user_id, key, value, source, confidence)
select user_id, 'timezone', stated_timezone, 'user_stated', 1.0
from knowledge_profile
where stated_timezone is not null and stated_timezone <> ''
on conflict (user_id, key) do update
  set value = excluded.value,
      source = excluded.source,
      updated_at = now();

insert into user_context (user_id, key, value, source, confidence)
select user_id, 'summary', stated_summary, 'user_stated', 1.0
from knowledge_profile
where stated_summary is not null and stated_summary <> ''
on conflict (user_id, key) do update
  set value = excluded.value,
      source = excluded.source,
      updated_at = now();


-- ─── 2. Migrate knowledge_styles → user_context ──────────────────────────────
-- Only stated_preferences.tone and stated_preferences.verbosity. Skip inferred.

insert into user_context (user_id, key, value, source, confidence)
select
  user_id,
  'tone_' || platform,
  stated_preferences->>'tone',
  'user_stated',
  1.0
from knowledge_styles
where stated_preferences->>'tone' is not null
  and stated_preferences->>'tone' <> ''
on conflict (user_id, key) do update
  set value = excluded.value,
      source = excluded.source,
      updated_at = now();

insert into user_context (user_id, key, value, source, confidence)
select
  user_id,
  'verbosity_' || platform,
  stated_preferences->>'verbosity',
  'user_stated',
  1.0
from knowledge_styles
where stated_preferences->>'verbosity' is not null
  and stated_preferences->>'verbosity' <> ''
on conflict (user_id, key) do update
  set value = excluded.value,
      source = excluded.source,
      updated_at = now();


-- ─── 3. Migrate knowledge_entries → user_context ─────────────────────────────
-- Only is_active entries with user_stated or manual source.
-- key = '{entry_type}:{content truncated to 80 chars to make a stable key}'
-- We use a short hash-like key derived from content since entries have free-form content.
-- Use entry_type + first 60 chars of content as the key (deduplication handled by unique constraint).

insert into user_context (user_id, key, value, source, confidence)
select
  user_id,
  entry_type || ':' || left(regexp_replace(content, '[^a-zA-Z0-9_\- ]', '', 'g'), 60),
  content,
  case
    when source in ('manual', 'user_stated') then 'user_stated'
    else 'tp_extracted'
  end,
  coalesce(importance, 0.5)
from knowledge_entries
where is_active = true
  and content is not null
  and content <> ''
on conflict (user_id, key) do nothing;  -- Skip if key collision (prefer existing)
