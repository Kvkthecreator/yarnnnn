'use client';

/**
 * GrantGate — grant-derived affordance rendering (ADR-412 D3/D6).
 *
 * Wraps a pane/section whose write affordances land in one ADR-320 region
 * root. When the VIEWER's grant covers the region, children render
 * untouched. When it doesn't, the section renders EXPLICITLY read-only:
 * a banner names the coverage gap, and the body's form controls are
 * disabled via a native <fieldset disabled> (buttons/inputs inert for
 * pointer AND keyboard).
 *
 * The check is the viewer's resolved write-region set (grant scopes or
 * class-default) from useViewerGrant — NEVER a role enum. This is the UI
 * twin of ADR-405's no-species-law: the same rule for every principal,
 * derived from the grant. Reads stay universal; FE gating is LEGIBILITY,
 * the server gate (permission.py) is enforcement — an unresolved grant
 * fails open here and is still enforced there.
 */

import type { ReactNode } from 'react';
import { Eye } from 'lucide-react';
import { useSurfacePreferences } from '@/lib/shell/useSurfacePreferences';
import { useViewerGrant } from '@/lib/workspace/viewer';

/** Operator words for the ADR-320 region roots (banner copy only). */
const REGION_LABELS: Record<string, string> = {
  'constitution/': 'the constitution',
  'governance/': 'the grant',
  'persona/': 'the persona',
  'contract/': 'the operating contract',
  'operation/': 'the operation',
  'system/': 'system state',
  'agents/': 'the agent', // ADR-419 — hired-agent constitution (agents/{slug}/)
};

interface GrantGateProps {
  /** The ADR-320 region root the wrapped affordances write (e.g. 'constitution/'). */
  region: string;
  children: ReactNode;
}

export function GrantGate({ region, children }: GrantGateProps) {
  const { userId } = useSurfacePreferences();
  const grant = useViewerGrant(userId);

  if (grant.covers(region)) return <>{children}</>;

  const label = REGION_LABELS[region] ?? region;
  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2 rounded-md border border-border/60 bg-muted/40 px-3 py-2 text-xs text-muted-foreground">
        <Eye className="h-3.5 w-3.5 shrink-0" />
        <span>
          Read-only — your access to this workspace doesn&apos;t include writing{' '}
          {label}.
        </span>
      </div>
      <fieldset disabled className="opacity-80">
        {children}
      </fieldset>
    </div>
  );
}
