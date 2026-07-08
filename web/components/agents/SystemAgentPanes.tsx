'use client';

/**
 * SystemAgentPanes — Freddie's inspection + dial panes.
 *
 * The system agent's legibility home. Lineage: ADR-387 §6.4 homed these on
 * the /agents roster as Freddie's pane; ADR-412 D5 reversed that — Freddie
 * left the roster (the Agents surface is Altitude 3), and the panes re-homed
 * to Workspace Settings as the SYSTEM AGENT group.
 *
 * ADR-418 (2026-07-08) PURIFIED the group to what the system agent actually
 * owns. Post ADR-414 D2 the STEWARD has no operator-authored persona
 * (identity/principles are kernel constants) and no output contract (that is
 * a HIRED Altitude-3 agent's concern, ADR-408 D2 / ADR-382 §3). So:
 *   - Identity + Principles LEFT this group → the Constitution group of
 *     Workspace Settings (they are constitution mirrors doored from the Home
 *     band, not Freddie's persona; rendered in workspace-settings/page.tsx
 *     beside Mandate).
 *   - Expected Output LEFT and went DORMANT (routeless; returns with the
 *     per-agent contract FE — ADR-382 / ADR-414 §9b).
 * What remains is the system agent's genuine surface: its two operator-tunable
 * dials (Autonomy = the witness dial, Budget = the allocation — ADR-414 D2)
 * plus the two read-only legibility panes (Capabilities · Activity).
 *
 * "System Agent" stays the group label (the role, not the proper noun — the
 * entity is named Freddie on its chrome home, the rail; ADR-381 D1 / ADR-412
 * D5). Rendered by the same *Card full variants (Singular Implementation).
 */

import {
  ShieldCheck,
  Wallet,
  FileCode,
  Activity as ActivityIcon,
} from 'lucide-react';
import type { PaneGroup } from '@/components/settings/SettingsPaneShell';
import { GrantGate } from '@/components/workspace-concepts/GrantGate';
import { FreddieActivityPanel } from './FreddieActivityPanel';
import { FreddieCapabilitiesPanel } from './FreddieCapabilitiesPanel';
import { AutonomyCard } from '@/components/workspace-concepts/AutonomyCard';
import { BudgetCard } from '@/components/workspace-concepts/BudgetCard';

/**
 * One sidebar group under Workspace Settings — the system agent's dials +
 * legibility. Pane keys autonomy/budget match the kernel registry slugs (so
 * foregroundSurface(slug) resolves here via pane_of: workspace-settings);
 * capabilities + activity are local pane keys (no registry row). ADR-418
 * removed identity/principles (→ Constitution group) + expected-output
 * (dormant) — see module header.
 */
export const SYSTEM_AGENT_PANE_GROUP: PaneGroup = {
  label: 'System Agent',
  panes: [
    { key: 'autonomy', label: 'Autonomy', icon: ShieldCheck },
    { key: 'budget', label: 'Budget', icon: Wallet },
    { key: 'capabilities', label: 'Capabilities', icon: FileCode },
    { key: 'activity', label: 'Activity', icon: ActivityIcon },
  ],
};

export const SYSTEM_AGENT_PANE_KEYS = SYSTEM_AGENT_PANE_GROUP.panes.map((p) => p.key);

/** ADR-412 D3 — each pane's write affordances land in one ADR-320 region
 *  root; the pane renders per the viewer's grant coverage (GrantGate:
 *  explicit read-only when outside it, never a role-enum check).
 *  capabilities/activity are pure reads — no gate. */
const PANE_REGIONS: Record<string, string> = {
  autonomy: 'governance/',
  budget: 'governance/',
};

/** Render one System Agent pane body — the same components the roster mount
 *  rendered (Singular Implementation). */
export function renderSystemAgentPane(pane: string) {
  const body = renderPaneBody(pane);
  if (!body) return null;
  const region = PANE_REGIONS[pane];
  return region ? <GrantGate region={region}>{body}</GrantGate> : body;
}

function renderPaneBody(pane: string) {
  switch (pane) {
    case 'autonomy':
      return <AutonomyCard variant="full" />;
    case 'budget':
      return <BudgetCard variant="full" />;
    case 'capabilities':
      return <FreddieCapabilitiesPanel />;
    case 'activity':
      return <FreddieActivityPanel />;
    default:
      return null;
  }
}
