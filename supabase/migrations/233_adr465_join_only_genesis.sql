-- 233_adr465_join_only_genesis.sql
-- ADR-465 D2 (ratified 2026-08-03, operator delegation) — join-only genesis.
--
-- Retires the migration-106 auto-mint: `on_auth_user_created` unconditionally
-- inserted an owner workspace for EVERY new auth.users row, below the app —
-- which made join-only arrival impossible (a stranger accepting a share was
-- minted a phantom empty workspace before the share was ever considered,
-- ADR-465 §2). Owner-genesis moves up into the app where it can be
-- conditional: `services.supabase.ensure_owner_workspace`, called from the
-- cold-user door (`GET /api/workspace/state` when the principal resolves NO
-- workspace — no owner row, no grants). A share/invite-first arrival holds a
-- member grant and never triggers it.
--
-- The invariant amends from exactly-one to ZERO-OR-ONE owner workspace per
-- user. Existing rows are untouched; only new sign-ups change behavior.
-- Rollback: re-run migration 106 (trigger + function are self-contained).

DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
DROP FUNCTION IF EXISTS public.handle_new_user();
