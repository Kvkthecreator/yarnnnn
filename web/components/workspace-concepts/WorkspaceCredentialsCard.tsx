"use client";

/**
 * WorkspaceCredentialsCard — what this workspace's AGENTS act through (ADR-566 D5).
 *
 * ⚠️ THIS IS NOT THE ACCOUNT DOOR'S CONNECTORS PANE, and the difference is the
 * whole point. ADR-425 D1 moved a HUMAN's connectors to their account door and
 * that ruling stands untouched: a member's own Slack is theirs, keyed `user_id`,
 * and no agent reaches it. This pane renders the OTHER store — credentials the
 * workspace allocated, keyed `workspace_id`, which its `own-agent` principals
 * act through (ADR-566 D2/D3).
 *
 * The pane ADR-425 removed presented HUMANS' connectors under a workspace
 * heading, which was the mis-scoping it correctly fixed. This one presents the
 * workspace's own. Two panes, two questions — never re-merged.
 *
 * ⚠️ READING IS NOT AUTHORITY. A member sees what the workspace's agents can
 * reach (commons legibility, DP29 — an agent whose capabilities are
 * unexplainable is worse than one whose reach is visible). Allocation is
 * workspace governance, so the acting affordance is authority-gated
 * (`can_manage`, the ADR-491 D1 convention Billing already uses).
 *
 * ⚠️ EVERY ROW STATES ITS CEILING (ADR-535 D3's discipline). A credential
 * grants REACH, never AUTHORITY: a consequential act through one still passes
 * the ADR-307 gate and waits for approval. Naming a capability's edge is part
 * of granting it — without it, a reader infers that allocating Slack means the
 * agent can post, and it cannot.
 */

import { useEffect, useState } from "react";
import { Loader2, ShieldCheck } from "lucide-react";
import { api } from "@/lib/api/client";
import { connectorMeta } from "@/lib/connectors/registry";

interface WorkspaceCredential {
  id: string;
  provider: string;
  status: string;
  workspace_name: string | null;
  connected_at: string;
}

export function WorkspaceCredentialsCard() {
  const [credentials, setCredentials] = useState<WorkspaceCredential[] | null>(null);
  const [canManage, setCanManage] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const res = await api.integrations.workspaceCredentials();
        if (cancelled) return;
        setCredentials(res.credentials ?? []);
        setCanManage(Boolean(res.can_manage));
      } catch {
        // Shown, never swallowed — a pane that silently renders empty reads as
        // "nothing allocated", which is a different and wrong fact.
        if (!cancelled) setError("Couldn't load the workspace's credentials.");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  if (credentials === null && !error) {
    return (
      <div className="py-8 grid place-items-center">
        <Loader2 className="w-4 h-4 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <p className="text-xs text-muted-foreground leading-relaxed">
        Credentials this workspace has allocated to its agents. These belong to
        the workspace, not to any person — your own connections live in your
        account settings and no agent uses them.
      </p>

      {error && (
        <p className="text-xs text-destructive" role="alert">
          {error}
        </p>
      )}

      {credentials && credentials.length === 0 && !error && (
        <p className="text-xs text-muted-foreground py-3">
          Nothing allocated yet. This workspace&apos;s agents can read and write
          files here, and reach nothing outside it.
        </p>
      )}

      {credentials && credentials.length > 0 && (
        <div className="space-y-1.5">
          {credentials.map((c) => {
            const meta = connectorMeta(c.provider);
            return (
              <div
                key={c.id}
                className="flex items-center gap-3 p-2.5 rounded-md border border-border"
              >
                <span className="min-w-0 flex-1">
                  <span className="block text-sm">{meta?.displayName ?? c.provider}</span>
                  {c.workspace_name && (
                    <span className="block text-xs text-muted-foreground truncate">
                      {c.workspace_name}
                    </span>
                  )}
                </span>
                <span className="text-xs text-muted-foreground shrink-0">
                  {c.status === "active" ? "Allocated" : c.status}
                </span>
              </div>
            );
          })}
        </div>
      )}

      {/* THE CEILING, stated affirmatively (ADR-535 D3). Prose, because it is a
          true sentence about a gate that already holds — not a switch. */}
      <p className="text-[11px] text-muted-foreground/70 flex items-start gap-1.5 border-t border-border pt-4">
        <ShieldCheck className="w-3 h-3 mt-0.5 shrink-0" />
        Allocating a credential lets your agents see it — it does not let them
        act on their own. Anything they send, post, or spend still waits for
        someone to approve it.
      </p>

      {!canManage && credentials && credentials.length > 0 && (
        <p className="text-[11px] text-muted-foreground/70">
          An owner can change what&apos;s allocated here.
        </p>
      )}
    </div>
  );
}
