"use client";

import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { createClient } from "@/lib/supabase/client";
import { Suspense } from "react";
import { getSafeNextPath } from "@/lib/auth/redirect";
import { HOME_ROUTE } from "@/lib/routes";
import { Wordmark } from "@/components/shared/Wordmark";
import { Working } from '@/components/shared/Working';
import { MIN_PASSWORD_LENGTH } from "@/lib/auth/password";

function CallbackHandler() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const supabase = createClient();
  const [status, setStatus] = useState("Completing sign in...");
  /**
   * RECOVERY lands here too, and it must not just sign the member in (2026-09-15).
   *
   * The reset link verifies as a `recovery` OTP, which establishes a session —
   * so before this, finishing the flow would have dropped the member into the
   * app still holding the password they had forgotten, with NO surface anywhere
   * in the product to change it (there is no password pane in /settings). A
   * door that opens onto nothing.
   *
   * So recovery stops here and asks for the new password, which is the one
   * moment the member is authenticated specifically in order to set it.
   */
  const [recovery, setRecovery] = useState(false);
  const [newPassword, setNewPassword] = useState("");
  const [recoveryNotice, setRecoveryNotice] = useState<
    { tone: "error" | "success"; text: string } | null
  >(null);
  const [savingPassword, setSavingPassword] = useState(false);

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

      setStatus("Verifying session...");

      // MAGIC-LINK / EMAIL-OTP BRANCH (2026-07-31).
      //
      // The cookie-backed `createClientComponentClient` does NOT auto-detect an
      // implicit `#access_token=...` fragment, and it only exchanges a `?code=`
      // param for PKCE. A Supabase `magiclink` / `recovery` / `invite` link
      // arrives as `?token_hash=&type=` (or the equivalent fragment), so before
      // this branch existed every such link died here with "Could not establish
      // session" — observed against production while standing up the
      // settings-surfaces click-pass. Verified: POST /auth/v1/verify returns a
      // valid session for the same token the page was discarding.
      //
      // verifyOtp() consumes the token AND persists the session through the
      // auth-helpers cookie writer, which is what middleware.ts reads.
      const hashParams = new URLSearchParams(
        typeof window !== "undefined" ? window.location.hash.replace(/^#/, "") : ""
      );
      const tokenHash = searchParams.get("token_hash") ?? hashParams.get("token_hash");
      const otpType = (searchParams.get("type") ?? hashParams.get("type")) as
        | "magiclink" | "recovery" | "invite" | "email" | "signup" | null;

      if (tokenHash && otpType) {
        const { error: otpError } = await supabase.auth.verifyOtp({
          token_hash: tokenHash,
          type: otpType,
        });
        if (otpError) {
          router.replace(
            `/auth/login?error=otp_error&message=${encodeURIComponent(otpError.message)}${nextParam}`
          );
          return;
        }
        // The session now exists, which is exactly what makes `updateUser`
        // possible. Stop here and collect the new password rather than
        // finalizing into the app.
        if (otpType === "recovery") {
          setRecovery(true);
          return;
        }
      }

      const { data: { session }, error: sessionError } = await supabase.auth.getSession();

      if (sessionError) {
        router.replace(
          `/auth/login?error=session_error&message=${encodeURIComponent(sessionError.message)}${nextParam}`
        );
        return;
      }

      const finalize = async () => {
        // ADR-437 (2026-07-10): NO first-run wizard. Genesis is empty (ADR-414
        // D4) and activation is not a setup ceremony — a cold sign-up lands on
        // the default landing (HOME_ROUTE), where the empty-state teaches the
        // moat and invites the first substrate-creating act (ADR-437 D3). The
        // guided /setup SEQUENCE surface + its first_run redirect are deleted.
        // Genesis needs NOTHING from this page. The cold-user workspace mint
        // lives in the API's auth dependency (`get_user_client`, ADR-465 D2),
        // so it fires on the first authenticated request whatever that is.
        //
        // ⚠️ This comment used to say "a lazy workspace-state fetch triggers
        // backend scaffolding on first load; the shell does it". That was true
        // until ADR-437 Phase A deleted /setup — the last surface that fetched
        // GET /api/workspace/state on login. The comment then named a caller
        // that did not exist, and every cold sign-up from 2026-07-11 landed
        // workspace-less. Do not re-point genesis at a route: a door on a route
        // is only as live as that route's caller.
        window.location.href = next;
      };

      if (session) {
        await finalize();
        return;
      }

      // No session yet - the callback might still be processing
      // Check one more time after a short delay
      setStatus("Finalizing...");
      await new Promise(resolve => setTimeout(resolve, 1000));

      const { data: { session: retrySession } } = await supabase.auth.getSession();

      if (retrySession) {
        await finalize();
        return;
      }

      // Still no session
      router.replace(`/auth/login?error=no_session&message=Could not establish session${nextParam}`);
    };

    handleCallback();
  }, [searchParams, router, supabase.auth]);

  const handleSetPassword = async (e: React.FormEvent) => {
    e.preventDefault();
    if (newPassword.length < MIN_PASSWORD_LENGTH) {
      setRecoveryNotice({
        tone: "error",
        text: `Use at least ${MIN_PASSWORD_LENGTH} characters.`,
      });
      return;
    }
    setSavingPassword(true);
    setRecoveryNotice(null);
    const { error } = await supabase.auth.updateUser({ password: newPassword });
    if (error) {
      setRecoveryNotice({ tone: "error", text: error.message });
      setSavingPassword(false);
      return;
    }
    // Signed in already, and now with the password they just chose.
    window.location.href = getSafeNextPath(searchParams.get("next"), HOME_ROUTE);
  };

  if (recovery) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
        <form onSubmit={handleSetPassword} className="w-full max-w-sm text-center">
          <h1 className="mb-2"><Wordmark className="text-2xl" /></h1>
          <p className="mb-6 text-sm text-gray-600">Choose a new password.</p>
          <input
            type="password"
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
            required
            minLength={MIN_PASSWORD_LENGTH}
            autoFocus
            placeholder="New password"
            aria-label="New password"
            className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
          />
          <p className="mt-1 text-left text-xs text-gray-500">
            At least {MIN_PASSWORD_LENGTH} characters.
          </p>
          {recoveryNotice && (
            <p
              role={recoveryNotice.tone === "error" ? "alert" : "status"}
              className={`mt-3 text-sm ${
                recoveryNotice.tone === "success" ? "text-emerald-600" : "text-red-600"
              }`}
            >
              {recoveryNotice.text}
            </p>
          )}
          <button
            type="submit"
            disabled={savingPassword}
            className="mt-4 w-full rounded-md bg-[#1a1a1a] px-3 py-2 text-sm text-white disabled:opacity-60"
          >
            {savingPassword ? "Saving…" : "Save password"}
          </button>
        </form>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="text-center">
        <h1 className="mb-2"><Wordmark className="text-2xl" /></h1>
        <Working label={status} />
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
            <h1 className="mb-2"><Wordmark className="text-2xl" /></h1>
            <Working label="Loading…" />
          </div>
        </div>
      }
    >
      <CallbackHandler />
    </Suspense>
  );
}
