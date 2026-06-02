'use client';

/**
 * HomeContext — ADR-225 Phase 3; renamed from CockpitContext by ADR-312 D1.
 *
 * The context that threads the chat-draft handler from the Home surface
 * into kernel-home components (and any bundle-supplied program-section
 * components that opt in).
 *
 * Slot chips seed chat drafts on click — the page's composer receives
 * the text. Same channel pattern as WorkDetailActionsContext but scoped
 * to the Home's composed slots.
 *
 * Singular Implementation: this is the single channel by which home
 * components reach the chat seeder.
 */

import { createContext, useContext } from 'react';

export interface HomeContextValue {
  onOpenChatDraft: (prompt: string) => void;
}

const HomeContext = createContext<HomeContextValue | null>(null);

export const HomeProvider = HomeContext.Provider;

export function useHome(): HomeContextValue {
  const ctx = useContext(HomeContext);
  if (!ctx) {
    throw new Error(
      'useHome must be used inside <HomeProvider> — '
      + 'kernel-home and program-section components are rendered through '
      + 'the compositor seam (ADR-225 Phase 3) and require the home context.',
    );
  }
  return ctx;
}
