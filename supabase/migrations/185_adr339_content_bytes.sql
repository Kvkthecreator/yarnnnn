-- ADR-339 D1: working-tree perception economics.
-- ListFiles returns the subtree with metadata; content_bytes makes the
-- 0-byte litter class (f1ef557 defect class) visible in listings without
-- a ReadFile per suspect. Generated column — always consistent with content.

ALTER TABLE workspace_files
  ADD COLUMN content_bytes integer GENERATED ALWAYS AS (octet_length(content)) STORED;

NOTIFY pgrst, 'reload schema';
