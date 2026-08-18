"use client";

/**
 * Create a workspace — the deliberate genesis act (ADR-465 D2).
 *
 * Sits under WORKSPACE beside General, deliberately NOT inside it: General
 * edits the identity of the workspace you are IN, and creating a different
 * commons is not a property of the current one. Same door, separate pane —
 * the ADR-515 lesson (one surface, one job).
 *
 * Why the workspace door and not the account door: a workspace is the billing
 * unit (ADR-416 §2) and the outermost unit YARNNN composes (ADR-378); it is a
 * commons, not a personal object. The account door holds things scoped to the
 * human (their connections, their reset). Operator ruling 2026-08-18.
 *
 * SCOPE: a name. This is the whole act today. A future flow — directory
 * handling, starting structure, signup-shaped steps — extends
 * `services/workspace_genesis.py::_GENESIS_STEPS` server-side; this pane grows
 * a stepper over the SAME endpoint rather than a second creation path.
 *
 * Open to any authenticated principal, including a member-only one who owns
 * nothing yet (ADR-465:129's "explicitly start your own workspace"), which is
 * why this pane renders no owner gate — unlike General, whose PATCH is
 * owner-only by RLS. Genesis stamps owner_id from the authenticated caller, so
 * the created workspace is always the caller's own.
 */

import { useState } from "react";
import { Loader2, Plus } from "lucide-react";

import { api, setActiveWorkspace } from "@/lib/api/client";

export function WorkspaceCreatePane() {
  const [name, setName] = useState("");
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const trimmed = name.trim();
  const canCreate = trimmed.length > 0 && !creating;

  const handleCreate = async () => {
    if (!canCreate) return;
    setCreating(true);
    setError(null);
    try {
      const created = await api.workspace.create(trimmed);
      // Bind to the new workspace, then HARD-navigate. A bind change requires a
      // full reload (ADR-407 D9): ~10 mount-only consumers never refetch, so a
      // client-side route would leave surfaces reading the previous commons.
      // This is the same rebind the invite/share accept paths take.
      setActiveWorkspace(created.workspace_id);
      window.location.assign("/chat");
    } catch (e) {
      // Stay on the pane and keep the typed name — the workspace was not
      // created, so there is nothing to bind to.
      setError(e instanceof Error ? e.message : "Couldn't create the workspace");
      setCreating(false);
    }
  };

  return (
    <div className="max-w-xl">
      <div className="flex items-start gap-3 mb-1">
        <Plus className="w-5 h-5 mt-0.5 text-muted-foreground shrink-0" />
        <div>
          <h2 className="text-xl font-semibold">Create a workspace</h2>
          <p className="text-sm text-muted-foreground mt-1">
            A separate commons with its own files, members, and billing.
          </p>
        </div>
      </div>

      <div className="mt-6">
        <label
          htmlFor="new-workspace-name"
          className="block text-sm font-medium mb-1.5"
        >
          Workspace name
        </label>
        <input
          id="new-workspace-name"
          type="text"
          value={name}
          maxLength={80}
          disabled={creating}
          placeholder="e.g. Acme Research"
          onChange={(e) => setName(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") handleCreate();
          }}
          className="w-full px-3 py-2 rounded-lg border bg-background text-sm disabled:opacity-60"
        />
        <p className="text-xs text-muted-foreground mt-1.5">
          You can rename it later in General. You&rsquo;ll be switched into the
          new workspace.
        </p>
      </div>

      {/* The honest consequence, stated before the act (ADR-529's rule: a
          governance act names its own weight). Workspaces do not compose —
          ADR-378's ceiling — and each carries its own balance (ADR-416). */}
      <div className="mt-5 rounded-lg border bg-muted/40 px-3.5 py-3">
        <p className="text-xs text-muted-foreground leading-relaxed">
          Workspaces are fully separate. Files, members, and history don&rsquo;t
          carry over, and the new workspace has its own balance — it starts
          empty and unfunded.
        </p>
      </div>

      {error && (
        <p className="text-sm text-destructive mt-4" role="alert">
          {error}
        </p>
      )}

      <button
        type="button"
        onClick={handleCreate}
        disabled={!canCreate}
        className="mt-5 inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-primary text-primary-foreground text-sm font-medium disabled:opacity-50"
      >
        {creating && <Loader2 className="w-4 h-4 animate-spin" />}
        {creating ? "Creating…" : "Create workspace"}
      </button>
    </div>
  );
}
