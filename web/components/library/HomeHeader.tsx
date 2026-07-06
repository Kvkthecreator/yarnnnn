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
 * Design reference: docs/design/HOME-COMPONENT-DESIGN.md §"Layer 1"
 *
 * NOT a card — full-width, prose-weight header that frames what the
 * operation is trying to achieve and what permissions it carries. Present
 * for every workspace regardless of active bundle.
 *
 * Substrate reads:
 *   /workspace/constitution/MANDATE.md  → title + summary (via canonical
 *                                            L2 parser at content-shapes/mandate.ts
 *                                            per ADR-245 D3 + ADR-266 D3)
 *   /workspace/governance/_autonomy.yaml → level + ceiling
 *                                              (via useAutonomy hook)
 *
 * Singular Implementation discipline: parsing MANDATE.md goes through the
 * one canonical L2 parser, not a parallel inline implementation. The
 * earlier inline `isSkeleton` + `deriveTitle` + `deriveSummary` were
 * deleted in 2026-05-14 — they false-positive-flagged authored mandates
 * as skeleton (any "Author here:" prompt in a sub-section triggered the
 * whole-file skeleton banner even when Primary Action was authored).
 *
 * Autonomy posture links to the Autonomy pane (Workspace Settings →
 * System Agent per ADR-412 D5; the registry pane_of re-point carries the
 * foregroundSurface call — this component stays pane-blind).
 */

import { useEffect, useState } from 'react';
import { MessageSquare, ShieldCheck, ShieldAlert } from 'lucide-react';
import { api } from '@/lib/api/client';
import { useAutonomy } from '@/lib/content-shapes/autonomy';
import type { AutonomyDelegation } from '@/lib/content-shapes/autonomy';
import { parse as parseMandate } from '@/lib/content-shapes/mandate';
import { useSurfacePreferences } from '@/lib/shell/useSurfacePreferences';
import { useHome } from './HomeContext';
import { cn } from '@/lib/utils';

const MANDATE_PATH = '/workspace/constitution/MANDATE.md';

// ---------------------------------------------------------------------------
// Constitution links — ADR-340 P3
// ---------------------------------------------------------------------------

/**
 * ConstitutionLinks — the constitution band is the canonical DOOR to the
 * three constitution mirrors (ADR-340 D5: mandate/principles/identity
 * leave the launcher's at-rest top level; flat search still finds them).
 * Quiet trio of links opening the mirror windows via foregroundSurface.
 */
function ConstitutionLinks() {
  const { foregroundSurface } = useSurfacePreferences();
  const items: { slug: string; label: string }[] = [
    { slug: 'mandate', label: 'Mandate' },
    { slug: 'principles', label: 'Principles' },
    { slug: 'identity', label: 'Identity' },
  ];
  return (
    <div className="mt-2 flex items-center gap-1 text-[11px] text-muted-foreground/60">
      {items.map((item, i) => (
        <span key={item.slug} className="flex items-center gap-1">
          {i > 0 && <span aria-hidden>·</span>}
          <button
            type="button"
            onClick={() => foregroundSurface(item.slug)}
            className="hover:text-foreground hover:underline underline-offset-4 transition-colors"
          >
            {item.label}
          </button>
        </span>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Autonomy display
// ---------------------------------------------------------------------------

function AutonomyBadge({ level, summary }: { level: AutonomyDelegation | null; summary: string }) {
  // ADR-358 (2026-06-23) — open the Autonomy pane via foregroundSurface
  // (which resolves the pane to its parent window + ?pane= WITHOUT flipping
  // the pathname), NOT a <Link>. The <Link> did a full Next.js navigation
  // that left the /desktop SPA and reset the chat rail — breaking the Canvas
  // two-pane continuity. ADR-412 D5 (2026-07-06): autonomy is
  // pane_of: workspace-settings (System Agent group) — the registry re-point
  // carries this call; the component stays pane-blind.
  const { foregroundSurface } = useSurfacePreferences();
  const Icon =
    level === 'autonomous' ? ShieldCheck :
    level === 'bounded' ? ShieldAlert :
    null;

  const colorClass =
    level === 'autonomous' ? 'text-primary' :
    level === 'bounded' ? 'text-amber-600' :
    'text-muted-foreground/50';

  return (
    <button
      type="button"
      onClick={() => foregroundSurface('autonomy')}
      className={cn(
        'flex items-center gap-1.5 text-[11px] font-medium hover:opacity-80 transition-opacity',
        colorClass,
      )}
      title={`${summary} — click to view and edit autonomy declaration`}
    >
      {Icon && <Icon className="h-3 w-3 shrink-0" />}
      <span className="capitalize">{(level ?? 'manual').replace(/_/g, ' ')}</span>
    </button>
  );
}

// ---------------------------------------------------------------------------
// HomeHeader
// ---------------------------------------------------------------------------

interface HomeHeaderProps {
  /**
   * ADR-312 home-bundle: raw MANDATE.md + _autonomy.yaml content from the
   * Home's single bundled call. When present the band primes from them and
   * skips its two self-fetches (mandate file + useAutonomy's _autonomy.yaml
   * read). `null` is a valid primed value (file absent). Standalone reuse
   * (none passed) self-fetches both.
   */
  initialMandate?: string | null;
  initialAutonomy?: string | null;
}

export function HomeHeader({ initialMandate, initialAutonomy }: HomeHeaderProps = {}) {
  const { onOpenChatDraft } = useHome();
  const primed = initialMandate !== undefined;
  const { effectiveLevel, summary: autonomySummary, loading: autonomyLoading } = useAutonomy(
    // useAutonomy already supports a pre-primed path via initialContent.
    primed ? { initialContent: initialAutonomy } : undefined,
  );

  const [mandate, setMandate] = useState<string | null>(
    primed ? (initialMandate ?? '') : null,
  );
  const [loaded, setLoaded] = useState(primed);

  useEffect(() => {
    if (primed) {
      setMandate(initialMandate ?? '');
      setLoaded(true);
      return;
    }
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
  }, [primed, initialMandate]);

  if (!loaded || autonomyLoading) return null;

  // Canonical L2 parse — single source of truth for what's authored vs
  // skeleton. isEmpty = no Primary Action + no Success Criteria + no
  // Boundary Conditions. A workspace with Primary Action authored is NOT
  // skeleton even if downstream sub-sections still carry "Author here:"
  // prompts (those are operator-facing nudges, not skeleton markers).
  const parsed = parseMandate(mandate ?? '');

  if (parsed.isEmpty) {
    return (
      <header className="w-full px-4 py-4 sm:px-6 sm:py-5 border-b border-border/60">
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
            <ConstitutionLinks />
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
    <header className="w-full px-4 py-4 sm:px-6 sm:py-5 border-b border-border/60">
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
          <ConstitutionLinks />
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
