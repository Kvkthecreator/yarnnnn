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

export interface TemplateChoice {
  slug: string;
  label: string;
  description: string;
}

interface NewArtifactModalProps {
  /** The shapes to choose among (null/empty = closed). ADR-470: the DELIBERATE
   *  door owns the whole choice — shape, name, and destination — because the
   *  member who takes it is the one who arrived knowing all three. */
  templates: TemplateChoice[] | null;
  onClose: () => void;
  /** Create + open — throws so the failure shows inline here. `name` is what
   *  the member typed, carried alongside the slugified path so the artifact's
   *  <title> gets the real thing (ADR-469). */
  onCreate: (
    templateSlug: string,
    path: string,
    name: string,
    dims?: { width: number; height: number },
  ) => Promise<void>;
  /** ADR-472 D3 — DIMENSIONS-FIRST. When set, the modal asks for the stage's
   *  size before anything else, the way a design tool does: the box is the
   *  first decision, not a ratio applied to a document after the fact. */
  dimensionsFirst?: boolean;
}

/** The stage presets (ADR-472 D3) — real pixel boxes, mirroring
 *  services/images.py::STAGE_PRESETS. Kept in step with the Python: the kernel
 *  owns the numbers, this is the picker's copy of the same table. */
export const STAGE_PRESETS = [
  { slug: 'square', label: 'Square', width: 1080, height: 1080, hint: 'Instagram / LinkedIn post' },
  { slug: 'story', label: 'Story', width: 1080, height: 1920, hint: 'Story / Reel, 9:16' },
  { slug: 'wide', label: 'Wide', width: 1600, height: 900, hint: 'Slide still, thumbnail, 16:9' },
  { slug: 'ad', label: 'Ad', width: 1200, height: 628, hint: 'Meta / LinkedIn link ad' },
  { slug: 'portrait', label: 'Portrait', width: 1080, height: 1350, hint: 'Instagram portrait, 4:5' },
  { slug: 'banner', label: 'Banner', width: 1500, height: 500, hint: 'X / site header' },
] as const;

export function NewArtifactModal({
  templates,
  onClose,
  onCreate,
  dimensionsFirst = false,
}: NewArtifactModalProps) {
  // ADR-472 D3: the stage's box. `custom` carries any W×H — a preset is a
  // convenience, never a constraint.
  const [presetSlug, setPresetSlug] = useState<string>('square');
  const [customW, setCustomW] = useState('1080');
  const [customH, setCustomH] = useState('1080');
  const [templateSlug, setTemplateSlug] = useState<string>('');
  const [name, setName] = useState('');
  const [dest, setDest] = useState(DEFAULT_DEST);
  const [pickingDest, setPickingDest] = useState(false);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const open = !!templates?.length;

  useEffect(() => {
    if (open) {
      setTemplateSlug(templates![0].slug);
      setPresetSlug('square');
      setCustomW('1080');
      setCustomH('1080');
      setName('');
      setDest(DEFAULT_DEST);
      setErr(null);
      requestAnimationFrame(() => inputRef.current?.focus());
    }
  }, [open, templates]);

  if (!open) return null;

  const template = templates!.find((t) => t.slug === templateSlug) ?? templates![0];

  // The composed path — meaning-placed under the picked destination.
  const composedPath = name.trim()
    ? `${dest.replace(/^\/workspace\//, '')}/${slugify(name)}/${template.slug}.html`
    : '';

  // The resolved box — a preset's numbers, or the typed custom pair.
  const dims = dimensionsFirst
    ? presetSlug === 'custom'
      ? { width: Number(customW) || 0, height: Number(customH) || 0 }
      : (() => {
          const p = STAGE_PRESETS.find((x) => x.slug === presetSlug) ?? STAGE_PRESETS[0];
          return { width: p.width, height: p.height };
        })()
    : undefined;
  const dimsValid =
    !dimensionsFirst || (!!dims && dims.width >= 16 && dims.height >= 16);

  const canCreate = !!name.trim() && dimsValid && !busy;
  const submit = async () => {
    if (!canCreate) return;
    setBusy(true);
    setErr(null);
    try {
      await onCreate(template.slug, composedPath, name.trim(), dims);
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
          <h3 className="text-base font-semibold text-card-foreground">New {template.label.toLowerCase()}</h3>

          {/* The shape — chosen HERE, because the deliberate door owns all
              three decisions (ADR-470). Hidden when there is only one shape. */}
          {templates!.length > 1 && (
            <div className="mt-3 flex flex-wrap gap-1.5" role="radiogroup" aria-label="Type">
              {templates!.map((t) => {
                const active = t.slug === template.slug;
                return (
                  <button
                    key={t.slug}
                    type="button"
                    role="radio"
                    aria-checked={active}
                    title={t.description}
                    onClick={() => setTemplateSlug(t.slug)}
                    className={cn(
                      'rounded-md border px-2.5 py-1 text-xs transition-colors',
                      active
                        ? 'border-primary bg-primary/10 font-medium text-primary'
                        : 'border-border text-muted-foreground hover:bg-muted/60',
                    )}
                  >
                    {t.label}
                  </button>
                );
              })}
            </div>
          )}
          {/* ADR-472 D3 — SIZE FIRST. A stage's box is the first decision (the
              Canva/Fabric model): every object is placed relative to it and the
              render target IS this size. Real pixels, not a ratio slug — which
              is why the ADR-471 aspect token could not survive the carve. */}
          {dimensionsFirst && (
            <div className="mt-3">
              <div className="text-xs font-medium text-muted-foreground">Size</div>
              <div className="mt-1.5 grid grid-cols-3 gap-1.5" role="radiogroup" aria-label="Size">
                {STAGE_PRESETS.map((p) => (
                  <button
                    key={p.slug}
                    type="button"
                    role="radio"
                    aria-checked={presetSlug === p.slug}
                    title={`${p.hint} — ${p.width}×${p.height}`}
                    onClick={() => setPresetSlug(p.slug)}
                    className={cn(
                      'rounded-md border px-2 py-1.5 text-left transition-colors',
                      presetSlug === p.slug
                        ? 'border-primary bg-primary/10'
                        : 'border-border hover:bg-muted/50',
                    )}
                  >
                    <div className="text-xs font-medium">{p.label}</div>
                    <div className="text-[10px] text-muted-foreground">
                      {p.width}×{p.height}
                    </div>
                  </button>
                ))}
                <button
                  type="button"
                  role="radio"
                  aria-checked={presetSlug === 'custom'}
                  onClick={() => setPresetSlug('custom')}
                  className={cn(
                    'rounded-md border px-2 py-1.5 text-left transition-colors',
                    presetSlug === 'custom'
                      ? 'border-primary bg-primary/10'
                      : 'border-border hover:bg-muted/50',
                  )}
                >
                  <div className="text-xs font-medium">Custom</div>
                  <div className="text-[10px] text-muted-foreground">any size</div>
                </button>
              </div>
              {presetSlug === 'custom' && (
                <div className="mt-1.5 flex items-center gap-1.5">
                  <input
                    value={customW}
                    onChange={(e) => setCustomW(e.target.value.replace(/[^0-9]/g, ''))}
                    inputMode="numeric"
                    className="w-20 rounded-md border border-border bg-background px-2 py-1 text-sm outline-none focus:border-primary"
                    aria-label="Width in pixels"
                  />
                  <span className="text-xs text-muted-foreground">×</span>
                  <input
                    value={customH}
                    onChange={(e) => setCustomH(e.target.value.replace(/[^0-9]/g, ''))}
                    inputMode="numeric"
                    className="w-20 rounded-md border border-border bg-background px-2 py-1 text-sm outline-none focus:border-primary"
                    aria-label="Height in pixels"
                  />
                  <span className="text-xs text-muted-foreground">px</span>
                </div>
              )}
            </div>
          )}

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
