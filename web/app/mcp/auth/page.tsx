"use client";

/**
 * MCP Auth — the self-contained connect-moment login (ADR-370, A1-lite).
 *
 * This is the headless-as-a-human-can-be auth surface for the MCP boundary.
 * It lives in the cockpit-FREE `/mcp/` route tree (outside the (authenticated)
 * group), so a connector-user authenticating from claude.ai/ChatGPT NEVER lands
 * in the operator cockpit (`/desktop`). It is a *separate door to the same
 * account* — the same Supabase project / auth.users / substrate as yarnnn.com
 * (ADR-370 D2 Constraint 1: DB mandatorily shared). After auth it returns to
 * `/mcp/authorize` (which completes the OAuth bind + bounces back to the LLM) —
 * NEVER to `/auth/login` or the cockpit (Constraint 2: separate onboarding,
 * shared access).
 *
 * The auth MECHANICS are shared with the cockpit login via <AuthForm> (Singular
 * Implementation); this page owns only the MCP-specific redirect + copy.
 */

import { useEffect, useState, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { createClient } from "@/lib/supabase/client";
import { AuthForm } from "@/components/auth/AuthForm";

function MCPAuthInner() {
  const searchParams = useSearchParams();
  const [initialError, setInitialError] = useState<string | null>(null);

  // The pending OAuth code is round-tripped through auth so the connect flow
  // resumes at /mcp/authorize after sign-in. Never points at the cockpit.
  const code = searchParams.get("code") ?? "";
  const resumeTarget = code
    ? `/mcp/authorize?code=${encodeURIComponent(code)}`
    : "/mcp/authorize";
  const callbackRedirect =
    typeof window === "undefined"
      ? ""
      : `${window.location.origin}/auth/callback?next=${encodeURIComponent(resumeTarget)}`;

  useEffect(() => {
    const errorParam = searchParams.get("error");
    const messageParam = searchParams.get("message");
    if (errorParam) {
      setInitialError(`${errorParam}${messageParam ? `: ${messageParam}` : ""}`);
    }
  }, [searchParams]);

  // Already signed in? Resume the connect flow immediately — no need to log in.
  useEffect(() => {
    const supabase = createClient();
    const check = async () => {
      const {
        data: { session },
      } = await supabase.auth.getSession();
      if (session) window.location.href = resumeTarget;
    };
    check();
  }, [resumeTarget]);

  return (
    <div className="relative min-h-screen flex items-center justify-center bg-[#faf8f5] px-4">
      <div className="relative z-10 w-full max-w-md">
        <div className="text-center">
          <h1 className="text-3xl font-brand text-[#1a1a1a]">yarnnn</h1>
        </div>

        <AuthForm
          onPasswordSuccess={() => {
            window.location.href = resumeTarget;
          }}
          callbackRedirect={callbackRedirect}
          loginSubheading="Sign in to connect your assistant to your memory"
          signupSubheading="Create your yarnnn memory"
          loginSubmitLabel="Sign in & connect"
          signupSubmitLabel="Sign up & connect"
          initialError={initialError}
        />

        <p className="text-center text-xs text-[#1a1a1a]/40 mt-6">
          Connecting your assistant to your yarnnn memory. You can visit yarnnn.com anytime with the same account.
        </p>
      </div>
    </div>
  );
}

export default function MCPAuthPage() {
  return (
    <Suspense
      fallback={
        <div className="relative min-h-screen flex items-center justify-center bg-[#faf8f5] px-4">
          <div className="text-center">
            <h1 className="text-3xl font-brand text-[#1a1a1a]">yarnnn</h1>
            <p className="mt-2 text-[#1a1a1a]/60">Loading…</p>
          </div>
        </div>
      }
    >
      <MCPAuthInner />
    </Suspense>
  );
}
