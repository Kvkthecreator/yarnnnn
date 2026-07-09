"use client";

/**
 * /system-agent — the Freddie System Agent door (ADR-426, 2026-07-09).
 *
 * The system agent's own settings door, carved out of Workspace Settings. It
 * sits on the SAME launcher plane as Workspace Settings + User Settings — three
 * sibling doors, three altitudes: the operation (workspace-settings) · the
 * system agent (this) · the human (settings). Prior to this ADR these four panes
 * were the "System Agent" GROUP inside Workspace Settings (ADR-412 D5 / ADR-418);
 * the group leaves that door and gets a frame of its own so the workspace-
 * operation door stops mixing "how Freddie is configured" with "what this
 * operation is."
 *
 * Window-grade surface (registry `slug: system-agent`, `route: /system-agent`,
 * `launcher_tier: system-agent-config`). Mounts the shared SettingsPaneShell
 * (Singular Implementation, ADR-341 D5) with the SYSTEM_AGENT_PANE_GROUP — the
 * SAME SystemAgentPanes bodies (Autonomy · Budget · Capabilities · Activity),
 * not duplicated. The budget/autonomy registry rows re-point pane_of →
 * system-agent, so foregroundSurface('autonomy' | 'budget') resolves here.
 *
 * The door carries the proper noun "Freddie System Agent" (ADR-426 D3); the rail
 * stays Freddie's conversational chrome home (ADR-412 D1) — this is the config
 * door, not a second conversational entry point.
 */

import { SettingsPaneShell } from "@/components/settings/SettingsPaneShell";
import {
  SYSTEM_AGENT_PANE_GROUP,
  renderSystemAgentPane,
} from "@/components/agents/SystemAgentPanes";

export default function SystemAgentPage() {
  return (
    <SettingsPaneShell
      windowSlug="system-agent"
      paneGroups={[SYSTEM_AGENT_PANE_GROUP]}
      defaultPane="about"
      renderPane={(pane) => (
        <section className="mb-8">{renderSystemAgentPane(pane)}</section>
      )}
    />
  );
}
