-- Migration 208 — ADR-423: revision_kind on the authored-substrate ledger.
--
-- The observation/derivation distinction (ADR-376 DP32 / ADR-384 D3) becomes a
-- COLUMN on the revision chain instead of a path-prefix (`inbound/`) + a content
-- frontmatter string (`derived_from:`). This is what lets the `inbound/`
-- DIRECTORY dissolve: a raw arrival is no longer distinguished by WHERE it sits
-- but by WHAT it is — `revision_kind='observation'` — so the two raw lanes
-- (uploads/ + inbound/) can unify under one Downloads/ anchor (the Files-model
-- note, 2026-07-09).
--
-- Value set:
--   'authored'    → an ordinary attributed revision (the DEFAULT — every
--                   existing revision reads as this; NO backfill needed)
--   'observation' → a retained raw intake, immutable-by-intent (ADR-376):
--                   MCP remember, connector capture, web watches
--   'derivation'  → a derived act citing an observation. RESERVED — written by
--                   NO live code this pass (the MCP-remember derive step is a
--                   prompt contract, not deterministic code). Lands when a real
--                   derive step exists (ADR-423 §7 second pass).
--
-- Additive + legacy-safe (the 193_adr393_capture_kind.sql pattern): NOT NULL
-- DEFAULT means no row is ever NULL and every pre-migration revision reads as
-- 'authored'. No partial index this pass — nothing queries BY kind yet (trace
-- reads the column per-revision after a path resolve, not as a filter); add one
-- when a kind-filtered query appears.

ALTER TABLE workspace_file_versions
    ADD COLUMN IF NOT EXISTS revision_kind text NOT NULL DEFAULT 'authored';

COMMENT ON COLUMN workspace_file_versions.revision_kind IS
    'ADR-423: authored (ordinary revision, DEFAULT) | observation (retained raw intake, ADR-376) | derivation (RESERVED — derived act citing an observation, no live writer yet). NULL impossible (NOT NULL DEFAULT); pre-migration rows read authored.';
