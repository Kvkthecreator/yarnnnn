"use client";

/**
 * Workspace Danger Zone — the workspace-CONTENT purges (ADR-476 D3).
 *
 * L1 (clear work history) and L2 (clear workspace) destroy shared content:
 * in a multi-member workspace they remove EVERY member's work, not the
 * caller's own rows. Under ADR-407's three-scope taxonomy that makes them
 * workspace-scope, not account-scope — so they live here rather than in User
 * Settings (which keeps L3/L4/L5: a member's own platform connections, their
 * account reset, their deactivation). Those are split across TWO panes there:
 * connections on `connectors` (ADR-425), reset + deactivate on `account`.
 *
 * The backend gates both on owner-grade authority (ADR-476 D2 —
 * `workspaces.owner_id` or a grant carrying `workspace:clear`), so a
 * non-owner member gets a 403. This component surfaces that up-front rather
 * than letting the operator discover it at confirm time.
 *
 * Singular Implementation: the purge cards live only here — and as of
 * 2026-08-20 that is TRUE rather than merely asserted. The cards moved with
 * ADR-476 D3 but their plumbing did not: User Settings kept a `DangerAction`
 * type carrying "work-history"/"workspace", live handler branches calling
 * clearWorkHistory()/clearWorkspace(), confirm copy for both, and a
 * workspace-scoped stats grid. All unreachable (nothing set those values), all
 * now deleted. A comment claiming singularity is not singularity.
 */

import { useCallback, useEffect, useState } from "react";
import {
  AlertTriangle,
  Database,
  History,
  Loader2,
  RefreshCw,
  Users,
} from "lucide-react";

import { useTranslations } from "next-intl";

import { api, APIError } from "@/lib/api/client";
import { useFeedback } from "@/contexts/FeedbackContext";
import { useWorkspaceMemberships } from "@/lib/workspace/viewer";
import { WorkspaceDeleteCard } from "./WorkspaceDeleteCard";
import { WorkspaceExportCard } from "./WorkspaceExportCard";
// Cross-door links go through the window manager, not a hard navigation
// (2026-08-20) — see SurfaceLink's docblock for the two-step this avoids.
import { SurfaceLink } from "@/components/shell/SurfaceLink";
import { Working } from '@/components/shared/Working';

interface DangerZoneStats {
  workspace_files: number;
  // `work_history_files` REPLACES `agent_runs` (2026-08-26). The card below is
  // GATED on this number, and `agent_runs` counted a table that had been empty
  // for as long as it existed — so "Clear History" was permanently disabled
  // while still deleting real output folders. This counts what L1 clears.
  work_history_files: number;
  tasks: number;
  chat_sessions: number;
  platform_connections: number;
  action_proposals: number;
}

type WorkspaceAction = "work-history" | "workspace";

export function WorkspaceDangerZone() {
  const t = useTranslations("workspaceSettings.danger");
  const [stats, setStats] = useState<DangerZoneStats | null>(null);
  const [loading, setLoading] = useState(false);
  // ADR-501: the server's own clear-authority verdict (`can_clear` on
  // /workspace/memberships — owner OR the `workspace:clear` grant scope),
  // never predicted from the role label (ADR-405: the test is "which grant").
  // Derived, never stored (DP29). The backend gate remains the authority —
  // this only avoids offering an action that would 403.
  const [canClear, setCanClear] = useState(true);
  // The ACTING workspace, from the server's own `is_active` flag. NOT
  // getActiveWorkspaceId(): the pin is null for an owner (switching to your own
  // workspace CLEARS it), which is precisely the caller who may delete.
  const { memberships } = useWorkspaceMemberships();
  const activeWorkspaceId = memberships.find((m) => m.is_active)?.workspace_id ?? null;
  // The acting workspace's NAME, for the typed confirmation on L2. `label` is
  // the server's own display name (workspace name, else a humanized fallback),
  // so the string the operator is asked to type is the string every other
  // surface shows them.
  const activeWorkspaceLabel = memberships.find((m) => m.is_active)?.label ?? null;
  const [otherMemberCount, setOtherMemberCount] = useState(0);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const [ms, roster] = await Promise.all([
          api.workspace.memberships(),
          api.workspace.getMembers(),
        ]);
        if (cancelled) return;
        setCanClear(ms.can_clear !== false);
        const humans = roster.members.filter(
          (m) => m.role === "owner" || m.role === "member",
        );
        setOtherMemberCount(Math.max(0, humans.length - 1));
      } catch {
        // Leave the optimistic default: the backend gate is the real authority,
        // and a failed probe must not lock an owner out of their own surface.
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);
  const [pending, setPending] = useState<WorkspaceAction | null>(null);
  const [confirming, setConfirming] = useState<WorkspaceAction | null>(null);
  // The outcome reports through the canonical action-feedback layer
  // (ACTION-FEEDBACK.md). The bespoke `result` state that used to carry it is
  // DELETED: one `{ ok, message }` var rendered both arms, so a failure printed
  // in the same muted line as a success — the exact shared channel rule 6 bans.
  // `pending` stays: that is the button's own spinner, not a notice.
  const { runAction } = useFeedback();

  const loadStats = useCallback(async () => {
    setLoading(true);
    try {
      setStats(await api.account.getDangerZoneStats());
    } catch {
      setStats(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadStats();
  }, [loadStats]);

  const run = async (action: WorkspaceAction) => {
    const isHistory = action === "work-history";
    setPending(action);
    setConfirming(null);
    try {
      // The server counts what it removed and says so; that sentence is the
      // only honest success line here (a fixed "Cleared" would claim a number
      // nobody measured), so the success toast repeats it.
      await runAction(
        () =>
          isHistory
            ? api.account.clearWorkHistory()
            : api.account.clearWorkspace(),
        {
          pending: isHistory ? t("history.pending") : t("workspace.pending"),
          success: (res) =>
            res.message ||
            (isHistory ? t("history.success") : t("workspace.success")),
          error: (e) =>
            e instanceof APIError
              ? (e.data as { detail?: string })?.detail ||
                (isHistory ? t("history.failed") : t("workspace.failed"))
              : isHistory
                ? t("history.failed")
                : t("workspace.failed"),
        },
      );
      await loadStats();
    } catch {
      // Reported by runAction. The counts on the cards are left as they were —
      // nothing was removed, so nothing to re-read.
    } finally {
      setPending(null);
    }
  };

  // The shared-content sentence. This is the ADR-476 §4 falsifier made visible:
  // a member may reasonably expect "clear" to mean "my contributions" — the
  // copy has to say plainly that it does not.
  const sharedWarning =
    otherMemberCount > 0
      ? t("sharedWarning", { count: otherMemberCount })
      : null;

  if (loading && !stats) {
    return (
      <Working label={t("loading")} fill />
    );
  }

  if (!stats) {
    return (
      <p className="text-sm text-muted-foreground">
        {t("statsFailed")}{" "}
        <button onClick={() => void loadStats()} className="underline">
          {t("retry")}
        </button>
      </p>
    );
  }

  return (
    <div className="space-y-4">
      {sharedWarning && (
        <div className="flex items-start gap-2 p-3 rounded-lg border border-amber-300 dark:border-amber-800 bg-amber-50 dark:bg-amber-950/30 text-sm">
          <Users className="w-4 h-4 mt-0.5 text-amber-600 dark:text-amber-400 shrink-0" />
          <span className="text-amber-900 dark:text-amber-200">{sharedWarning}</span>
        </div>
      )}

      {!canClear && (
        <div className="flex items-start gap-2 p-3 rounded-lg border border-border bg-muted/40 text-sm">
          <AlertTriangle className="w-4 h-4 mt-0.5 text-muted-foreground shrink-0" />
          <span className="text-muted-foreground">{t("notOwner")}</span>
        </div>
      )}

      {/* ADR-328 D4 — the copy comes out BEFORE anything empties or ends the
          workspace. Not destructive, so it is not gated on clear-authority. */}
      <WorkspaceExportCard />

      {/* L1 — clear work history */}
      <ActionCard
        icon={<History className="w-4 h-4 text-amber-600 dark:text-amber-400" />}
        title={t("history.title")}
        description={t("history.description", { count: stats.work_history_files })}
        cta={t("history.cta")}
        tone="amber"
        disabled={!canClear || stats.work_history_files === 0 || pending !== null}
        busy={pending === "work-history"}
        confirming={confirming === "work-history"}
        confirmCopy={t("history.confirm")}
        onAsk={() => setConfirming("work-history")}
        onCancel={() => setConfirming(null)}
        onConfirm={() => void run("work-history")}
      />

      {/* L2 — clear workspace */}
      <ActionCard
        icon={<Database className="w-4 h-4 text-orange-600 dark:text-orange-400" />}
        title={t("workspace.title")}
        description={t("workspace.description", {
          files: stats.workspace_files,
          proposals: stats.action_proposals,
        })}
        cta={t("workspace.cta")}
        tone="orange"
        disabled={
          !canClear ||
          (stats.workspace_files === 0 && stats.action_proposals === 0) ||
          pending !== null
        }
        busy={pending === "workspace"}
        confirming={confirming === "workspace"}
        confirmCopy={t("workspace.confirm")}
        typeToConfirm={activeWorkspaceLabel}
        onAsk={() => setConfirming("workspace")}
        onCancel={() => setConfirming(null)}
        onConfirm={() => void run("workspace")}
      />

      {/* ADR-578 — ending the workspace, below the two that empty it. Clearing
          keeps the workspace; deleting ends it. */}
      <WorkspaceDeleteCard workspaceId={activeWorkspaceId} />

      {/* Two doors, two scopes. Connections moved to the Connectors pane
          (ADR-425 — a human's credential is an account object), so they need
          their own link: the Account pane no longer carries them. Name each
          pane as its sidebar labels it, or the reader hunts for a menu item
          that isn't there. */}
      <p className="text-xs text-muted-foreground pt-2 border-t border-border">
        {t.rich("accountPointer", {
          reach: (chunks) => (
            <SurfaceLink to="reach" params={{ pane: "connected" }} className="underline">
              {chunks}
            </SurfaceLink>
          ),
          settings: (chunks) => (
            <SurfaceLink to="settings" params={{ pane: "account" }} className="underline">
              {chunks}
            </SurfaceLink>
          ),
        })}
      </p>
    </div>
  );
}

function ActionCard({
  icon,
  title,
  description,
  cta,
  tone,
  disabled,
  busy,
  confirming,
  confirmCopy,
  typeToConfirm,
  onAsk,
  onCancel,
  onConfirm,
}: {
  icon: React.ReactNode;
  title: string;
  description: string;
  cta: string;
  tone: "amber" | "orange";
  disabled: boolean;
  busy: boolean;
  confirming: boolean;
  confirmCopy: string;
  /** When set, the operator must type this string to enable Confirm. OPT-IN:
   *  only the IRREVERSIBLE act carries it (L2 wipes every member's files with
   *  no undo). L1 stays a two-click act — putting friction on the lighter one
   *  too would just train people to type through the heavier one. */
  typeToConfirm?: string | null;
  onAsk: () => void;
  onCancel: () => void;
  onConfirm: () => void;
}) {
  const t = useTranslations("workspaceSettings.danger");
  // Local to the card: cleared on cancel so a reopened confirm starts empty.
  const [typed, setTyped] = useState("");
  // Trimmed + case-insensitive — a speed bump that makes the operator NAME
  // what they are destroying, not a spelling test.
  const confirmSatisfied =
    !typeToConfirm ||
    typed.trim().toLowerCase() === typeToConfirm.trim().toLowerCase();

  const border =
    tone === "amber"
      ? "border-amber-200 dark:border-amber-900/50"
      : "border-orange-200 dark:border-orange-900/50";
  const button =
    tone === "amber"
      ? "text-amber-700 dark:text-amber-400 border-amber-300 dark:border-amber-700 hover:bg-amber-50 dark:hover:bg-amber-950/40"
      : "text-orange-700 dark:text-orange-400 border-orange-300 dark:border-orange-700 hover:bg-orange-50 dark:hover:bg-orange-950/40";

  return (
    <div className={`p-4 border rounded-lg ${border}`}>
      <div className="flex items-center justify-between gap-4">
        <div>
          <div className="font-medium flex items-center gap-2">
            {icon}
            {title}
          </div>
          <div className="text-sm text-muted-foreground">{description}</div>
        </div>
        {confirming ? (
          <div className="flex items-center gap-2 shrink-0">
            {typeToConfirm && (
              <label className="inline-flex items-center gap-2 text-sm">
                <span className="text-muted-foreground">
                  {t.rich("typeToConfirm", {
                    name: typeToConfirm,
                    b: (chunks) => (
                      <span className="font-medium text-foreground">{chunks}</span>
                    ),
                  })}
                </span>
                <input
                  type="text"
                  value={typed}
                  onChange={(e) => setTyped(e.target.value)}
                  aria-label={t("typeToConfirmAria", { name: typeToConfirm })}
                  autoComplete="off"
                  className="w-40 rounded-md border border-border bg-background px-2 py-1 text-sm"
                />
              </label>
            )}
            <button
              onClick={() => {
                setTyped("");
                onCancel();
              }}
              className="px-3 py-2 text-sm text-muted-foreground hover:text-foreground"
            >
              {t("cancel")}
            </button>
            <button
              onClick={onConfirm}
              disabled={!confirmSatisfied}
              className="px-4 py-2 text-sm font-medium rounded-md border border-destructive/50 text-destructive hover:bg-destructive/10 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {t("confirmCta")}
            </button>
          </div>
        ) : (
          <button
            onClick={onAsk}
            disabled={disabled}
            className={`px-4 py-2 border rounded-md text-sm font-medium shrink-0 disabled:opacity-40 disabled:cursor-not-allowed ${button}`}
          >
            {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : cta}
          </button>
        )}
      </div>
      {confirming && (
        <p className="text-sm text-destructive mt-3">{confirmCopy}</p>
      )}
    </div>
  );
}
