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
import { useViewerGrant } from '@/lib/workspace/viewer';
import { useHome } from './HomeContext';
import { cn } from '@/lib/utils';

const MANDATE_PATH = '/workspace/constitution/MANDATE.md';

// ---------------------------------------------------------------------------
// Constitution links — ADR-340 P3
// ---------------------------------------------------------------------------

// ADR-421: ConstitutionLinks (the mandate/principles/identity mirror-link trio)
// is DELETED. A workspace has no constitution of its own — those are per-agent
// concepts surfaced on the agent detail (AgentConstitutionBlock, ADR-419). The
// band's remaining content (the mandate hero, when a hired agent has one) is
// re-homed by the deferred §9b Home recompose.

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
  // ADR-412 D3 — the author/edit chat-drafts are CONSTITUTIONAL affordances
  // (they draft writes to constitution/MANDATE.md): they render per the
  // viewer's grant coverage, never a role enum. Reads stay universal —
  // the band itself renders for every member.
  const { userId } = useSurfacePreferences();
  const canAmendConstitution = useViewerGrant(userId).covers('constitution/');
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
  //
  // ADR-421: a steward-default MANDATE.md (the kernel constant seeded on
  // pre-genesis workspaces, marked `yarnnn:steward-default`) is NOT an
  // operator/agent mandate — it is Freddie's kernel purpose. Treat it as empty
  // at the Home hero so a bare workspace shows the honest empty state instead of
  // rendering "Steward this workspace's substrate" as the operation headline.
  // (The backend envelope already rejects it via STEWARD_DEFAULT_MARKER; this is
  // the FE parity. The real fix is the deferred §9b Home recompose — this keeps
  // the interim hero honest until then.)
  const isStewardDefault = (mandate ?? '').includes('yarnnn:steward-default');
  const parsed = isStewardDefault
    ? { primaryAction: null, successCriteria: [], boundaryCount: 0, isEmpty: true }
    : parseMandate(mandate ?? '');

  if (parsed.isEmpty) {
    return (
      <header className="w-full px-4 py-4 sm:px-6 sm:py-5 border-b border-border/60">
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1 min-w-0">
            {/* ADR-421: altitude-honest empty state. A workspace has no mandate
                of its own — it holds files, members, and a balance. A mandate is
                a hired agent's declared intent (surfaced on the agent detail). */}
            <div className="rounded-md border border-dashed border-border/60 bg-muted/20 px-4 py-3 text-sm text-muted-foreground">
              <span className="font-medium text-foreground">This workspace is a commons.</span>{' '}
              It holds your files, members, and connections. To give it an operation —
              a declared intent that runs on cadence —{' '}
              {canAmendConstitution ? (
                <button
                  type="button"
                  onClick={() => onOpenChatDraft('Help me set up an operation for this workspace — walk me through hiring an agent with a mandate.')}
                  className="font-medium text-foreground underline underline-offset-4 hover:no-underline"
                >
                  hire an agent
                </button>
              ) : (
                <span className="font-medium text-foreground">hire an agent</span>
              )}
              .
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
          {/* ADR-421: the constitution-trio band (mandate/identity/principles
              mirror links) is removed — a workspace has no constitution of its
              own; those live on the agent detail. When this header shows an
              authored mandate it is a HIRED agent's (read from agents/{slug}/ via
              the home-bundle); the deferred §9b Home recompose re-homes the hero. */}
        </div>
        <div className="flex items-center gap-3 shrink-0 mt-0.5">
          {/* Autonomy posture — links to Reviewer Autonomy tab for editing */}
          <AutonomyBadge
            level={effectiveLevel as AutonomyDelegation | null}
            summary={autonomySummary}
          />
          {/* Edit mandate shortcut — constitutional affordance (ADR-412 D3) */}
          {canAmendConstitution && (
            <button
              type="button"
              onClick={() => onOpenChatDraft('I want to revise my mandate — show me the current declaration and help me sharpen it.')}
              className="inline-flex items-center gap-1 text-[11px] text-muted-foreground/50 hover:text-muted-foreground transition-colors"
              title="Edit mandate in chat"
            >
              <MessageSquare className="h-3 w-3" />
            </button>
          )}
        </div>
      </div>
    </header>
  );
}
