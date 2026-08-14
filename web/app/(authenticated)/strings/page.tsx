'use client';

/**
 * /strings — the STRINGS surface route (ADR-569).
 *
 * The maintained file, kept by Keeper: the member designates a file (the
 * designation is a "string"), declares what it must stay true to
 * (CONTRACT.md) and where currency comes from (_string.yaml), and the
 * standing loop keeps the head current while their corrections compound.
 * This window is Keeper's desk: the string roster + the composed view (file
 * canvas · what changed · setup · consumers) — a lazy projection over
 * substrate + ledger, never stored state.
 *
 * launcher_tier starts search-only (registration ≠ unveil — the ADR-486 D7
 * rule; the D8 falsifiers gate promotion).
 */

import StringsSurface from '@/components/strings/StringsSurface';

export default function StringsPage() {
  return <StringsSurface />;
}
