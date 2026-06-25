"use client";

import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { Suspense } from "react";
import { createClient } from "@/lib/supabase/client";
import { api } from "@/lib/api/client";

/**
 * MCP OAuth login handoff — ADR-310 D4 (Auth Piece 2).
 *
 * The MCP server's /authorize stores a PENDING auth code and redirects the
 * operator here. This page ensures the operator is authenticated, then calls
 * /api/mcp/oauth-callback (JWT in header) to bind the real Supabase user onto
 * the pending code, and finally navigates the browser to the returned
 * redirect_url — back to the OAuth client (Claude.ai / ChatGPT / etc.).
 *
 * If unauthenticated, redirect to login with next= back to this page (code
 * preserved) so the flow resumes after sign-in.
 */
function MCPAuthorizeHandler() {
  const searchParams = useSearchParams();
  const supabase = createClient();
  const [status, setStatus] = useState("Connecting your workspace…");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const run = async () => {
      const code = searchParams.get("code");
      if (!code) {
        setError("Missing authorization code. Please retry the connection from your LLM.");
        return;
      }

      const { data: { session } } = await supabase.auth.getSession();
      if (!session) {
        // ADR-370 (A1-lite): bounce to the cockpit-FREE MCP auth surface
        // (/mcp/auth), NOT /auth/login. /auth/login lands the user in the
        // operator cockpit (/desktop) after sign-in; the connector-user's
        // onboarding is separate from the cockpit. /mcp/auth resumes here
        // (preserving the pending code) and returns to the LLM — the user
        // never sees /desktop. Same account, separate door (Constraint 2).
        window.location.href = `/mcp/auth?code=${encodeURIComponent(code)}`;
        return;
      }

      try {
        setStatus("Authorizing connection…");
        const { redirect_url } = await api.mcp.completeAuthorize(code);
        setStatus("Redirecting back to your assistant…");
        window.location.href = redirect_url;
      } catch (e) {
        const msg = e instanceof Error ? e.message : "Authorization failed.";
        setError(`Could not complete the connection: ${msg}`);
      }
    };

    run();
  }, [searchParams, supabase.auth]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="text-center max-w-md px-6">
        <h1 className="text-2xl font-brand mb-2">yarnnn</h1>
        {error ? (
          <p className="text-red-600">{error}</p>
        ) : (
          <p className="text-gray-600">{status}</p>
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
