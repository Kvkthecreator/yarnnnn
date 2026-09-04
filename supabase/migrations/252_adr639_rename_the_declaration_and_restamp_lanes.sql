-- Migration 252 — ADR-639 D4/D6: the one live declaration takes the concept's
-- name; the lanes stamped for the deleted app re-stamp to the app their
-- artifact belongs to.
--
-- ⚠️ APPLY AFTER THE ADR-639 DEPLOY (migration 251 goes BEFORE it). The new
-- code discovers `_standing.yaml`; the old code discovered `_string.yaml`.
-- Between deploy and this migration the declaration is simply undiscovered
-- for a few minutes (its next fire is 04:00Z daily); after it, the new code
-- finds it. Applying this BEFORE the deploy would have the OLD code lose the
-- declaration until the deploy lands — same gap, wrong order for a rollback.
--
-- MEASURED BEFORE WRITING (production, 2026-09-04, PostgREST exact counts):
--   workspace_files          _string.yaml                 1 row
--   workspace_file_versions  path = …/_string.yaml        (moves with it — the
--                                                          path is the file's
--                                                          identity; history
--                                                          follows the file)
--   tasks                    kind='string'                1 row
--   chat_sessions            context_metadata.lane.app    (counted by the
--                            = 'strings'                   RETURNING below)
--   workspace_file_versions  authored_by='system:strings' 2 rows — UNTOUCHED
--   execution_events         funnel_decision='string'    18 rows — UNTOUCHED
--   conversation_members     agent_slug='supervisor'      7 rows — UNTOUCHED
--   session_messages         metadata.agent_slug=…        5 rows — UNTOUCHED
-- The ledger, the cast and the transcript are never rewritten (ADR-460 D2):
-- `system:strings` is display-resolved ("Standing work"), `supervisor` is
-- resolved by HISTORICAL_AGENT_NAMES, and the cast re-seats at read
-- (ADR-614) once its lane derives a resident again — which is what the
-- re-stamp below gives it.
--
-- WHY `text`: the deleted app's lanes were bound to the kept file
-- (`{folder}/{target}`), and every such file in production is prose. A Text
-- lane on that path IS the same conversation with the app that owns prose
-- (ADR-602 D7 — the app follows the artifact); its cast's sole `supervisor`
-- row re-seats as Editor at read. A non-prose target would have no owning
-- app; there are none, and a stamp for one would be a guess, so the
-- predicate is on the artifact's extension, not blanket.
--
-- Each statement self-commits (the migration-self-commits lesson); each is
-- idempotent on a second run (its WHERE finds nothing).

UPDATE workspace_files
   SET path = regexp_replace(path, '/_string\.yaml$', '/_standing.yaml')
 WHERE path LIKE '/workspace/%/\_string.yaml';

UPDATE workspace_file_versions
   SET path = regexp_replace(path, '/_string\.yaml$', '/_standing.yaml')
 WHERE path LIKE '/workspace/%/\_string.yaml';

UPDATE tasks
   SET kind = 'standing',
       slug = regexp_replace(slug, '^string:', 'standing:'),
       declaration_path = regexp_replace(declaration_path, '/_string\.yaml$', '/_standing.yaml')
 WHERE kind = 'string';

UPDATE chat_sessions
   SET context_metadata = jsonb_set(context_metadata, '{lane,app}', '"text"'::jsonb)
 WHERE context_metadata -> 'lane' ->> 'app' = 'strings'
   AND lower(coalesce(context_metadata -> 'lane' ->> 'artifact_path', '')) ~ '\.(md|txt)$'
RETURNING id, context_metadata -> 'lane' ->> 'artifact_path' AS artifact_path;
