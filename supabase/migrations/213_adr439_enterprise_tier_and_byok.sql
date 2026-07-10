-- Migration 213: the enterprise tier + workspace-scoped BYOK secret (ADR-439 §9)
--
-- ADR-439 makes BYOK an enterprise-tier capability (default-OFF toggle). Two data
-- prerequisites, neither of which is BYOK itself:
--
--   P1 — the `enterprise` tier does not exist. The live tiers are free/starter/pro
--        (ADR-429 §12; `pro` dormant). "BYOK is enterprise-only" is meaningless
--        until an enterprise tier exists. This migration widens the
--        subscription_tier CHECK to admit 'enterprise'. The tier's config (price,
--        allowance, bundle) lives in billing_tiers.TIER_CONFIG — this is the
--        write-boundary guard only, mirroring migration 194's pattern.
--
--   P2 — there is no workspace-scoped secret store. platform_connections is
--        user_id-scoped (account-scoped, ADR-425) — the wrong scope for a
--        workspace-level key. A BYOK key belongs on the workspace, alongside
--        subscription_tier / billing_exempt / balance_usd. Three columns:
--        byok_enabled (the toggle), byok_provider (which provider the key is for),
--        byok_key_encrypted (Fernet ciphertext via TokenManager / the existing
--        INTEGRATION_ENCRYPTION_KEY — no new crypto).
--
-- N=1 / existing-workspace safety: every existing workspace keeps its tier
-- unchanged; byok_enabled defaults false and the key columns default NULL, so the
-- seat-lane key path resolves to the managed default (our keys) — BYTE-IDENTICAL
-- to pre-migration behavior. Nothing routes to a customer key until an enterprise
-- workspace explicitly enables BYOK and stores a key.
--
-- Companion canon: ADR-439 (this), ADR-409 (per-seat Type-B — BYOK draws nothing),
-- ADR-429 §12 (the tier structure this extends), ADR-425 (why platform_connections
-- is the wrong scope for a workspace key).

BEGIN;

-- ── 1. Widen the tier CHECK to admit 'enterprise' ───────────────────────────
-- Mirrors migration 194's constraint pattern. The three prior enum values are
-- untouched (no data migration — every existing row stays valid); 'enterprise'
-- is additive. billing_tiers.normalize_tier still coerces unknowns → free, so
-- the app layer is safe against any stray value; this keeps the column honest at
-- the write boundary.

ALTER TABLE workspaces
  DROP CONSTRAINT IF EXISTS workspaces_subscription_tier_check;
ALTER TABLE workspaces
  ADD CONSTRAINT workspaces_subscription_tier_check
  CHECK (subscription_tier IN ('free', 'starter', 'pro', 'enterprise'));

-- ── 2. Workspace-scoped BYOK secret columns (ADR-439 D1 + §9 P2) ─────────────
-- byok_enabled — the default-OFF toggle. Only meaningful on the enterprise tier
--   (the app gates availability on tier_byok_available); the column itself carries
--   no tier logic.
-- byok_provider — which LLM provider the stored key is for ('anthropic' | 'openai'
--   | 'gemini' | 'deepseek', matching the LANE_MODELS provider prefixes). One key
--   per workspace at launch (a member-override / multi-provider store is deferred,
--   ADR-439 §2 / §8).
-- byok_key_encrypted — Fernet ciphertext (TokenManager.encrypt over
--   INTEGRATION_ENCRYPTION_KEY). NEVER store plaintext; the app is the only
--   decryptor at the router call site.

ALTER TABLE workspaces
  ADD COLUMN IF NOT EXISTS byok_enabled boolean NOT NULL DEFAULT false,
  ADD COLUMN IF NOT EXISTS byok_provider text,
  ADD COLUMN IF NOT EXISTS byok_key_encrypted text;

COMMIT;
