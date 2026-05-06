'use client';

/**
 * WorkspaceConfigSection — body of /workspace.
 *
 * Assembles four L3 concept components (MandateCard, DelegationCard,
 * PrinciplesCard, IdentityBrandCard) at `full` variant, plus the
 * program lifecycle section (active program, capability gaps, available programs).
 *
 * No file paths, no raw markdown, no state badges from file format.
 * Each section renders meaning extracted from the substrate file.
 * Edits route through the chat panel on the right (ThreePanelLayout).
 *
 * See docs/design/WORKSPACE-COMPONENTS.md for the component catalog.
 */

import { useEffect, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import {
  Loader2,
  Check,
  AlertCircle,
  Sparkles,
  ArrowRight,
  Power,
  Link2,
} from 'lucide-react';
import { api, APIError } from '@/lib/api/client';
import { useTP } from '@/contexts/TPContext';
import { cn } from '@/lib/utils';
import { MandateCard } from '@/components/workspace-concepts/MandateCard';
import { DelegationCard } from '@/components/workspace-concepts/DelegationCard';
import { PrinciplesCard } from '@/components/workspace-concepts/PrinciplesCard';
import { IdentityBrandCard } from '@/components/workspace-concepts/IdentityBrandCard';

type WorkspaceState = Awaited<ReturnType<typeof api.workspace.getState>>;
type ProgramItem = WorkspaceState['available_programs'][number];

export function WorkspaceConfigSection() {
  const { sendMessage } = useTP();
  const router = useRouter();
  const searchParams = useSearchParams();
  const isFirstRun = searchParams.get('first_run') === '1';

  const [state, setState] = useState<WorkspaceState | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [isMutating, setIsMutating] = useState<string | null>(null);
  const [opError, setOpError] = useState<string | null>(null);
  const [opSuccess, setOpSuccess] = useState<string | null>(null);

  const refresh = async () => {
    try {
      const next = await api.workspace.getState();
      setState(next);
      setLoadError(null);
    } catch (err) {
      setLoadError(err instanceof APIError ? err.message : 'Failed to load workspace state');
    }
  };

  useEffect(() => { refresh(); }, []);

  useEffect(() => {
    if (opSuccess) {
      const t = setTimeout(() => setOpSuccess(null), 4000);
      return () => clearTimeout(t);
    }
  }, [opSuccess]);

  const handleActivate = async (slug: string) => {
    setIsMutating(slug); setOpError(null);
    try {
      await api.programs.activate(slug);
      setOpSuccess(`Activated ${slug}`);
      await refresh();
    } catch (err) {
      setOpError(err instanceof APIError ? err.message : 'Activation failed');
    } finally { setIsMutating(null); }
  };

  const handleDeactivate = async () => {
    setIsMutating('deactivate'); setOpError(null);
    try {
      const res = await api.programs.deactivate();
      if (res.deactivated) setOpSuccess(`Deactivated ${res.prior_program_slug}`);
      await refresh();
    } catch (err) {
      setOpError(err instanceof APIError ? err.message : 'Deactivation failed');
    } finally { setIsMutating(null); }
  };

  // Chat edit handler — fires the prompt into the right panel
  const handleEdit = (prompt: string) => sendMessage(prompt);

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
    ? state.available_programs.find(p => p.slug === state.active_program_slug) ?? null
    : null;

  return (
    <div className="space-y-8 max-w-2xl">

      {/* First-run banner */}
      {isFirstRun && (
        <div className="rounded-lg border border-primary/30 bg-primary/5 p-4 flex items-start gap-3">
          <Sparkles className="w-5 h-5 text-primary shrink-0 mt-0.5" />
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium">Welcome to YARNNN</p>
            <p className="text-xs text-muted-foreground mt-1">
              Pick a program to get started, or head to chat and tell YARNNN what you want to do.
            </p>
          </div>
          <button type="button" onClick={() => router.push('/chat')}
            className="text-sm font-medium text-primary hover:text-primary/80 flex items-center gap-1 shrink-0">
            Go to chat <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      {/* ── Program lifecycle ─────────────────────────────────────────── */}

      <section className="space-y-3">
        <h2 className="text-sm font-semibold">Active program</h2>
        {activeProgram ? (
          <div className="rounded-lg border border-primary/40 bg-primary/5 p-4 flex items-start justify-between gap-3">
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 flex-wrap">
                <span className="text-sm font-medium">{activeProgram.title}</span>
                {activeProgram.current_phase && (
                  <span className="text-[10px] uppercase tracking-wider text-muted-foreground/60">
                    {activeProgram.current_phase}
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
              No program activated. Pick one below or continue running as-is.
            </p>
          </div>
        )}
      </section>

      {/* Capability gaps */}
      {state.capability_gaps.length > 0 && (
        <section className="space-y-3">
          <h2 className="text-sm font-semibold">Platform connections needed</h2>
          <p className="text-xs text-muted-foreground">
            Your active program needs these platforms connected before it can execute autonomously.
          </p>
          <div className="space-y-2">
            {state.capability_gaps.map(gap => (
              <div key={`${gap.capability}-${gap.requires_platform}`}
                className="rounded-md border border-border bg-card px-3 py-2 flex items-center justify-between gap-3">
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-medium">{gap.capability}</div>
                  <div className="text-xs text-muted-foreground">
                    requires <code className="text-xs">{gap.requires_platform}</code>
                  </div>
                </div>
                {gap.connected ? (
                  <span className="text-xs text-green-700 dark:text-green-400 flex items-center gap-1 shrink-0">
                    <Check className="w-3.5 h-3.5" /> Connected
                  </span>
                ) : (
                  <a href="/connectors"
                    className="text-xs font-medium text-primary hover:text-primary/80 flex items-center gap-1 shrink-0">
                    <Link2 className="w-3.5 h-3.5" /> Connect
                  </a>
                )}
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Available programs */}
      <section className="space-y-3">
        <h2 className="text-sm font-semibold">
          {activeProgram ? 'Switch program' : 'Available programs'}
        </h2>
        <p className="text-xs text-muted-foreground">
          {activeProgram
            ? 'Switching forks the new program on top — your authored content is preserved.'
            : 'Activating a program forks its starting configuration into your workspace.'}
        </p>
        <div className="space-y-2">
          {state.available_programs.map(p => (
            <ProgramRow key={p.slug} program={p}
              isActive={p.slug === state.active_program_slug}
              isMutating={isMutating === p.slug}
              disabled={isMutating !== null && isMutating !== p.slug}
              onActivate={() => handleActivate(p.slug)} />
          ))}
        </div>
      </section>

      {/* ── Concept components — workspace setup ─────────────────────── */}

      <div className="border-t border-border/40 pt-8 space-y-8">
        <div>
          <h2 className="text-sm font-semibold">Workspace setup</h2>
          <p className="text-xs text-muted-foreground mt-1">
            These govern how YARNNN and your agents behave. Edit via chat on the right.
          </p>
        </div>

        <MandateCard variant="full" onEdit={handleEdit} />
        <DelegationCard variant="full" />
        <PrinciplesCard variant="full" onEdit={handleEdit} />
        <IdentityBrandCard variant="full" onEdit={handleEdit} />
      </div>

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
  );
}

// ─── Program row ──────────────────────────────────────────────────────────────

function ProgramRow({
  program, isActive, isMutating, disabled, onActivate,
}: {
  program: ProgramItem;
  isActive: boolean;
  isMutating: boolean;
  disabled: boolean;
  onActivate: () => void;
}) {
  const interactive = !program.deferred && !isActive;
  return (
    <div className={cn('rounded-lg border px-4 py-3', isActive ? 'border-primary/50 bg-primary/5' : 'border-border bg-card')}>
      <div className="flex items-start gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-sm font-medium">{program.title}</span>
            {isActive && (
              <span className="text-[10px] uppercase tracking-wider px-1.5 py-0.5 rounded bg-primary/15 text-primary">Active</span>
            )}
            {program.deferred && (
              <span className="text-[10px] uppercase tracking-wider px-1.5 py-0.5 rounded bg-muted text-muted-foreground/70">Coming soon</span>
            )}
            {program.current_phase && !program.deferred && !isActive && (
              <span className="text-[10px] uppercase tracking-wider text-muted-foreground/60">{program.current_phase}</span>
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
