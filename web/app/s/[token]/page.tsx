"use client";

/**
 * The shared-artifact page — ADR-437 D4 (the /s/{token} surface), made PUBLIC
 * by ADR-513: the attribution walk as the landing page.
 *
 * A stranger with the link sees the artifact + who made it — the walk — with
 * NO account (the token is the read capability; middleware no longer bounces
 * /s). Becoming a principal stays auth-gated: the Accept action hits the
 * auth-gated API and, on 401, bounces through login with ?next preserved.
 *
 * Rendering discipline (ADR-513 D3): member-authored HTML renders EXCLUSIVELY
 * in a fully-locked iframe (`sandbox=""` — the WebViewer grammar: no scripts,
 * no same-origin). There is no server-side sanitizer; the sandbox is the
 * boundary, so no looser form and no inlining, ever. Text renders escaped.
 *
 * Standalone threshold page, deliberately OUTSIDE the (authenticated) shell
 * group — the same lesson as /invite (2026-07-04 incident: inside the shell,
 * SurfaceViewport renders page children only when no windows are mounted).
 */

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { FileText, Loader2 } from "lucide-react";

import { api, APIError, setActiveWorkspace } from "@/lib/api/client";

type WalkEntry = {
  authored_by: string | null;
  when: string | null;
  change: string | null;
};

type Preview = {
  workspace_name: string | null;
  artifact_path: string | null;
  label: string | null;
  role: string;
  status: string;
  artifact_name?: string | null;
  artifact_kind?: string | null;
  artifact_content?: string | null;
  truncated?: boolean;
  walk?: WalkEntry[];
};

/** The artifact's display name — the label, the API's name, or the leaf. */
function artifactName(p: Preview): string | null {
  if (p.artifact_name) return p.artifact_name;
  if (p.label) return p.label;
  if (!p.artifact_path) return null;
  const seg = p.artifact_path.split("/").filter(Boolean).pop();
  return seg || p.artifact_path;
}

/** "operator" → You'd recognize it; keep attribution verbatim but humanize
 *  the two structural prefixes for a stranger's first read. */
function walkActor(authored_by: string | null): string {
  if (!authored_by) return "unknown";
  return authored_by;
}

function walkDate(when: string | null): string {
  if (!when) return "";
  try {
    return new Date(when).toLocaleDateString(undefined, {
      month: "short", day: "numeric",
    });
  } catch {
    return "";
  }
}

export default function SharePublicPage() {
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
          e instanceof APIError && (e.status === 404 || e.status === 410)
            ? "This share link doesn't exist or has been revoked."
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
      // the artifact is the landing page).
      window.location.assign(result.artifact_path ? "/files" : "/desktop");
    } catch (e) {
      if (e instanceof APIError && e.status === 401) {
        // ADR-513: reading needed no account; JOINING does. Bounce through
        // login with the share preserved — the unified-door flow (ADR-465 D2).
        window.location.assign(`/auth/login?next=${encodeURIComponent(`/s/${token}`)}`);
        return;
      }
      const data = e instanceof APIError ? (e.data as { detail?: unknown } | undefined) : undefined;
      const detail =
        typeof data?.detail === "string" ? data.detail : "Could not accept the share.";
      setError(detail);
      setAccepting(false);
    }
  }, [token]);

  const wsName = preview?.workspace_name || "a shared workspace";
  const artifact = preview ? artifactName(preview) : null;
  const walk = preview?.walk ?? [];
  const hasContent = Boolean(preview?.artifact_content);

  return (
    <div className="flex min-h-screen flex-col items-center bg-background px-4 py-10">
      <p className="mb-8 font-brand text-2xl">yarnnn</p>

      {loading ? (
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" /> Loading…
        </div>
      ) : error && !preview ? (
        <div className="w-full max-w-md rounded-xl border border-border/60 bg-card p-8 text-center shadow-sm">
          <p className="text-sm text-muted-foreground">{error}</p>
        </div>
      ) : (
        <div className="flex w-full max-w-3xl flex-col gap-6">
          {/* ── The artifact (ADR-513 D3: locked sandbox, or escaped text) ── */}
          {hasContent && (
            <div className="overflow-hidden rounded-xl border border-border/60 bg-card shadow-sm">
              <div className="flex items-center gap-2 border-b border-border/60 px-4 py-2.5">
                <FileText className="h-4 w-4 text-muted-foreground" />
                <span className="text-sm font-medium">{artifact}</span>
                <span className="ml-auto text-xs text-muted-foreground">
                  shared from {wsName}
                  {preview?.role === "viewer" ? " · read-only" : ""}
                </span>
              </div>
              {preview?.artifact_kind === "html" ? (
                <iframe
                  title={artifact ?? "shared artifact"}
                  srcDoc={preview.artifact_content ?? ""}
                  sandbox=""
                  className="h-[70vh] w-full bg-white"
                />
              ) : (
                <pre className="max-h-[70vh] overflow-auto whitespace-pre-wrap p-4 text-sm">
                  {preview?.artifact_content}
                </pre>
              )}
              {preview?.truncated && (
                <p className="border-t border-border/60 px-4 py-2 text-xs text-muted-foreground">
                  Preview truncated — join the workspace to see the full document.
                </p>
              )}
            </div>
          )}

          <div className="flex flex-col gap-6 sm:flex-row">
            {/* ── The attribution walk — the moat on contact (ADR-513 D2) ── */}
            {walk.length > 0 && (
              <div className="flex-1 rounded-xl border border-border/60 bg-card p-4 shadow-sm">
                <p className="mb-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                  Every change, signed
                </p>
                <ul className="space-y-1.5">
                  {walk.map((w, i) => (
                    <li key={i} className="flex items-baseline gap-2 text-sm">
                      <span className="shrink-0 text-xs tabular-nums text-muted-foreground">
                        {walkDate(w.when)}
                      </span>
                      <span className="truncate font-medium">{walkActor(w.authored_by)}</span>
                      {w.change && (
                        <span className="truncate text-xs text-muted-foreground">
                          — {w.change}
                        </span>
                      )}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* ── The join card (accept stays auth-gated) ── */}
            <div className="w-full rounded-xl border border-border/60 bg-card p-6 text-center shadow-sm sm:max-w-xs">
              {artifact ? (
                <>
                  <h1 className="text-base font-semibold">
                    {preview?.role === "viewer" ? "View this document" : "Work on this together"}
                  </h1>
                  <p className="mt-2 text-sm text-muted-foreground">
                    {preview?.role === "viewer"
                      ? `You'll see it read-only — the document and who changed it.`
                      : `Join ${wsName} with full access — every change signed by whoever made it, human or not.`}
                  </p>
                </>
              ) : (
                <>
                  <h1 className="text-base font-semibold">Join {wsName}</h1>
                  <p className="mt-2 text-sm text-muted-foreground">
                    A shared, attributed workspace — every change records who made it.
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
                  className="mt-5 inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-60"
                >
                  {accepting && <Loader2 className="h-4 w-4 animate-spin" />}
                  {preview?.role === "viewer"
                    ? "View read-only"
                    : artifact ? "Open & join" : "Accept & join"}
                </button>
              )}
              {error && <p className="mt-3 text-xs text-destructive">{error}</p>}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
