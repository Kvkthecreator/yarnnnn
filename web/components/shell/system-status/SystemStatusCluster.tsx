'use client';

/**
 * SystemStatusCluster — agent-OS menu-bar status cluster (ADR-297 D20;
 * consolidated by ADR-340 P1; conceptually reframed 2026-07-01).
 *
 * Three kernel-general status chips in the Right region of the top bar,
 * between the Dock and UserMenu. macOS Control Center / menu-bar-extras
 * analog: always-visible operator-level standing STATE about the
 * system's capacity to do work. Events that demand the operator are a
 * different chrome role — the AttentionCenter (Notification Center
 * analog, ADR-340 D3), a sibling top-bar item, never a chip here.
 *
 * THE MENTAL MODEL (2026-07-01 reframe): the substrate filesystem is the
 * service, and Freddie is the system agent latched onto it (GitHub ⇄ Copilot
 * — the substrate is the repo, Freddie is the agent working over it). The
 * cluster reads through that lens, left-to-right:
 *   1. Freddie      — the system agent's disposition (autonomy = how much it
 *                     acts on its own). The chip names the ENTITY, not an
 *                     abstract OS dial. Footer → Freddie's settings.
 *   2. Money        — the spend that backs the work (budget envelope + balance
 *                     runway, battery analog). Being reframed separately with
 *                     the pricing-model work — untouched in the 2026-07-01 pass.
 *   3. Connections  — the SUBSTRATE's reach: what feeds the service (Wi-Fi
 *                     analog). Not Freddie — the inputs the operation perceives.
 *
 * Responsive collapse (2026-07-04, operator ruling): the cluster is a
 * DESKTOP-CLASS affordance — md+ only. The prior <md rollup (a Cpu chip
 * opening a popover of all three items) was two-levels-nested chrome on
 * a phone for standing state the surfaces already carry (Workspace
 * Settings → Autonomy/Budget panes; Channels → Connections). On mobile
 * the top bar keeps only the load-bearing items: Dock, bell, UserMenu.
 *
 * Read-only popovers per D20 §D2 — every mutation routes to the
 * corresponding atomic surface via the popover footer link.
 */

import { FreddieStatusItem } from './FreddieStatusItem';
import { BudgetStatusItem } from './BudgetStatusItem';
import { ConnectionsStatusItem } from './ConnectionsStatusItem';

export function SystemStatusCluster() {
  return (
    // md+ only — hidden entirely on phones (see header comment).
    <div
      className="hidden md:flex items-center gap-0.5 shrink-0"
      role="group"
      aria-label="System status"
    >
      <FreddieStatusItem />
      <BudgetStatusItem />
      <ConnectionsStatusItem />
    </div>
  );
}
