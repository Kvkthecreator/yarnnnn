-- ADR-059: Drop inference pipeline tables
-- Run AFTER 055 (create user_context) and 056 (data migration).
--
-- What's being removed and why:
--   knowledge_profile  — replaced by user_context keys: name, role, company, timezone, summary
--   knowledge_styles   — replaced by user_context keys: tone_{platform}, verbosity_{platform}
--   knowledge_domains  — removed entirely (domain grouping is a UI concept on deliverables, not a DB concept)
--   knowledge_entries  — replaced by user_context with key = '{type}:{content}'

drop table if exists knowledge_profile cascade;
drop table if exists knowledge_styles cascade;
drop table if exists knowledge_domains cascade;
drop table if exists knowledge_entries cascade;
