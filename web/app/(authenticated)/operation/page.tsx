"use client";

/**
 * /operation — the Operation surface, the SECOND composition window
 * (ADR-346, 2026-06-19). Home was the first composition (Dwell); this one
 * carries the three operating-work acts ADR-340 D2 named but never built a
 * composition for:
 *
 *   "To do"    (Decide, pane key `resolve`)    → the Queue body over action_proposals
 *   "Activity" (Read, pane key `understand`)   → the Feed narrative + run ledger (escape hatch)
 *   "Schedule" (Tune, pane key `tune`)         → the recurring-work list (escape hatch → full Recurrence)
 *
 * Label pass (2026-06-19): the operator-facing labels are plain words ("To
 * do" / "Activity" / "Schedule"); the Attention center uses the SAME words
 * for its section headers so the bell and this surface speak one language.
 * Pane keys + act identities (Decide/Read/Tune, ADR-340 D2) are unchanged.
 *
 * It is a COMPOSITION over the operational mirrors, not a new mirror: it owns
 * no substrate and no state, and each pane reuses an existing mirror BODY
 * (one body, two mounts — the ADR-340 D8 rule) with an "Open full ___ →"
 * escape hatch into the complete mirror. Mounts the shared SettingsPaneShell
 * (Singular Implementation, the same shell behind both Settings doors), in
 * fullBleed mode so the Feed/Recurrence panes fill the pane region.
 *
 * Launcher: primary tier — the default destination for operating work. The
 * mirrors it fronts (Feed, Queue) demote to utilities in the same ADR; they
 * stay complete + reachable, just no longer the default route in.
 *
 * (Replaces the pre-launch /operation → /mandate redirect stub, dead after
 * the ADR-297 atomic-shell migration — nothing linked to the /operation
 * route; verified before overwrite.)
 */

import { ExternalLink, ClipboardCheck, ScrollText, Clock } from "lucide-react";
import { useSurfacePreferences } from "@/lib/shell/useSurfacePreferences";
import { useAgentsAndRecurrences } from "@/hooks/useAgentsAndRecurrences";
import { SettingsPaneShell, type PaneGroup } from "@/components/settings/SettingsPaneShell";
import { QueueBody } from "@/components/queue/QueueBody";
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

/** Shared pane header — title + subtitle + escape-hatch link. */
function PaneHeader({ title, subtitle, link }: { title: string; subtitle: string; link: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between border-b border-border/60 px-6 py-3 shrink-0">
      <div>
        <h2 className="text-sm font-medium text-foreground">{title}</h2>
        <p className="text-xs text-muted-foreground">{subtitle}</p>
      </div>
      {link}
    </div>
  );
}

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
              title="To do"
              subtitle="What wants your decision — approve or reject below."
              link={<MirrorLink label="Open full Queue" onClick={() => navigateToSurface("queue")} />}
            />
            <div className="flex-1 overflow-y-auto p-6">
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
              title="Activity"
              subtitle="What just happened — the narrative of every invocation."
              link={<MirrorLink label="Open run ledger" onClick={() => navigateToSurface("recurrence", { pane: "activity" })} />}
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
      paneGroups={PANE_GROUPS}
      defaultPane="resolve"
      renderPane={renderPane}
      fullBleed
      navLabel="Operation acts"
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
        title="Schedule"
        subtitle="The recurring work — pick a row to pause, run now, or edit."
        link={<MirrorLink label="Open full Recurrence" onClick={onOpenFull} />}
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
