'use client';

/**
 * SystemAgentPanes — Freddie's inspection + dial panes (ADR-412 D5).
 *
 * The system agent's legibility home. Extracted from AgentContentView's
 * ReviewerDetail (ADR-387 §6.4 had homed these on the /agents roster as
 * Freddie's pane); ADR-412 D5 reverses that placement — Freddie leaves the
 * roster (the Agents surface is Altitude 3: domain + persona agents), and
 * its panes re-home to Workspace Settings as the SYSTEM AGENT group. The
 * steward's inspection surface belongs on the system layer, not the staff
 * roster — same chrome must not imply same kind.
 *
 * ADR-387's substance is preserved: these are still the AGENT's settings
 * (persona/ · governance/ grant · contract/), rendered by the same *Card
 * full variants (Singular Implementation — a MOVE, not a copy; the
 * ReviewerDetail mount is deleted). When persona agents build (ADR-382),
 * their per-agent equivalents live on THEIR roster detail — the roster
 * shows staff; Workspace Settings shows the system.
 */

import {
  User,
  Scale,
  ShieldCheck,
  Wallet,
  Crosshair,
  FileCode,
  Activity as ActivityIcon,
} from 'lucide-react';
import type { PaneGroup } from '@/components/settings/SettingsPaneShell';
import { SubstrateTab } from './SubstrateTab';
import { FreddieActivityPanel } from './FreddieActivityPanel';
import { FreddieCapabilitiesPanel } from './FreddieCapabilitiesPanel';
import { PrinciplesCard } from '@/components/workspace-concepts/PrinciplesCard';
import { AutonomyCard } from '@/components/workspace-concepts/AutonomyCard';
import { BudgetCard } from '@/components/workspace-concepts/BudgetCard';
import { ExpectedOutputCard } from '@/components/workspace-concepts/ExpectedOutputCard';

/**
 * One sidebar group under Workspace Settings. The ADR-387 five-group
 * pedagogy (Persona/Grant/Contract/Operation/Supervision) flattens to one
 * "System Agent" group — the pane bodies carry their own root-ownership
 * taglines, and a five-group insert would double Workspace Settings'
 * sidebar. Pane keys match the kernel registry slugs (identity, principles,
 * autonomy, budget, expected-output) so foregroundSurface(slug) resolves
 * here via pane_of: workspace-settings; capabilities + activity are local
 * pane keys (no registry row), as they were on the roster mount.
 */
export const SYSTEM_AGENT_PANE_GROUP: PaneGroup = {
  label: 'System Agent',
  panes: [
    { key: 'identity', label: 'Identity', icon: User },
    { key: 'principles', label: 'Principles', icon: Scale },
    { key: 'autonomy', label: 'Autonomy', icon: ShieldCheck },
    { key: 'budget', label: 'Budget', icon: Wallet },
    { key: 'expected-output', label: 'Expected Output', icon: Crosshair },
    { key: 'capabilities', label: 'Capabilities', icon: FileCode },
    { key: 'activity', label: 'Activity', icon: ActivityIcon },
  ],
};

export const SYSTEM_AGENT_PANE_KEYS = SYSTEM_AGENT_PANE_GROUP.panes.map((p) => p.key);

/** Render one System Agent pane body — the same components the roster mount
 *  rendered (Singular Implementation). */
export function renderSystemAgentPane(pane: string) {
  switch (pane) {
    case 'identity':
      return (
        <SubstrateTab
          title="Identity"
          path="/workspace/persona/IDENTITY.md"
          tagline="Freddie's persona — who occupies the seat. Operator-authored; shapes how it reasons (stewardship, and judgment when an operation runs)."
          editPrompt="I want to evolve Freddie's identity and persona. Walk me through the current declaration."
          emptyBody={
            <p className="text-center text-xs">
              No identity declared yet. Author Freddie&apos;s persona to shape
              how it reasons — Simons, Buffett, or your own original.
            </p>
          }
        />
      );
    case 'principles':
      return <PrinciplesCard variant="full" />;
    case 'autonomy':
      return <AutonomyCard variant="full" />;
    case 'budget':
      return <BudgetCard variant="full" />;
    case 'expected-output':
      return <ExpectedOutputCard variant="full" />;
    case 'capabilities':
      return <FreddieCapabilitiesPanel />;
    case 'activity':
      return <FreddieActivityPanel />;
    default:
      return null;
  }
}
