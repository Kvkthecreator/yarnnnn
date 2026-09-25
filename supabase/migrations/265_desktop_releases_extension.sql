-- 265 — the desktop-releases bucket admits the Chrome extension's manual-install zip
-- (ADR-662 Accepted, ADR-664 Amendment 2).
--
-- Until the Chrome Web Store listing is approved, a member installs the extension
-- by hand from Settings → Your browser: a zip of `extension/` (keeping the
-- manifest's `key`, so it is the same extension id the website talks to),
-- written by `scripts/package-extension.sh manual` alone — still no
-- storage.objects policy, so only the service key writes (migration 261).

UPDATE storage.buckets
SET allowed_mime_types = ARRAY[
  'application/x-apple-diskimage',
  'application/vnd.microsoft.portable-executable',
  'application/gzip',
  'application/json',
  'application/zip'
]
WHERE id = 'desktop-releases';
