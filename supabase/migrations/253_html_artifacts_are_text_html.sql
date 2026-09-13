-- 253 — every `.html` artifact row is typed text/html (2026-09-13)
--
-- `workspace_files.content_type` defaults to text/markdown, and the Studio
-- doors never passed a type, so all 18 live `.html` artifacts on prod (and
-- their trashed siblings) were typed text/markdown. write_revision now derives
-- the type from the path for text writes too (services/authored_substrate.py),
-- which heals a row on its next revision; this closes the rows that will not
-- be written again. Metadata only — no revision is minted, no content moves
-- (the same shape as 252's restamps). Idempotent: a second run finds nothing.
-- `workspace_file_versions` carries no content_type column.
UPDATE workspace_files
   SET content_type = 'text/html'
 WHERE path LIKE '%.html'
   AND content_type = 'text/markdown';
