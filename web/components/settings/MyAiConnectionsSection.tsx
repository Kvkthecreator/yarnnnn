"use client";

/**
 * MyAiConnectionsSection — the viewer's OWN inbound AI connections, mirrored
 * into the account door (ADR-496 D1).
 *
 * ## Why this exists
 *
 * An MCP connection is a MEMBER's connection, not the workspace's — ADR-431 §2
 * made that a relational fact (`principal_grants.connected_by`), because it is
 * authorized under one human's OAuth session, perceives on their behalf, and
 * tears down on THEIR eviction. But the only surface that rendered it was
 * Workspace Settings → Members, whose primary job is governing OTHER people. A
 * member asking the ordinary question *"what have I connected?"* had to open a
 * workspace-governance surface and visually filter for their own rows.
 *
 * That is the same account-object argument ADR-425 already made for outbound
 * platform credentials ("a credential is a human's account object"), applied to
 * the inbound side of the same MCP boundary. Both halves of a member's own
 * connections now answer on the account door.
 *
 * ## What this is NOT
 *
 * A second governance surface. Per ADR-340 DP29 ("mirror once, compose few")
 * this is a READ-ONLY mirror:
 *   • It shows ONLY grants the viewer themself authorized (`connected_by_is_you`).
 *     A member never sees a peer's connection here — that is the roster's job.
 *   • It carries NO narrow/revoke verbs, no invite box, no seat accounting.
 *     Governance stays singular in `WorkspaceMembersCard`; this links across.
 *
 * Rendering intentionally reuses the roster's own primitives (the shared
 * `providerBrandIcon` module, the same zone chips) so the two surfaces cannot
 * drift into two visual languages for one fact.
 */

import { useEffect, useState } from "react";
import { ArrowRight, Loader2, Plug } from "lucide-react";
import { api } from "@/lib/api/client";
import { providerBrandIcon } from "@/lib/ai-providers/brand-icons";

/** The roles that are inbound AI principals (ADR-373 role vocabulary). */
const EXTERNAL_AI_ROLES = new Set(["foreign-llm", "a2a", "platform"]);

const ROLE_LABEL: Record<string, string> = {
  "foreign-llm": "External LLM",
  a2a: "Agent-to-agent",
  platform: "Platform",
};

interface MemberRow {
  principal_id: string;
  role: string;
  label?: string | null;
  connected_by_is_you?: boolean;
  write_zones?: string[] | null;
}

export function MyAiConnectionsSection() {
  const [rows, setRows] = useState<MemberRow[] | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await api.workspace.getMembers();
        if (cancelled) return;
        // ADR-496 D1 — the viewer's OWN connections only. `connected_by_is_you`
        // is served by GET /workspace/members (ADR-431 D3), so the filter is a
        // read of an existing attributed fact, not a new derivation.
        setRows(
          (res.members ?? []).filter(
            (m: MemberRow) =>
              EXTERNAL_AI_ROLES.has(m.role) && m.connected_by_is_you === true,
          ),
        );
      } catch {
        if (!cancelled) setRows([]);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-6">
        <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        <Plug className="h-4 w-4 text-muted-foreground" />
        <h3 className="text-sm font-medium">Your AI connections</h3>
      </div>
      <p className="text-xs text-muted-foreground">
        External AI assistants you&apos;ve connected to this workspace over MCP.
        Each one reaches in as itself and writes under your authorization — so a
        connection is yours, not the workspace&apos;s, and it goes away when you
        do.
      </p>

      {rows && rows.length > 0 ? (
        <ul className="divide-y divide-border rounded-lg border border-border">
          {rows.map((m) => (
            <li key={`${m.principal_id}-${m.role}`} className="flex items-start gap-3 px-4 py-3">
              <div className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-muted">
                {providerBrandIcon(m.principal_id)}
              </div>
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <span className="truncate text-sm font-medium text-foreground">
                    {m.label || m.principal_id}
                  </span>
                  <span className="shrink-0 rounded-full bg-muted px-2 py-0.5 text-[11px] font-medium text-muted-foreground">
                    {ROLE_LABEL[m.role] ?? m.role}
                  </span>
                </div>
                <div className="mt-1 text-[11px] text-muted-foreground/70">
                  Connects over MCP · writes as itself
                </div>
                {(m.write_zones ?? []).length > 0 && (
                  <div className="mt-1.5 flex flex-wrap items-center gap-1.5">
                    <span className="text-[11px] text-muted-foreground">Can write:</span>
                    {(m.write_zones ?? []).map((z) => (
                      <span
                        key={z}
                        className="rounded border border-border px-1.5 py-0.5 text-[11px] text-muted-foreground"
                      >
                        {z}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            </li>
          ))}
        </ul>
      ) : (
        <div className="rounded-lg border border-dashed border-border px-4 py-6 text-center text-xs text-muted-foreground">
          You haven&apos;t connected an AI assistant yet. Connect this workspace
          from ChatGPT or Claude to give it durable, attributed memory.
        </div>
      )}

      {/* Governance stays singular (ADR-340 DP29): this pane READS, the roster
          GOVERNS. The link is the seam, not a duplicated verb set. */}
      <a
        href="/workspace-settings?pane=members"
        className="inline-flex items-center gap-1 text-xs text-primary hover:underline"
      >
        Manage access for everyone in the workspace
        <ArrowRight className="h-3 w-3" />
      </a>
    </div>
  );
}
