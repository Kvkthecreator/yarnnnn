'use client';

/**
 * /text — the TEXT surface route (ADR-571).
 *
 * The prose app: plain-text documents (.md/.markdown/.txt) opened with a
 * cursor, with Editor — the app's name for the designer resident (ADR-562,
 * the Docs/"Writer" shape) — in a bound lane beside the canvas. Every save
 * is a signed revision through the ADR-570 member write door, CAS-guarded,
 * so a connector revising the same file mid-edit surfaces as a conflict
 * that names who moved the head rather than a silent clobber.
 *
 * Docs-shaped by operator direction ("a dedicated app. just like docs"),
 * which re-cut ADR-570's inline-in-Files housing. Unveiled at birth.
 */

import TextSurface from '@/components/text/TextSurface';

export default function TextPage() {
  return <TextSurface />;
}
