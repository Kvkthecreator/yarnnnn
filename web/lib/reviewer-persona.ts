'use client';

/**
 * ADR-246: Reviewer persona name resolution.
 *
 * Reads /workspace/persona/IDENTITY.md and extracts the operator-authored
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
 *
 * Module-level singleton cache: the persona name is workspace-stable
 * within a session, so a single fetch (deduped across all hook callers)
 * is correct. Without this dedupe, every chat message row mounts the
 * hook → fires its own fetch, producing tens-of-fetches-per-second
 * loops as the conversation re-renders.
 */

import { useState, useEffect } from 'react';
import { api } from '@/lib/api/client';

const REVIEWER_IDENTITY_PATH = '/workspace/persona/IDENTITY.md';

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

// ---------------------------------------------------------------------------
// Module-level singleton cache + subscriber pattern
// ---------------------------------------------------------------------------
// One in-flight fetch shared across all hook callers; one cached result;
// component subscribers notified when the result resolves.

let cachedPersonaName: string | null = null;
let resolved = false;
let inFlight: Promise<string | null> | null = null;
const subscribers = new Set<(name: string | null) => void>();

async function fetchPersonaOnce(): Promise<string | null> {
  if (resolved) return cachedPersonaName;
  if (inFlight) return inFlight;

  inFlight = (async () => {
    try {
      const file = await api.workspace.getFile(REVIEWER_IDENTITY_PATH);
      const name = extractPersonaName(file?.content ?? '');
      cachedPersonaName = name;
    } catch {
      cachedPersonaName = null;
    } finally {
      resolved = true;
      inFlight = null;
      // Notify all subscribers
      subscribers.forEach((cb) => cb(cachedPersonaName));
    }
    return cachedPersonaName;
  })();

  return inFlight;
}

/**
 * Hook that resolves the operator-authored Reviewer persona name.
 * Returns null if the persona hasn't been authored yet (skeleton state).
 *
 * Module-level cache + subscriber pattern: every hook caller subscribes
 * to the same single fetch. Persona name is workspace-stable within a
 * session — there is no need to refetch per component mount.
 */
export function useReviewerPersona(): string | null {
  const [personaName, setPersonaName] = useState<string | null>(cachedPersonaName);

  useEffect(() => {
    let cancelled = false;

    // Subscribe so this component is notified when the fetch resolves
    // (even if it mounted after another component already triggered it).
    const onResolved = (name: string | null) => {
      if (!cancelled) setPersonaName(name);
    };
    subscribers.add(onResolved);

    // Kick the fetch (no-op if already resolved or in flight).
    if (!resolved) {
      fetchPersonaOnce();
    } else if (cachedPersonaName !== personaName) {
      setPersonaName(cachedPersonaName);
    }

    return () => {
      cancelled = true;
      subscribers.delete(onResolved);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return personaName;
}
