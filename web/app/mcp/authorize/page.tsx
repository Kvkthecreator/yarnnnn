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
};

function MCPAuthorizeHandler() {
  const searchParams = useSearchParams();
  const supabase = createClient();
  const [info, setInfo] = useState<ConsentInfo | null>(null);
  const [phase, setPhase] = useState<"loading" | "consent" | "approving" | "done">("loading");
  const [error, setError] = useState<string | null>(null);

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
        setPhase("consent");
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
      const { redirect_url } = await api.mcp.completeAuthorize(code);
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
            <p className="text-gray-800 mb-3">
              <span className="font-semibold">{clientLabel}</span> is requesting access to your
              yarnnn workspace — it will be able to <span className="font-semibold">read and
              write your memory</span> on your behalf.
            </p>
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
