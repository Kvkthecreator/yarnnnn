'use client';

/**
 * Persona name resolution (ADR-246; amended ADR-414 D2 / ADR-418).
 *
 * Reads /workspace/persona/IDENTITY.md and extracts the operator-authored
 * persona name so the rail + attribution can show "Simons" instead of a
 * generic label.
 *
 * ADR-414 D2 note: the SYSTEM AGENT (Freddie) has NO operator-authored
 * persona — its identity is a kernel constant, and a bare workspace's
 * persona/IDENTITY.md is the kernel steward-default (rejected below via the
 * `yarnnn:steward-default` marker → the caller falls back to "Freddie"). This
 * hook returns a name only once a HIRED agent (or a program activation) has
 * installed a real persona at persona/IDENTITY.md (the occupant-agnostic SEAT
 * path, ADR-315). So "persona name" here means the hired occupant's — never
 * the steward's.
 *
 * Resolution rules (in order):
 * 1. First `# ` heading line → strip `# ` prefix → use as persona name
 * 2. File missing or empty → return null (caller falls back to generic label)
 * 3. File is a skeleton/template/kernel-default → return null
 *
 * Kept intentionally thin — no composition, no inference. Just a name
 * extracted from the IDENTITY.md at the seat path.
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

/**
 * Markers that indicate a skeleton/template/kernel-default file with NO
 * operator-authored persona yet.
 *
 * ADR-414/419 note: under PURE GENESIS a bare workspace no longer SEEDS
 * `persona/IDENTITY.md` at all — the file is simply ABSENT, so the LIVE path
 * for a bare workspace is the empty-content branch (returns null → the caller
 * falls back to "Freddie"). The `yarnnn:steward-default` marker guard below is
 * now reachable ONLY on a PRE-ADR-414 workspace that still carries a
 * marker-bearing seeded file; it is retained so those legacy workspaces don't
 * surface the steward-default heading ("# Identity — the system agent") as an
 * operator persona name (the old "Freddie flashes then gets replaced" bug).
 * A hired agent overwrites IDENTITY.md (at its own home) with a real persona.
 */
const SKELETON_MARKERS = [
  '_(empty',
  '(template)',
  '# Reviewer Identity — (template)',
  'yarnnn:steward-default', // legacy pre-ADR-414 seeded steward-default (ADR-381/383)
];

function extractPersonaName(content: string): string | null {
  if (!content || !content.trim()) return null;

  // Reject skeleton / template / kernel-default content
  for (const marker of SKELETON_MARKERS) {
    if (content.includes(marker)) return null;
  }

  // Extract first # heading
  const lines = content.split('\n');
  for (const line of lines) {
    const trimmed = line.trim();
    if (trimmed.startsWith('# ')) {
      const name = trimmed.slice(2).trim();
      // Reject generic / default headings. "system agent" catches the steward
      // default even in older workspaces whose seed predates the HTML marker
      // above ("Identity — the system agent" is the kernel label, not a persona).
      if (
        name.toLowerCase().includes('reviewer identity') ||
        name.toLowerCase().includes('template') ||
        name.toLowerCase().includes('the system agent') ||
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
 * Synchronous getter for the resolved persona name — for callers that run
 * OUTSIDE React render (SSE stream callbacks, event handlers) where the
 * `useFreddiePersona` hook is illegal. Returns the module-cached value
 * (`null` until the first fetch resolves). By the time any streamed turn
 * arrives, the chat header's `useFreddiePersona` has already primed the
 * cache, so the transient status line resolves the same name the bubble
 * shows. Callers fall back to 'Freddie' on null — same `?? 'Freddie'`
 * pattern as the hook consumers.
 */
export function getFreddiePersonaName(): string | null {
  return cachedPersonaName;
}

/**
 * Hook that resolves the operator-authored Reviewer persona name.
 * Returns null if the persona hasn't been authored yet (skeleton state).
 *
 * Module-level cache + subscriber pattern: every hook caller subscribes
 * to the same single fetch. Persona name is workspace-stable within a
 * session — there is no need to refetch per component mount.
 */
export function useFreddiePersona(): string | null {
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
