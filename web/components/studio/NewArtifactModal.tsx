'use client';

/**
 * NewArtifactModal — the "name it" step of scratch creation (ADR-452 v2).
 *
 * The landing shows choices, never form fields: clicking a type card opens this
 * focused modal — name → destination folder (PICKED, never typed) → Create.
 *
 * ── The OS gesture (2026-07-20) ───────────────────────────────────────────
 * This used to carry a font-mono `operation/…/artifact.html` path INPUT the
 * operator typed into — the exact raw-path gesture ADR-400 Q2 banned for Move
 * ("shouldn't be a URL path input") and that `MoveToFolderModal` exists to kill.
 * New now follows the same Finder truth: name it, then NAVIGATE to a destination
 * folder in the shared `WorkspacePicker`. The path is composed for the operator
 * as `{folder}/{slug(name)}/{template}.html` — never edited as a string.
 *
 * The default destination is `operation/` (ADR-440 D6 — the Studio never invents
 * an app-named root; work lives under operation/), so the fast path stays one
 * field + Enter. Choosing elsewhere is the picker, the same one Open/Move use.
 */

import { useEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { Loader2, Plus, Folder } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Z_CONFIRM_BACKDROP, Z_CONFIRM_DIALOG } from '@/lib/shell/z-tiers';
import { operatorCanOrganize } from '@/lib/workspace/ownership';
import type { WorkspaceTreeNode } from '@/types';
import { WorkspacePickerModal } from '@/components/workspace/WorkspacePicker';

/** The path KEY for a typed name — mirrors `services/naming.py::path_slug`
 *  (ADR-469). Accents FOLD to their base letter (`café` → `cafe`) rather than
 *  being deleted; a name with no Latin characters yields `untitled`, and the
 *  server disambiguates it (`untitled-2`, …) against what already exists.
 *
 *  Lossy ON PURPOSE and no longer load-bearing: the key does not carry the
 *  name any more. What the member typed travels beside it and lands in the
 *  artifact's <title>, verbatim. Keep in step with the Python. */
export function slugify(name: string): string {
  return (
    name
      .normalize('NFKD')
      .replace(/[\u0300-\u036f]/g, '') // strip combining marks: é -> e
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/-{2,}/g, '-')
      .replace(/^-+|-+$/g, '')
      .slice(0, 48)
      .replace(/-+$/, '') || 'untitled'
  );
}

/** The default destination — the operation/ root (ADR-440 D6). */
const DEFAULT_DEST = '/workspace/operation';

/** A destination for display — trim the workspace prefix. */
function shortDest(path: string): string {
  return path.replace(/^\/workspace\//, '') || '/';
}

interface NewArtifactModalProps {
  /** The chosen type (null = closed). */
  template: { slug: string; label: string; description: string } | null;
  onClose: () => void;
  /** Create + open — throws so the failure shows inline here. `name` is what
   *  the member typed, carried alongside the slugified path so the artifact's
   *  <title> gets the real thing (ADR-469). */
  onCreate: (templateSlug: string, path: string, name: string) => Promise<void>;
}

export function NewArtifactModal({ template, onClose, onCreate }: NewArtifactModalProps) {
  const [name, setName] = useState('');
  const [dest, setDest] = useState(DEFAULT_DEST);
  const [pickingDest, setPickingDest] = useState(false);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (template) {
      setName('');
      setDest(DEFAULT_DEST);
      setErr(null);
      requestAnimationFrame(() => inputRef.current?.focus());
    }
  }, [template]);

  if (!template) return null;

  // The composed path — meaning-placed under the picked destination.
  const composedPath = name.trim()
    ? `${dest.replace(/^\/workspace\//, '')}/${slugify(name)}/${template.slug}.html`
    : '';

  const canCreate = !!name.trim() && !busy;
  const submit = async () => {
    if (!canCreate) return;
    setBusy(true);
    setErr(null);
    try {
      await onCreate(template.slug, composedPath, name.trim());
    } catch (e) {
      setErr(e instanceof Error ? e.message : 'Creation failed.');
      setBusy(false);
    }
  };

  return createPortal(
    <>
      <div
        className="fixed inset-0 bg-black/50 animate-in fade-in duration-150"
        style={{ zIndex: Z_CONFIRM_BACKDROP }}
        onClick={onClose}
      />
      <div
        className="fixed inset-0 flex items-center justify-center p-4 pointer-events-none"
        style={{ zIndex: Z_CONFIRM_DIALOG }}
      >
        <div
          className="pointer-events-auto w-full max-w-sm rounded-lg border border-border bg-card p-5 shadow-xl animate-in fade-in zoom-in-95 duration-150"
          role="dialog"
          aria-modal="true"
        >
          <h3 className="text-base font-semibold text-card-foreground">
            New {template.label.toLowerCase()}
          </h3>
          <input
            ref={inputRef}
            value={name}
            onChange={(e) => setName(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') void submit();
              if (e.key === 'Escape') onClose();
            }}
            placeholder="Name it (e.g. IR deck v3)"
            className="mt-3 w-full rounded-md border border-border bg-background px-3 py-2 text-sm outline-none focus:border-primary"
            aria-label="Name"
          />

          {/* Destination — picked, not typed. Clicking opens the shared
              folder-picker (the same tree Open/Move use). */}
          <button
            type="button"
            onClick={() => setPickingDest(true)}
            className="mt-2 flex w-full items-center gap-2 rounded-md border border-border bg-background px-3 py-2 text-left text-sm transition-colors hover:bg-muted/50"
            aria-label="Choose destination folder"
          >
            <Folder className="h-3.5 w-3.5 shrink-0 text-blue-500" />
            <span className="min-w-0 flex-1 truncate text-muted-foreground">
              <span className="text-foreground">{shortDest(dest)}</span>
              {name.trim() && (
                <span className="font-mono text-xs">
                  {' / '}
                  {slugify(name)}/{template.slug}.html
                </span>
              )}
            </span>
            <span className="shrink-0 text-xs text-muted-foreground/70">Change</span>
          </button>

          {err && <p className="mt-1.5 text-xs text-destructive">{err}</p>}
          <div className="mt-5 flex justify-end gap-2">
            <button
              type="button"
              onClick={onClose}
              className="rounded-md border border-border px-3.5 py-1.5 text-sm text-foreground transition-colors hover:bg-muted/60"
            >
              Cancel
            </button>
            <button
              type="button"
              disabled={!canCreate}
              onClick={() => void submit()}
              className={cn(
                'inline-flex items-center gap-1.5 rounded-md px-3.5 py-1.5 text-sm font-medium transition-colors',
                canCreate
                  ? 'bg-primary text-primary-foreground hover:bg-primary/90'
                  : 'cursor-not-allowed bg-muted text-muted-foreground',
              )}
            >
              {busy ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Plus className="h-3.5 w-3.5" />}
              Create
            </button>
          </div>
        </div>
      </div>

      <WorkspacePickerModal
        open={pickingDest}
        mode="folder"
        title="Choose a destination"
        subtitle="Where the new file lives"
        confirmLabel="Choose"
        emptyMessage="No folders available."
        initialSelected={dest}
        selectable={(node: WorkspaceTreeNode) => operatorCanOrganize(`${node.path}/x`)}
        folderDisabledTitle={(node) =>
          operatorCanOrganize(`${node.path}/x`) ? undefined : 'This folder is managed by the system'
        }
        canConfirm={(sel) => operatorCanOrganize(`${sel}/x`)}
        footerHint={(sel) =>
          sel ? <>Into <span className="font-mono">{shortDest(sel)}</span></> : 'Pick a folder'
        }
        onClose={() => setPickingDest(false)}
        onConfirm={(folder) => {
          setDest(folder);
          setPickingDest(false);
        }}
      />
    </>,
    document.body,
  );
}
