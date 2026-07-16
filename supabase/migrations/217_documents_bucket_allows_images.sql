-- 217 — the `documents` bucket accepts images
--
-- THE BUG (operator receipt, 2026-07-16, uploading Lisa's avatar):
--   Failed to upload file: {'statusCode': 415, 'error': 'invalid_mime_type',
--                           'message': mime type image/png is not supported}
--
-- The API was never the problem. `routes/documents.py::_ALLOWED_EXTS` accepts
-- png/jpg/jpeg/webp/gif, and `services/documents.py::upload_mime` sends the
-- real MIME (`image/png`). The wall is one layer down: the `documents` bucket's
-- own `allowed_mime_types` predates image support —
--
--   documents     → {application/pdf, …wordprocessingml.document,
--                    text/plain, text/markdown}          ← no image types
--   agent-outputs → {…, image/png, image/svg+xml, image/jpeg, …}
--
-- so Supabase Storage rejected the object before our code ever saw it.
--
-- ⚠️ THIS IS BIGGER THAN THE AVATAR. The same bucket is the ADR-395 raw lane
-- that PHASE-A IMAGE ATTACHMENTS ride (`services/documents.py::IMAGE_TYPES` →
-- skip projection → signed URL → vision content parts). Those have been broken
-- since 4c6c56d shipped — "attachments: images as vision parts" was gate-green
-- and prod-probed at the API layer, and could never have worked. No gate could
-- see it: the failure lives in Supabase config, not in code. This is exactly
-- the class of bug that only a human clicking the button finds (debt §6.1).
--
-- The four types match `IMAGE_TYPES` in services/documents.py — the one place
-- that decides what an image IS. Keep them in sync; a type accepted there and
-- rejected here is a 415 the member sees and the gates don't.

UPDATE storage.buckets
SET allowed_mime_types = allowed_mime_types || ARRAY[
      'image/png',
      'image/jpeg',   -- covers .jpg + .jpeg (upload_mime normalizes both)
      'image/webp',
      'image/gif'
    ]::text[]
WHERE id = 'documents'
  AND NOT (allowed_mime_types @> ARRAY['image/png']::text[]);
