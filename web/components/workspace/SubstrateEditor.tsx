'use client';

/**
 * SubstrateEditor — inline edit surface for operator-authored substrate files
 * on the Files tab (ADR-215 R3).
 *
 * R3: if the thing being edited IS a file, the edit surface is Files. The
 * revision chain (ADR-209) records `authored_by=operator`. No "Edit in chat"
 * button on substrate files — Chat would invoke UpdateContext anyway, and
 * direct substrate edit produces the same write with clearer provenance.
 *
 * Scope:
 *   - `/workspace/context/_shared/*.md` — the four authored rules files
 *     (IDENTITY, BRAND, CONVENTIONS, MANDATE). Phase 2 landing.
 *   - `/workspace/review/principles.md` — Reviewer principles. Phase 3
 *     landing (ADR-215 Phase 3 — R3 compliance for the last remaining
 *     operator-authored substrate file editable via chat).
 *
 * Out of scope:
 *   - Task files (TASK.md, DELIVERABLE.md, feedback.md) — edit path is Chat
 *     per R1 (task lifecycle is judgment-shaped).
 *   - Uploads — re-upload is the edit path; no inline text editor.
 *   - Agent AGENT.md files — edits flow through ManageAgent / UpdateContext
 *     primitives (judgment-shaped), not direct operator substrate writes.
 *
 * Writes route through `api.workspace.editFile()` (PATCH /api/workspace/file),
 * which invokes `write_revision()` with `authored_by="operator"` on the server
 * (ADR-209).
 */

import { useEffect, useState } from 'react';
import { Loader2, Save, X } from 'lucide-react';
import { api } from '@/lib/api/client';

/**
 * Whether a given path supports inline substrate editing on Files.
 * Keep in sync with `editable_prefixes` in api/routes/workspace.py for the
 * authored-rules paths that ADR-215 R3 routes here.
 */
const SHARED_EDITABLE_PATHS = new Set<string>([
  '/workspace/context/_shared/IDENTITY.md',
  '/workspace/context/_shared/BRAND.md',
  '/workspace/context/_shared/CONVENTIONS.md',
  '/workspace/context/_shared/MANDATE.md',
  '/workspace/review/principles.md',  // ADR-215 Phase 3
]);

export function isSubstrateEditable(path: string | null | undefined): boolean {
  if (!path) return false;
  return SHARED_EDITABLE_PATHS.has(path);
}

export interface SubstrateEditorProps {
  path: string;
  /** Initial content loaded from the file. */
  initialContent: string;
  /** Called after a successful save so the parent can refresh if desired. */
  onSaved?: () => void;
}

export function SubstrateEditor({ path, initialContent, onSaved }: SubstrateEditorProps) {
  const [content, setContent] = useState(initialContent);
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [savedAt, setSavedAt] = useState<number | null>(null);

  useEffect(() => {
    setContent(initialContent);
    setEditing(false);
    setError(null);
    setSavedAt(null);
  }, [path, initialContent]);

  const filename = path.split('/').pop() || path;

  const handleSave = async () => {
    setSaving(true);
    setError(null);
    try {
      await api.workspace.editFile(
        path,
        content,
        `edit ${filename}`,
        `operator edit ${filename}`,
      );
      setSavedAt(Date.now());
      setEditing(false);
      onSaved?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Save failed');
    } finally {
      setSaving(false);
    }
  };

  const handleCancel = () => {
    setContent(initialContent);
    setEditing(false);
    setError(null);
  };

  if (!editing) {
    return (
      <div className="flex flex-wrap items-center gap-2">
        <button
          type="button"
          onClick={() => setEditing(true)}
          className="inline-flex items-center gap-1 rounded-md border border-border px-2.5 py-1.5 text-xs text-muted-foreground hover:bg-muted/40 hover:text-foreground"
        >
          Edit file
        </button>
        {savedAt && (
          <span className="text-[11px] text-muted-foreground/70">
            Saved. A new revision was recorded.
          </span>
        )}
      </div>
    );
  }

  return (
    <div className="rounded-md border border-border bg-muted/10 p-3">
      <div className="mb-2 flex items-center justify-between gap-2">
        <p className="text-[11px] text-muted-foreground">
          Editing <span className="font-mono">{filename}</span> — your changes
          record as an operator revision on save.
        </p>
        <button
          type="button"
          onClick={handleCancel}
          disabled={saving}
          className="rounded p-1 text-muted-foreground/60 hover:bg-muted hover:text-foreground disabled:opacity-50"
          aria-label="Cancel edit"
        >
          <X className="h-4 w-4" />
        </button>
      </div>
      <textarea
        value={content}
        onChange={(e) => setContent(e.target.value)}
        rows={16}
        className="w-full resize-y rounded-md border border-border bg-background px-3 py-2 font-mono text-xs focus:outline-none focus:ring-1 focus:ring-foreground/20"
        disabled={saving}
      />
      {error && (
        <div className="mt-2 rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-xs text-destructive">
          {error}
        </div>
      )}
      <div className="mt-2 flex items-center justify-end gap-2">
        <button
          type="button"
          onClick={handleCancel}
          disabled={saving}
          className="rounded-md border border-border px-3 py-1.5 text-xs text-muted-foreground hover:bg-muted hover:text-foreground disabled:opacity-50"
        >
          Cancel
        </button>
        <button
          type="button"
          onClick={handleSave}
          disabled={saving || content === initialContent}
          className="inline-flex items-center gap-1.5 rounded-md bg-foreground px-3 py-1.5 text-xs text-background hover:bg-foreground/90 disabled:opacity-50"
        >
          {saving ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Save className="h-3.5 w-3.5" />}
          {saving ? 'Saving…' : 'Save'}
        </button>
      </div>
    </div>
  );
}
