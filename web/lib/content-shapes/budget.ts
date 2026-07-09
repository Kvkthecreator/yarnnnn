/**
 * Budget content shape — `/workspace/governance/_budget.yaml`.
 *
 * ADR-327 (2026-06-08): supersedes the pace content shape. Pace retired —
 * "how often the agent works" is the Reviewer's allocation problem within the
 * dollar budget, not an operator dial. The operator declares a spend envelope
 * (amount + window); the Reviewer allocates wakes within it against ground
 * truth (the self-improving loop, ADR-327 D6).
 *
 * Mirrors autonomy.ts/pace.ts: configuration WRITE_CONTRACT, FE-side
 * parse/serialize, write routes through `writeShape('budget', ...)` so
 * ADR-245 D5 contract enforcement runs.
 *
 * V1 edit scope is amount + window (the two budget fields). `per_wake_ceiling_usd`
 * and `min_interval_between_recurrence_fires_seconds` are read, displayed, and
 * round-tripped on disk; edits to those defer to chat → WriteFile.
 *
 * Budget is operator-only substrate per ADR-327: the path is under the
 * governance/ root (locked from the Reviewer per ADR-320 CALLER_WRITE_POLICY).
 * The Reviewer reads it in the wake envelope; only the operator session writes.
 *
 * Utilization (window-to-date spend) is NOT in the file — it's computed from
 * the execution_events cost ledger and served by GET /api/budget. The hook
 * fetches both: the file (declared envelope, editable) + the route (live spend,
 * read-only).
 */

'use client';

import { useEffect, useState } from 'react';
import { api } from '@/lib/api/client';
import type { ContentShapeMeta } from './index';

// ---------------------------------------------------------------------------
// Shape registry metadata (ADR-245 D3 + ADR-327)
// ---------------------------------------------------------------------------

export const SHAPE_KEY = 'budget' as const;
export const PATH_GLOB = '**/governance/_budget.yaml';
export const WRITE_CONTRACT = 'configuration' as const;
export const CANONICAL_L3 = 'BudgetCard' as const;

export const META: ContentShapeMeta = {
  SHAPE_KEY,
  PATH_GLOB,
  WRITE_CONTRACT,
  CANONICAL_L3,
};

// ---------------------------------------------------------------------------
// Constants — mirror GOVERNANCE_BUDGET_PATH in api/services/workspace_paths.py
// ---------------------------------------------------------------------------

export const BUDGET_YAML_PATH = '/workspace/governance/_budget.yaml';

export const BUDGET_WINDOWS = ['monthly', 'weekly', 'daily'] as const;
export type BudgetWindow = typeof BUDGET_WINDOWS[number];

// ---------------------------------------------------------------------------
// Types — align with api/services/budget.py `Budget` dataclass + `load_budget`
// ---------------------------------------------------------------------------

export interface BudgetMeta {
  /** The dollar spend envelope. */
  amount_usd?: number;
  /** Timeframe the amount covers. */
  window?: BudgetWindow;
  /** Runaway floor — single-fire cap. Round-tripped; edit via chat. */
  per_wake_ceiling_usd?: number;
  /** Per-slug fire floor (ADR-313 Gate 3). Round-tripped; edit via chat. */
  min_interval_between_recurrence_fires_seconds?: number;
}

// ---------------------------------------------------------------------------
// Tier frontmatter stripper — identical convention to autonomy.ts/pace.ts
// ---------------------------------------------------------------------------

export function stripTierFrontmatter(content: string): string {
  const m = content.match(/^---\s*\n([\s\S]*?)\n---\s*\n/);
  if (m && /\btier\s*:/.test(m[1])) {
    return content.slice(m[0].length);
  }
  return content;
}

// ---------------------------------------------------------------------------
// Pure parser — reads _budget.yaml (plain YAML after tier strip)
// ---------------------------------------------------------------------------
//
// Line-based parse (same approach as pace.ts). Handles the `budget:` block
// (amount_usd + window) plus top-level per_wake_ceiling_usd +
// min_interval_between_recurrence_fires_seconds. Comments + unknown fields
// pass through; serialize() reconstructs only the keys it owns.

export function parse(content: string): BudgetMeta {
  const yaml = stripTierFrontmatter(content);
  const meta: BudgetMeta = {};
  let inBudgetBlock = false;
  for (const line of yaml.split('\n')) {
    if (/^\s*#/.test(line) || /^\s*$/.test(line)) continue;

    // Top-level key (no leading whitespace).
    const topLevelMatch = line.match(/^([a-z_]+):\s*(.*)$/);
    if (topLevelMatch && !line.startsWith(' ')) {
      const key = topLevelMatch[1];
      const rawValue = topLevelMatch[2]
        .trim()
        .replace(/^['"]|['"]$/g, '')
        .replace(/\s*#.*$/, '')
        .trim();
      if (key === 'budget') {
        inBudgetBlock = true;
        continue;
      }
      inBudgetBlock = false;
      if (key === 'per_wake_ceiling_usd' && rawValue) {
        const n = Number(rawValue);
        if (!Number.isNaN(n)) meta.per_wake_ceiling_usd = n;
      }
      if (key === 'min_interval_between_recurrence_fires_seconds' && rawValue) {
        const n = Number(rawValue);
        if (!Number.isNaN(n)) meta.min_interval_between_recurrence_fires_seconds = n;
      }
      continue;
    }

    // Indented field — only consumed when inside `budget:`.
    if (!inBudgetBlock) continue;
    const fieldMatch = line.match(/^\s+([a-z_]+):\s*(.*)$/);
    if (!fieldMatch) continue;
    const k = fieldMatch[1].trim();
    const v = fieldMatch[2]
      .trim()
      .replace(/^['"]|['"]$/g, '')
      .replace(/\s*#.*$/, '')
      .trim();
    if (k === 'amount_usd' && v) {
      const n = Number(v);
      if (!Number.isNaN(n)) meta.amount_usd = n;
    }
    if (k === 'window' && BUDGET_WINDOWS.includes(v as BudgetWindow)) {
      meta.window = v as BudgetWindow;
    }
  }
  return meta;
}

// ---------------------------------------------------------------------------
// Round-trip parser — splits tier frontmatter so serialize() preserves it
// ---------------------------------------------------------------------------

export interface ParsedBudget {
  meta: BudgetMeta;
  tierBlock: string;
  body: string;
}

export function parseRoundTrip(content: string): ParsedBudget {
  const m = content.match(/^---\s*\n([\s\S]*?)\n---\s*\n/);
  const hasTierBlock = m && /\btier\s*:/.test(m[1]);
  const tierBlock = hasTierBlock ? m![0] : '';
  const body = hasTierBlock ? content.slice(tierBlock.length) : content;
  return { meta: parse(content), tierBlock, body };
}

// ---------------------------------------------------------------------------
// serialize() — rewrites the `budget:` block; preserves tier + rest of body
// (per_wake_ceiling_usd + min_interval live as top-level keys, untouched).
// ---------------------------------------------------------------------------

export function serialize(meta: BudgetMeta, body: string = '', tierBlock: string = ''): string {
  const lines: string[] = ['budget:'];
  if (meta.amount_usd != null) {
    lines.push(`  amount_usd: ${meta.amount_usd}`);
  }
  if (meta.window) {
    lines.push(`  window: ${meta.window}`);
  }
  const budgetSection = lines.join('\n') + '\n';

  // Strip the existing `budget:` block (whole block incl. indented children).
  const bodyWithoutBudget = body.replace(/^budget:\s*\n(\s+\S[^\n]*\n)*/m, '');

  let out = tierBlock + budgetSection + bodyWithoutBudget;
  if (!out.endsWith('\n')) out += '\n';
  return out;
}

// ---------------------------------------------------------------------------
// Pure helpers
// ---------------------------------------------------------------------------

const WINDOW_LABELS: Record<BudgetWindow, string> = {
  monthly: 'per month',
  weekly: 'per week',
  daily: 'per day',
};

export function budgetWindowLabel(window: BudgetWindow | undefined | null): string {
  if (!window) return '';
  return WINDOW_LABELS[window];
}

export function formatBudgetSummary(meta: BudgetMeta | null): string {
  if (!meta || meta.amount_usd == null) return 'No budget declared';
  const w = meta.window ? ` ${budgetWindowLabel(meta.window)}` : '';
  return `$${meta.amount_usd.toFixed(2)}${w}`;
}

// ---------------------------------------------------------------------------
// React hook — reads declared envelope (file) + live utilization (route)
// ---------------------------------------------------------------------------

export interface BudgetUtilization {
  amount_usd: number;
  window: BudgetWindow;
  window_spend_usd: number;
  remaining_usd: number;
  per_wake_ceiling_usd: number;
  queue_depth: number;
  // ADR-338 D4.4 — runway framing (null until enough spend signal this window).
  daily_burn_usd?: number | null;
  runway_days?: number | null;
  // ADR-433 D2 — the real pooled balance (allowance + top-ups − metered spend).
  // The pace draw-down reads against this, not the fictional envelope amount_usd.
  effective_balance_usd?: number | null;
}

export interface UseBudgetResult {
  meta: BudgetMeta | null;
  /** Live utilization from GET /api/budget (window-to-date spend). */
  utilization: BudgetUtilization | null;
  loading: boolean;
  summary: string;
  /** Mutate the budget envelope (amount + window). Routes through
   *  writeShape('budget', ...) so ADR-245 D5 WRITE_CONTRACT enforcement runs. */
  setBudget: (next: { amount_usd?: number; window?: BudgetWindow }) => Promise<void>;
}

export function useCockpitBudget(opts?: { initialContent?: string | null }): UseBudgetResult {
  const initial = opts?.initialContent;
  const initialParsed =
    initial != null && initial !== '' ? parseRoundTrip(initial) : null;
  const [meta, setMeta] = useState<BudgetMeta | null>(initialParsed?.meta ?? null);
  const [utilization, setUtilization] = useState<BudgetUtilization | null>(null);
  const [loading, setLoading] = useState(initialParsed === null);
  const [tierBlock, setTierBlock] = useState(initialParsed?.tierBlock ?? '');
  const [rawBody, setRawBody] = useState(initialParsed?.body ?? '');

  useEffect(() => {
    let cancelled = false;
    (async () => {
      // Declared envelope (file) — unless primed from initialContent.
      if (initial === undefined) {
        try {
          const file = await api.workspace.getFile(BUDGET_YAML_PATH);
          if (!cancelled && file?.content) {
            const parsed = parseRoundTrip(file.content);
            setMeta(parsed.meta);
            setTierBlock(parsed.tierBlock);
            setRawBody(parsed.body);
          }
        } catch {
          /* leave meta null — kernel default applies server-side */
        }
      } else if (initial != null && initial !== '') {
        const parsed = parseRoundTrip(initial);
        setMeta(parsed.meta);
        setTierBlock(parsed.tierBlock);
        setRawBody(parsed.body);
      }
      // Live utilization (route) — always fetched.
      try {
        const u = await api.budget();
        if (!cancelled) setUtilization(u as BudgetUtilization);
      } catch {
        /* utilization stays null — surface degrades to envelope-only */
      }
      if (!cancelled) setLoading(false);
    })();
    return () => {
      cancelled = true;
    };
  }, [initial]);

  const setBudget = async (next: { amount_usd?: number; window?: BudgetWindow }) => {
    if (next.window && !BUDGET_WINDOWS.includes(next.window)) {
      throw new Error(`useCockpitBudget.setBudget: invalid window ${next.window}`);
    }
    const nextMeta: BudgetMeta = { ...(meta ?? {}), ...next };
    const content = serialize(nextMeta, rawBody, tierBlock);
    setMeta(nextMeta); // optimistic
    const { writeShape } = await import('./write');
    await writeShape('budget', 'governance/_budget.yaml', content, {
      message: `budget: $${nextMeta.amount_usd ?? '?'}/${nextMeta.window ?? '?'}`,
    });
  };

  const summary = formatBudgetSummary(meta);

  return { meta, utilization, loading, summary, setBudget };
}
