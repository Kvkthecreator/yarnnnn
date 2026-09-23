-- 261 — the desktop app's installers live in our own storage (ADR-661 §7q).
--
-- A PUBLIC bucket: www.yarnnn.com/download/{platform} redirects to
-- /storage/v1/object/public/desktop-releases/<name>, which anyone can fetch
-- without a token — a download link a stranger opens cannot carry one.
--
-- Written by the service role ONLY: there are no storage.objects policies for
-- this bucket, so an anon or member key can read it (public) and write nothing.
-- The one writer is scripts/publish-desktop-release.sh. This is also why a
-- public bucket here does not reopen the question of members hosting
-- executables on our domain — no member path can put a file in it.
--
-- The size cap is well above the ~5 MB installers (the host carries no web
-- code, ADR-663 D1) and low enough that a wrong file cannot land by accident.
-- The MIME roster is exactly what the publish script sends.

INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES (
  'desktop-releases',
  'desktop-releases',
  true,
  104857600,
  ARRAY['application/x-apple-diskimage', 'application/vnd.microsoft.portable-executable']
)
ON CONFLICT (id) DO NOTHING;
