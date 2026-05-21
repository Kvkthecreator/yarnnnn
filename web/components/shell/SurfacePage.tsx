'use client';

/**
 * SurfacePage — ADR-297 atomic surface chrome.
 *
 * Common chrome for atomic surface pages — title + summary header,
 * content slot. Each atomic surface renders its substrate concept
 * inside this wrapper for consistent layout and posture.
 *
 * Per ADR-297 D7, the shell's chrome (top bar + dock) lives in
 * AuthenticatedLayout; SurfacePage is the *content* chrome inside a
 * single surface's route.
 */

import type { ReactNode } from 'react';
import { resolveSurfaceIcon } from '@/lib/shell/surface-icons';

interface SurfacePageProps {
  iconKey: string;
  title: string;
  summary?: string;
  children: ReactNode;
}

export function SurfacePage({ iconKey, title, summary, children }: SurfacePageProps) {
  const Icon = resolveSurfaceIcon(iconKey);
  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto max-w-3xl px-4 sm:px-6 py-6">
        <header className="mb-6">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-md bg-muted text-muted-foreground">
              <Icon className="h-5 w-5" />
            </div>
            <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
          </div>
          {summary && (
            <p className="mt-1.5 ml-12 text-sm text-muted-foreground">
              {summary}
            </p>
          )}
        </header>
        <div>{children}</div>
      </div>
    </div>
  );
}
