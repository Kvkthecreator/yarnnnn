'use client';

/**
 * StudioNewMenu — the single "+ New" entry point (2026-07-14 operator ruling).
 *
 * The start state used to spread the four shape cards + Learn-from as a flat
 * 5-card grid across the top, pushing Recents below the fold. This collapses
 * them into ONE button + a popover menu, so Recents ("continue where you left
 * off") owns the surface — the thing a returning member actually wants.
 *
 * Scalable by construction: a fifth shape is one more row from the served
 * templates list, never a grid reflow. The menu only CHOOSES a shape; the
 * existing focused modals (NewArtifactModal / LearnFromFlowModal) still own the
 * name-it / source-it steps, unchanged — this is a router, not a new flow.
 */

import { useEffect, useRef, useState } from 'react';
import { FilePlus, Sparkles } from 'lucide-react';
import { cn } from '@/lib/utils';
import { studioShapeStyle } from './studioShapes';

interface TemplateInfo {
  slug: string;
  label: string;
  description: string;
}

interface StudioNewMenuProps {
  templates: TemplateInfo[];
  /** Whether the Learn-from row is available (needs the model router). */
  learnEnabled: boolean;
  /** A shape card was chosen — open the name-it modal for it. */
  onPickTemplate: (t: TemplateInfo) => void;
  /** The Learn-from row was chosen — open the source/target flow. */
  onPickLearn: () => void;
}

export function StudioNewMenu({
  templates,
  learnEnabled,
  onPickTemplate,
  onPickLearn,
}: StudioNewMenuProps) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  // Close on outside-click / Escape (the popover is anchored, not a full modal).
  useEffect(() => {
    if (!open) return;
    const onClick = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setOpen(false);
    };
    window.addEventListener('mousedown', onClick);
    window.addEventListener('keydown', onKey);
    return () => {
      window.removeEventListener('mousedown', onClick);
      window.removeEventListener('keydown', onKey);
    };
  }, [open]);

  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-haspopup="menu"
        aria-expanded={open}
        className="inline-flex items-center gap-1.5 rounded-md bg-primary px-3 py-1.5 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90"
      >
        <FilePlus className="h-4 w-4" />
        New
      </button>

      {open && (
        <div
          role="menu"
          className="absolute right-0 z-30 mt-1.5 w-64 overflow-hidden rounded-lg border border-border bg-popover py-1 shadow-lg animate-in fade-in zoom-in-95 duration-100"
        >
          {templates.map((t) => {
            // ADR-459: the slug IS the kind — no fake filename to round-trip
            // it through, and the label comes from the served registry.
            const shape = studioShapeStyle(t.slug);
            const Icon = shape.icon;
            return (
              <button
                key={t.slug}
                type="button"
                role="menuitem"
                onClick={() => {
                  setOpen(false);
                  onPickTemplate(t);
                }}
                className="flex w-full items-start gap-2.5 px-3 py-2 text-left transition-colors hover:bg-accent/60"
              >
                <Icon className={cn('mt-0.5 h-4 w-4 shrink-0', shape.color)} />
                <span className="min-w-0">
                  <span className="block text-sm font-medium leading-tight">{t.label}</span>
                  <span className="mt-0.5 block truncate text-[11px] leading-snug text-muted-foreground">
                    {t.description}
                  </span>
                </span>
              </button>
            );
          })}

          <div className="my-1 h-px bg-border/60" />

          <button
            type="button"
            role="menuitem"
            disabled={!learnEnabled}
            onClick={() => {
              setOpen(false);
              onPickLearn();
            }}
            title={learnEnabled ? undefined : 'Chat helpers aren’t enabled on this workspace.'}
            className="flex w-full items-start gap-2.5 px-3 py-2 text-left transition-colors hover:bg-accent/60 disabled:cursor-not-allowed disabled:opacity-40"
          >
            <Sparkles className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground" />
            <span className="min-w-0">
              <span className="block text-sm font-medium leading-tight">Learn from…</span>
              <span className="mt-0.5 block truncate text-[11px] leading-snug text-muted-foreground">
                Start from a file — yours or one you upload.
              </span>
            </span>
          </button>
        </div>
      )}
    </div>
  );
}
