-- 219 — ADR-427 Phase 2: the binary blob lane (Category-1 binary)
--
-- The CAS generalizes from text-addressed to bytes-addressed (ADR-427 D1).
-- `workspace_file_versions.blob_sha` carries an FK to workspace_blobs(sha256),
-- so EVERY revision — text or binary — must have a workspace_blobs row. The
-- binary lane is therefore a MARKER ROW:
--
--   inline text blob:  content = <the text>,  storage_key IS NULL
--   binary blob:       content = '',          storage_key = 'cas/<sha[:2]>/<sha>'
--                      (bytes live in the private `workspace-cas` bucket,
--                       keyed by content address — git's loose-object layout,
--                       ADR-427 D2c/D3)
--
-- This keeps has_blob, FK integrity, dedup, and GC single-table: the blob
-- index is workspace_blobs regardless of where the bytes physically live —
-- physical placement is the DRIVER's business (services/storage_backend.py),
-- invisible above the seam.
--
-- `size_bytes` is GENERATED from octet_length(content) (migration 158) and
-- reads 0 for a marker row, so binary carries its real length in `byte_size`.
-- Effective size = COALESCE(byte_size, size_bytes).

ALTER TABLE workspace_blobs
  ADD COLUMN IF NOT EXISTS storage_key TEXT,
  ADD COLUMN IF NOT EXISTS byte_size BIGINT;

COMMENT ON COLUMN workspace_blobs.storage_key IS
  'ADR-427: non-NULL = bytes live in the object store at this key (binary lane); NULL = inline text in content.';
COMMENT ON COLUMN workspace_blobs.byte_size IS
  'ADR-427: real byte length for external (binary) blobs; inline text uses the generated size_bytes.';

-- The content-addressed store for binary bytes. Private; no MIME allowlist —
-- the CAS is content-agnostic by design (type is DERIVED per ADR-427 D5; the
-- intake gate is the conformance check in code, not bucket config). Access is
-- service-role only (no storage.objects policies for this bucket): serving is
-- signed URLs minted per-request by the API behind the powerbox read-gate.
INSERT INTO storage.buckets (id, name, public)
VALUES ('workspace-cas', 'workspace-cas', false)
ON CONFLICT (id) DO NOTHING;
