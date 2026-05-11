/**
 * Autonomy content shape — `/workspace/context/_shared/_autonomy.yaml`.
 *
 * ADR-254 (file format discipline): machine-parsed delegation config moved
 * from AUTONOMY.md frontmatter → _autonomy.yaml. AUTONOMY.md is now
 * prose-only (LLM/human reading). All reads and writes target _autonomy.yaml.
 *
 * _autonomy.yaml has a tier frontmatter block (--- tier: authored ... ---)
 * prepended by the bundle fork. stripTierFrontmatter() removes it before
 * YAML parsing so the parser only sees the raw YAML fields.
 *
 * Lifted-from history: MandateFace.tsx → web/lib/autonomy.ts (ADR-238) →
 * content-shapes/autonomy.ts (ADR-245 Phase 2) → _autonomy.yaml target (ADR-254).
 */

'use client';

import { useEffect, useState } from 'react';
import { api } from '@/lib/api/client';
import type { ContentShapeMeta } from './index';

// ---------------------------------------------------------------------------
// Shape registry metadata (ADR-245 D3)
// ---------------------------------------------------------------------------

export const SHAPE_KEY = 'autonomy' as const;
export const PATH_GLOB = '**/_shared/_autonomy.yaml';
export const WRITE_CONTRACT = 'configuration' as const;
export const CANONICAL_L3 = 'DelegationCard' as const;

export const META: ContentShapeMeta = {
  SHAPE_KEY,
  PATH_GLOB,
  WRITE_CONTRACT,
  CANONICAL_L3,
};

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

/**
 * Machine-parsed delegation config (ADR-254). Mirrors Python constant
 * SHARED_AUTONOMY_YAML_PATH = "context/_shared/_autonomy.yaml".
 * AUTONOMY_PATH kept as alias pointing to prose doc for link-outs only.
 */
export const AUTONOMY_YAML_PATH = '/workspace/context/_shared/_autonomy.yaml';
/** Prose documentation — human/LLM reading only. Not machine-parsed. */
export const AUTONOMY_PATH = '/workspace/context/_shared/AUTONOMY.md';

// ---------------------------------------------------------------------------
// Types — match ADR-261 D5 / Commit F (2026-05-11) canonical schema
// ---------------------------------------------------------------------------
//
// Field name + value space aligned with backend `_validate_autonomy_block` +
// `should_auto_execute_verdict` (api/services/review_policy.py). Pre-Commit-F
// the FE wrote `level: bounded_autonomous` (4-value union including
// `assisted`) which the backend silently treated as "manual" because the
// field name and values both didn't match. Commit F unifies on:
//
//   field: `delegation`  (was `level`)
//   values: 'manual' | 'bounded' | 'autonomous'  (was 4 values)
//
// `assisted` and `bounded_autonomous` are retired — `assisted` had no
// backend semantics; `bounded_autonomous` collapsed to `bounded` per
// Singular Implementation rule.

export type AutonomyDelegation = 'manual' | 'bounded' | 'autonomous';

/** @deprecated post-Commit-F use AutonomyDelegation. Kept as a transient
 *  alias to ease migration; remove after all callers use the new name. */
export type AutonomyLevel = AutonomyDelegation;

export interface AutonomyDomain {
  delegation?: AutonomyDelegation | string;
  ceiling_cents?: number;
}

export interface AutonomyMeta {
  default_delegation?: AutonomyDelegation | string;
  default_ceiling_cents?: number;
  domains?: Record<string, AutonomyDomain>;
  /** ADR-248 D3: ISO-8601 UTC timestamp. While non-expired, every
   *  proposal defers regardless of delegation. */
  paused_until?: string;
  /** Operator-readable note that surfaces on the cockpit while paused. */
  pause_reason?: string;
}

// ---------------------------------------------------------------------------
// Tier frontmatter stripper (ADR-254)
// ---------------------------------------------------------------------------
//
// Bundle-forked yaml files have a `---\ntier: authored\n...\n---` block at
// the top (same convention as Python _strip_tier_frontmatter). Strip it so
// the parser only sees raw YAML field lines.

export function stripTierFrontmatter(content: string): string {
  // Match the leading --- block only if it contains a `tier:` key,
  // distinguishing bundle tier blocks from legitimate YAML `---` separators.
  const m = content.match(/^---\s*\n([\s\S]*?)\n---\s*\n/);
  if (m && /\btier\s*:/.test(m[1])) {
    return content.slice(m[0].length);
  }
  return content;
}

// ---------------------------------------------------------------------------
// Pure parser — reads _autonomy.yaml (ADR-254, plain YAML after tier strip)
// ---------------------------------------------------------------------------

export function parse(content: string): AutonomyMeta {
  const yaml = stripTierFrontmatter(content);
  const meta: AutonomyMeta = { domains: {} };
  let currentDomain: string | null = null;
  let inDefault = false;
  let inDomains = false;
  for (const line of yaml.split('\n')) {
    // Skip comment lines and blank lines
    if (/^\s*#/.test(line) || /^\s*$/.test(line)) continue;
    if (/^default:\s*$/.test(line)) {
      inDefault = true;
      inDomains = false;
      currentDomain = null;
      continue;
    }
    if (/^domains:\s*$/.test(line)) {
      inDefault = false;
      inDomains = true;
      currentDomain = null;
      continue;
    }
    // Top-level keys that are not `default` or `domains` — reset section
    // context so we don't mis-attribute. Capture pause fields (ADR-248 D3).
    const topLevelMatch = line.match(/^([a-z_]+):\s*(.*)$/);
    if (topLevelMatch && !line.startsWith(' ')) {
      const key = topLevelMatch[1];
      const value = topLevelMatch[2].trim().replace(/^['"]|['"]$/g, '').replace(/\s*#.*$/, '').trim();
      if (key !== 'default' && key !== 'domains') {
        if (key === 'paused_until' && value) meta.paused_until = value;
        if (key === 'pause_reason' && value) meta.pause_reason = value;
        inDefault = false;
        inDomains = false;
        currentDomain = null;
        continue;
      }
    }
    const domainMatch = line.match(/^\s{2}([a-z_]+):\s*$/);
    if (inDomains && domainMatch) {
      currentDomain = domainMatch[1];
      meta.domains![currentDomain] = {};
      continue;
    }
    const fieldMatch = line.match(/^\s+([a-z_]+):\s*(.*)$/);
    if (!fieldMatch) continue;
    const k = fieldMatch[1].trim();
    const v = fieldMatch[2].trim().replace(/^['"]|['"]$/g, '').replace(/\s*#.*$/, '').trim();
    if (inDefault) {
      // Commit F (2026-05-11): canonical field name is `delegation`. Pre-Commit-F
      // files used `level` — read it as a fallback and normalize to delegation.
      // Migration 172 + the rewriter ensures persisted files only carry
      // `delegation` going forward; this fallback exists for in-flight reads
      // during deploy + as a safety net for any unmigrated legacy file.
      if (k === 'delegation' || k === 'level') {
        meta.default_delegation = _normalizeDelegation(v);
      }
      if (k === 'ceiling_cents') meta.default_ceiling_cents = Number(v);
    } else if (inDomains && currentDomain) {
      const dom = meta.domains![currentDomain];
      if (k === 'delegation' || k === 'level') {
        dom.delegation = _normalizeDelegation(v);
      }
      if (k === 'ceiling_cents') dom.ceiling_cents = Number(v);
    }
  }
  return meta;
}

/** Normalize legacy 4-value union → canonical 3-value enum. Same mapping as
 *  the migration 172 rewriter — keep them in lockstep. */
function _normalizeDelegation(raw: string): AutonomyDelegation {
  const s = raw.toLowerCase().trim();
  if (s === 'bounded_autonomous') return 'bounded';
  if (s === 'autonomous') return 'autonomous';
  if (s === 'bounded') return 'bounded';
  if (s === 'manual' || s === 'assisted') return 'manual';
  return 'manual';
}

/** Legacy alias — back-compat for callers still importing `parseAutonomy`. */
export const parseAutonomy = parse;

// ---------------------------------------------------------------------------
// Round-trip parser — splits frontmatter from operator-authored body
// ---------------------------------------------------------------------------
//
// _autonomy.yaml round-trip (ADR-254):
// The file has an optional tier frontmatter block at the top (bundle-forked
// workspaces). parseRoundTrip splits that block from the YAML body so
// serialize() can re-emit it unchanged — operators reading the file keep
// the documentation comments the bundle shipped.

export interface ParsedAutonomy {
  meta: AutonomyMeta;
  /** The tier frontmatter block verbatim (e.g. "---\ntier: authored\n...\n---\n"), or ''. */
  tierBlock: string;
  /** The raw YAML body after the tier block, including comments. */
  body: string;
}

export function parseRoundTrip(content: string): ParsedAutonomy {
  const m = content.match(/^---\s*\n([\s\S]*?)\n---\s*\n/);
  const hasTierBlock = m && /\btier\s*:/.test(m[1]);
  const tierBlock = hasTierBlock ? m![0] : '';
  const body = hasTierBlock ? content.slice(tierBlock.length) : content;
  return { meta: parse(content), tierBlock, body };
}

// ---------------------------------------------------------------------------
// serialize() — writes back only the `default:` and `domains:` keys,
// preserving the tier block and the rest of the YAML body verbatim.
// ---------------------------------------------------------------------------

export function serialize(meta: AutonomyMeta, body: string = '', tierBlock: string = ''): string {
  // Rebuild only the structured keys we own; preserve comment lines in body.
  // Commit F (2026-05-11): canonical field name is `delegation`.
  // Commit G (2026-05-11): paused_until + pause_reason emitted as top-level
  // keys (ADR-248 D3); reads + writes round-trip cleanly.
  const lines: string[] = [];
  if (meta.default_delegation !== undefined || meta.default_ceiling_cents !== undefined) {
    lines.push('default:');
    if (meta.default_delegation !== undefined) {
      lines.push(`  delegation: ${meta.default_delegation}`);
    }
    if (meta.default_ceiling_cents !== undefined) {
      lines.push(`  ceiling_cents: ${meta.default_ceiling_cents}`);
    }
  }
  if (meta.domains && Object.keys(meta.domains).length > 0) {
    lines.push('domains:');
    for (const [name, dom] of Object.entries(meta.domains)) {
      lines.push(`  ${name}:`);
      if (dom.delegation !== undefined) lines.push(`    delegation: ${dom.delegation}`);
      if (dom.ceiling_cents !== undefined) lines.push(`    ceiling_cents: ${dom.ceiling_cents}`);
    }
  }
  if (meta.paused_until) {
    lines.push(`paused_until: ${meta.paused_until}`);
  }
  if (meta.pause_reason) {
    // Quote the reason in case it contains colons or special yaml chars.
    const escaped = meta.pause_reason.replace(/"/g, '\\"');
    lines.push(`pause_reason: "${escaped}"`);
  }
  const yamlSection = lines.join('\n') + (lines.length > 0 ? '\n' : '');
  // Patch the existing body to replace only the structured keys, keeping
  // comment lines (never_auto, etc.). Strip default/domains/paused_until/
  // pause_reason from body, prepend the new ones.
  const bodyWithoutStructured = body
    .replace(/^default:\s*\n(\s+\S[^\n]*\n)*/m, '')
    .replace(/^domains:\s*\n(\s+\S[^\n]*\n)*/m, '')
    .replace(/^paused_until:\s.*\n/m, '')
    .replace(/^pause_reason:\s.*\n/m, '');
  let out = tierBlock + yamlSection + bodyWithoutStructured;
  if (!out.endsWith('\n')) out += '\n';
  return out;
}

// ---------------------------------------------------------------------------
// Pure helpers
// ---------------------------------------------------------------------------

export function formatAutonomySummary(autonomy: AutonomyMeta): string {
  const delegation =
    autonomy.default_delegation ??
    Object.values(autonomy.domains ?? {})[0]?.delegation ??
    null;
  if (!delegation) return 'No autonomy declared';
  const ceiling =
    autonomy.default_ceiling_cents ??
    Object.values(autonomy.domains ?? {})[0]?.ceiling_cents ??
    null;
  const label = delegation.replace(/_/g, ' ');
  if (ceiling && ceiling > 0) {
    return `${label} · ceiling $${(ceiling / 100).toLocaleString()}`;
  }
  return label;
}

export function resolveEffectiveLevel(
  meta: AutonomyMeta | null,
  domain?: string,
): AutonomyDelegation | null {
  if (!meta) return null;
  if (domain) {
    const domEntry = meta.domains?.[domain];
    if (domEntry?.delegation) return domEntry.delegation as AutonomyDelegation;
  }
  if (meta.default_delegation) return meta.default_delegation as AutonomyDelegation;
  return null;
}

// ---------------------------------------------------------------------------
// React hook — substrate read for FE consumers
// ---------------------------------------------------------------------------

export interface PauseInfo {
  /** True iff paused_until is set AND in the future. */
  active: boolean;
  /** ISO-8601 timestamp the pause expires. Null when not paused. */
  until: string | null;
  /** Human-readable note that surfaces on the cockpit. */
  reason: string | null;
}

export interface UseAutonomyResult {
  meta: AutonomyMeta | null;
  loading: boolean;
  /** Effective delegation: per-domain override → workspace default → null. */
  effectiveDelegation: AutonomyDelegation | null;
  /** @deprecated post-Commit-F use effectiveDelegation. */
  effectiveLevel: AutonomyDelegation | null;
  /** Workspace-wide pause state (ADR-248 D3). When active, every proposal
   *  defers regardless of delegation. */
  pause: PauseInfo;
  summary: string;
  /** Substrate write via writeShape (ADR-245 D5 contract enforcement). */
  setDelegation: (delegation: AutonomyDelegation, ceilingCents?: number) => Promise<void>;
  /** @deprecated post-Commit-F use setDelegation. */
  setLevel: (delegation: AutonomyDelegation, ceilingCents?: number) => Promise<void>;
  /** Pause the entire autonomy gate until the given ISO timestamp.
   *  Pass null to "indefinite" (sets a far-future timestamp the operator
   *  must lift manually). The Reviewer's auto-execute gate respects this
   *  via review_policy.should_auto_execute_verdict. */
  setPause: (untilIso: string | null, reason: string) => Promise<void>;
  /** Lift the pause immediately. */
  clearPause: () => Promise<void>;
}

export function useAutonomy(opts?: { initialContent?: string | null }): UseAutonomyResult {
  // ADR-266 D8: when the parent has already fetched _autonomy.yaml (via the
  // bundled /workspace/setup-bundle endpoint), prime the round-trip state
  // synchronously and skip the self-fetch. Falls back to the original
  // self-fetch path when initialContent is not supplied (e.g. /agents reuse).
  const initial = opts?.initialContent;
  const initialParsed =
    initial != null && initial !== ''
      ? parseRoundTrip(initial)
      : null;
  const [meta, setMeta] = useState<AutonomyMeta | null>(initialParsed?.meta ?? null);
  const [loading, setLoading] = useState(initialParsed === null);
  const [tierBlock, setTierBlock] = useState(initialParsed?.tierBlock ?? '');
  const [rawBody, setRawBody] = useState(initialParsed?.body ?? '');

  useEffect(() => {
    // Pre-primed path: parent supplied initialContent, nothing to fetch.
    if (initial !== undefined) {
      if (initial != null && initial !== '') {
        const parsed = parseRoundTrip(initial);
        setMeta(parsed.meta);
        setTierBlock(parsed.tierBlock);
        setRawBody(parsed.body);
      } else {
        setMeta(null);
        setTierBlock('');
        setRawBody('');
      }
      setLoading(false);
      return;
    }
    let cancelled = false;
    (async () => {
      try {
        // ADR-254: machine-parsed config lives in _autonomy.yaml, not AUTONOMY.md
        const file = await api.workspace.getFile(AUTONOMY_YAML_PATH);
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
        if (cancelled) return;
        setMeta(null);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, [initial]);

  const setDelegation = async (delegation: AutonomyDelegation, ceilingCents?: number) => {
    const next: AutonomyMeta = {
      ...(meta ?? {}),
      default_delegation: delegation,
      default_ceiling_cents:
        delegation === 'bounded'
          ? (ceilingCents ?? meta?.default_ceiling_cents ?? 200000)
          : undefined,
    };
    const content = serialize(next, rawBody, tierBlock);
    // Optimistic update — UI reflects immediately, API confirms in background
    setMeta(next);
    // Singular Implementation (ADR-245 D5): all autonomy-shape mutations
    // route through writeShape so the WRITE_CONTRACT guard runs. Same
    // backend primitive as before (api.workspace.editFile internally).
    // The duplicate write path that bypassed the guard was retired
    // 2026-05-11 (post-FOUNDATIONS-v8.4 audit pass).
    const { writeShape } = await import('./write');
    await writeShape('autonomy', 'context/_shared/_autonomy.yaml', content, {
      message: `autonomy delegation → ${delegation}`,
    });
  };

  const setPause = async (untilIso: string | null, reason: string) => {
    // null = "indefinite" → set to far-future (year 2099); operator must lift manually.
    const ts = untilIso ?? '2099-12-31T23:59:59Z';
    const next: AutonomyMeta = {
      ...(meta ?? {}),
      paused_until: ts,
      pause_reason: reason || 'paused by operator',
    };
    const content = serialize(next, rawBody, tierBlock);
    setMeta(next);
    const { writeShape } = await import('./write');
    await writeShape('autonomy', 'context/_shared/_autonomy.yaml', content, {
      message: `autonomy paused until ${ts}: ${reason || 'operator-initiated'}`,
    });
  };

  const clearPause = async () => {
    const next: AutonomyMeta = { ...(meta ?? {}) };
    delete next.paused_until;
    delete next.pause_reason;
    const content = serialize(next, rawBody, tierBlock);
    setMeta(next);
    const { writeShape } = await import('./write');
    await writeShape('autonomy', 'context/_shared/_autonomy.yaml', content, {
      message: 'autonomy pause lifted by operator',
    });
  };

  const effectiveDelegation = resolveEffectiveLevel(meta);
  const summary = formatAutonomySummary(meta ?? {});

  // Pause is "active" iff paused_until exists AND is in the future.
  const pause: PauseInfo = (() => {
    const until = meta?.paused_until ?? null;
    const reason = meta?.pause_reason ?? null;
    if (!until) return { active: false, until: null, reason };
    const expiry = Date.parse(until);
    if (isNaN(expiry) || expiry <= Date.now()) {
      return { active: false, until, reason };
    }
    return { active: true, until, reason };
  })();

  return {
    meta,
    loading,
    effectiveDelegation,
    effectiveLevel: effectiveDelegation,  // back-compat alias
    pause,
    summary,
    setDelegation,
    setLevel: setDelegation,  // back-compat alias
    setPause,
    clearPause,
  };
}
