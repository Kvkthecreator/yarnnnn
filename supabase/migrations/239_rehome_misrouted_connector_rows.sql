-- Re-home the substrate misrouted by the unscoped owner resolver (2026-08-17).
--
-- `_resolve_owner_workspace_id_cached` lost its `.eq("owner_id", user_id)`
-- filter, so every principal resolved to the OLDEST workspace in the table.
-- Between 02:15 and 02:36 UTC the operator's connector — authenticated as
-- 2abf3f96 (kvkthecreator@gmail.com), who owns d5b9029b — wrote attributed
-- revisions into bf5b25a9, a workspace owned by a DIFFERENT account
-- (67c5c637). The writes succeeded and returned revision ids; the rows are
-- intact, they are simply in the wrong commons.
--
-- This moves ONLY rows that satisfy all three conditions, which together make
-- the misrouting unambiguous:
--   1. workspace_id = bf5b25a9  (the wrongly-resolved destination)
--   2. user_id      = 2abf3f96  (the authoring principal, who has NO ownership
--                                and NO active grant into bf5b25a9 — verified
--                                against principal_grants)
--   3. authored_by LIKE 'yarnnn:mcp%'  (arrived through the connector)
--
-- Condition 2 is what makes this safe rather than a guess: a row authored by a
-- principal with no reach into the workspace holding it cannot legitimately
-- belong there. Rows written by bf5b25a9's actual owner are untouched.
--
-- Verified before writing: no path collision exists at the destination, so no
-- head is overwritten and no revision chain is merged (ADR-209 — chains are
-- appended, never rewritten). The revision ids, authored_by, timestamps and
-- parent pointers are all preserved; only the workspace binding changes.
--
-- Scoped by explicit id rather than a broad predicate, and wrapped in a
-- verification that ABORTS if the affected count is not exactly what the audit
-- found — so a re-run after further drift fails loudly instead of sweeping
-- rows this migration never examined.

DO $$
DECLARE
  v_files   int;
  v_versions int;
  wrong_ws  uuid := 'bf5b25a9-477f-462e-b7f3-65812f489411';
  right_ws  uuid := 'd5b9029b-bd4e-4757-9fcb-e2b139fd4913';
  actor     uuid := '2abf3f96-118b-4987-9d95-40f2d9be9a18';
BEGIN
  -- Fail closed if the authoring principal has since been granted reach into
  -- the workspace: that would make the rows legitimately theirs, and this
  -- migration's premise false.
  IF EXISTS (
    SELECT 1 FROM principal_grants
    WHERE principal_id = actor::text
      AND workspace_id = wrong_ws
      AND status = 'active'
  ) THEN
    RAISE EXCEPTION
      'ABORT: % now holds an active grant into % — the misrouting premise no longer holds',
      actor, wrong_ws;
  END IF;

  -- Content blobs are WORKSPACE-SCOPED (ADR-474: sharing is a grant, never a
  -- byte coincidence), keyed (workspace_id, sha256), and
  -- workspace_file_versions carries an FK onto that pair. So the blobs must
  -- exist at the destination BEFORE the versions move, or the UPDATE violates
  -- workspace_file_versions_blob_sha_fkey — which the dry run caught.
  --
  -- COPY, never move: a blob row belongs to the workspace that holds it, and
  -- the source workspace's own rows may reference it. Verified for these two
  -- shas: zero references from any other principal in bf5b25a9, and neither is
  -- present at the destination yet — so this adds two rows and orphans nothing.
  -- ON CONFLICT DO NOTHING keeps it idempotent if content already coincides.
  INSERT INTO workspace_blobs (workspace_id, sha256, content, storage_key, byte_size)
  SELECT right_ws, b.sha256, b.content, b.storage_key, b.byte_size
    FROM workspace_blobs b
   WHERE b.workspace_id = wrong_ws
     AND b.sha256 IN (
       SELECT DISTINCT v.blob_sha FROM workspace_file_versions v
        WHERE v.workspace_id = wrong_ws
          AND v.user_id = actor
          AND v.blob_sha IS NOT NULL
     )
  ON CONFLICT (workspace_id, sha256) DO NOTHING;

  UPDATE workspace_file_versions
     SET workspace_id = right_ws
   WHERE workspace_id = wrong_ws
     AND user_id = actor
     AND authored_by LIKE 'yarnnn:mcp%';
  GET DIAGNOSTICS v_versions = ROW_COUNT;

  UPDATE workspace_files
     SET workspace_id = right_ws
   WHERE workspace_id = wrong_ws
     AND user_id = actor;
  GET DIAGNOSTICS v_files = ROW_COUNT;

  RAISE NOTICE 're-homed % file row(s) and % revision row(s) from % to %',
    v_files, v_versions, wrong_ws, right_ws;

  -- The audit found exactly 1 live file and 3 revisions. A different count
  -- means the tree moved under us; abort rather than proceed on stale analysis.
  IF v_files <> 1 OR v_versions <> 3 THEN
    RAISE EXCEPTION
      'ABORT: expected 1 file / 3 revisions, found % / % — re-audit before running',
      v_files, v_versions;
  END IF;
END $$;
