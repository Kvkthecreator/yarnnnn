-- 264 — the desktop-releases bucket admits the host updater's files (ADR-663 D6).
--
-- The updater (src-tauri/src/update.rs) reads a manifest, `latest.json`, and
-- downloads the file it names for its platform: on Windows the NSIS installer
-- the bucket already admits; on macOS a signed `.app.tar.gz`. Both new types
-- are written by scripts/publish-desktop-release.sh alone — the bucket still
-- has no storage.objects policy, so only the service key writes (migration 261).
--
-- The size cap and everything else stand.

UPDATE storage.buckets
SET allowed_mime_types = ARRAY[
  'application/x-apple-diskimage',
  'application/vnd.microsoft.portable-executable',
  'application/gzip',
  'application/json'
]
WHERE id = 'desktop-releases';
