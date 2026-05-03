'use client';

/**
 * ADR-246: Reviewer persona name resolution.
 *
 * Reads /workspace/review/IDENTITY.md and extracts the operator-authored
 * persona name so ReviewerCard can show "Simons approved" instead of
 * "AI Reviewer approved".
 *
 * Resolution rules (in order):
 * 1. First `# ` heading line → strip `# ` prefix → use as persona name
 * 2. File missing or empty → return null (caller falls back to generic label)
 * 3. File is a skeleton/template (contains "_(empty" or "template") → return null
 *
 * Kept intentionally thin — no composition, no inference. Just a name
 * extracted from the operator-authored IDENTITY.md per ADR-246 D2.
 */

import { useState, useEffect } from 'react';
import { api } from '@/lib/api/client';

const REVIEWER_IDENTITY_PATH = '/workspace/review/IDENTITY.md';

/** Markers that indicate a skeleton/template file with no real persona yet. */
const SKELETON_MARKERS = ['_(empty', '(template)', '# Reviewer Identity — (template)'];

function extractPersonaName(content: string): string | null {
  if (!content || !content.trim()) return null;

  // Reject skeleton content
  for (const marker of SKELETON_MARKERS) {
    if (content.includes(marker)) return null;
  }

  // Extract first # heading
  const lines = content.split('\n');
  for (const line of lines) {
    const trimmed = line.trim();
    if (trimmed.startsWith('# ')) {
      const name = trimmed.slice(2).trim();
      // Reject generic/default headings
      if (
        name.toLowerCase().includes('reviewer identity') ||
        name.toLowerCase().includes('template') ||
        name.length < 2
      ) {
        return null;
      }
      return name;
    }
  }
  return null;
}

/**
 * Hook that resolves the operator-authored Reviewer persona name.
 * Returns null if the persona hasn't been authored yet (skeleton state).
 * Fetches once per session; result is stable.
 */
export function useReviewerPersona(): string | null {
  const [personaName, setPersonaName] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    api.workspace.getFile(REVIEWER_IDENTITY_PATH)
      .then((file) => {
        if (cancelled) return;
        const name = extractPersonaName(file?.content ?? '');
        setPersonaName(name);
      })
      .catch(() => {
        // Non-fatal — IDENTITY.md may not exist yet; fall back to generic label
      });
    return () => { cancelled = true; };
  }, []);

  return personaName;
}
