/**
 * Expected Output content shape — `/workspace/contract/_expected_output.yaml`.
 *
 * ADR-348 (2026-06-19): the operator-facing FE for ADR-345's Expected Output.
 * ADR-345 shipped the concept + the `_expected_output.yaml` referent + the
 * wake-envelope wiring backend-only; this shape is the parser/editor the
 * operator sees + sets, mounted in the ADR-347 Contract group of the one
 * Settings door (alongside Budget=Rhythm + Autonomy=Witness).
 *
 * The output contract: WHAT the operation owes when it works —
 *   kind            — the artifact (piece, trade, campaign, shortlist, …)
 *   delivery_cadence — the rhythm of delivery (a FLOOR-GATED cadence,
 *                      NEVER a quota — the ADR-345 Goodhart guard)
 *   bar             — pointer to where the quality floor lives
 *   rough_volume_per_window — optional advisory only; order-of-magnitude
 *
 * Orthogonal to _budget.yaml (Rhythm: how often the agent works) and
 * _autonomy.yaml (Witness dial). Neither derives the other (ADR-345 §2).
 *
 * Governance-region, operator-only substrate per ADR-345 / ADR-320: the
 * operator authors it; the Reviewer reads it in the wake envelope and holds
 * itself accountable (DP30) but NEVER authors it. WRITE_CONTRACT='configuration'
 * → operator-writable (ADR-347 §3: operator-authored → inline editor).
 *
 * Mirrors budget.ts/autonomy.ts: FE-side parse/serialize, write routes
 * through `writeShape('expected-output', ...)` so ADR-245 D5 contract
 * enforcement runs.
 */

'use client';

import { useEffect, useState } from 'react';
import { api } from '@/lib/api/client';
import type { ContentShapeMeta } from './index';

// ---------------------------------------------------------------------------
// Shape registry metadata (ADR-245 D3 + ADR-348)
// ---------------------------------------------------------------------------

export const SHAPE_KEY = 'expected-output' as const;
export const PATH_GLOB = '**/contract/_expected_output.yaml';
export const WRITE_CONTRACT = 'configuration' as const;
export const CANONICAL_L3 = 'ExpectedOutputCard' as const;

export const META: ContentShapeMeta = {
  SHAPE_KEY,
  PATH_GLOB,
  WRITE_CONTRACT,
  CANONICAL_L3,
};

// ---------------------------------------------------------------------------
// Constants — mirror GOVERNANCE_EXPECTED_OUTPUT_PATH in
// api/services/workspace_paths.py
// ---------------------------------------------------------------------------

export const EXPECTED_OUTPUT_YAML_PATH = '/workspace/contract/_expected_output.yaml';

/**
 * Declared delivery cadences (ADR-348 D3 generic kernel-fallback form). Free
 * entry is also accepted on the editor — these are the presets a program's
 * shipped YAML uses (`event-driven`, `per-signal-when-fires`) plus the common
 * count-cadence shapes (`weekly`/`biweekly`/`monthly`). The cadence is a
 * floor-gated rhythm, NEVER a quota (ADR-345 Goodhart guard).
 */
export const DELIVERY_CADENCES = [
  'event-driven',
  'per-signal-when-fires',
  'daily',
  'weekly',
  'biweekly',
  'monthly',
  'on-demand',
] as const;
export type DeliveryCadence = typeof DELIVERY_CADENCES[number] | string;

/**
 * Event-shaped cadences produce when a trigger fires and owe ZERO when none
 * does — "zero is on-contract" (ADR-345 trader case). Used to render the
 * Goodhart guard copy + suppress any quota framing.
 */
export const EVENT_SHAPED_CADENCES: ReadonlySet<string> = new Set([
  'event-driven',
  'per-signal-when-fires',
  'on-demand',
]);

// ---------------------------------------------------------------------------
// Types — align with the bundle _expected_output.yaml instances (ADR-345)
// ---------------------------------------------------------------------------

export interface ExpectedOutputMeta {
  /** The artifact this operation produces. */
  kind?: string;
  /** The rhythm of delivery — floor-gated, never a quota. */
  delivery_cadence?: DeliveryCadence;
  /** Pointer to where the quality floor lives (NOT duplicated here). */
  bar?: string;
  /** Optional advisory order-of-magnitude — never enforced as a quota. */
  rough_volume_per_window?: string;
}

// ---------------------------------------------------------------------------
// Tier frontmatter stripper — identical convention to budget.ts/autonomy.ts
// ---------------------------------------------------------------------------

export function stripTierFrontmatter(content: string): string {
  const m = content.match(/^---\s*\n([\s\S]*?)\n---\s*\n/);
  if (m && /\btier\s*:/.test(m[1])) {
    return content.slice(m[0].length);
  }
  return content;
}

// ---------------------------------------------------------------------------
// Pure parser — reads _expected_output.yaml (plain YAML after tier strip)
// ---------------------------------------------------------------------------
//
// Line-based parse (same approach as budget.ts). Handles the
// `expected_output:` block (kind + delivery_cadence + bar +
// rough_volume_per_window). Comments + unknown fields pass through;
// serialize() reconstructs only the keys it owns.

export function parse(content: string): ExpectedOutputMeta {
  const yaml = stripTierFrontmatter(content);
  const meta: ExpectedOutputMeta = {};
  let inBlock = false;
  for (const line of yaml.split('\n')) {
    if (/^\s*#/.test(line) || /^\s*$/.test(line)) continue;

    // Top-level key (no leading whitespace).
    const topLevelMatch = line.match(/^([a-z_]+):\s*(.*)$/);
    if (topLevelMatch && !line.startsWith(' ')) {
      if (topLevelMatch[1] === 'expected_output') {
        inBlock = true;
        continue;
      }
      inBlock = false;
      continue;
    }

    if (!inBlock) continue;
    const fieldMatch = line.match(/^\s+([a-z_]+):\s*(.*)$/);
    if (!fieldMatch) continue;
    const k = fieldMatch[1].trim();
    const v = fieldMatch[2]
      .trim()
      .replace(/^['"]|['"]$/g, '')
      .replace(/\s*#.*$/, '')
      .trim();
    if (!v) continue;
    if (k === 'kind') meta.kind = v;
    if (k === 'delivery_cadence') meta.delivery_cadence = v;
    if (k === 'bar') meta.bar = v;
    if (k === 'rough_volume_per_window') meta.rough_volume_per_window = v;
  }
  return meta;
}

// ---------------------------------------------------------------------------
// Round-trip parser — splits tier frontmatter so serialize() preserves it
// ---------------------------------------------------------------------------

export interface ParsedExpectedOutput {
  meta: ExpectedOutputMeta;
  tierBlock: string;
  body: string;
}

export function parseRoundTrip(content: string): ParsedExpectedOutput {
  const m = content.match(/^---\s*\n([\s\S]*?)\n---\s*\n/);
  const hasTierBlock = m && /\btier\s*:/.test(m[1]);
  const tierBlock = hasTierBlock ? m![0] : '';
  const body = hasTierBlock ? content.slice(tierBlock.length) : content;
  return { meta: parse(content), tierBlock, body };
}

// ---------------------------------------------------------------------------
// serialize() — rewrites the `expected_output:` block; preserves tier + rest
// of body (comments, optional advisory lines the operator left).
// ---------------------------------------------------------------------------

function needsQuote(v: string): boolean {
  return /[:#]/.test(v);
}

function emitField(key: string, value: string): string {
  return needsQuote(value)
    ? `  ${key}: "${value.replace(/"/g, '\\"')}"`
    : `  ${key}: ${value}`;
}

export function serialize(
  meta: ExpectedOutputMeta,
  body: string = '',
  tierBlock: string = '',
): string {
  const lines: string[] = ['expected_output:'];
  if (meta.kind) lines.push(emitField('kind', meta.kind));
  if (meta.delivery_cadence) lines.push(emitField('delivery_cadence', meta.delivery_cadence));
  if (meta.bar) lines.push(emitField('bar', meta.bar));
  if (meta.rough_volume_per_window) {
    lines.push(emitField('rough_volume_per_window', meta.rough_volume_per_window));
  }
  const section = lines.join('\n') + '\n';

  // Strip the existing `expected_output:` block (whole block incl. children).
  const bodyWithout = body.replace(/^expected_output:\s*\n(\s+\S[^\n]*\n)*/m, '');

  let out = tierBlock + section + bodyWithout;
  if (!out.endsWith('\n')) out += '\n';
  return out;
}

// ---------------------------------------------------------------------------
// Pure helpers
// ---------------------------------------------------------------------------

export function isEventShaped(cadence: DeliveryCadence | undefined | null): boolean {
  return !!cadence && EVENT_SHAPED_CADENCES.has(cadence);
}

/** Plain-words headline of the declared contract (ADR-348 D2 — the READ). */
export function formatExpectedOutputSummary(meta: ExpectedOutputMeta | null): string {
  if (!meta || (!meta.kind && !meta.delivery_cadence)) {
    return 'No output contract declared';
  }
  const kind = meta.kind ?? 'output';
  if (!meta.delivery_cadence) return `Owes: ${kind}`;
  if (isEventShaped(meta.delivery_cadence)) {
    return `Owes: a ${kind} when the trigger fires (zero when it doesn't is on-contract)`;
  }
  return `Owes: a ${kind}, ${meta.delivery_cadence} (a floor-gated cadence, not a quota)`;
}

// ---------------------------------------------------------------------------
// React hook — reads the declared output contract (file)
// ---------------------------------------------------------------------------

export interface UseExpectedOutputResult {
  meta: ExpectedOutputMeta | null;
  loading: boolean;
  summary: string;
  /** Mutate the output contract. Routes through writeShape('expected-output', ...)
   *  so ADR-245 D5 WRITE_CONTRACT enforcement runs. */
  setContract: (next: Partial<ExpectedOutputMeta>) => Promise<void>;
}

export function useExpectedOutput(opts?: { initialContent?: string | null }): UseExpectedOutputResult {
  const initial = opts?.initialContent;
  const initialParsed =
    initial != null && initial !== '' ? parseRoundTrip(initial) : null;
  const [meta, setMeta] = useState<ExpectedOutputMeta | null>(initialParsed?.meta ?? null);
  const [loading, setLoading] = useState(initialParsed === null);
  const [tierBlock, setTierBlock] = useState(initialParsed?.tierBlock ?? '');
  const [rawBody, setRawBody] = useState(initialParsed?.body ?? '');

  useEffect(() => {
    if (initial !== undefined) {
      if (initial != null && initial !== '') {
        const parsed = parseRoundTrip(initial);
        setMeta(parsed.meta);
        setTierBlock(parsed.tierBlock);
        setRawBody(parsed.body);
      } else {
        setMeta(null);
      }
      setLoading(false);
      return;
    }
    let cancelled = false;
    (async () => {
      try {
        const file = await api.workspace.getFile(EXPECTED_OUTPUT_YAML_PATH);
        if (cancelled) return;
        if (file?.content) {
          const parsed = parseRoundTrip(file.content);
          setMeta(parsed.meta);
          setTierBlock(parsed.tierBlock);
          setRawBody(parsed.body);
        } else {
          setMeta(null);
        }
      } catch {
        if (!cancelled) setMeta(null);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [initial]);

  const setContract = async (next: Partial<ExpectedOutputMeta>) => {
    const nextMeta: ExpectedOutputMeta = { ...(meta ?? {}), ...next };
    const content = serialize(nextMeta, rawBody, tierBlock);
    setMeta(nextMeta); // optimistic
    const { writeShape } = await import('./write');
    await writeShape('expected-output', 'contract/_expected_output.yaml', content, {
      message: `expected output: ${nextMeta.kind ?? '?'} · ${nextMeta.delivery_cadence ?? '?'}`,
    });
  };

  const summary = formatExpectedOutputSummary(meta);

  return { meta, loading, summary, setContract };
}
