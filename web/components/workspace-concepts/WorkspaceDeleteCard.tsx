"use client";

/**
 * Delete this workspace — the lifecycle (ADR-578).
 *
 * Distinct from the Clear cards above it, and the distinction is the point:
 * clearing empties a workspace you keep using; deleting ENDS it. Clearing
 * leaves the row on the switcher forever, which is why a workspace the operator
 * was finished with had nowhere to go before this shipped.
 *
 * Three states, one card:
 *   live     → "Delete workspace" (soft, reversible)
 *   deleted  → "Restore" + "Purge permanently" (the second, terminal act)
 *
 * NO TIMER (ADR-478 D2 / ADR-405): a deleted workspace waits indefinitely. The
 * conventional SaaS 30-day auto-purge is deliberately refused — a schedule that
 * destroys a member's work with nobody watching is the one convention canon
 * already ruled against. The copy says "kept until you purge it" and means it.
 *
 * The confirmation NAMES the other principals who lose access (D4) rather than
 * printing a generic "cannot be undone" — that is the witness dial's whole job,
 * and it is the only fact that makes this act heavy.
 */

import { useCallback, useEffect, useState } from "react";
import { AlertTriangle, Loader2, RotateCcw, Trash2 } from "lucide-react";

import { api, clearActiveWorkspace } from "@/lib/api/client";

interface Preview {
  workspace_id: string;
  name: string;
  is_last_owned: boolean;
  other_principals: Array<{ principal_id: string; role: string }>;
  deleted_at: string | null;
}

export function WorkspaceDeleteCard({ workspaceId }: { workspaceId: string | null }) {
  const [preview, setPreview] = useState<Preview | null>(null);
  const [loaded, setLoaded] = useState(false);
  const [forbidden, setForbidden] = useState(false);
  const [confirming, setConfirming] = useState<"delete" | "purge" | null>(null);
  const [pending, setPending] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!workspaceId) return;
    try {
      setPreview(await api.workspace.deletePreview(workspaceId));
      setForbidden(false);
    } catch (e) {
      // A 403 is a FACT about the caller (not the owner), not a broken surface.
      setForbidden(true);
    } finally {
      setLoaded(true);
    }
  }, [workspaceId]);

  useEffect(() => {
    void load();
  }, [load]);

  if (!workspaceId || !loaded) return null;
  if (forbidden || !preview) return null;

  const others = preview.other_principals ?? [];
  const isDeleted = !!preview.deleted_at;

  const act = async (verb: "delete" | "restore" | "purge") => {
    setPending(verb);
    setError(null);
    try {
      if (verb === "delete") {
        await api.workspace.softDelete(workspaceId);
        // The acting workspace is now unreachable — drop the pin and hard-
        // navigate, or every surface keeps requesting a workspace that 403s.
        clearActiveWorkspace();
        window.location.assign("/chat");
        return;
      }
      if (verb === "purge") {
        await api.workspace.purge(workspaceId);
        clearActiveWorkspace();
        window.location.assign("/chat");
        return;
      }
      await api.workspace.restore(workspaceId);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : `Couldn't ${verb} this workspace`);
    } finally {
      setPending(null);
      setConfirming(null);
    }
  };

  return (
    <div className="rounded-lg border border-destructive/40 p-4">
      <div className="flex items-start gap-3">
        <Trash2 className="w-4 h-4 mt-0.5 text-destructive shrink-0" />
        <div className="flex-1 min-w-0">
          <h3 className="text-sm font-medium">
            {isDeleted ? "Workspace deleted" : "Delete Workspace"}
          </h3>
          <p className="text-sm text-muted-foreground mt-1">
            {isDeleted
              ? "This workspace is deleted and hidden. Nothing has been destroyed — it's kept until you purge it."
              : "Remove this workspace and everything in it. It's hidden immediately and kept until you purge it — there's no automatic deletion."}
          </p>

          {/* D3 — the last owned workspace cannot be deleted. Say why, rather
              than presenting a button that 400s. */}
          {!isDeleted && preview.is_last_owned && (
            <p className="text-xs text-muted-foreground mt-2">
              This is your only workspace. Create another one first — deleting
              your last workspace would immediately mint a replacement.
            </p>
          )}

          {/* D4 — the witness dial: name who loses access. */}
          {!isDeleted && others.length > 0 && (
            <div className="mt-2 rounded border border-destructive/30 bg-destructive/5 px-3 py-2">
              <p className="text-xs text-destructive">
                {others.length} other {others.length === 1 ? "principal" : "principals"} will
                lose access to this workspace and everything they&rsquo;ve made in it:
              </p>
              <ul className="mt-1 text-xs text-muted-foreground">
                {others.slice(0, 5).map((p) => (
                  <li key={p.principal_id}>
                    {p.principal_id} ({p.role})
                  </li>
                ))}
                {others.length > 5 && <li>…and {others.length - 5} more</li>}
              </ul>
            </div>
          )}

          {error && (
            <p className="text-sm text-destructive mt-2" role="alert">
              {error}
            </p>
          )}

          <div className="mt-3 flex flex-wrap items-center gap-2">
            {!isDeleted && confirming !== "delete" && (
              <button
                type="button"
                disabled={preview.is_last_owned || pending !== null}
                onClick={() => setConfirming("delete")}
                className="px-3 py-1.5 rounded-md border border-destructive/50 text-destructive text-sm disabled:opacity-50"
              >
                Delete workspace
              </button>
            )}

            {!isDeleted && confirming === "delete" && (
              <>
                <span className="text-sm text-muted-foreground">
                  Delete &ldquo;{preview.name}&rdquo;? You can restore it afterwards.
                </span>
                <button
                  type="button"
                  onClick={() => void act("delete")}
                  disabled={pending !== null}
                  className="px-3 py-1.5 rounded-md bg-destructive text-destructive-foreground text-sm inline-flex items-center gap-1.5"
                >
                  {pending === "delete" && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                  Confirm delete
                </button>
                <button
                  type="button"
                  onClick={() => setConfirming(null)}
                  className="px-3 py-1.5 rounded-md border text-sm"
                >
                  Cancel
                </button>
              </>
            )}

            {isDeleted && (
              <>
                <button
                  type="button"
                  onClick={() => void act("restore")}
                  disabled={pending !== null}
                  className="px-3 py-1.5 rounded-md border text-sm inline-flex items-center gap-1.5"
                >
                  {pending === "restore" ? (
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  ) : (
                    <RotateCcw className="w-3.5 h-3.5" />
                  )}
                  Restore
                </button>

                {confirming !== "purge" ? (
                  <button
                    type="button"
                    onClick={() => setConfirming("purge")}
                    disabled={pending !== null}
                    className="px-3 py-1.5 rounded-md border border-destructive/50 text-destructive text-sm"
                  >
                    Purge permanently
                  </button>
                ) : (
                  <>
                    <span className="text-sm text-destructive inline-flex items-center gap-1.5">
                      <AlertTriangle className="w-3.5 h-3.5" />
                      Destroys every file and its history. Cannot be undone.
                    </span>
                    <button
                      type="button"
                      onClick={() => void act("purge")}
                      disabled={pending !== null}
                      className="px-3 py-1.5 rounded-md bg-destructive text-destructive-foreground text-sm inline-flex items-center gap-1.5"
                    >
                      {pending === "purge" && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                      Purge forever
                    </button>
                    <button
                      type="button"
                      onClick={() => setConfirming(null)}
                      className="px-3 py-1.5 rounded-md border text-sm"
                    >
                      Cancel
                    </button>
                  </>
                )}
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
