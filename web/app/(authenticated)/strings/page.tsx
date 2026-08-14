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
 * Unveiled to primary + the Dock 2026-08-14, same day as the build (operator
 * decision — the Radar precedent). The D8 falsifiers stay armed as measures
 * of the standing loop, no longer as the unveil's gate.
 */

import StringsSurface from '@/components/strings/StringsSurface';

export default function StringsPage() {
  return <StringsSurface />;
}
