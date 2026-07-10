-- 211_powerbox_read_write_scopes.sql
-- THE POWERBOX (2026-07-10) — access(2)'s open-fact half, built future-proof.
--
-- ADR-373 shipped a single `scopes text[]` per grant: a flat list of TOP-LEVEL
-- WRITE roots, enforced on writes only. That was a class-granular, write-only,
-- one-axis stub. This migration lifts the grant model to the shape a
-- multi-principal commons actually needs at scale:
--
--   1. TWO INDEPENDENT AXES — read_scopes + write_scopes. A read-only auditor, a
--      contractor who reads broadly but writes one folder, an external AI that
--      sees much but changes little: all representable. read ⊇ write is now a
--      DEFAULT (the backfill), never a hard constraint.
--
--   2. OBJECT-GRANULARITY — each element is a PATH PREFIX at ARBITRARY DEPTH
--      ('operation/', 'operation/marketing/', 'operation/reports/q3.md'), not a
--      top-level root. The matcher is longest-prefix; teams share folders and
--      files, not kernel roots. (macOS security-scoped-bookmark granularity.)
--
--   3. THREE-STATE POLARITY per axis (the powerbox polarity fix, preserved):
--      NULL → class default (unconfigured) · [] → EXPLICIT deny-all (an empty
--      allow-list) · [..] → exactly those prefixes. NULL ≠ [].
--
-- BACKFILL (byte-identical): the live `scopes` becomes BOTH read_scopes AND
-- write_scopes (read ⊇ write, equal — today's exact behavior). Every live grant
-- is NULL-scoped (owner/member/foreign-llm, 15 rows @ 2026-07-10), so the
-- backfill writes NULL→NULL on both axes: the class-default fall-through is
-- unchanged. Any future [] or [..] is copied faithfully.
--
-- TRANSITION: `scopes` is KEPT as a DEPRECATED MIRROR (not dropped) so a
-- deploy-window with old code reading `scopes` still works. New code reads
-- read_scopes/write_scopes and writes all three (mirror scopes := write_scopes)
-- until the mirror is dropped in a follow-up migration once no reader remains.
--
-- Idempotent: IF NOT EXISTS guards; the backfill only touches rows where the new
-- columns are still absent-of-value (safe to re-run).

-- -----------------------------------------------------------------------------
-- 1. The two axes (path-prefix arrays, arbitrary depth)
-- -----------------------------------------------------------------------------
ALTER TABLE principal_grants
    ADD COLUMN IF NOT EXISTS read_scopes  text[],
    ADD COLUMN IF NOT EXISTS write_scopes text[];

COMMENT ON COLUMN principal_grants.read_scopes IS
    'Powerbox read axis (2026-07-10). Path prefixes at ARBITRARY DEPTH the '
    'principal may READ. NULL → class default; [] → explicit deny-all; '
    '[..] → exactly those prefixes (longest-prefix match). Independent of '
    'write_scopes (read ⊇ write is the backfill default, not a constraint).';

COMMENT ON COLUMN principal_grants.write_scopes IS
    'Powerbox write axis (2026-07-10). Path prefixes at ARBITRARY DEPTH the '
    'principal may WRITE. Same three-state polarity as read_scopes. Supersedes '
    'the flat top-level-root `scopes` column (kept as a deprecated mirror).';

COMMENT ON COLUMN principal_grants.scopes IS
    'DEPRECATED (2026-07-10, powerbox) — superseded by write_scopes. Kept as a '
    'transition mirror (= write_scopes) for deploy-window readers; drop once no '
    'reader remains. Was: flat top-level WRITE roots, ADR-373 D3.';

-- -----------------------------------------------------------------------------
-- 2. Backfill — read ⊇ write, byte-identical (scopes → both axes)
-- -----------------------------------------------------------------------------
-- Only backfill rows not yet migrated (both new columns still NULL AND the old
-- column carries the source of truth). This copies NULL→NULL (the 15 live
-- rows), [] → [] (deny-all, none live yet), [..] → [..] faithfully. Because a
-- genuine NULL scopes row is indistinguishable from an unmigrated row, we gate
-- the backfill on a one-time marker: run it unconditionally ONCE. Re-running is
-- safe — it re-copies scopes into the axes, which for an already-migrated row
-- (where a later narrow may have set the axes independently) we must NOT clobber.
-- So: only set an axis when it IS NULL and scopes IS DISTINCT (covers the
-- NULL-scopes rows too, since NULL→NULL is a no-op write we skip).

-- Rows WITH an explicit scopes value ([] or [..]): mirror into both axes if the
-- axis is still NULL (unmigrated). NULL-scopes rows need no write (NULL is the
-- absent default on the new columns already).
UPDATE principal_grants
   SET read_scopes  = scopes
 WHERE scopes IS NOT NULL
   AND read_scopes IS NULL;

UPDATE principal_grants
   SET write_scopes = scopes
 WHERE scopes IS NOT NULL
   AND write_scopes IS NULL;

-- =============================================================================
-- Verification (manual):
--   SELECT column_name FROM information_schema.columns
--     WHERE table_name='principal_grants'
--       AND column_name IN ('read_scopes','write_scopes','scopes');
--   -- Expect all three.
--
--   -- Byte-identity: every live grant is NULL-scoped → NULL on both axes →
--   -- class-default fall-through unchanged.
--   SELECT count(*)                                        AS total,
--          count(*) FILTER (WHERE scopes IS NULL)          AS scopes_null,
--          count(*) FILTER (WHERE read_scopes IS NULL)     AS read_null,
--          count(*) FILTER (WHERE write_scopes IS NULL)    AS write_null
--     FROM principal_grants WHERE status='active';
--   -- Expect total == scopes_null == read_null == write_null (all 15 NULL).
-- =============================================================================
