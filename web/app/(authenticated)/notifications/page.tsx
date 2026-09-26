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
 * declarations; retire-clean. Run RECEIPTS surface here in the Activity
 * ledger (`invocation` kind over execution_events), which is ADR-603's own
 * sentence: "runs stop being a concept: receipts surface in notifications."
 * The `tune` pane key retires with the pane.
 *
 * ADR-639 (2026-09-04): "Standing work" (pane key `standing`) JOINS — the
 * roster of files kept current + the two direct switches (Run now · Pause).
 * Standing work is a kernel lane, not an app: its declaration lives beside
 * the kept file, its run is a daemon, its craft is a skill, and this is where
 * a member reads what stands (ADR-603 D4's lens, housed). The Strings app
 * that carried it is deleted; /strings redirects here. The steward-era
 * StandingBand (the Reviewer's standing intent, retired with ADR-632) is
 * deleted from the To-do pane in the same change — "standing" means
 * declarations now, and a fossil in that slot was the ambiguity itself.
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

import { useTranslations } from "next-intl";
import { ExternalLink, ClipboardCheck, ClipboardList, ScrollText } from "lucide-react";
import { useSurfacePreferences } from "@/lib/shell/useSurfacePreferences";
import { SettingsPaneShell, PaneHeader, type PaneGroup } from "@/components/settings/SettingsPaneShell";
import { QueueBody } from "@/components/queue/QueueBody";
import { ActivityLedger } from "@/components/notifications/ActivityLedger";
import { MentionQueue } from "@/components/notifications/MentionQueue";
import { WaitingRunQueue } from "@/components/notifications/WaitingRunQueue";
import { StandingWork } from "@/components/notifications/StandingWork";
import { SurfaceBoundary } from '@/components/shell/SurfaceBoundary';

// ADR-346 label pass (2026-06-19): the act labels are plain operator words.
// The pane KEYS (resolve/understand) are unchanged — they are URL params +
// the ADR-340 D2 act identities (Decide/Read); only the roster shrank
// (ADR-603 D5 removed `tune`).
// ADR-660: the roster holds catalog KEYS — it is evaluated at import, before
// any member's language is known; the labels are worded inside the component.
const PANE_ROSTER = [
  {
    labelKey: "groupOperate",
    panes: [
      { key: "resolve", labelKey: "paneToDo", icon: ClipboardCheck },
      { key: "understand", labelKey: "paneActivity", icon: ScrollText },
      { key: "standing", labelKey: "paneStanding", icon: ClipboardList },
    ],
  },
] as const;

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

function OperationPageBody() {
  const t = useTranslations("supervisor.notifications");
  const { navigateToSurface } = useSurfacePreferences();

  const paneGroups: PaneGroup[] = PANE_ROSTER.map((g) => ({
    label: t(g.labelKey),
    panes: g.panes.map((p) => ({ key: p.key, label: t(p.labelKey), icon: p.icon })),
  }));

  const renderPane = (pane: string) => {
    switch (pane) {
      case "resolve":
        // Decide — the Queue body. "Open full Queue →" keeps the complete
        // decide mirror one click away (ADR-346 D1 escape hatch).
        return (
          <div className="flex h-full flex-col">
            <PaneHeader
              icon={ClipboardCheck}
              title={t("paneToDo")}
              subtitle={t("toDoSubtitle")}
              action={
                <div className="flex items-center gap-4">
                  {/* ADR-642 D4 — the Queue surface is absorbed by Reach; what
                      is about to LEAVE the workspace has its door there. */}
                  <MirrorLink label={t("openReach")} onClick={() => navigateToSurface("reach", { pane: "leaving" })} />
                  {/* ADR-593 D5 — the window finally links the settings that
                      govern what reaches its viewer. */}
                  <MirrorLink
                    label={t("notificationSettings")}
                    onClick={() => navigateToSurface("settings", { pane: "notification-settings" })}
                  />
                </div>
              }
            />
            <div className="flex-1 overflow-y-auto p-6">
              {/* ADR-670 D5 — every section reads ONE store (`useNeedsYou`):
                  runs due on the viewer, unresolved mentions (ADR-605,
                  discharged by visiting or by Dismiss), then decisions. */}
              <WaitingRunQueue />
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
              title={t("paneActivity")}
              subtitle={t("activitySubtitle")}
            />
            <div className="flex-1 min-h-0">
              <ActivityLedger />
            </div>
          </div>
        );
      case "standing":
        // Keep — what stands (ADR-639 D4): every declaration the kernel
        // discovers, its cadence, its last run, and the two direct switches.
        return (
          <div className="flex h-full flex-col">
            <PaneHeader
              icon={ClipboardList}
              title={t("paneStanding")}
              subtitle={t("standingSubtitle")}
            />
            <div className="flex-1 min-h-0">
              <StandingWork />
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
      paneGroups={paneGroups}
      defaultPane="resolve"
      renderPane={renderPane}
      fullBleed
      navLabel={t("navLabel")}
    />
  );
}

/**
 * The route's export. `OperationPageBody` reads `useSearchParams` (directly or through
 * the shell's param hooks), so the Suspense boundary must sit OUTSIDE it —
 * a boundary inside the component is reached only after the hook has already
 * run. ADR-661 §8 step 3.
 */
export default function OperationPage() {
  return (
    <SurfaceBoundary>
      <OperationPageBody />
    </SurfaceBoundary>
  );
}
