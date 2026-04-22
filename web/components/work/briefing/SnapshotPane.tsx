'use client';

/**
 * SnapshotPane — Dashboard-snippet tiles (ADR-198 §3 Dashboard archetype).
 *
 * Three at-a-glance tiles, each LINKED to a deeper destination (invariant
 * I2: no embedding of foreign substrate; links only).
 *
 *   Book tile     → Ledger-style money-truth headline from _performance_summary.md
 *   Workforce     → Team roster + Work task counts
 *   Context       → Freshest domain in /workspace/context/
 *
 * Any tile that can't load degrades silently (renders as a muted "—" state).
 * Nothing here holds state; all reads are live (invariant I1).
 */

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { Coins, Users, FolderOpen } from 'lucide-react';
import { api } from '@/lib/api/client';
import type { Task } from '@/types';

interface Snapshot {
  bookHeadline: string | null;
  bookHref: string;
  workforceHeadline: string | null;
  teamHref: string;
  workHref: string;
  contextHeadline: string | null;
  contextHref: string;
}

export interface SnapshotPaneProps {
  /**
   * When true, tile copy shifts to teaching-mode: "No trades yet. Fires
   * when you approve your first signal trigger." etc. Per ADR-203 §4b.
   * Post-ADR-205 F2 the BriefingStrip no longer performs day-zero gating
   * (cold-start is the /chat empty state now). This flag is defensive for
   * future "sparse" states where tiles render but still need operator-vocabulary copy.
   */
  isDayZero?: boolean;
}

export function SnapshotPane({ isDayZero = false }: SnapshotPaneProps) {
  const [snap, setSnap] = useState<Snapshot | null>(null);
  const [personaKind, setPersonaKind] = useState<'trading' | 'commerce' | 'neutral'>('neutral');

  useEffect(() => {
    void loadSnapshot().then(({ snapshot, persona }) => {
      setSnap(snapshot);
      setPersonaKind(persona);
    });
  }, []);

  const bookHeadline = isDayZero
    ? bookTeachingCopy(personaKind)
    : snap?.bookHeadline ?? null;
  const workforceHeadline = isDayZero
    ? 'YARNNN + 6 Specialists ready. Authored agents appear here as you create them.'
    : snap?.workforceHeadline ?? null;
  const contextHeadline = isDayZero
    ? 'No context yet. YARNNN creates domains as you describe your work.'
    : snap?.contextHeadline ?? null;

  return (
    <section>
      <h2 className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
        Snapshot
      </h2>
      <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
        <SnapshotTile
          icon={<Coins className="h-4 w-4" />}
          label="Book"
          headline={bookHeadline}
          href={snap?.bookHref ?? '/context'}
        />
        <SnapshotTile
          icon={<Users className="h-4 w-4" />}
          label="Workforce"
          headline={workforceHeadline}
          href={snap?.teamHref ?? '/team'}
        />
        <SnapshotTile
          icon={<FolderOpen className="h-4 w-4" />}
          label="Context"
          headline={contextHeadline}
          href={snap?.contextHref ?? '/context'}
        />
      </div>
    </section>
  );
}

/**
 * Persona-aware teaching copy for the Book tile on day-zero / sparse
 * states (ADR-203 §4b). Reads from platform_connections kind — trading
 * gets P&L framing, commerce gets revenue framing, no connections gets
 * a neutral framing.
 */
function bookTeachingCopy(
  personaKind: 'trading' | 'commerce' | 'neutral',
): string {
  if (personaKind === 'trading') {
    return 'No trades yet. Fires when you approve your first signal trigger.';
  }
  if (personaKind === 'commerce') {
    return 'No revenue yet. Fires when your first platform records a sale.';
  }
  return 'No performance yet. Connect a platform and YARNNN will track it here.';
}

function SnapshotTile({
  icon,
  label,
  headline,
  href,
}: {
  icon: React.ReactNode;
  label: string;
  headline: string | null;
  href: string;
}) {
  return (
    <Link
      href={href}
      className="group flex flex-col rounded-md border border-border bg-card px-3 py-2.5 hover:bg-muted/40"
    >
      <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
        {icon}
        <span className="font-medium uppercase tracking-wide">{label}</span>
      </div>
      <div className="mt-1 text-sm text-foreground">
        {headline ?? <span className="text-muted-foreground/60">—</span>}
      </div>
    </Link>
  );
}

async function loadSnapshot(): Promise<{
  snapshot: Snapshot;
  persona: 'trading' | 'commerce' | 'neutral';
}> {
  const [perfResult, agentsResult, tasksResult, contextNavResult, integrationsResult] =
    await Promise.allSettled([
      api.workspace.getFile('/workspace/context/_performance_summary.md'),
      api.agents.list('active'),
      api.tasks.list(),
      api.workspace.getNav(),
      api.integrations.list(),
    ]);

  // Detect persona from connected platforms. Trading + commerce map to
  // known persona framings; anything else (or nothing) is neutral.
  let persona: 'trading' | 'commerce' | 'neutral' = 'neutral';
  if (integrationsResult.status === 'fulfilled') {
    const providers = (integrationsResult.value.integrations ?? []).map(
      (i) => i.provider,
    );
    const hasTrading = providers.some((p) => p === 'alpaca' || p === 'trading');
    const hasCommerce = providers.some(
      (p) => p === 'lemonsqueezy' || p === 'shopify' || p === 'stripe',
    );
    if (hasTrading && !hasCommerce) persona = 'trading';
    else if (hasCommerce && !hasTrading) persona = 'commerce';
    // both or neither → neutral
  }

  // Book: parse frontmatter from _performance_summary.md if present.
  let bookHeadline: string | null = null;
  if (perfResult.status === 'fulfilled' && perfResult.value.content) {
    bookHeadline = parsePerformanceHeadline(perfResult.value.content);
  }

  // Workforce: N agents · M tasks active
  const agents = agentsResult.status === 'fulfilled' ? agentsResult.value : [];
  const tasks = tasksResult.status === 'fulfilled' ? tasksResult.value : [];
  const activeTasks = tasks.filter((t: Task) => t.status === 'active').length;
  const workforceHeadline =
    agents.length > 0 || activeTasks > 0
      ? `${agents.length} agent${agents.length === 1 ? '' : 's'} · ${activeTasks} active task${activeTasks === 1 ? '' : 's'}`
      : null;

  // Context: highlight the domain with the most entities (stand-in for richness).
  // No updated_at on domain nav shape; domains with more entities are the
  // operator's richer accumulation zones.
  let contextHeadline: string | null = null;
  let contextHref = '/context';
  if (contextNavResult.status === 'fulfilled') {
    const nav = contextNavResult.value;
    const domains = nav?.domains ?? [];
    if (domains.length > 0) {
      const richest = [...domains].sort(
        (a, b) => (b.entity_count ?? 0) - (a.entity_count ?? 0),
      )[0];
      if (richest) {
        const entityCount = richest.entity_count ?? 0;
        contextHeadline = `${richest.display_name}${entityCount > 0 ? ` · ${entityCount} ${entityCount === 1 ? 'entity' : 'entities'}` : ''}`;
        contextHref = `/context?domain=${encodeURIComponent(richest.key)}`;
      }
    }
  }

  return {
    snapshot: {
      bookHeadline,
      bookHref:
        '/context?path=' +
        encodeURIComponent('/workspace/context/_performance_summary.md'),
      workforceHeadline,
      teamHref: '/team',
      workHref: '/work',
      contextHeadline,
      contextHref,
    },
    persona,
  };
}

/**
 * Parse _performance_summary.md YAML frontmatter for a headline.
 *
 * Expected shape (per ADR-195 v2 + Phase 3):
 *   ---
 *   aggregate_pnl_cents: <int>
 *   aggregate_revenue_cents: <int>
 *   currency: USD
 *   rolling_30d:
 *     pnl_cents: <int>
 *     revenue_cents: <int>
 *   ---
 *
 * Returns a human-readable one-liner. Tolerant of schema drift — if fields
 * are missing, returns whatever it can read; if the frontmatter can't parse,
 * returns null.
 */
function parsePerformanceHeadline(content: string): string | null {
  const match = content.match(/^---\s*\n([\s\S]*?)\n---/);
  if (!match) return null;
  const yaml = match[1];

  const readNum = (key: string): number | null => {
    const m = yaml.match(new RegExp(`^\\s*${key}:\\s*(-?\\d+)`, 'm'));
    if (!m) return null;
    const n = parseInt(m[1], 10);
    return Number.isNaN(n) ? null : n;
  };

  const pnlCents = readNum('aggregate_pnl_cents');
  const revenueCents = readNum('aggregate_revenue_cents');
  const currencyMatch = yaml.match(/^\s*currency:\s*(\S+)/m);
  const currency = currencyMatch?.[1] ?? 'USD';

  const parts: string[] = [];
  if (revenueCents !== null && revenueCents !== 0) {
    parts.push(`Rev ${formatMoney(revenueCents, currency)}`);
  }
  if (pnlCents !== null && pnlCents !== 0) {
    const sign = pnlCents >= 0 ? '+' : '';
    parts.push(`P&L ${sign}${formatMoney(pnlCents, currency)}`);
  }

  return parts.length > 0 ? parts.join(' · ') : null;
}

function formatMoney(cents: number, currency: string): string {
  const amount = cents / 100;
  const abs = Math.abs(amount);
  const prefix = currency === 'USD' ? '$' : '';
  if (abs >= 1000) {
    return `${amount < 0 ? '-' : ''}${prefix}${(abs / 1000).toFixed(1)}k`;
  }
  return `${amount < 0 ? '-' : ''}${prefix}${abs.toFixed(0)}`;
}
