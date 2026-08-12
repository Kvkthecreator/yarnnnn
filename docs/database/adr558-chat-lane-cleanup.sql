-- ADR-558 — delete chat lanes carrying a birth-persona.
--
-- ✅ APPLIED 2026-08-12 (operator-authorized, run through the ACCESS.md
-- `.secrets.local` path). Result: 19 lanes, 42 session_messages, 33
-- conversation_members deleted. Post-state verified: 56 bound (Studio · Docs ·
-- IMAGES) + 3 derive lanes INTACT, 24 engine-only chat lanes preserved, 0
-- birth-personas remaining.
--
-- The safety check that mattered, run BEFORE the delete: zero of the 19 had
-- more than one human in the cast, so no real multi-party conversation was in
-- the set. Kept here as the record of what was done, and as the shape to reuse
-- if this ever needs repeating.
--
-- ⚠️ IF RE-RUN: the SELECTs are not optional. This is not reversible, and a
-- lane someone actually wanted is worth more than the tidiness.
--
--   psql "$SUPABASE_DB_URL" -f docs/database/adr558-chat-lane-cleanup.sql
--
-- WHAT IS NOT TOUCHED, and why the WHERE clause is shaped this way:
--   * BOUND lanes (Studio · Docs · IMAGES) keep their resident — an app pins a
--     colleague (ADR-467 D1). They are excluded by the artifact_path test.
--   * DERIVE lanes (`Learn from`) are bound too — excluded by derive_recipe.
--   * Any lane with NO agent is already ADR-558-shaped — untouched.
--   * Radar declares its resident in code, not on a lane — unaffected.

-- ---------------------------------------------------------------------------
-- 1. LOOK FIRST — what would go.
-- ---------------------------------------------------------------------------
SELECT
    id,
    context_metadata -> 'lane' ->> 'name'          AS lane_name,
    context_metadata -> 'lane' ->> 'agent'         AS birth_persona,
    context_metadata -> 'lane' ->> 'model'         AS engine,
    status,
    updated_at
FROM chat_sessions
WHERE session_type = 'lane'
  AND context_metadata -> 'lane' ->> 'agent' IS NOT NULL
  AND context_metadata -> 'lane' ->> 'artifact_path' IS NULL   -- not Studio/Docs/IMAGES
  AND context_metadata -> 'lane' ->> 'derive_recipe' IS NULL   -- not a Learn-from lane
ORDER BY updated_at DESC;

-- 2. And the count, plainly.
SELECT count(*) AS chat_lanes_with_a_birth_persona
FROM chat_sessions
WHERE session_type = 'lane'
  AND context_metadata -> 'lane' ->> 'agent' IS NOT NULL
  AND context_metadata -> 'lane' ->> 'artifact_path' IS NULL
  AND context_metadata -> 'lane' ->> 'derive_recipe' IS NULL;

-- ---------------------------------------------------------------------------
-- 3. THE DELETE — uncomment to run, only after reading the SELECT above.
-- ---------------------------------------------------------------------------
-- Order matters: children first. `session_messages` and `conversation_members`
-- reference `chat_sessions(id)`; if either lacks ON DELETE CASCADE the parent
-- delete fails, and deleting children first is correct under both schemas.
--
-- BEGIN;
--
-- WITH doomed AS (
--     SELECT id FROM chat_sessions
--     WHERE session_type = 'lane'
--       AND context_metadata -> 'lane' ->> 'agent' IS NOT NULL
--       AND context_metadata -> 'lane' ->> 'artifact_path' IS NULL
--       AND context_metadata -> 'lane' ->> 'derive_recipe' IS NULL
-- )
-- DELETE FROM session_messages WHERE session_id IN (SELECT id FROM doomed);
--
-- WITH doomed AS (
--     SELECT id FROM chat_sessions
--     WHERE session_type = 'lane'
--       AND context_metadata -> 'lane' ->> 'agent' IS NOT NULL
--       AND context_metadata -> 'lane' ->> 'artifact_path' IS NULL
--       AND context_metadata -> 'lane' ->> 'derive_recipe' IS NULL
-- )
-- DELETE FROM conversation_members WHERE conversation_id IN (SELECT id FROM doomed);
--
-- DELETE FROM chat_sessions
-- WHERE session_type = 'lane'
--   AND context_metadata -> 'lane' ->> 'agent' IS NOT NULL
--   AND context_metadata -> 'lane' ->> 'artifact_path' IS NULL
--   AND context_metadata -> 'lane' ->> 'derive_recipe' IS NULL;
--
-- -- Re-run query 2 here: it must return 0. THEN commit.
-- COMMIT;
