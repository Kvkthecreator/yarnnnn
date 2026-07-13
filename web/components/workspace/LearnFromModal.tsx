'use client';

/**
 * LearnFromModal — the "Learn from…" recipe chooser (ADR-450 D5).
 *
 * The contextual entrance of the Learn-from verb: pick what to derive from
 * this file (the kernel recipes, served on the lane capability envelope —
 * never hardcoded here). Submitting hands {recipeSlug, model} back to the
 * caller, which creates the derive-bound lane and navigates to chat.
 *
 * Mirrors the RenameModal shell (portal + Z_CONFIRM tiers) so the verb reads
 * native beside Rename/Move.
 */

import { useEffect, useState } from 'react';
import { createPortal } from 'react-dom';
import { cn } from '@/lib/utils';
import { Z_CONFIRM_BACKDROP, Z_CONFIRM_DIALOG } from '@/lib/shell/z-tiers';
import { api } from '@/lib/api/client';

interface Recipe {
  slug: string;
  label: string;
  description: string;
}

interface LearnFromModalProps {
  /** The source file (null = closed). */
  target: { path: string; name: string } | null;
  onClose: () => void;
  /** Called with the chosen recipe + the default lane model. */
  onSubmit: (recipeSlug: string, model: string) => void | Promise<void>;
}

export function LearnFromModal({ target, onClose, onSubmit }: LearnFromModalProps) {
  const [recipes, setRecipes] = useState<Recipe[] | null>(null);
  const [model, setModel] = useState<string>('');
  const [enabled, setEnabled] = useState(true);
  const [selected, setSelected] = useState<string>('');
  const [starting, setStarting] = useState(false);

  useEffect(() => {
    if (!target) return;
    setRecipes(null);
    setSelected('');
    setStarting(false);
    api
      .lanes.list()
      .then((d) => {
        setEnabled(d.enabled);
        setRecipes(d.recipes ?? []);
        setModel(d.models[0]?.id ?? '');
      })
      .catch(() => {
        setEnabled(false);
        setRecipes([]);
      });
  }, [target]);

  if (!target) return null;

  const canStart = enabled && !!selected && !!model && !starting;

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
          <h3 className="text-base font-semibold text-card-foreground">Learn from “{target.name}”</h3>
          <p className="mt-1 text-xs text-muted-foreground">
            A helper reads this file and creates something new from it — cited back to the source.
          </p>

          {recipes === null ? (
            <p className="mt-4 text-sm text-muted-foreground">Loading…</p>
          ) : !enabled ? (
            <p className="mt-4 text-sm text-muted-foreground">
              Chat helpers aren’t enabled on this workspace yet.
            </p>
          ) : (
            <div className="mt-4 space-y-1.5" role="radiogroup" aria-label="What to create">
              {recipes.map((r) => (
                <button
                  key={r.slug}
                  type="button"
                  role="radio"
                  aria-checked={selected === r.slug}
                  onClick={() => setSelected(r.slug)}
                  className={cn(
                    'w-full rounded-md border px-3 py-2 text-left transition-colors',
                    selected === r.slug
                      ? 'border-primary bg-primary/5'
                      : 'border-border hover:bg-muted/50',
                  )}
                >
                  <span className="block text-sm font-medium text-foreground">{r.label}</span>
                  <span className="block text-xs text-muted-foreground">{r.description}</span>
                </button>
              ))}
            </div>
          )}

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
              disabled={!canStart}
              onClick={async () => {
                if (!canStart) return;
                setStarting(true);
                try {
                  await onSubmit(selected, model);
                } finally {
                  setStarting(false);
                }
              }}
              className={cn(
                'rounded-md px-3.5 py-1.5 text-sm font-medium transition-colors',
                canStart
                  ? 'bg-primary text-primary-foreground hover:bg-primary/90'
                  : 'cursor-not-allowed bg-muted text-muted-foreground',
              )}
            >
              {starting ? 'Starting…' : 'Start'}
            </button>
          </div>
        </div>
      </div>
    </>,
    document.body,
  );
}
