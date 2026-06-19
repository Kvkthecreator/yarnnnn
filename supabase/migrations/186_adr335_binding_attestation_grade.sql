-- ADR-335 derived-trust-tier amendment (ratified 2026-06-19) — Crawl-B Increment A, step 1.
-- The binding row gains two facts, NO policy column. Transport trust-tier is DERIVED
-- from flow-participation at evaluation time (required_tier = HIGH if the read feeds
-- ground-truth/a-primary-action else OPEN); the tier is never stored (DP7 — only the
-- flow declarations + the binding's attestation_grade are stored).
--
-- attestation_grade: the ADR-330 D2 enum (platform > operator > agent), derived from
--   provenance. Every EXISTING connection is a first-party API read with the operator's
--   own token = attestation 'platform' (gold) BY DEFINITION (api/services/outcomes/base.py:59).
--   The backfill default is therefore not a decision — it's the correct grade. Because gold
--   satisfies every tier, the subsequent gate generalization (orchestration.py:1363) cannot
--   regress any capability that fires today: the admitted set is a strict superset.
--
-- watch_id: nullable. NULL = capability binding (ADR-207: operator connects a platform ->
--   capabilities unlock, connection-scoped, serves any recurrence declaring the capability).
--   SET = watch binding (ADR-335 D5: a declared watch resolves a transport, watch-scoped).
--   The two binding shapes coexist permanently and correctly (amendment §E.A / Open Q A
--   closed NO) — opposite sides of the declaration/transport boundary, not transitional.

ALTER TABLE platform_connections
  ADD COLUMN attestation_grade text NOT NULL DEFAULT 'platform'
    CHECK (attestation_grade IN ('platform', 'operator', 'agent'));

ALTER TABLE platform_connections
  ADD COLUMN watch_id uuid NULL;

COMMENT ON COLUMN platform_connections.attestation_grade IS
  'ADR-335/ADR-330 trust grade (platform>operator>agent), derived from provenance. '
  'The derived-tier gate admits a binding iff grade >= required_tier(read, program). '
  'Existing first-party connections backfill to platform (gold).';

COMMENT ON COLUMN platform_connections.watch_id IS
  'ADR-335 D5: NULL = capability binding (ADR-207, connection-scoped); '
  'SET = watch binding (D5, watch-scoped). Two binding shapes, one table.';

NOTIFY pgrst, 'reload schema';
