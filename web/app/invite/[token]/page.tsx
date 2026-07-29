"use client";

/**
 * Invite-accept page — ADR-404 step 5 (member provisioning).
 *
 * The link an invited email receives. Auth-gated by middleware (/invite is
 * a protected prefix — an anonymous visitor bounces through login with
 * ?next preserved), but deliberately OUTSIDE the (authenticated) shell
 * group: it is a threshold/transport page, not a workspace surface.
 * Inside the shell, SurfaceViewport renders page children for non-surface
 * routes ONLY when no windows are mounted — any operator with persisted
 * dock state got their Desktop instead of this page and the accept never
 * ran (operator-observed 2026-07-04: invited member landed on Mandate,
 * invite stayed pending). Standalone route = no shell, no window sync.
 *
 * Accepting mints the member grant server-side and binds the commons
 * client-side (X-Workspace-Id via setActiveWorkspace) before entering.
 */

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { Loader2, Users, AlertTriangle } from "lucide-react";

import { api, APIError, setActiveWorkspace } from "@/lib/api/client";
import { createClient } from "@/lib/supabase/client";

type Preview = {
  workspace_name: string | null;
  email: string;
  role: string;
  status: string;
};

export default function InviteAcceptPage() {
  const params = useParams<{ token: string }>();
  const token = params?.token ?? "";

  const [preview, setPreview] = useState<Preview | null>(null);
  const [loading, setLoading] = useState(true);
  const [accepting, setAccepting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // ADR-498 — WHO is currently signed in. The accept is email-bound
  // (`accept_invite` 403s on mismatch), and the page previously discovered that
  // only AFTER the click: an owner who opened an invite meant for a teammate
  // got a bare "Failed to load resource: 403" with no explanation and no way
  // forward. The signed-in identity is knowable BEFORE the click, so the
  // mismatch is surfaced as a state, not as a failure.
  const [viewerEmail, setViewerEmail] = useState<string | null>(null);
  const [signingOut, setSigningOut] = useState(false);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const { data } = await createClient().auth.getSession();
        if (!cancelled) setViewerEmail(data.session?.user?.email ?? null);
      } catch {
        if (!cancelled) setViewerEmail(null);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!token) return;
    api.workspace
      .previewInvite(token)
      .then(setPreview)
      .catch((e) =>
        setError(
          e instanceof APIError && e.status === 404
            ? "This invite link doesn't exist (it may have been revoked)."
            : "Could not load the invite.",
        ),
      )
      .finally(() => setLoading(false));
  }, [token]);

  const accept = useCallback(async () => {
    setAccepting(true);
    setError(null);
    try {
      const result = await api.workspace.acceptInvite(token);
      // Bind the commons for every subsequent API call. Shell state is
      // keyed per (workspace, user) — ADR-407 Phase 3 — so the new binding
      // reads fresh keys by construction; no wipe needed on accept.
      setActiveWorkspace(result.workspace_id);
      window.location.assign("/chat");
    } catch (e) {
      const data = e instanceof APIError ? (e.data as { detail?: unknown } | undefined) : undefined;
      const detail =
        typeof data?.detail === "string" ? data.detail : "Could not accept the invite.";
      setError(detail);
      setAccepting(false);
    }
  }, [token]);

  // ADR-498 — the mismatch is decided from two knowable facts, before any
  // network call. Compared case-insensitively + trimmed, mirroring the server's
  // own test (`workspace_invites.py::accept_invite`) so the FE can never
  // disagree with the gate about what counts as a match.
  const invitedEmail = preview?.email?.trim().toLowerCase() ?? null;
  const signedInEmail = viewerEmail?.trim().toLowerCase() ?? null;
  const wrongAccount =
    !!invitedEmail && !!signedInEmail && invitedEmail !== signedInEmail;

  // Sign out and return HERE — the invite link survives the round-trip, so the
  // member lands back on the accept button as the right person instead of
  // having to re-open the email.
  const switchAccount = useCallback(async () => {
    setSigningOut(true);
    try {
      await createClient().auth.signOut();
    } catch {
      // best-effort — the redirect below re-gates through login either way
    }
    window.location.assign(
      `/auth/login?next=${encodeURIComponent(`/invite/${token}`)}`,
    );
  }, [token]);

  const wsName = preview?.workspace_name || "a shared workspace";

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-background px-4">
      <p className="mb-6 font-brand text-2xl">yarnnn</p>
      <div className="w-full max-w-md rounded-xl border border-border/60 bg-card p-8 text-center shadow-sm">
        <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-muted">
          <Users className="h-6 w-6 text-muted-foreground" />
        </div>

        {loading ? (
          <div className="flex items-center justify-center gap-2 text-sm text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" /> Loading invite…
          </div>
        ) : error && !preview ? (
          <p className="text-sm text-muted-foreground">{error}</p>
        ) : (
          <>
            <h1 className="text-lg font-semibold">Join {wsName}</h1>
            <p className="mt-2 text-sm text-muted-foreground">
              You&apos;ve been invited as a <strong>{preview?.role}</strong> —
              you&apos;ll work in the same shared, attributed workspace; every
              change records who made it.
            </p>
            {preview?.status !== "pending" ? (
              <p className="mt-4 text-sm text-muted-foreground">
                This invite is {preview?.status}.
              </p>
            ) : wrongAccount ? (
              /* ADR-498 — the wrong-account state. Named BEFORE the click, with
                 the way out attached: the accept is email-bound, so the only
                 resolution is to sign in as the invited address. */
              <div className="mt-5">
                <div className="flex items-start gap-2 rounded-md border border-amber-300/60 bg-amber-50 p-3 text-left dark:border-amber-800/50 dark:bg-amber-950/30">
                  <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-amber-600 dark:text-amber-400" />
                  <p className="text-xs text-amber-900 dark:text-amber-200">
                    This invite was sent to{" "}
                    <span className="font-medium">{preview?.email}</span>, but
                    you&apos;re signed in as{" "}
                    <span className="font-medium">{viewerEmail}</span>. Invites
                    are bound to their address, so switch accounts to accept it.
                  </p>
                </div>
                <button
                  onClick={() => void switchAccount()}
                  disabled={signingOut}
                  className="mt-4 inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-60"
                >
                  {signingOut && <Loader2 className="h-4 w-4 animate-spin" />}
                  Sign in as {preview?.email}
                </button>
                <p className="mt-3 text-xs text-muted-foreground">
                  You&apos;ll come back to this invite after signing in.
                </p>
              </div>
            ) : (
              <>
                <button
                  onClick={() => void accept()}
                  disabled={accepting}
                  className="mt-6 inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-60"
                >
                  {accepting && <Loader2 className="h-4 w-4 animate-spin" />}
                  Accept invite
                </button>
                <p className="mt-3 text-xs text-muted-foreground">
                  Invited address: {preview?.email}
                  {signedInEmail ? " · signed in as you" : ""}.
                </p>
              </>
            )}
            {error && <p className="mt-3 text-xs text-destructive">{error}</p>}
          </>
        )}
      </div>
    </div>
  );
}
