"use client";

import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { Suspense } from "react";
import { createClient } from "@/lib/supabase/client";
import { api } from "@/lib/api/client";

/**
 * MCP OAuth login handoff + CONSENT — ADR-310 D4 (Auth Piece 2).
 *
 * The MCP server's /authorize stores a PENDING auth code and redirects the
 * operator here. This page:
 *   1. ensures the operator is authenticated (else bounce to /mcp/auth),
 *   2. DESCRIBES the requesting client (read-only, binds nothing),
 *   3. asks the operator to explicitly Approve or Deny,
 *   4. only on Approve, POSTs to bind the code and navigates to the client.
 *
 * Security (2026-08-01): the old version auto-called completeAuthorize in a
 * useEffect on page load. That let an attacker who registered their own client
 * send a logged-in victim a `?code=` link that silently bound the victim's
 * account to the attacker's client (forced-consent account takeover). The bind
 * now requires an explicit click, and nothing is written until then.
 */

type ConsentInfo = {
  client_name: string | null;
  client_id: string;
  redirect_host: string;
  account_email: string | null;
  workspace_name: string | null;
  workspace_id: string | null;
  grants: string[];
  legacy_full_access: boolean;
};

/** ADR-573 — one workspace the operator may bind this connection to. */
type WorkspaceChoice = {
  workspace_id: string;
  label: string;
  role: string;
  icon: string | null;
  is_active: boolean;
};

function MCPAuthorizeHandler() {
  const searchParams = useSearchParams();
  const supabase = createClient();
  const [info, setInfo] = useState<ConsentInfo | null>(null);
  const [phase, setPhase] = useState<"loading" | "consent" | "approving" | "done">("loading");
  const [error, setError] = useState<string | null>(null);
  // ADR-573 — the workspaces this operator reaches, and which one they picked.
  // `chosen` starts at the server-resolved default so approving without
  // touching the picker is byte-identical to the pre-573 flow.
  const [workspaces, setWorkspaces] = useState<WorkspaceChoice[]>([]);
  const [chosen, setChosen] = useState<string | null>(null);

  const code = searchParams.get("code");

  // Step 1–2: authenticate, then fetch the consent description (no bind).
  useEffect(() => {
    const run = async () => {
      if (!code) {
        setError("Missing authorization code. Please retry the connection from your LLM.");
        return;
      }

      const { data: { session } } = await supabase.auth.getSession();
      if (!session) {
        // ADR-370 (A1-lite): bounce to the cockpit-FREE MCP auth surface
        // (/mcp/auth), preserving the pending code, then resume here.
        window.location.href = `/mcp/auth?code=${encodeURIComponent(code)}`;
        return;
      }

      try {
        const consent = await api.mcp.consentInfo(code);
        setInfo(consent);
        setChosen(consent.workspace_id);
        setPhase("consent");
        // ADR-573 — the picker's options come from the EXISTING memberships
        // endpoint (the switcher's, ADR-407 Phase 5), not a second list that
        // could disagree with it about what this operator reaches.
        // Best-effort: a failure leaves the default binding and no picker,
        // which is the pre-573 flow — never a blocked connection.
        try {
          const { memberships } = await api.workspace.memberships();
          const list = memberships ?? [];
          setWorkspaces(list);
          // The picker must show what the token will actually bind: if the
          // server-side default resolution degraded to null but memberships
          // loaded, select the acting workspace (else the first) explicitly
          // rather than stamping NULL behind a picker that names a workspace.
          if (!consent.workspace_id && list.length > 0) {
            setChosen((list.find((w) => w.is_active) ?? list[0]).workspace_id);
          }
        } catch {
          setWorkspaces([]);
        }
      } catch (e) {
        const msg = e instanceof Error ? e.message : "Could not load the connection request.";
        setError(msg);
      }
    };

    run();
  }, [code, supabase.auth]);

  // Step 4: bind on explicit approval.
  const approve = async () => {
    if (!code) return;
    setPhase("approving");
    try {
      const { redirect_url } = await api.mcp.completeAuthorize(code, chosen);
      setPhase("done");
      window.location.href = redirect_url;
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Authorization failed.";
      setError(`Could not complete the connection: ${msg}`);
      setPhase("consent");
    }
  };

  const deny = () => {
    // No bind ever happened — just tell the user they can close the tab.
    setError("Connection denied. You can close this tab.");
    setPhase("done");
  };

  const clientLabel = info?.client_name?.trim() || "An application";

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="text-center max-w-md px-6">
        <h1 className="text-2xl font-brand mb-4">yarnnn</h1>

        {error ? (
          <p className="text-red-600">{error}</p>
        ) : phase === "loading" ? (
          <p className="text-gray-600">Loading the connection request…</p>
        ) : phase === "consent" && info ? (
          <div className="text-left">
            <p className="text-gray-800 mb-4">
              <span className="font-semibold">{clientLabel}</span> is requesting access to{" "}
              {workspaces.length > 1 ? (
                "one of your yarnnn workspaces"
              ) : info.workspace_name ? (
                <span className="font-semibold">{info.workspace_name}</span>
              ) : (
                "your yarnnn workspace"
              )}
              .
            </p>

            {/* WHO — the account the bind will use. It comes from the JWT, so on
                a shared browser or a second account this is the difference
                between approving as yourself and approving as someone else. */}
            {info.account_email && (
              <p className="text-sm text-gray-600 mb-4">
                Connecting as <span className="font-medium text-gray-900">{info.account_email}</span>
              </p>
            )}

            {/* WHERE — ADR-573. The picker shows whenever memberships loaded,
                even for a single workspace: the binding is explicit, never
                implied (2026-08-19 — the one-workspace screen read as if no
                selection existed at all). Zero workspaces = the memberships
                fetch failed or a fresh account; the sentence above degrades
                and the NULL binding resolves the principal's default.
                A connector binds to ONE workspace: before this it silently
                took the principal's default, so a member of a shared commons
                could not point their assistant at the commons at all. */}
            {workspaces.length > 0 && (
              <div className="mb-4">
                <label
                  htmlFor="mcp-workspace"
                  className="mb-1 block text-sm font-medium text-gray-700"
                >
                  Workspace
                </label>
                <select
                  id="mcp-workspace"
                  value={chosen ?? ""}
                  onChange={(e) => setChosen(e.target.value || null)}
                  className="w-full rounded border border-gray-300 bg-white px-2 py-1.5 text-sm text-gray-900"
                >
                  {workspaces.map((w) => (
                    <option key={w.workspace_id} value={w.workspace_id}>
                      {w.icon ? `${w.icon} ` : ""}
                      {w.label}
                      {w.role === "owner" ? " (yours)" : ` (${w.role})`}
                    </option>
                  ))}
                </select>
                <p className="mt-1 text-xs text-gray-500">
                  This connection reaches only the workspace you choose.
                </p>
              </div>
            )}

            {/* WHAT — the token's REAL scopes (ADR-563), one sentence each,
                riskiest last. Replaces a fixed sentence that used pre-ADR-512
                vocabulary and understated a legacy token's actual reach: it
                never mentioned deletion or member-granting share links. */}
            <p className="text-sm font-medium text-gray-700 mb-2">It will be able to:</p>
            <ul className="mb-4 space-y-1.5">
              {info.grants.map((g) => (
                <li key={g} className="flex gap-2 text-sm text-gray-700">
                  <span aria-hidden="true" className="text-gray-400">
                    •
                  </span>
                  <span>{g}</span>
                </li>
              ))}
            </ul>

            {info.legacy_full_access && (
              <p className="mb-4 rounded border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800">
                This app is requesting <span className="font-semibold">full access</span> rather
                than a narrower permission. Only approve if you trust it with everything above.
              </p>
            )}

            <p className="text-sm text-gray-500 mb-6">
              Redirects to <span className="font-mono">{info.redirect_host}</span>. Only approve
              if you started this connection from an app you trust.
            </p>
            <div className="flex gap-3 justify-center">
              <button
                onClick={approve}
                className="px-4 py-2 rounded bg-gray-900 text-white hover:bg-gray-700"
              >
                Approve
              </button>
              <button
                onClick={deny}
                className="px-4 py-2 rounded border border-gray-300 text-gray-700 hover:bg-gray-100"
              >
                Deny
              </button>
            </div>
          </div>
        ) : phase === "approving" ? (
          <p className="text-gray-600">Authorizing connection…</p>
        ) : (
          <p className="text-gray-600">Redirecting back to your assistant…</p>
        )}
      </div>
    </div>
  );
}

export default function MCPAuthorizePage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen flex items-center justify-center bg-gray-50">
          <div className="text-center">
            <h1 className="text-2xl font-brand mb-2">yarnnn</h1>
            <p className="text-gray-600">Loading…</p>
          </div>
        </div>
      }
    >
      <MCPAuthorizeHandler />
    </Suspense>
  );
}
