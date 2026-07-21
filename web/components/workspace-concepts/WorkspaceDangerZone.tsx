"use client";

/**
 * Workspace Danger Zone — the workspace-CONTENT purges (ADR-476 D3).
 *
 * L1 (clear work history) and L2 (clear workspace) destroy shared content:
 * in a multi-member workspace they remove EVERY member's work, not the
 * caller's own rows. Under ADR-407's three-scope taxonomy that makes them
 * workspace-scope, not account-scope — so they live here rather than in
 * System Settings → Account (which keeps L3/L4/L5: a member's own platform
 * connections, their account reset, their deactivation).
 *
 * The backend gates both on owner-grade authority (ADR-476 D2 —
 * `workspaces.owner_id` or a grant carrying `workspace:clear`), so a
 * non-owner member gets a 403. This component surfaces that up-front rather
 * than letting the operator discover it at confirm time.
 *
 * Singular Implementation: the purge CARDS live only here. System Settings
 * mounts nothing of L1/L2 — it links across.
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

import { api } from "@/lib/api/client";

interface DangerZoneStats {
  workspace_files: number;
  agents: number;
  tasks: number;
  chat_sessions: number;
  platform_connections: number;
  platform_context_files: number;
  agent_runs: number;
  action_proposals: number;
}

type WorkspaceAction = "work-history" | "workspace";

export function WorkspaceDangerZone() {
  const [stats, setStats] = useState<DangerZoneStats | null>(null);
  const [loading, setLoading] = useState(false);
  // ADR-476 D2 mirrored from the same facts the backend gates on: the caller's
  // role for the ACTING workspace (`/workspace/memberships`) and the human
  // roster (`/workspace/members`). Derived, never stored (DP29). The backend
  // is the authority — this only avoids offering an action that would 403.
  const [canClear, setCanClear] = useState(true);
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
        const active = ms.memberships.find((m) => m.is_active) ?? ms.memberships[0];
        setCanClear(active?.role === "owner");
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
  const [result, setResult] = useState<{ ok: boolean; message: string } | null>(null);

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
    setPending(action);
    setConfirming(null);
    setResult(null);
    try {
      const res =
        action === "work-history"
          ? await api.account.clearWorkHistory()
          : await api.account.clearWorkspace();
      setResult({ ok: true, message: res.message });
      await loadStats();
    } catch (err) {
      setResult({
        ok: false,
        message: err instanceof Error ? err.message : "Action failed",
      });
    } finally {
      setPending(null);
    }
  };

  // The shared-content sentence. This is the ADR-476 §4 falsifier made visible:
  // a member may reasonably expect "clear" to mean "my contributions" — the
  // copy has to say plainly that it does not.
  const sharedWarning =
    otherMemberCount > 0
      ? `This workspace has ${otherMemberCount} other member${otherMemberCount === 1 ? "" : "s"}. These actions remove everyone's work, not just yours.`
      : null;

  if (loading && !stats) {
    return (
      <div className="flex items-center justify-center py-8">
        <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (!stats) {
    return (
      <p className="text-sm text-muted-foreground">
        Could not load workspace data.{" "}
        <button onClick={() => void loadStats()} className="underline">
          Retry
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
          <span className="text-muted-foreground">
            Only the workspace owner can clear shared content.
          </span>
        </div>
      )}

      {/* L1 — clear work history */}
      <ActionCard
        icon={<History className="w-4 h-4 text-amber-600 dark:text-amber-400" />}
        title="Clear Work History"
        description={`Delete ${stats.agent_runs} past run records and all dated output folders. Scheduled work, agents, identity, and accumulated context are preserved.`}
        cta="Clear History"
        tone="amber"
        disabled={!canClear || stats.agent_runs === 0 || pending !== null}
        busy={pending === "work-history"}
        confirming={confirming === "work-history"}
        confirmCopy="This deletes every member's run records and outputs. Continue?"
        onAsk={() => setConfirming("work-history")}
        onCancel={() => setConfirming(null)}
        onConfirm={() => void run("work-history")}
      />

      {/* L2 — clear workspace */}
      <ActionCard
        icon={<Database className="w-4 h-4 text-orange-600 dark:text-orange-400" />}
        title="Clear Workspace"
        description={`Delete ${stats.agents} agents, ${stats.workspace_files} workspace files, ${stats.action_proposals} pending proposals, and all activity. The workspace is re-scaffolded afterwards.`}
        cta="Clear Workspace"
        tone="orange"
        disabled={
          !canClear ||
          (stats.workspace_files === 0 &&
            stats.agents === 0 &&
            stats.action_proposals === 0) ||
          pending !== null
        }
        busy={pending === "workspace"}
        confirming={confirming === "workspace"}
        confirmCopy="This removes all workspace content for every member. Continue?"
        onAsk={() => setConfirming("workspace")}
        onCancel={() => setConfirming(null)}
        onConfirm={() => void run("workspace")}
      />

      {result && (
        <p
          className={`text-sm ${result.ok ? "text-muted-foreground" : "text-destructive"}`}
        >
          {result.message}
        </p>
      )}

      <p className="text-xs text-muted-foreground pt-2 border-t border-border">
        Looking for account-level actions? Disconnecting your own platform
        connections, resetting your account, and deactivating live in{" "}
        <a href="/settings?pane=account" className="underline">
          System Settings → Account
        </a>
        .
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
  onAsk: () => void;
  onCancel: () => void;
  onConfirm: () => void;
}) {
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
            <button
              onClick={onCancel}
              className="px-3 py-2 text-sm text-muted-foreground hover:text-foreground"
            >
              Cancel
            </button>
            <button
              onClick={onConfirm}
              className="px-4 py-2 text-sm font-medium rounded-md border border-destructive/50 text-destructive hover:bg-destructive/10"
            >
              Confirm
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
