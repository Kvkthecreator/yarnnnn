'use client';

/**
 * SystemAgentPanes — Freddie's inspection + dial panes.
 *
 * The system agent's legibility home. Lineage: ADR-387 §6.4 homed these on
 * the /agents roster as Freddie's pane; ADR-412 D5 reversed that — Freddie
 * left the roster (the Agents surface is Altitude 3), and the panes re-homed
 * to Workspace Settings as the SYSTEM AGENT group. ADR-426 (2026-07-09)
 * carved the group out again — it becomes its OWN door ("Freddie System
 * Agent", the /system-agent surface, same launcher plane as Workspace
 * Settings), so the workspace-operation door no longer mixes the system
 * agent's config with the operation's. Same bodies, new frame (Singular
 * Implementation — the /system-agent page mounts this module).
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
 * plus its read-only legibility (About · Activity).
 *
 * ADR-426 (2026-07-09): the group label becomes the proper noun "Freddie
 * System Agent" — the ADR-412 D5 role-only ruling is reversed now that the
 * panes have their OWN door (a door titled by its entity reads clearer than an
 * abstract "System Agent"; the operator asked for it by name). The rail stays
 * Freddie's conversational home (ADR-412 D1); this is the config door.
 * Rendered by the same *Card full variants (Singular Implementation).
 *
 * ADR-426 amendment (2026-07-09): the Capabilities pane is RETIRED. It read
 * /workspace/operation/specs/ ("the Reviewer's capability library" — quality
 * contracts for producing recurring outputs), a pre-ADR-414 concept: post
 * ADR-414 the specs library is a HIRED agent's operation concern, not the
 * steward's, and the pane wrongly invited the operator to configure output
 * specs for the system agent. Replaced by an "About" pane (read-only — who
 * Freddie is and what the operator tunes here). Pane order: About · Autonomy ·
 * Budget · Activity.
 */

import {
  Info,
  ShieldCheck,
  Wallet,
  Activity as ActivityIcon,
} from 'lucide-react';
import type { PaneGroup } from '@/components/settings/SettingsPaneShell';
import { GrantGate } from '@/components/workspace-concepts/GrantGate';
import { FreddieAboutPanel } from './FreddieAboutPanel';
import { FreddieActivityPanel } from './FreddieActivityPanel';
import { AutonomyCard } from '@/components/workspace-concepts/AutonomyCard';
import { BudgetCard } from '@/components/workspace-concepts/BudgetCard';

/**
 * The one sidebar group of the Freddie System Agent door — Freddie's About +
 * dials + legibility. Pane keys autonomy/budget match the kernel registry slugs
 * (so foregroundSurface(slug) resolves to /system-agent via pane_of:
 * system-agent, ADR-426); about + activity are local pane keys (no registry
 * row). ADR-418 removed identity/principles (→ Constitution group, later
 * removed by ADR-421) + expected-output (dormant); ADR-426 amendment retired
 * capabilities and added about — see module header.
 */
export const SYSTEM_AGENT_PANE_GROUP: PaneGroup = {
  label: 'Freddie System Agent',
  panes: [
    { key: 'about', label: 'About', icon: Info },
    { key: 'autonomy', label: 'Autonomy', icon: ShieldCheck },
    { key: 'budget', label: 'Budget', icon: Wallet },
    { key: 'activity', label: 'Activity', icon: ActivityIcon },
  ],
};

export const SYSTEM_AGENT_PANE_KEYS = SYSTEM_AGENT_PANE_GROUP.panes.map((p) => p.key);

/** ADR-412 D3 — each pane's write affordances land in one ADR-320 region
 *  root; the pane renders per the viewer's grant coverage (GrantGate:
 *  explicit read-only when outside it, never a role-enum check).
 *  about/activity are pure reads — no gate. */
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
    case 'about':
      return <FreddieAboutPanel />;
    case 'autonomy':
      return <AutonomyCard variant="full" />;
    case 'budget':
      return <BudgetCard variant="full" />;
    case 'activity':
      return <FreddieActivityPanel />;
    default:
      return null;
  }
}
