'use client';

/**
 * HomeHeader — the Constitution band (slot #1) of the Home, always present.
 * Renamed from CockpitHeader by ADR-312 D1; ADR-312 D2/D5 names this
 * kernel-general Layer-1 header the "Constitution band" (mandate one-liner
 * + autonomy posture — the operation's authored intent).
 *
 * ADR-243 Phase A. Implements the "common - page header" block from the
 * operator's design sketch: mandate-based title + summary on the left,
 * autonomy mode indicator + toggle on the right.
 *
 * Design reference: docs/design/COCKPIT-COMPONENT-DESIGN.md §"Layer 1"
 *
 * NOT a card — full-width, prose-weight header that frames what the
 * operation is trying to achieve and what permissions it carries. Present
 * for every workspace regardless of active bundle.
 *
 * Substrate reads:
 *   /workspace/context/_shared/MANDATE.md  → title + summary (via canonical
 *                                            L2 parser at content-shapes/mandate.ts
 *                                            per ADR-245 D3 + ADR-266 D3)
 *   /workspace/context/_shared/_autonomy.yaml → level + ceiling
 *                                              (via useAutonomy hook)
 *
 * Singular Implementation discipline: parsing MANDATE.md goes through the
 * one canonical L2 parser, not a parallel inline implementation. The
 * earlier inline `isSkeleton` + `deriveTitle` + `deriveSummary` were
 * deleted in 2026-05-14 — they false-positive-flagged authored mandates
 * as skeleton (any "Author here:" prompt in a sub-section triggered the
 * whole-file skeleton banner even when Primary Action was authored).
 *
 * Autonomy posture links to /autonomy (atomic Autonomy surface;
 * renamed from /delegation 2026-05-24; formerly
 * /agents?agent=reviewer&tab=autonomy per ADR-251).
 */

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { MessageSquare, ShieldCheck, ShieldAlert } from 'lucide-react';
import { api } from '@/lib/api/client';
import { useAutonomy } from '@/lib/content-shapes/autonomy';
import type { AutonomyDelegation } from '@/lib/content-shapes/autonomy';
import { parse as parseMandate } from '@/lib/content-shapes/mandate';
import { useHome } from './HomeContext';
import { cn } from '@/lib/utils';

const MANDATE_PATH = '/workspace/context/_shared/MANDATE.md';
// Atomic Autonomy surface (renamed from /delegation 2026-05-24).
const AUTONOMY_EDIT_HREF = '/autonomy';

// ---------------------------------------------------------------------------
// Autonomy display
// ---------------------------------------------------------------------------

function AutonomyBadge({ level, summary }: { level: AutonomyDelegation | null; summary: string }) {
  const Icon =
    level === 'autonomous' ? ShieldCheck :
    level === 'bounded' ? ShieldAlert :
    null;

  const colorClass =
    level === 'autonomous' ? 'text-primary' :
    level === 'bounded' ? 'text-amber-600' :
    'text-muted-foreground/50';

  return (
    <Link
      href={AUTONOMY_EDIT_HREF}
      className={cn(
        'flex items-center gap-1.5 text-[11px] font-medium hover:opacity-80 transition-opacity',
        colorClass,
      )}
      title={`${summary} — click to view and edit autonomy declaration`}
    >
      {Icon && <Icon className="h-3 w-3 shrink-0" />}
      <span className="capitalize">{(level ?? 'manual').replace(/_/g, ' ')}</span>
    </Link>
  );
}

// ---------------------------------------------------------------------------
// HomeHeader
// ---------------------------------------------------------------------------

export function HomeHeader() {
  const { onOpenChatDraft } = useHome();
  const { effectiveLevel, summary: autonomySummary, loading: autonomyLoading } = useAutonomy();

  const [mandate, setMandate] = useState<string | null>(null);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const file = await api.workspace.getFile(MANDATE_PATH);
        if (!cancelled) setMandate(file?.content ?? '');
      } catch {
        if (!cancelled) setMandate('');
      } finally {
        if (!cancelled) setLoaded(true);
      }
    })();
    return () => { cancelled = true; };
  }, []);

  if (!loaded || autonomyLoading) return null;

  // Canonical L2 parse — single source of truth for what's authored vs
  // skeleton. isEmpty = no Primary Action + no Success Criteria + no
  // Boundary Conditions. A workspace with Primary Action authored is NOT
  // skeleton even if downstream sub-sections still carry "Author here:"
  // prompts (those are operator-facing nudges, not skeleton markers).
  const parsed = parseMandate(mandate ?? '');

  if (parsed.isEmpty) {
    return (
      <header className="w-full px-6 py-5 border-b border-border/60">
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1 min-w-0">
            <div className="rounded-md border border-dashed border-amber-300 bg-amber-50/50 px-4 py-3 text-sm text-amber-900">
              <span className="font-medium">Mandate not yet declared.</span>{' '}
              Your mandate is the Primary Action and guardrails YARNNN operates within.{' '}
              <button
                type="button"
                onClick={() => onOpenChatDraft('Help me author my mandate — the Primary Action this workspace is running, success criteria, and boundary conditions.')}
                className="font-medium underline underline-offset-4 hover:no-underline"
              >
                Author in chat
              </button>
            </div>
          </div>
          <AutonomyBadge
            level={effectiveLevel as AutonomyDelegation | null}
            summary={autonomySummary}
          />
        </div>
      </header>
    );
  }

  // Authored mandate — Primary Action is the operation's one-sentence
  // declaration. Per ADR-266 D3 schema discipline, the Primary Action is
  // load-bearing (one declarative sentence, the value-moving external
  // write). Render it as the operation headline; success criteria render
  // as truncated supporting prose.
  const headline = parsed.primaryAction ?? 'Operation';
  const supportingLines = parsed.successCriteria;

  return (
    <header className="w-full px-6 py-5 border-b border-border/60">
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 min-w-0">
          <h1 className="text-xl font-semibold text-foreground line-clamp-2">
            {headline}
          </h1>
          {supportingLines.length > 0 && (
            <p className="mt-1.5 text-sm text-muted-foreground line-clamp-2">
              {supportingLines.slice(0, 3).join(' · ')}
            </p>
          )}
        </div>
        <div className="flex items-center gap-3 shrink-0 mt-0.5">
          {/* Autonomy posture — links to Reviewer Autonomy tab for editing */}
          <AutonomyBadge
            level={effectiveLevel as AutonomyDelegation | null}
            summary={autonomySummary}
          />
          {/* Edit mandate shortcut */}
          <button
            type="button"
            onClick={() => onOpenChatDraft('I want to revise my mandate — show me the current declaration and help me sharpen it.')}
            className="inline-flex items-center gap-1 text-[11px] text-muted-foreground/50 hover:text-muted-foreground transition-colors"
            title="Edit mandate in chat"
          >
            <MessageSquare className="h-3 w-3" />
          </button>
        </div>
      </div>
    </header>
  );
}
