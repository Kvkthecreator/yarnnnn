'use client';

/**
 * ChromeRenderer — ADR-225 Phase 3 dispatcher for WorkDetail chrome.
 *
 * Sibling to MiddleResolver. Where MiddleResolver dispatches the
 * content area (the middle), ChromeRenderer dispatches the chrome
 * (metadata strip + actions row). Both go through the same
 * LIBRARY_COMPONENTS registry — kernel defaults register alongside
 * bundle components.
 *
 * Per ADR-225 Phase 3 §5: chrome flows through the compositor seam
 * uniformly with the middle. The deleted per-kind chrome switch in
 * WorkDetail.tsx is replaced by `<ChromeRenderer>` — singular
 * implementation.
 */

import { Fragment } from 'react';
import type { ComponentDecl } from '@/lib/compositor';
import { dispatchComponent } from './registry';

interface ChromeRendererProps {
  /**
   * Single component for the metadata slot (operational signal strip)
   * or array of components for the actions slot. Pass `decl` for the
   * single-component slot, `decls` for the multi-component slot. Mutually
   * exclusive — caller picks based on slot semantics.
   */
  decl?: ComponentDecl;
  decls?: ComponentDecl[];
}

export function ChromeRenderer({ decl, decls }: ChromeRendererProps) {
  if (decl) {
    return dispatchComponent(decl);
  }
  if (decls && decls.length > 0) {
    return (
      <>
        {decls.map((d, idx) => (
          <Fragment key={`${d.kind}-${idx}`}>{dispatchComponent(d)}</Fragment>
        ))}
      </>
    );
  }
  return null;
}
