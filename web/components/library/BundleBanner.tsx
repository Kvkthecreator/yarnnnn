'use client';

/**
 * BundleBanner — system component library, ADR-225.
 *
 * Renders the bundle-supplied banner for a tab's list mode. Only renders
 * when a banner is declared on the active bundle's SURFACES.yaml + phase
 * overlay (e.g., alpha-trader's `Paper-only. Live trading gated...` for
 * current_phase=observation). Silent fallback when no banner is supplied.
 *
 * Used by WorkListSurface (Work list-mode banner) and any future tab
 * surface that wants phase-aware chrome.
 */

import { Info } from 'lucide-react';
import { useComposition, getTab } from '@/lib/compositor';

interface BundleBannerProps {
  /** Which tab's list block to read the banner from. */
  tab: 'work' | 'agents' | 'context' | 'files' | 'chat';
}

export function BundleBanner({ tab }: BundleBannerProps) {
  const { data } = useComposition();
  const tabBlock = getTab(data.composition, tab);
  const banner = tabBlock.list?.banner;

  if (!banner) return null;

  return (
    <div className="flex items-start gap-2 rounded-md border border-amber-200/60 bg-amber-50/60 px-3 py-2 text-[12px] text-amber-900 mx-4 sm:mx-6 mt-2">
      <Info className="h-3.5 w-3.5 mt-0.5 flex-shrink-0" />
      <div className="flex-1">{banner}</div>
    </div>
  );
}
