'use client';

/**
 * Agents Page — the surface's mount (ADR-297 D1 + D19).
 *
 * Content-only (D19: the WindowFrame is the chrome). The body is
 * `AgentsSurface` — list + detail over the workspace's Agent folders and the
 * kernel set.
 *
 * REWRITTEN 2026-07-16. This page previously rendered a roster over the
 * `agents` DB TABLE via `useAgentsAndRecurrences` + `AgentContentView` — for
 * the ADR-382 Rung-2 persona seats. That table is EMPTY (ADR-414 retired the
 * last row), so the page was an empty view over an empty table for a horizon
 * that is deferred AND scoped out of the vision (ADR-380 §5). It is replaced,
 * not siblinged (Singular Implementation).
 *
 * What it shows now is what actually exists: the colleagues a member hires and
 * names (ADR-460 D4 + the personified widening). Nothing here re-opens Rung 2
 * — every pane is identity or capability, never authority.
 *
 * Derivation: docs/analysis/agents-surface-and-debt-2026-07-16.md
 */

import { AgentsSurface } from '@/components/agents/AgentsSurface';

export default function AgentsPage() {
  return <AgentsSurface />;
}
