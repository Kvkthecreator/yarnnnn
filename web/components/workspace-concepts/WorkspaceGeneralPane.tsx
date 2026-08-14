"use client";

/**
 * Workspace General — name + icon (workspace identity phase 1, 2026-08-14).
 *
 * The one place the workspace's own identity is edited. The name is what
 * invite emails, the invite/share landings, and the switcher show; the icon
 * is a short text glyph (emoji) — deliberately NOT an image upload (the
 * unauthenticated invite/share landings would need a public serving lane the
 * private workspace-cas bucket rightly refuses).
 *
 * Gate: the backend PATCH writes through the CALLER's client, so the RLS
 * UPDATE policy (owner-only) is the enforcement — a member's save would 403.
 * Like the Danger Zone's `can_clear` pattern, this surface reads the server's
 * own membership row (role) only to avoid OFFERING an action that would 403;
 * the backend gate remains the authority.
 */

import { useState } from "react";
import { Building2, Loader2 } from "lucide-react";

import { api } from "@/lib/api/client";
import { useWorkspaceMemberships } from "@/lib/workspace/viewer";

export function WorkspaceGeneralPane() {
  const { memberships, loaded } = useWorkspaceMemberships();
  const active = memberships.find((m) => m.is_active);
  const isOwner = active?.role === "owner";

  // Form state seeds from the membership row once loaded; `null` = untouched
  // (render the server value), a string = the operator's edit in progress.
  const [nameEdit, setNameEdit] = useState<string | null>(null);
  const [iconEdit, setIconEdit] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!loaded) {
    return (
      <div className="flex items-center gap-2 text-sm text-muted-foreground">
        <Loader2 className="w-4 h-4 animate-spin" /> Loading…
      </div>
    );
  }
  if (!active) {
    return (
      <p className="text-sm text-muted-foreground">
        Couldn&rsquo;t resolve the current workspace.
      </p>
    );
  }

  const name = nameEdit ?? active.label;
  const icon = iconEdit ?? (active.icon || "");
  const dirty =
    (nameEdit !== null && nameEdit.trim() !== active.label) ||
    (iconEdit !== null && iconEdit.trim() !== (active.icon || ""));

  const handleSave = async () => {
    const trimmed = name.trim();
    if (!trimmed) {
      setError("The workspace needs a name.");
      return;
    }
    setSaving(true);
    setError(null);
    try {
      const body: { name?: string; icon?: string | null } = {};
      if (nameEdit !== null) body.name = trimmed;
      if (iconEdit !== null) body.icon = icon.trim() || null;
      await api.workspace.updateIdentity(body);
      // The switcher label rides the module-cached memberships read
      // (lib/workspace/viewer.ts) and every open surface may render the old
      // identity — a hard reload is the shell's existing rebind gesture
      // (workspace switch does the same), and a rename is rare enough to
      // afford it.
      window.location.reload();
    } catch (e) {
      const detail =
        e && typeof e === "object" && "message" in e
          ? String((e as { message?: string }).message)
          : null;
      setError(detail || "Couldn't save — try again.");
      setSaving(false);
    }
  };

  return (
    <div className="max-w-md space-y-5">
      {/* Identity preview — the same row shape the switcher renders. */}
      <div className="flex items-center gap-3 rounded-lg border border-border px-3 py-2.5">
        {icon.trim() ? (
          <span className="w-5 h-5 flex items-center justify-center text-base leading-none">
            {icon.trim()}
          </span>
        ) : (
          <Building2 className="w-5 h-5 text-muted-foreground" />
        )}
        <span className="text-sm font-medium truncate">
          {name.trim() || "Untitled workspace"}
        </span>
      </div>

      <div>
        <label
          htmlFor="workspace-name"
          className="block text-xs font-medium text-muted-foreground mb-1"
        >
          Workspace name
        </label>
        <input
          id="workspace-name"
          type="text"
          value={name}
          maxLength={80}
          disabled={!isOwner || saving}
          onChange={(e) => setNameEdit(e.target.value)}
          className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/30 disabled:opacity-60"
        />
        <p className="mt-1 text-[11px] text-muted-foreground">
          Shown to members in the workspace switcher, and to invitees in
          invite emails and share links.
        </p>
      </div>

      <div>
        <label
          htmlFor="workspace-icon"
          className="block text-xs font-medium text-muted-foreground mb-1"
        >
          Icon
        </label>
        <input
          id="workspace-icon"
          type="text"
          value={icon}
          maxLength={16}
          disabled={!isOwner || saving}
          onChange={(e) => setIconEdit(e.target.value)}
          placeholder="🏢"
          className="w-24 rounded-md border border-border bg-background px-3 py-2 text-sm text-center focus:outline-none focus:ring-2 focus:ring-primary/30 disabled:opacity-60"
        />
        <p className="mt-1 text-[11px] text-muted-foreground">
          An emoji. Leave empty for the default glyph.
        </p>
      </div>

      {error && <p className="text-xs text-destructive">{error}</p>}

      {isOwner ? (
        <button
          type="button"
          onClick={handleSave}
          disabled={!dirty || saving}
          className="inline-flex items-center gap-2 rounded-md bg-primary px-3 py-1.5 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50 transition-colors"
        >
          {saving && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
          Save
        </button>
      ) : (
        <p className="text-xs text-muted-foreground">
          Only the workspace owner can change the name and icon.
        </p>
      )}
    </div>
  );
}
