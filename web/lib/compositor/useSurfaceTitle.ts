'use client';

/**
 * useSurfaceTitle — ADR-660 ruling 1 (2026-09-20). The served roster's titles
 * and summaries are English literals in `api/services/kernel_surfaces.py`, and
 * §8 leaves served strings undecided. So the SHELL words them client-side by
 * SLUG: the catalog key `surfaces.{slug}.title` when it exists, the served
 * title otherwise. No API change, and a program surface the kernel never heard
 * of still reads as whatever the compositor served.
 *
 * ONE resolver for every consumer (SurfaceViewport's window title, the
 * GlobalLocatorStrip crumb, the Launcher rows, the Dock tooltips) — the
 * Singular Implementation `surfaceTitleFor` already established, now with the
 * catalog in front of it.
 */

import { useTranslations } from 'next-intl';
import type { Surface } from '@/lib/compositor/types';
import { surfaceTitleFor } from '@/lib/compositor/surfaceTitle';

export interface SurfaceWords {
  /** The surface's name, in the member's language when the catalog has it. */
  title: (slug: string | null, fallback?: string) => string;
  /** The surface's one-line summary, likewise. */
  summary: (slug: string, served: string) => string;
}

export function useSurfaceWords(surfaces: Surface[] | undefined): SurfaceWords {
  const t = useTranslations('surfaces');
  const shell = useTranslations('shell');
  return {
    title: (slug, fallback) => {
      const served = surfaceTitleFor(surfaces, slug, fallback ?? shell('desktop'));
      if (!slug) return served;
      // `has` is the only honest test: a missing key renders its own path.
      return t.has(`${slug}.title`) ? t(`${slug}.title`) : served;
    },
    summary: (slug, served) => (t.has(`${slug}.summary`) ? t(`${slug}.summary`) : served),
  };
}
