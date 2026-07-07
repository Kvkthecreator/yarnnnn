'use client';

/**
 * SetupSequence — the `/setup` Sequence-archetype renderer (ADR-331 D1).
 *
 * macOS Setup Assistant ⇄ System Settings: ONE substrate, two presentation
 * registers. This is the guided, ordered rendering; `/program` (the
 * ProgramLifecycleDrawer) is the random-access reference rendering. Both read
 * the SAME `api.workspace.getState()` composition — complete a step anywhere,
 * both renderings reflect it.
 *
 * NO stored wizard state (ADR-331 anti-goal, Sequence-archetype invariant):
 * every step's status is DERIVED from substrate at render time —
 *   1. Pick program       → active_program_slug set
 *   2. Author constitution → substrate_status.mandate/identity == authored
 *   3. Connect platforms   → no unmet capability_gaps
 *   4. Bring in reality    → harvest invocation in narrative OR uploads exist
 *   5. First artifact lands → operation produced its first output
 * "Dual tracking is impossible because there is nothing to drift."
 *
 * Every action already exists; `/setup` only ORDERS them. Actions reuse the
 * exact affordances the reference rendering uses (api.programs.activate,
 * navigateToSurface for chat-overlay authoring, /connectors deep-link).
 *
 * Phase 1 (this commit): steps 1–3 fully derived + actioned; steps 4–5
 * render with their derivation honestly scoped to what getState() carries
 * today (uploads-presence is the Phase-1 signal for step 4; step 5 points to
 * Home). The harvest scope picker (D3/D4) lands in Phase 2 and slots into
 * step 4's action without changing this surface's shape.
 */

import { useEffect, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import {
  Loader2,
  Check,
  Circle,
  AlertCircle,
  Sparkles,
  ArrowRight,
  Link2,
  Power,
  Home as HomeIcon,
} from 'lucide-react';
import { api, APIError } from '@/lib/api/client';
import { useSurfacePreferences } from '@/lib/shell/useSurfacePreferences';
import { cn } from '@/lib/utils';
import { HarvestPicker } from '@/components/library/HarvestPicker';
import { SurfaceLink } from '@/components/shell/SurfaceLink';
import type { KernelSurfaceSlug } from '@/types/desk';

type WorkspaceState = Awaited<ReturnType<typeof api.workspace.getState>>;
type ProgramItem = WorkspaceState['available_programs'][number];

/** A derived setup step — status computed from substrate, never stored. */
interface SetupStep {
  key: string;
  title: string;
  detail: string;
  /** Derived from substrate at render time. */
  done: boolean;
  /** Whether this step is the current focus (first not-done step). */
  current: boolean;
  /** The step's action affordance (an existing mechanism). */
  action?: React.ReactNode;
}

export function SetupSequence() {
  const { navigateToSurface } = useSurfacePreferences();
  const searchParams = useSearchParams();
  const isFirstRun = searchParams.get('first_run') === '1';

  const [state, setState] = useState<WorkspaceState | null>(null);
  const [uploadsPresent, setUploadsPresent] = useState<boolean | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [isMutating, setIsMutating] = useState<string | null>(null);
  const [opError, setOpError] = useState<string | null>(null);
  const [opSuccess, setOpSuccess] = useState<string | null>(null);

  const refresh = async () => {
    try {
      const [next, nav] = await Promise.all([
        api.workspace.getState(),
        // nav carries uploads[] — the Phase-1 "reality brought in" signal
        // (harvest-invocation-in-narrative derivation lands with Phase 2).
        api.workspace.getNav().catch(() => null),
      ]);
      setState(next);
      setUploadsPresent(nav ? (nav.uploads?.length ?? 0) > 0 : null);
      setLoadError(null);
    } catch (err) {
      setLoadError(err instanceof APIError ? err.message : 'Failed to load workspace state');
    }
  };

  useEffect(() => {
    refresh();
  }, []);

  useEffect(() => {
    if (opSuccess) {
      const t = setTimeout(() => setOpSuccess(null), 4000);
      return () => clearTimeout(t);
    }
  }, [opSuccess]);

  const handleActivate = async (slug: string) => {
    setIsMutating(slug);
    setOpError(null);
    try {
      await api.programs.activate(slug);
      setOpSuccess(`Activated ${slug}`);
      await refresh();
    } catch (err) {
      setOpError(err instanceof APIError ? err.message : 'Activation failed');
    } finally {
      setIsMutating(null);
    }
  };

  if (loadError) {
    return (
      <div className="rounded-md border border-destructive/30 bg-destructive/5 px-4 py-3 text-sm text-destructive flex items-center gap-2">
        <AlertCircle className="w-4 h-4 shrink-0" />
        <span>{loadError}</span>
      </div>
    );
  }

  if (!state) {
    return (
      <div className="flex items-center justify-center py-10">
        <Loader2 className="w-5 h-5 animate-spin text-muted-foreground" />
      </div>
    );
  }

  const activeProgram = state.active_program_slug
    ? state.available_programs.find((p) => p.slug === state.active_program_slug) || null
    : null;
  const unmetGaps = state.capability_gaps.filter((g) => !g.connected);
  const constitutionAuthored =
    state.substrate_status.mandate.state === 'authored' &&
    state.substrate_status.identity.state === 'authored';

  // ── Derive each step's status from substrate (no stored progress) ──────
  const rawSteps: Array<Omit<SetupStep, 'current'>> = [
    {
      key: 'pick-program',
      title: 'Pick a program',
      detail:
        'A program forks a domain-shaped workspace — mandate, agents, recurrences, context structure. The floor of becoming operational.',
      done: !!state.active_program_slug,
      action: !state.active_program_slug ? (
        <div className="space-y-2">
          {state.available_programs.map((p) => (
            <ProgramRow
              key={p.slug}
              program={p}
              isMutating={isMutating === p.slug}
              disabled={isMutating !== null && isMutating !== p.slug}
              onActivate={() => handleActivate(p.slug)}
            />
          ))}
          {/* Direction A: bare workspace stays the honest secondary — a
              resting state, not an operating path (ADR-331 §3 step 1). */}
          <p className="text-[11px] text-muted-foreground/60 italic pt-1">
            Or continue without a program — you can activate any time. The
            workspace stays in standby until you do.
          </p>
        </div>
      ) : (
        <ActiveProgramLine program={activeProgram} />
      ),
    },
    {
      key: 'author-constitution',
      title: 'Author your constitution',
      detail:
        'Your mandate and identity — what this workspace is for, and the voice it reasons in. Authored in chat; the agent walks you through it.',
      done: constitutionAuthored,
      action: (
        <StepAction
          icon={<Sparkles className="w-3.5 h-3.5" />}
          label={constitutionAuthored ? 'Revisit in chat' : 'Author in chat'}
          // ADR-385 follow-on (2026-06-30): narrative is the Channels Flow pane.
          onClick={() => navigateToSurface('channels')}
        />
      ),
    },
    {
      key: 'connect-platforms',
      title: 'Connect platforms',
      detail:
        'Your active program reads and writes through connected platforms. Until connected, the operation runs in knowledge mode only.',
      // No gaps declared (or all connected) = done. A program with no
      // platform capabilities (e.g. alpha-author) has zero gaps → done.
      done: unmetGaps.length === 0,
      action:
        unmetGaps.length > 0 ? (
          <StepAction
            icon={<Link2 className="w-3.5 h-3.5" />}
            label={`Connect ${unmetGaps.length} platform${unmetGaps.length !== 1 ? 's' : ''}`}
            to="connectors"
          />
        ) : (
          <p className="text-xs text-muted-foreground/70">
            {state.capability_gaps.length > 0
              ? 'All declared platforms connected.'
              : 'This program needs no platform connections.'}
          </p>
        ),
    },
    {
      key: 'bring-in-reality',
      title: 'Bring in your reality',
      detail:
        'Your accumulated context — channel history, docs, repos — is what makes the workspace cumulative. Harvest your connected sources directly, curated into context domains.',
      // Derivation: uploads present OR a harvest has run (uploads-presence is
      // the kernel signal available without a per-harvest narrative read; the
      // picker's onHarvested refresh re-checks after a run). ADR-331 D3/D4.
      done: uploadsPresent === true,
      action: <HarvestPicker onHarvested={refresh} />,
    },
    {
      key: 'first-artifact',
      title: 'See your first artifact',
      detail:
        'When the operation produces its first output, it lands on Home — the operation, rendered. Outcomes calibrate the agent from there.',
      // No getState() signal for "first output" yet; this step points the
      // operator at Home where the operation renders. Honest Phase-1 shape:
      // not auto-completed (it completes when the operation runs, surfaced
      // on Home), action is "go to Home."
      done: false,
      action: (
        <StepAction
          icon={<HomeIcon className="w-3.5 h-3.5" />}
          label="Go to Home"
          onClick={() => navigateToSurface('home')}
        />
      ),
    },
  ];

  // Mark the first not-done step as `current` (the focus).
  const firstIncompleteIdx = rawSteps.findIndex((s) => !s.done);
  const steps: SetupStep[] = rawSteps.map((s, i) => ({
    ...s,
    current: i === firstIncompleteIdx,
  }));

  const completedCount = steps.filter((s) => s.done).length;

  return (
    <section className="space-y-6 max-w-2xl">
      {/* First-run welcome */}
      {isFirstRun && (
        <div className="rounded-lg border border-primary/30 bg-primary/5 p-4 flex items-start gap-3">
          <Sparkles className="w-5 h-5 text-primary shrink-0 mt-0.5" />
          <div className="flex-1 min-w-0">
            <h3 className="text-sm font-medium">Welcome to YARNNN</h3>
            <p className="text-xs text-muted-foreground mt-1">
              Four moves to an operating workspace. Do them in order or out of
              order — each one is done the moment your workspace says so. You can
              leave and come back any time.
            </p>
          </div>
        </div>
      )}

      {/* Progress glance — derived, not stored */}
      <p className="text-xs text-muted-foreground">
        {completedCount} of {steps.length} steps complete
      </p>

      {/* The sequence */}
      <ol className="space-y-3">
        {steps.map((step, i) => (
          <StepRow key={step.key} step={step} index={i + 1} />
        ))}
      </ol>

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
    </section>
  );
}

// ─── Step row ───────────────────────────────────────────────────────────

function StepRow({ step, index }: { step: SetupStep; index: number }) {
  return (
    <li
      className={cn(
        'rounded-lg border p-4 transition-colors',
        step.done
          ? 'border-green-500/30 bg-green-500/5'
          : step.current
            ? 'border-primary/40 bg-primary/5'
            : 'border-border bg-card/50',
      )}
    >
      <div className="flex items-start gap-3">
        <div className="shrink-0 mt-0.5">
          {step.done ? (
            <Check className="w-5 h-5 text-green-600 dark:text-green-400" />
          ) : (
            <Circle
              className={cn(
                'w-5 h-5',
                step.current ? 'text-primary' : 'text-muted-foreground/40',
              )}
            />
          )}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="text-[11px] font-mono text-muted-foreground/50">{index}</span>
            <h3
              className={cn(
                'text-sm font-medium',
                step.done && 'text-muted-foreground line-through decoration-muted-foreground/30',
              )}
            >
              {step.title}
            </h3>
          </div>
          <p className="text-xs text-muted-foreground mt-1">{step.detail}</p>
          {/* Action only renders for the current + not-done steps to keep the
              sequence focused; done steps show their resolved line. */}
          {!step.done && step.current && step.action && (
            <div className="mt-3">{step.action}</div>
          )}
          {step.done && step.action && step.key === 'pick-program' && (
            <div className="mt-2">{step.action}</div>
          )}
        </div>
      </div>
    </li>
  );
}

// ─── Action button / link ────────────────────────────────────────────────

function StepAction({
  icon,
  label,
  to,
  onClick,
}: {
  icon: React.ReactNode;
  label: string;
  to?: KernelSurfaceSlug;
  onClick?: () => void;
}) {
  const cls =
    'inline-flex items-center gap-1.5 rounded-md border border-border bg-background px-3 py-1.5 text-xs font-medium hover:bg-muted/30 transition-colors';
  if (to) {
    return (
      <SurfaceLink to={to} className={cls}>
        {icon}
        {label}
        <ArrowRight className="w-3 h-3" />
      </SurfaceLink>
    );
  }
  return (
    <button type="button" onClick={onClick} className={cls}>
      {icon}
      {label}
      <ArrowRight className="w-3 h-3" />
    </button>
  );
}

// ─── Active-program resolved line (shown under a done step-1) ─────────────

function ActiveProgramLine({ program }: { program: ProgramItem | null }) {
  if (!program) return null;
  return (
    <div className="rounded-md border border-primary/30 bg-primary/5 px-3 py-2 flex items-center gap-2">
      <Sparkles className="w-3.5 h-3.5 text-primary shrink-0" />
      <span className="text-xs font-medium">{program.title}</span>
      {program.current_phase_label && (
        <span className="text-[10px] px-1.5 py-0.5 rounded bg-muted text-muted-foreground/80">
          {program.current_phase_label}
        </span>
      )}
      <SurfaceLink
        to="program"
        className="ml-auto text-[11px] text-muted-foreground hover:text-foreground inline-flex items-center gap-1"
      >
        <Power className="w-3 h-3" /> Manage
      </SurfaceLink>
    </div>
  );
}

// ─── Program row (activate affordance, reused shape from reference) ───────

function ProgramRow({
  program,
  isMutating,
  disabled,
  onActivate,
}: {
  program: ProgramItem;
  isMutating: boolean;
  disabled: boolean;
  onActivate: () => void;
}) {
  const interactive = !program.deferred;
  return (
    <div className="rounded-lg border border-border bg-card px-4 py-3">
      <div className="flex items-start gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-sm font-medium">{program.title}</span>
            {program.deferred && (
              <span className="text-[10px] uppercase tracking-wider px-1.5 py-0.5 rounded bg-muted text-muted-foreground/70">
                Coming soon
              </span>
            )}
            {program.current_phase_label && !program.deferred && (
              <span className="text-[10px] text-muted-foreground/60">
                {program.current_phase_label}
              </span>
            )}
          </div>
          {program.tagline && (
            <p className="text-xs text-muted-foreground mt-0.5">{program.tagline}</p>
          )}
        </div>
        {interactive && (
          <button
            type="button"
            onClick={onActivate}
            disabled={disabled}
            className="px-3 py-1.5 text-xs font-medium border border-border rounded-md hover:bg-muted/20 disabled:opacity-40 flex items-center gap-1.5 shrink-0"
          >
            {isMutating ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
            ) : (
              <Sparkles className="w-3.5 h-3.5" />
            )}
            Activate
          </button>
        )}
      </div>
    </div>
  );
}
