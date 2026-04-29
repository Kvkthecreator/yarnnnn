"use client";

import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { createClient } from "@/lib/supabase/client";
import { Suspense } from "react";
import { getSafeNextPath } from "@/lib/auth/redirect";
import { HOME_ROUTE } from "@/lib/routes";
import { api } from "@/lib/api/client";
import { OnboardingModal } from "@/components/onboarding/OnboardingModal";

function CallbackHandler() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const supabase = createClient();
  const [status, setStatus] = useState("Completing sign in...");
  // ADR-240: when the operator hasn't picked a program yet
  // (activation_state==='none' && !active_program_slug), mount the
  // OnboardingModal before redirecting. The modal calls onComplete
  // which triggers the redirect we'd otherwise do immediately.
  const [pendingRedirect, setPendingRedirect] = useState<string | null>(null);

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
        // ADR-205 + ADR-212: HOME_ROUTE is /chat. initialize_workspace
        // scaffolds the two systemic Agents (YARNNN + Reviewer seat).
        // Production roles + platform integrations are orchestration
        // capability bundles (not Agents) — production-role rows are
        // lazy-created on first dispatch; platform integrations activate
        // on OAuth connect.
        //
        // ADR-240: if landing on HOME_ROUTE for the first time (operator
        // hasn't picked a program yet), mount the OnboardingModal first.
        // The modal owns the redirect via onComplete. If the operator
        // already picked a program (return visit, post-skip session
        // restore, etc.), redirect immediately as before.
        if (next === HOME_ROUTE) {
          try {
            setStatus("Setting up...");
            const state = await api.onboarding.getState(); // triggers roster scaffolding
            if (state.activation_state === 'none' && !state.active_program_slug) {
              // First-time signup with no program picked → modal flow.
              setPendingRedirect(next);
              setStatus("Choose a program...");
              return;
            }
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
        // ADR-240: same modal gate on the retry path.
        if (next === HOME_ROUTE) {
          try {
            const state = await api.onboarding.getState();
            if (state.activation_state === 'none' && !state.active_program_slug) {
              setPendingRedirect(next);
              setStatus("Choose a program...");
              return;
            }
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

  // ADR-240: when pendingRedirect is set, mount the OnboardingModal.
  // onComplete fires the deferred redirect.
  if (pendingRedirect) {
    return (
      <>
        <div className="min-h-screen flex items-center justify-center bg-gray-50">
          <div className="text-center">
            <h1 className="text-2xl font-brand mb-2">yarnnn</h1>
            <p className="text-gray-600">{status}</p>
          </div>
        </div>
        <OnboardingModal onComplete={() => { window.location.href = pendingRedirect; }} />
      </>
    );
  }

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
