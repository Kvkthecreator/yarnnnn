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
import { useTranslations } from "next-intl";
import { Wordmark } from "@/components/shared/Wordmark";
import { Working } from '@/components/shared/Working';

function MCPAuthInner() {
  const t = useTranslations("auth.connect");
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
          <h1 className="text-[#1a1a1a]"><Wordmark className="text-3xl" /></h1>
        </div>

        <AuthForm
          onPasswordSuccess={() => {
            window.location.href = resumeTarget;
          }}
          callbackRedirect={callbackRedirect}
          loginSubheading={t("loginSubheading")}
          signupSubheading={t("signupSubheading")}
          loginSubmitLabel={t("signIn")}
          signupSubmitLabel={t("signUp")}
          initialError={initialError}
        />

        <p className="text-center text-xs text-[#1a1a1a]/40 mt-6">
          {t("footer")}
        </p>
      </div>
    </div>
  );
}

export default function MCPAuthPage() {
  // ADR-660 — the fallback is rendered by THIS component, so the word is bound
  // here; `Working` itself stays locale-free (it is also mounted by routes
  // outside every scope, where a translation hook would throw). Named `tAuth`,
  // not `t`: the inner component binds `auth.connect` under the name `t`, and a
  // second `t` in one file is a key that resolves by luck of which binding a
  // reader (or a gate) reaches first.
  const tAuth = useTranslations("auth");
  return (
    <Suspense
      fallback={
        <div className="relative min-h-screen flex items-center justify-center bg-[#faf8f5] px-4">
          <div className="text-center">
            <h1 className="text-[#1a1a1a]"><Wordmark className="text-3xl" /></h1>
            <div className="mt-2 flex justify-center"><Working label={tAuth('loading')} /></div>
          </div>
        </div>
      }
    >
      <MCPAuthInner />
    </Suspense>
  );
}
