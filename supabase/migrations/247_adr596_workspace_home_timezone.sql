-- 247 — ADR-596 D4: the workspace declares a home timezone.
--
-- The clock's first-class anchor. Shared declarations (recurrences, string
-- cadences, hooks) resolve "9am" against THIS, because a shared clock is a
-- fact about the commons, not about whoever authored the YAML. IANA name
-- ("Asia/Seoul"), never an offset; validated at the API door (pytz), written
-- through the owner's own client so the RLS UPDATE policy (owner-only,
-- mig 002) is the enforcement — same gate as name/icon.
--
-- NULL = not yet declared → scheduling uses UTC, and the settings surface
-- says so rather than pretending a choice was made. No backfill: measured
-- 2026-08-24, ZERO persona/IDENTITY.md files in production declare a
-- timezone, so the prose path this replaces (schedule_utils.get_user_timezone
-- regex-parsing IDENTITY.md — an ADR-254 violation in the scheduling path)
-- has resolved to UTC for every workspace since it was written.
--
-- (The migration-003 digest fossils this column supersedes were already
-- swept by 245 — verified live before writing this file; nothing to drop.)

ALTER TABLE workspaces ADD COLUMN IF NOT EXISTS timezone TEXT;

COMMENT ON COLUMN workspaces.timezone IS
  'ADR-596 D4 — the workspace home timezone (IANA name). NULL = undeclared → UTC. Shared clock declarations resolve against this.';

-- Verify the column landed (the runner's exit code is not verification; this
-- makes the migration itself refuse to report success on a half-applied state).
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'workspaces' AND column_name = 'timezone'
  ) THEN
    RAISE EXCEPTION 'workspaces.timezone did not land';
  END IF;
END $$;
