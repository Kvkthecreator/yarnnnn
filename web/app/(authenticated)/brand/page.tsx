/**
 * /brand redirect stub.
 *
 * ADR-309 (2026-06-01): `brand` is no longer a kernel surface slug. Brand is
 * not standalone — the Identity surface (IdentityBrandCard) co-renders it.
 * The /brand URL survives only as bookmark-safety transport.
 *
 * ADR-308 (2026-06-01): pure transport — server redirect(), never renders
 * inside the OS shell.
 */

import { redirect } from 'next/navigation';

export default function BrandRedirect() {
  redirect('/identity');
}
