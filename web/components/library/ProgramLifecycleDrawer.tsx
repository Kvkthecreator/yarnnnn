'use client';

/**
 * ProgramLifecycleDrawer — bottom-of-/workspace collapsible.
 *
 * Per ADR-266 D1: program lifecycle (active program, switch, deactivate,
 * capability gaps) is touched ≤ once per workspace lifetime. It collapses
 * to a single-line summary at the bottom of /workspace; expands inline.
 *
 * Copy hygiene (D6):
 *   - "Platform connections needed" header renders only when ≥1 gap is unmet
 *   - Platform display names from getPlatformDisplay() — never raw slugs
 *   - Switch list excludes the currently-active program
 *   - Phase tokens render via current_phase_label (bundle MANIFEST source)
 *   - Bundle taglines + "(Reference)" + COMING SOON deduplicated
 *
 * State machine:
 *   - opSuccess and opError live here (the only block with mutations)
 *   - Refresh after activate/deactivate is owned by the parent via onMutation
 */

import { useState } from 'react';
import {
  Loader2,
  Check,
  AlertCircle,
  Sparkles,
  Power,
  Link2,
  ChevronRight,
  ChevronDown,
} from 'lucide-react';
import { api, APIError } from '@/lib/api/client';
import { cn } from '@/lib/utils';
import { getPlatformDisplay } from '@/lib/platform-display';

type WorkspaceState = Awaited<ReturnType<typeof api.workspace.getState>>;
type ProgramItem = WorkspaceState['available_programs'][number];
type CapabilityGap = WorkspaceState['capability_gaps'][number];

interface ProgramLifecycleDrawerProps {
  state: WorkspaceState;
  /** Called after a successful activate/deactivate — parent re-fetches the
   *  setup bundle so cards reflect the newly-hired agent's installed content
   *  (ADR-432 D2b: activation HIRES an agent into agents/{slug}/, ADR-414 D5). */
  onMutation: () => Promise<void>;
}

export function ProgramLifecycleDrawer({ state, onMutation }: ProgramLifecycleDrawerProps) {
  const [expanded, setExpanded] = useState(false);
  const [isMutating, setIsMutating] = useState<string | null>(null);
  const [opError, setOpError] = useState<string | null>(null);
  const [opSuccess, setOpSuccess] = useState<string | null>(null);

  const activeProgram = state.active_program_slug
    ? state.available_programs.find(p => p.slug === state.active_program_slug) ?? null
    : null;

  const unmetGaps = state.capability_gaps.filter(g => !g.connected);

  // ADR-266 D6: switch-list excludes the active program. Operators don't
  // need to see "alpha-trader ACTIVE" when alpha-trader is already shown
  // in the active card above.
  const switchablePrograms = state.available_programs.filter(
    p => p.slug !== state.active_program_slug,
  );

  const handleActivate = async (slug: string) => {
    setIsMutating(slug); setOpError(null);
    try {
      await api.programs.activate(slug);
      setOpSuccess(`Activated ${slug}`);
      await onMutation();
    } catch (err) {
      setOpError(err instanceof APIError ? err.message : 'Activation failed');
    } finally { setIsMutating(null); }
  };

  const handleDeactivate = async () => {
    setIsMutating('deactivate'); setOpError(null);
    try {
      const res = await api.programs.deactivate();
      if (res.deactivated) setOpSuccess(`Deactivated ${res.prior_program_slug}`);
      await onMutation();
    } catch (err) {
      setOpError(err instanceof APIError ? err.message : 'Deactivation failed');
    } finally { setIsMutating(null); }
  };

  // ── Summary line ──────────────────────────────────────────────────────
  // Single-line "Running X · Y connected · Manage program" pattern. When
  // unmet gaps exist, the summary draws attention with a tinted ⚠ count.

  const summaryParts: React.ReactNode[] = [];
  if (activeProgram) {
    summaryParts.push(
      <span key="active" className="text-foreground">Running {activeProgram.title}</span>
    );
  } else {
    summaryParts.push(
      <span key="none" className="italic text-muted-foreground/60">No program active</span>
    );
  }
  if (state.capability_gaps.length > 0) {
    if (unmetGaps.length > 0) {
      summaryParts.push(
        <span key="gaps" className="text-amber-600 dark:text-amber-400">
          {unmetGaps.length} platform{unmetGaps.length !== 1 ? 's' : ''} needed
        </span>
      );
    } else {
      summaryParts.push(
        <span key="ok" className="text-green-700 dark:text-green-400">All platforms connected</span>
      );
    }
  }

  return (
    <section className="border-t border-border/40 pt-6 mt-2">
      <button
        type="button"
        onClick={() => setExpanded(e => !e)}
        className={cn(
          'w-full flex items-center justify-between gap-3 px-3 py-2 -mx-3 rounded-md',
          'text-left hover:bg-muted/30 transition-colors',
        )}
      >
        <div className="flex items-center gap-2 text-xs">
          {expanded
            ? <ChevronDown className="w-3.5 h-3.5 text-muted-foreground" />
            : <ChevronRight className="w-3.5 h-3.5 text-muted-foreground" />}
          {summaryParts.reduce<React.ReactNode[]>(
            (acc, part, i) => i === 0 ? [part] : [...acc, <span key={`sep-${i}`} className="text-muted-foreground/40 mx-1.5">·</span>, part],
            [],
          )}
        </div>
        <span className="text-[11px] text-muted-foreground">
          {expanded ? 'Hide' : 'Manage program'}
        </span>
      </button>

      {expanded && (
        <div className="mt-4 space-y-6">

          {/* Active program detail */}
          <div className="space-y-2">
            <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Active program</h3>
            {activeProgram ? (
              <div className="rounded-lg border border-primary/40 bg-primary/5 p-4 flex items-start justify-between gap-3">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-sm font-medium">{activeProgram.title}</span>
                    {/* ADR-266 D6: render label, never the bare enum slug */}
                    {activeProgram.current_phase_label && (
                      <span className="text-[10px] px-1.5 py-0.5 rounded bg-muted text-muted-foreground/80">
                        {activeProgram.current_phase_label}
                      </span>
                    )}
                  </div>
                  {activeProgram.tagline && (
                    <p className="text-xs text-muted-foreground mt-1">{activeProgram.tagline}</p>
                  )}
                </div>
                <button type="button" onClick={handleDeactivate} disabled={isMutating !== null}
                  className="px-3 py-1.5 text-xs font-medium border border-border rounded-md hover:bg-muted/20 disabled:opacity-40 flex items-center gap-1.5 shrink-0">
                  {isMutating === 'deactivate'
                    ? <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    : <Power className="w-3.5 h-3.5" />}
                  Deactivate
                </button>
              </div>
            ) : (
              <div className="rounded-lg border border-dashed border-border bg-muted/10 px-4 py-3">
                <p className="text-sm text-muted-foreground">
                  No program activated yet. Activate one below to begin — until then
                  the workspace is in standby.
                </p>
              </div>
            )}
          </div>

          {/* Capability gaps — ADR-266 D6: render only when at least one gap is unmet */}
          {unmetGaps.length > 0 && (
            <div className="space-y-2">
              <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                Platform connections needed
              </h3>
              <p className="text-xs text-muted-foreground/80">
                Your active program needs these platforms connected before it can execute autonomously.
              </p>
              <div className="space-y-2">
                {unmetGaps.map(gap => <CapabilityGapRow key={`${gap.capability}-${gap.requires_platform}`} gap={gap} />)}
              </div>
            </div>
          )}

          {/* Switchable programs */}
          {switchablePrograms.length > 0 ? (
            <div className="space-y-2">
              <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                {activeProgram ? 'Switch program' : 'Available programs'}
              </h3>
              <p className="text-xs text-muted-foreground/80">
                {activeProgram
                  ? 'Switching hires the new agent in place — your authored content is preserved.'
                  : 'Activating a program hires an agent — its load-out installs into the agent’s own home.'}
              </p>
              <div className="space-y-2">
                {switchablePrograms.map(p => (
                  <ProgramRow key={p.slug} program={p}
                    isMutating={isMutating === p.slug}
                    disabled={isMutating !== null && isMutating !== p.slug}
                    onActivate={() => handleActivate(p.slug)} />
                ))}
              </div>
            </div>
          ) : !activeProgram ? null : (
            <p className="text-xs text-muted-foreground/60 italic">
              More programs coming soon.
            </p>
          )}

          {/* Op feedback */}
          {opError && (
            <div className="rounded-md border border-destructive/30 bg-destructive/5 px-3 py-2 text-xs text-destructive flex items-center gap-2">
              <AlertCircle className="w-3.5 h-3.5 shrink-0" />
              <span>{opError}</span>
            </div>
          )}
          {opSuccess && (
            <div className="rounded-md border border-green-500/30 bg-green-500/5 px-3 py-2 text-xs text-green-700 dark:text-green-400 flex items-center gap-2">
              <Check className="w-3.5 h-3.5 shrink-0" />
              <span>{opSuccess}</span>
            </div>
          )}
        </div>
      )}
    </section>
  );
}

// ─── Capability gap row (ADR-266 D6 copy hygiene) ────────────────────────────

function CapabilityGapRow({ gap }: { gap: CapabilityGap }) {
  // Display the platform name, not the slug. "Alpaca" not "trading".
  const display = getPlatformDisplay(gap.requires_platform);
  return (
    <div className="rounded-md border border-border bg-card px-3 py-2 flex items-center justify-between gap-3">
      <div className="flex-1 min-w-0">
        <div className="text-sm font-medium">{display.name}</div>
        <div className="text-xs text-muted-foreground">{display.capability}</div>
      </div>
      <a href={display.href}
        className="text-xs font-medium text-primary hover:text-primary/80 flex items-center gap-1 shrink-0">
        <Link2 className="w-3.5 h-3.5" /> Connect
      </a>
    </div>
  );
}

// ─── Program row ──────────────────────────────────────────────────────────────

function ProgramRow({
  program, isMutating, disabled, onActivate,
}: {
  program: ProgramItem;
  isMutating: boolean;
  disabled: boolean;
  onActivate: () => void;
}) {
  const interactive = !program.deferred;
  return (
    <div className={cn('rounded-lg border px-4 py-3', 'border-border bg-card')}>
      <div className="flex items-start gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-sm font-medium">{program.title}</span>
            {/* ADR-266 D6: dedupe — only one signal per row.
                Deferred bundles get the COMING SOON badge; the
                "(Reference)" parenthetical is dropped. */}
            {program.deferred && (
              <span className="text-[10px] uppercase tracking-wider px-1.5 py-0.5 rounded bg-muted text-muted-foreground/70">Coming soon</span>
            )}
            {program.current_phase_label && !program.deferred && (
              <span className="text-[10px] text-muted-foreground/60">{program.current_phase_label}</span>
            )}
          </div>
          {program.tagline && (
            <p className="text-xs text-muted-foreground mt-0.5">{program.tagline}</p>
          )}
        </div>
        {interactive && (
          <button type="button" onClick={onActivate} disabled={disabled}
            className="px-3 py-1.5 text-xs font-medium border border-border rounded-md hover:bg-muted/20 disabled:opacity-40 flex items-center gap-1.5 shrink-0">
            {isMutating ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Sparkles className="w-3.5 h-3.5" />}
            Activate
          </button>
        )}
      </div>
    </div>
  );
}
