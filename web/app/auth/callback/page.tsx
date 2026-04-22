"use client";

import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { createClient } from "@/lib/supabase/client";
import { Suspense } from "react";
import { getSafeNextPath } from "@/lib/auth/redirect";
import { HOME_ROUTE } from "@/lib/routes";
import { api } from "@/lib/api/client";

function CallbackHandler() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const supabase = createClient();
  const [status, setStatus] = useState("Completing sign in...");

  useEffect(() => {
    const handleCallback = async () => {
      const error = searchParams.get("error");
      const errorDescription = searchParams.get("error_description");
      const next = getSafeNextPath(searchParams.get("next"), HOME_ROUTE);
      const nextParam = `&next=${encodeURIComponent(next)}`;

      if (error) {
        router.replace(
          `/auth/login?error=${encodeURIComponent(error)}&message=${encodeURIComponent(errorDescription || "")}${nextParam}`
        );
        return;
      }

      // Wait for Supabase to process the OAuth callback
      // The auth-helpers automatically detect hash fragments and exchange them
      setStatus("Verifying session...");

      // Give Supabase client time to process the callback
      // It auto-detects the hash fragment or code parameter
      const { data: { session }, error: sessionError } = await supabase.auth.getSession();

      if (sessionError) {
        router.replace(
          `/auth/login?error=session_error&message=${encodeURIComponent(sessionError.message)}${nextParam}`
        );
        return;
      }

      if (session) {
        // ADR-205: HOME_ROUTE is /chat. initialize_workspace scaffolds exactly
        // one agent (YARNNN); Specialists + Platform Bots are lazy-created on
        // first dispatch / OAuth connect. Both new and returning users land
        // on /chat — OnboardingModal auto-opens via TP's workspace_state signal
        // when identity is empty.
        if (next === HOME_ROUTE) {
          try {
            setStatus("Setting up...");
            await api.onboarding.getState(); // triggers roster scaffolding
          } catch {
            // Best effort — HOME_ROUTE is the fallback anyway
          }
        }
        window.location.href = next;
        return;
      }

      // No session yet - the callback might still be processing
      // Check one more time after a short delay
      setStatus("Finalizing...");
      await new Promise(resolve => setTimeout(resolve, 1000));

      const { data: { session: retrySession } } = await supabase.auth.getSession();

      if (retrySession) {
        // ADR-144: Ensure roster scaffolding on retry path too.
        // ADR-163: HOME_ROUTE is now /chat — single landing for all users.
        if (next === HOME_ROUTE) {
          try {
            await api.onboarding.getState();
          } catch {
            // Best effort — HOME_ROUTE is the fallback anyway
          }
        }
        window.location.href = next;
        return;
      }

      // Still no session
      router.replace(`/auth/login?error=no_session&message=Could not establish session${nextParam}`);
    };

    handleCallback();
  }, [searchParams, router, supabase.auth]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="text-center">
        <h1 className="text-2xl font-brand mb-2">yarnnn</h1>
        <p className="text-gray-600">{status}</p>
      </div>
    </div>
  );
}

export default function CallbackPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen flex items-center justify-center bg-gray-50">
          <div className="text-center">
            <h1 className="text-2xl font-brand mb-2">yarnnn</h1>
            <p className="text-gray-600">Loading...</p>
          </div>
        </div>
      }
    >
      <CallbackHandler />
    </Suspense>
  );
}
