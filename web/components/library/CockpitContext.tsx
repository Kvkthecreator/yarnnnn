'use client';

/**
 * CockpitContext — ADR-225 Phase 3.
 *
 * The context that threads the chat-draft handler from `/work` page
 * into kernel-cockpit components (and any bundle-supplied cockpit
 * components that opt in).
 *
 * NeedsMePane chips seed chat drafts on click — the page's rail
 * composer receives the text. Same channel pattern as
 * WorkDetailActionsContext but scoped to list-mode cockpit needs.
 *
 * Singular Implementation: this is the single channel by which
 * cockpit pane components reach the chat seeder.
 */

import { createContext, useContext } from 'react';

export interface CockpitContextValue {
  onOpenChatDraft: (prompt: string) => void;
}

const CockpitContext = createContext<CockpitContextValue | null>(null);

export const CockpitProvider = CockpitContext.Provider;

export function useCockpit(): CockpitContextValue {
  const ctx = useContext(CockpitContext);
  if (!ctx) {
    throw new Error(
      'useCockpit must be used inside <CockpitProvider> — '
      + 'kernel-cockpit and bundle-cockpit components are rendered through '
      + 'the compositor seam (ADR-225 Phase 3) and require the cockpit context.',
    );
  }
  return ctx;
}
