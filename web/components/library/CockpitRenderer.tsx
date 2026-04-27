'use client';

/**
 * CockpitRenderer — ADR-225 Phase 3 dispatcher for /work list-mode cockpit.
 *
 * Sibling to MiddleResolver and ChromeRenderer. Dispatches the cockpit
 * pane sequence (kernel default or bundle override) through the shared
 * LIBRARY_COMPONENTS registry.
 *
 * Singular Implementation: replaces the deleted BriefingStrip
 * component. The hardcoded 4-pane composition that lived there is
 * gone — `KERNEL_DEFAULT_COCKPIT_PANES` in `kernel-defaults.ts` is
 * the new source of truth. Bundles override via
 * `tabs.work.list.cockpit_panes` in SURFACES.yaml.
 *
 * Visual chrome (section label, tint, padding) per ADR-215 Phase 4
 * preserved here — the chrome wraps whichever pane sequence resolves.
 */

import { Fragment } from 'react';
import { resolveCockpitPanes, useComposition } from '@/lib/compositor';
import { CockpitProvider } from './CockpitContext';
import { dispatchComponent } from './registry';

interface CockpitRendererProps {
  /**
   * Chat-draft handler. NeedsMePane chips seed chat drafts on click;
   * the page's rail composer receives the text. Other cockpit panes
   * may consume this in the future via CockpitContext.
   */
  onOpenChatDraft?: (prompt: string) => void;
}

export function CockpitRenderer({ onOpenChatDraft }: CockpitRendererProps) {
  const { data: composition } = useComposition();
  const panes = resolveCockpitPanes(composition.composition);
  const handleOpenChatDraft = onOpenChatDraft ?? (() => { /* no-op */ });

  return (
    <CockpitProvider value={{ onOpenChatDraft: handleOpenChatDraft }}>
      <section
        aria-label="Cockpit"
        className="border-b border-border/60 bg-muted/20"
      >
        <div className="flex items-baseline justify-between px-6 pt-5 pb-2">
          <h2 className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground/70">
            Cockpit
          </h2>
          <span className="text-[10px] text-muted-foreground/40">
            What needs you · book · since last look · intelligence
          </span>
        </div>
        <div className="flex flex-col gap-6 px-6 pb-6">
          {panes.map((pane, idx) => (
            <Fragment key={`${pane.kind}-${idx}`}>
              {dispatchComponent(pane)}
            </Fragment>
          ))}
        </div>
      </section>
    </CockpitProvider>
  );
}
