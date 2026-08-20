/**
 * Legacy /memory route — redirects to /files with IDENTITY.md preselected.
 *
 * ADR-215 R3 (2026-04-24): identity/brand/profile are substrate; the
 * canonical edit surface is Files (/files). This route opens the Files
 * surface with IDENTITY.md already selected.
 *
 * ADR-308 (2026-06-01): pure transport — server redirect(), never renders
 * inside the OS shell.
 *
 * ADR-587: the param is `files.path`, not `path`. Surface params are
 * slug-namespaced (useSurfacePreferences' scopeParamKey), and the reconciler
 * only adopts params matching the foreground slug — a bare `?path=` was left
 * untouched and never read, so this redirect landed on Files with NO
 * selection. Silently: the surface renders its Recents, which looks like a
 * working page.
 */

import { redirect } from 'next/navigation';

export default function MemoryRedirect() {
  redirect('/files?files.path=%2Fworkspace%2Fcontext%2F_shared%2FIDENTITY.md');
}
