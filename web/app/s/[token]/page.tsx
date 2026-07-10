"use client";

/**
 * Shared-artifact accept page — ADR-437 D4 (the /s/{token} accept surface).
 *
 * The link a shared artifact resolves to. The artifact is the landing page:
 * the recipient arrives with a reason and a piece of real, attributed substrate
 * in hand, and the act of accessing IS the activation (ADR-437 D4). Accepting
 * mints a BROAD member grant (the Figma default, D4.2) and binds the commons.
 *
 * Standalone threshold page, deliberately OUTSIDE the (authenticated) shell
 * group — the same lesson as /invite (2026-07-04 incident: inside the shell,
 * SurfaceViewport renders page children only when no windows are mounted, so an
 * operator with persisted dock state got their Desktop instead and the accept
 * silently never ran). No shell, no window sync.
 *
 * Auth-gated by middleware (/s is a protected prefix — an anonymous visitor
 * bounces through login with ?next preserved). Any authenticated principal may
 * accept — the link is not email-locked (unlike an invite).
 */

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { FileText, Loader2 } from "lucide-react";

import { api, APIError, setActiveWorkspace } from "@/lib/api/client";

type Preview = {
  workspace_name: string | null;
  artifact_path: string | null;
  label: string | null;
  role: string;
  status: string;
};

/** The artifact's display name — the last path segment, or the label. */
function artifactName(p: Preview): string | null {
  if (p.label) return p.label;
  if (!p.artifact_path) return null;
  const seg = p.artifact_path.split("/").filter(Boolean).pop();
  return seg || p.artifact_path;
}

export default function ShareAcceptPage() {
  const params = useParams<{ token: string }>();
  const token = params?.token ?? "";

  const [preview, setPreview] = useState<Preview | null>(null);
  const [loading, setLoading] = useState(true);
  const [accepting, setAccepting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!token) return;
    api.workspace
      .previewShare(token)
      .then(setPreview)
      .catch((e) =>
        setError(
          e instanceof APIError && e.status === 404
            ? "This share link doesn't exist (it may have been revoked)."
            : "Could not load the share.",
        ),
      )
      .finally(() => setLoading(false));
  }, [token]);

  const accept = useCallback(async () => {
    setAccepting(true);
    setError(null);
    try {
      const result = await api.workspace.acceptShare(token);
      // Bind the commons for every subsequent API call. Shell state is keyed
      // per (workspace, user) — ADR-407 Phase 3 — so the new binding reads
      // fresh keys by construction; no wipe needed on accept.
      setActiveWorkspace(result.workspace_id);
      // Land where the shared artifact lives — Files opens it (ADR-437 D4:
      // the artifact is the landing page). The workspace desktop is the home
      // the recipient enters; Files is the surface that shows the artifact.
      window.location.assign(result.artifact_path ? "/files" : "/desktop");
    } catch (e) {
      const data = e instanceof APIError ? (e.data as { detail?: unknown } | undefined) : undefined;
      const detail =
        typeof data?.detail === "string" ? data.detail : "Could not accept the share.";
      setError(detail);
      setAccepting(false);
    }
  }, [token]);

  const wsName = preview?.workspace_name || "a shared workspace";
  const artifact = preview ? artifactName(preview) : null;

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-background px-4">
      <p className="mb-6 font-brand text-2xl">yarnnn</p>
      <div className="w-full max-w-md rounded-xl border border-border/60 bg-card p-8 text-center shadow-sm">
        <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-muted">
          <FileText className="h-6 w-6 text-muted-foreground" />
        </div>

        {loading ? (
          <div className="flex items-center justify-center gap-2 text-sm text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" /> Loading…
          </div>
        ) : error && !preview ? (
          <p className="text-sm text-muted-foreground">{error}</p>
        ) : (
          <>
            {artifact ? (
              <>
                <h1 className="text-lg font-semibold">
                  <span className="text-muted-foreground">Shared with you:</span>{" "}
                  {artifact}
                </h1>
                <p className="mt-2 text-sm text-muted-foreground">
                  From {wsName}. Open it to join the workspace — a shared,
                  attributed commons where every change records who made it.
                </p>
              </>
            ) : (
              <>
                <h1 className="text-lg font-semibold">Join {wsName}</h1>
                <p className="mt-2 text-sm text-muted-foreground">
                  You&apos;ve been invited into a shared, attributed workspace —
                  every change records who made it.
                </p>
              </>
            )}
            {preview?.status !== "active" ? (
              <p className="mt-4 text-sm text-muted-foreground">
                This share link is {preview?.status}.
              </p>
            ) : (
              <button
                onClick={() => void accept()}
                disabled={accepting}
                className="mt-6 inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-60"
              >
                {accepting && <Loader2 className="h-4 w-4 animate-spin" />}
                {artifact ? "Open & join" : "Accept & join"}
              </button>
            )}
            {error && <p className="mt-3 text-xs text-destructive">{error}</p>}
          </>
        )}
      </div>
    </div>
  );
}
