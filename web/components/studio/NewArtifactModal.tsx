'use client';

/**
 * NewArtifactModal — the "name it" step of scratch creation (ADR-452 v2).
 *
 * The landing shows choices, never form fields: clicking a type card opens
 * this focused modal — name → meaning-placed path (editable) → Create. The
 * path default follows ADR-440 D6: under operation/, named by the work; the
 * Studio never invents an app-named root. Mirrors the RenameModal shell.
 */

import { useEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { Loader2, Plus } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Z_CONFIRM_BACKDROP, Z_CONFIRM_DIALOG } from '@/lib/shell/z-tiers';

/** Meaning-placed slug (shared with the landing's learn-from flow). */
export function slugify(name: string): string {
  return name
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 48) || 'untitled';
}

interface NewArtifactModalProps {
  /** The chosen type (null = closed). */
  template: { slug: string; label: string; description: string } | null;
  onClose: () => void;
  /** Create + open — throws so the failure shows inline here. */
  onCreate: (templateSlug: string, path: string) => Promise<void>;
}

export function NewArtifactModal({ template, onClose, onCreate }: NewArtifactModalProps) {
  const [name, setName] = useState('');
  const [path, setPath] = useState('');
  const [pathEdited, setPathEdited] = useState(false);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (template) {
      setName('');
      setPath('');
      setPathEdited(false);
      setErr(null);
      requestAnimationFrame(() => inputRef.current?.focus());
    }
  }, [template]);

  useEffect(() => {
    if (pathEdited || !template) return;
    setPath(name ? `operation/${slugify(name)}/${template.slug}.html` : '');
  }, [name, template, pathEdited]);

  if (!template) return null;

  const canCreate = !!path.trim() && !busy;
  const submit = async () => {
    if (!canCreate) return;
    setBusy(true);
    setErr(null);
    try {
      await onCreate(template.slug, path.trim());
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
          <input
            value={path}
            onChange={(e) => {
              setPathEdited(true);
              setPath(e.target.value);
            }}
            placeholder="operation/…/artifact.html (meaning-placed)"
            className="mt-2 w-full rounded-md border border-border bg-background px-3 py-2 font-mono text-xs outline-none focus:border-primary"
            aria-label="Workspace path"
          />
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
    </>,
    document.body,
  );
}
