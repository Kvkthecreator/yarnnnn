/**
 * Legacy /memory route — redirects to /files with IDENTITY.md preselected.
 *
 * ADR-215 R3 (2026-04-24): identity/brand/profile are substrate; the
 * canonical edit surface is Files (/files). This route opens the Files
 * surface with IDENTITY.md already selected.
 *
 * ADR-308 (2026-06-01): pure transport — server redirect(), never renders
 * inside the OS shell.
 */

import { redirect } from 'next/navigation';

export default function MemoryRedirect() {
  redirect('/files?path=%2Fworkspace%2Fcontext%2F_shared%2FIDENTITY.md');
}
