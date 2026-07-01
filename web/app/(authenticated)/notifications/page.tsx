"use client";

/**
 * /notifications — the Notifications surface, the SECOND composition window
 * (ADR-346, renamed operation → notifications by ADR-349 D2). Home was the
 * first composition (Dwell); this one carries the three operating-work acts
 * ADR-340 D2 named but never built a composition for:
 *
 *   "To do"    (Decide, pane key `resolve`)    → the Queue body over action_proposals
 *   "Activity" (Read, pane key `understand`)   → the Feed narrative + run ledger (escape hatch)
 *   "Schedule" (Tune, pane key `tune`)         → the recurring-work list (escape hatch → full Recurrence)
 *
 * One object, two zooms: the topbar bell ("Notifications") is the glance;
 * this window is the full surface. They share one name + one vocabulary (To
 * do / Activity / Coming up — ADR-346 §5a). Pane keys + act identities
 * (Decide/Read/Tune, ADR-340 D2) are unchanged through the rename.
 *
 * It is a COMPOSITION over the operational mirrors, not a new mirror: it owns
 * no substrate and no state, and each pane reuses an existing mirror BODY
 * (one body, two mounts — the ADR-340 D8 rule) with an "Open full ___ →"
 * escape hatch into the complete mirror. Mounts the shared SettingsPaneShell
 * (Singular Implementation, the same shell behind both Settings doors), in
 * fullBleed mode so the Feed/Recurrence panes fill the pane region.
 *
 * Launcher: primary tier (Workspace group, ADR-349) — the default
 * destination for operating work. The mirrors it fronts (Feed/Queue/
 * Recurrence) are search-only (ADR-349) — complete + reachable by name, no
 * longer the default route in. /operation is an ADR-308 redirect stub here.
 */

import { ExternalLink, ClipboardCheck, ScrollText, Clock } from "lucide-react";
import { useSurfacePreferences } from "@/lib/shell/useSurfacePreferences";
import { useAgentsAndRecurrences } from "@/hooks/useAgentsAndRecurrences";
import { SettingsPaneShell, PaneHeader, type PaneGroup } from "@/components/settings/SettingsPaneShell";
import { QueueBody } from "@/components/queue/QueueBody";
import { StandingBand } from "@/components/queue/StandingBand";
import { FeedSurface } from "@/components/feed-surface/FeedSurface";
import { RecurrenceList } from "@/components/work/RecurrenceList";

// ADR-346 label pass (2026-06-19): the act labels are plain operator words
// — "To do" (the queue), "Activity" (what happened), "Schedule" (the
// recurring work). The Attention center's section headers use the SAME
// words so the bell and the surface it lands on speak one language. The
// pane KEYS (resolve/understand/tune) are unchanged — they are URL params
// + the ADR-340 D2 act identities (Decide/Read/Tune); only the labels change.
const PANE_GROUPS: PaneGroup[] = [
  {
    label: "Operate",
    panes: [
      { key: "resolve", label: "To do", icon: ClipboardCheck },
      { key: "understand", label: "Activity", icon: ScrollText },
      { key: "tune", label: "Schedule", icon: Clock },
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
              action={<MirrorLink label="Open full Queue" onClick={() => navigateToSurface("queue")} />}
            />
            <div className="flex-1 overflow-y-auto p-6">
              {/* ADR-350: the standing obligation (owed-vs-actual + the
                  Reviewer's standing intent) renders above the discrete
                  proposals — an unmet mandate is the deepest "to do". */}
              <StandingBand />
              <QueueBody />
            </div>
          </div>
        );
      case "understand":
        // Read — the Feed narrative. FeedSurface fills the pane region; its
        // own header carries filter + chat-summon. The run ledger is one hop
        // away via the Recurrence Runs lens.
        return (
          <div className="flex h-full flex-col">
            <PaneHeader
              icon={ScrollText}
              title="Activity"
              subtitle="What just happened — the narrative of every invocation."
              action={<MirrorLink label="Open run ledger" onClick={() => navigateToSurface("recurrence", { pane: "activity" })} />}
            />
            <div className="flex-1 min-h-0">
              <FeedSurface />
            </div>
          </div>
        );
      case "tune":
        // Tune — the recurring-work list. Selecting a row deep-links into the
        // full Recurrence window (detail mode: ?task=slug), where pause /
        // run-now / edit live. The list is the glance; the window is the bench.
        return (
          <TunePane
            onSelect={(slug) => navigateToSurface("recurrence", { task: slug })}
            onOpenFull={() => navigateToSurface("recurrence")}
          />
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

/**
 * TunePane — the recurring-work glance. Reuses RecurrenceList (the same body
 * the Recurrence mirror renders in list mode); selection deep-links into the
 * full Recurrence window where the Run/Pause/Edit controls live.
 */
function TunePane({ onSelect, onOpenFull }: { onSelect: (slug: string) => void; onOpenFull: () => void }) {
  const { agents, tasks, narrativeByTask, error } = useAgentsAndRecurrences({ includeNarrative: true });

  return (
    <div className="flex h-full flex-col">
      <PaneHeader
        icon={Clock}
        title="Schedule"
        subtitle="The recurring work — pick a row to pause, run now, or edit."
        action={<MirrorLink label="Open full Schedule" onClick={onOpenFull} />}
      />
      <div className="flex-1 overflow-y-auto">
        <RecurrenceList
          tasks={tasks}
          agents={agents}
          narrativeByTask={narrativeByTask}
          agentFilter={null}
          dataError={error}
          onClearAgentFilter={() => {}}
          onSelect={onSelect}
        />
      </div>
    </div>
  );
}
