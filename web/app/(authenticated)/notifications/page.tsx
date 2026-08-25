"use client";

/**
 * /notifications — the Notifications surface, the SECOND composition window
 * (ADR-346, renamed operation → notifications by ADR-349 D2). It carries the
 * operating-work acts:
 *
 *   "To do"    (Decide, pane key `resolve`)    → the Queue body over action_proposals
 *   "Activity" (Read, pane key `understand`)   → the workspace-timeline workbench
 *                                                 (ADR-410 D5 — run receipts included)
 *
 * ADR-603 D5 (2026-08-24): the "Schedule" pane (Tune) is DELETED with the
 * recurrence concept it fronted — production counted 0 recurrence
 * declarations; retire-clean. Standing work is the standing declaration
 * (strings today), read at its own desk; run RECEIPTS surface here in the
 * Activity ledger (`invocation` kind over execution_events), which is
 * ADR-603's own sentence: "runs stop being a concept: receipts surface in
 * notifications." The `tune` pane key retires with the pane.
 *
 * ADR-410 D5 (2026-07-06): the Activity pane re-mounts the SAME "what
 * happened" derivation the bell and the Home slot read — the workspace
 * timeline (the three attributed ledgers) — as the breadth workbench
 * (actor/kind/date filters, full history via the `before` cursor). Bell =
 * glance, THIS = workbench: depths over one source.
 *
 * It is a COMPOSITION over the operational mirrors, not a new mirror: it owns
 * no substrate and no state, and each pane reuses an existing mirror BODY
 * (one body, two mounts — the ADR-340 D8 rule). Mounts the shared
 * SettingsPaneShell (Singular Implementation) in fullBleed mode.
 */

import { ExternalLink, ClipboardCheck, ScrollText } from "lucide-react";
import { useSurfacePreferences } from "@/lib/shell/useSurfacePreferences";
import { SettingsPaneShell, PaneHeader, type PaneGroup } from "@/components/settings/SettingsPaneShell";
import { QueueBody } from "@/components/queue/QueueBody";
import { StandingBand } from "@/components/queue/StandingBand";
import { ActivityLedger } from "@/components/notifications/ActivityLedger";
import { MentionQueue } from "@/components/notifications/MentionQueue";

// ADR-346 label pass (2026-06-19): the act labels are plain operator words.
// The pane KEYS (resolve/understand) are unchanged — they are URL params +
// the ADR-340 D2 act identities (Decide/Read); only the roster shrank
// (ADR-603 D5 removed `tune`).
const PANE_GROUPS: PaneGroup[] = [
  {
    label: "Operate",
    panes: [
      { key: "resolve", label: "To do", icon: ClipboardCheck },
      { key: "understand", label: "Activity", icon: ScrollText },
    ],
  },
];

/** Shared "Open full ___ →" escape-hatch row (ADR-346 — mirrors stay reachable). */
function MirrorLink({ label, onClick }: { label: string; onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="inline-flex items-center gap-1.5 text-xs text-primary hover:underline"
    >
      <ExternalLink className="w-3.5 h-3.5" />
      {label}
    </button>
  );
}

// PaneHeader is the shared shell component (Singular Implementation, 2026-07-01);
// the escape-hatch MirrorLink rides its `action` slot.

export default function OperationPage() {
  const { navigateToSurface } = useSurfacePreferences();

  const renderPane = (pane: string) => {
    switch (pane) {
      case "resolve":
        // Decide — the Queue body. "Open full Queue →" keeps the complete
        // decide mirror one click away (ADR-346 D1 escape hatch).
        return (
          <div className="flex h-full flex-col">
            <PaneHeader
              icon={ClipboardCheck}
              title="To do"
              subtitle="What wants your decision — approve or reject below."
              action={
                <div className="flex items-center gap-4">
                  <MirrorLink label="Open full Queue" onClick={() => navigateToSurface("queue")} />
                  {/* ADR-593 D5 — the window finally links the settings that
                      govern what reaches its viewer. */}
                  <MirrorLink
                    label="Notification settings"
                    onClick={() => navigateToSurface("settings", { pane: "notification-settings" })}
                  />
                </div>
              }
            />
            <div className="flex-1 overflow-y-auto p-6">
              {/* ADR-350: the standing obligation (owed-vs-actual + the
                  Reviewer's standing intent) renders above the discrete
                  proposals — an unmet mandate is the deepest "to do". */}
              <StandingBand />
              {/* ADR-605 — the To-do second source (ADR-492 D3): unresolved
                  mentions of the viewer, discharged by replying or by Done. */}
              <MentionQueue />
              <QueueBody />
            </div>
          </div>
        );
      case "understand":
        // Read — the workspace timeline as a workbench (ADR-410 D5): every
        // attributed act, every actor, filters + full history. Run receipts
        // are the `invocation` kind here (ADR-603 D5 — the run ledger's home).
        return (
          <div className="flex h-full flex-col">
            <PaneHeader
              icon={ScrollText}
              title="Activity"
              subtitle="What happened across the workspace — every actor, attributed."
            />
            <div className="flex-1 min-h-0">
              <ActivityLedger />
            </div>
          </div>
        );
      default:
        return null;
    }
  };

  return (
    <SettingsPaneShell
      windowSlug="notifications"
      paneGroups={PANE_GROUPS}
      defaultPane="resolve"
      renderPane={renderPane}
      fullBleed
      navLabel="Notifications"
    />
  );
}
