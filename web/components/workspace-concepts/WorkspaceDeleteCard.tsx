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

import { useTranslations } from "next-intl";

import { api, APIError, clearActiveWorkspace } from "@/lib/api/client";
import { useFeedback } from "@/contexts/FeedbackContext";

interface Preview {
  workspace_id: string;
  name: string;
  is_last_owned: boolean;
  // `label` — the resolved display name (ADR-578 D4). Optional: server-side
  // resolution is best-effort, so an unresolved principal keeps only its id.
  other_principals: Array<{ principal_id: string; role: string; label?: string }>;
  deleted_at: string | null;
}

export function WorkspaceDeleteCard({ workspaceId }: { workspaceId: string | null }) {
  const t = useTranslations("workspaceSettings.delete");
  const tRoles = useTranslations("workspaceSettings.roles");
  const [preview, setPreview] = useState<Preview | null>(null);
  const [loaded, setLoaded] = useState(false);
  const [forbidden, setForbidden] = useState(false);
  const [confirming, setConfirming] = useState<"delete" | "purge" | null>(null);
  // Typed confirmation for PURGE only. Delete is reversible (Restore sits
  // beside it), so a second click is proportionate friction there; purge
  // destroys every file AND its history with no undo, which is the one act on
  // this surface where the near-universal SaaS convention — type the name —
  // actually earns its cost. Friction on a reversible act just trains people
  // to type through the irreversible one.
  const [purgeTyped, setPurgeTyped] = useState("");
  const [pending, setPending] = useState<string | null>(null);
  // `error` carries ONLY the preview's load failure — an unresolved state that
  // must survive until the operator retries (the in-surface banner lane). The
  // three VERBS below report through the canonical action-feedback layer
  // (ACTION-FEEDBACK.md): they are discrete acts with a point outcome, and two
  // of them hard-navigate, so an inline line would never be read.
  const [error, setError] = useState<string | null>(null);
  const { runAction } = useFeedback();

  const load = useCallback(async () => {
    if (!workspaceId) return;
    try {
      setPreview(await api.workspace.deletePreview(workspaceId));
      setForbidden(false);
    } catch (e) {
      // A 403 is a FACT about the caller (not the owner), not a broken surface
      // — hide the card. ANYTHING ELSE is a broken surface, and hiding it there
      // silently erased "Delete Workspace" on a 404 / 503 / transport blip with
      // no message at all (2026-08-20 audit). Key on the STATUS, like the
      // sibling roster read does (WorkspaceMembersCard) — the comment named 403
      // while the code caught everything.
      const status =
        e && typeof e === "object" && "status" in e
          ? (e as { status?: number }).status
          : undefined;
      if (status === 403) {
        setForbidden(true);
      } else {
        setError(
          e instanceof Error ? e.message : t("loadFailed")
        );
      }
    } finally {
      setLoaded(true);
    }
  }, [workspaceId, t]);

  useEffect(() => {
    void load();
  }, [load]);

  if (!workspaceId || !loaded) return null;
  // A 403 is a fact about the caller — but SHOW the control, disabled, with the
  // reason. This used to `return null`, so a member saw the two clear cards
  // greyed with "Only the workspace owner can clear shared content" and then
  // simply no delete card at all: ONE pane, TWO refusal treatments, and the
  // heavier act was the one that vanished. A missing control teaches nothing —
  // the member cannot tell whether deletion is unavailable to them, or absent
  // from the product. Disabled-with-a-reason tells them who to ask. Enforcement
  // is server-side regardless (_assert_delete_authority); this is legibility,
  // not permission. The preview never loads under a 403, so this renders from
  // no workspace data at all.
  if (forbidden) {
    return (
      <div className="rounded-lg border border-border p-4 opacity-70">
        <div className="flex items-start gap-3">
          <Trash2 className="w-4 h-4 mt-0.5 text-muted-foreground shrink-0" />
          <div className="min-w-0">
            <h3 className="text-sm font-medium text-muted-foreground">
              {t("forbiddenTitle")}
            </h3>
            <p className="mt-1 text-sm text-muted-foreground">
              {t("forbiddenBody")}
            </p>
          </div>
        </div>
      </div>
    );
  }
  // Anything else that stopped the preview loading is a BROKEN SURFACE, not a
  // refusal. Returning null here erased the card silently (2026-08-20 audit);
  // the whole point of naming the failure is that "Delete Workspace" vanishing
  // without a word is indistinguishable from not being offered it at all.
  if (!preview) {
    return error ? (
      <div className="rounded-lg border border-destructive/40 p-4">
        <p className="text-sm text-destructive" role="alert">{error}</p>
        <button
          onClick={() => void load()}
          className="mt-2 text-xs text-muted-foreground underline hover:text-foreground"
        >
          {t("tryAgain")}
        </button>
      </div>
    ) : null;
  }

  const others = preview.other_principals ?? [];
  const isDeleted = !!preview.deleted_at;

  const act = async (verb: "delete" | "restore" | "purge") => {
    setPending(verb);
    setPurgeTyped("");
    // Delete and purge END with a hard navigation, so there is no moment left
    // in which to show a success line — the pending toast is what makes the
    // wait legible, and arriving at Chat is the receipt. Restore stays put, so
    // it gets a success line.
    const copy = {
      delete: {
        pending: t("pendingDelete"),
        success: undefined,
        fallback: t("failedDelete"),
      },
      purge: {
        pending: t("pendingPurge"),
        success: undefined,
        fallback: t("failedPurge"),
      },
      restore: {
        pending: t("pendingRestore"),
        success: t("successRestore"),
        fallback: t("failedRestore"),
      },
    }[verb];
    try {
      await runAction(
        async () => {
          if (verb === "delete") {
            await api.workspace.softDelete(workspaceId);
            return;
          }
          if (verb === "purge") {
            await api.workspace.purge(workspaceId);
            return;
          }
          await api.workspace.restore(workspaceId);
        },
        {
          pending: copy.pending,
          success: copy.success,
          error: (e) =>
            e instanceof APIError
              ? (e.data as { detail?: string })?.detail || copy.fallback
              : copy.fallback,
        },
      );
      if (verb === "delete" || verb === "purge") {
        // The acting workspace is now unreachable — drop the pin and hard-
        // navigate, or every surface keeps requesting a workspace that 403s.
        clearActiveWorkspace();
        window.location.assign("/chat");
        return;
      }
      await load();
    } catch {
      // Reported by runAction; the card stays where it is so the act can be
      // retried. `error` is not touched — it belongs to the preview load.
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
            {isDeleted ? t("deletedTitle") : t("liveTitle")}
          </h3>
          <p className="text-sm text-muted-foreground mt-1">
            {isDeleted ? t("deletedBody") : t("liveBody")}
          </p>

          {/* D3 — the last owned workspace cannot be deleted. Say why, rather
              than presenting a button that 400s. */}
          {!isDeleted && preview.is_last_owned && (
            <p className="text-xs text-muted-foreground mt-2">{t("lastOwned")}</p>
          )}

          {/* D4 — the witness dial: name who loses access. */}
          {!isDeleted && others.length > 0 && (
            <div className="mt-2 rounded border border-destructive/30 bg-destructive/5 px-3 py-2">
              <p className="text-xs text-destructive">
                {t("witness", { count: others.length })}
              </p>
              <ul className="mt-1 text-xs text-muted-foreground">
                {others.slice(0, 5).map((p) => (
                  <li key={p.principal_id}>
                    {/* ADR-578 D4: this list is the fact that makes the act
                        heavy, so it must be READABLE. The server names each
                        principal best-effort; an unresolved id keeps its raw
                        value rather than rendering blank. */}
                    {p.label ?? p.principal_id} (
                    {tRoles.has(p.role) ? tRoles(p.role) : p.role})
                  </li>
                ))}
                {others.length > 5 && (
                  <li>{t("witnessMore", { count: others.length - 5 })}</li>
                )}
              </ul>
            </div>
          )}

          {/* The PREVIEW's load failure only — reachable when a refresh after
              Restore fails and the card is left showing stale details. The
              verbs' own failures report through the action-feedback layer. */}
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
                {t("deleteCta")}
              </button>
            )}

            {!isDeleted && confirming === "delete" && (
              <>
                <span className="text-sm text-muted-foreground">
                  {t("deleteAsk", { name: preview.name })}
                </span>
                <button
                  type="button"
                  onClick={() => void act("delete")}
                  disabled={pending !== null}
                  className="px-3 py-1.5 rounded-md bg-destructive text-destructive-foreground text-sm inline-flex items-center gap-1.5"
                >
                  {pending === "delete" && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                  {t("deleteConfirm")}
                </button>
                <button
                  type="button"
                  onClick={() => setConfirming(null)}
                  className="px-3 py-1.5 rounded-md border text-sm"
                >
                  {t("cancel")}
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
                  {t("restore")}
                </button>

                {confirming !== "purge" ? (
                  <button
                    type="button"
                    onClick={() => setConfirming("purge")}
                    disabled={pending !== null}
                    className="px-3 py-1.5 rounded-md border border-destructive/50 text-destructive text-sm"
                  >
                    {t("purgeCta")}
                  </button>
                ) : (
                  <>
                    <span className="text-sm text-destructive inline-flex items-center gap-1.5">
                      <AlertTriangle className="w-3.5 h-3.5" />
                      {t("purgeWarning")}
                      {/* ADR-405: the system does not destroy work unwitnessed.
                          Naming the loss without naming the remedy is only half
                          the witness — the copy is available right up to here. */}
                      <span className="text-muted-foreground">
                        {t("purgeRemedy")}
                      </span>
                    </span>
                    {/* Type the workspace name. The name is shown right here:
                        the point is not recall, it is making the operator
                        NAME the thing they are destroying, so an
                        already-moving hand has to stop. Compared
                        case-insensitively and trimmed — this is a speed bump,
                        not a spelling test. */}
                    <label className="inline-flex items-center gap-2 text-sm">
                      <span className="text-muted-foreground">
                        {t.rich("purgeTypeLabel", {
                          name: preview.name,
                          b: (chunks) => (
                            <span className="font-medium text-foreground">{chunks}</span>
                          ),
                        })}
                      </span>
                      <input
                        type="text"
                        value={purgeTyped}
                        onChange={(e) => setPurgeTyped(e.target.value)}
                        disabled={pending !== null}
                        aria-label={t("purgeTypeAria", { name: preview.name })}
                        autoComplete="off"
                        className="w-48 rounded-md border border-border bg-background px-2 py-1 text-sm"
                      />
                    </label>
                    <button
                      type="button"
                      onClick={() => void act("purge")}
                      disabled={
                        pending !== null ||
                        purgeTyped.trim().toLowerCase() !== preview.name.trim().toLowerCase()
                      }
                      className="px-3 py-1.5 rounded-md bg-destructive text-destructive-foreground text-sm inline-flex items-center gap-1.5 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      {pending === "purge" && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                      {t("purgeConfirm")}
                    </button>
                    <button
                      type="button"
                      onClick={() => {
                        setConfirming(null);
                        setPurgeTyped("");
                      }}
                      className="px-3 py-1.5 rounded-md border text-sm"
                    >
                      {t("cancel")}
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
