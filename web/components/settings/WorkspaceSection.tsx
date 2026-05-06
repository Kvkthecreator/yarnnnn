'use client';

/**
 * WorkspaceSection — `/settings?tab=workspace` body. ADR-244.
 *
 * One permanent surface for workspace-program lifecycle. Replaces the
 * one-shot OnboardingModal (ADR-240) — same activate flow, plus switch
 * + deactivate + status visibility, plus operator can revisit any time.
 *
 * Read-mostly. Mutation affordances:
 *   - Activate (when no active program): POST /api/programs/activate
 *   - Switch (when a different program is active): same POST endpoint;
 *     bundle's idempotent re-fork rules (ADR-226 §4) handle it
 *   - Deactivate (when a program is active): POST /api/programs/deactivate
 *     — soft, drops MANDATE.md marker, body untouched (ADR-244 D3)
 *   - Connect platform (capability gap): deep-link to /connectors
 *
 * Hard boundary (ADR-244 D7): zero edit affordances for substrate content.
 * MANDATE / IDENTITY / BRAND / AUTONOMY / principles authoring routes to
 * chat. The surface displays per-file state (skeleton / authored / missing)
 * and deep-links to Files for direct markdown editing.
 *
 * `?first_run=1` query param tightens the CTA — surfaces a "Continue to
 * chat" link prominently and emphasizes the program-pick affordance.
 * Same content layout otherwise; one render path.
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
  FileText,
  ExternalLink,
} from 'lucide-react';
import { api, APIError } from '@/lib/api/client';

type WorkspaceState = Awaited<ReturnType<typeof api.workspace.getState>>;
type ProgramItem = WorkspaceState['available_programs'][number];
type FileStatus = WorkspaceState['substrate_status']['mandate'];

const FILE_LABELS: Record<keyof WorkspaceState['substrate_status'], string> = {
  mandate: 'Mandate',
  identity: 'Identity',
  brand: 'Brand',
  autonomy: 'Autonomy',
  principles: 'Reviewer principles',
};

// Files page deep-links — substrate authoring routes through chat per
// ADR-244 D7, but Files is the right destination for raw markdown viewing.
const FILE_PATHS: Record<keyof WorkspaceState['substrate_status'], string> = {
  mandate: '/workspace/context/_shared/MANDATE.md',
  identity: '/workspace/context/_shared/IDENTITY.md',
  brand: '/workspace/context/_shared/BRAND.md',
  autonomy: '/workspace/context/_shared/AUTONOMY.md',
  principles: '/workspace/review/principles.md',
};

export function WorkspaceSection() {
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

  useEffect(() => {
    refresh();
  }, []);

  // Auto-dismiss op success
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

  const handleDeactivate = async () => {
    setIsMutating('deactivate');
    setOpError(null);
    try {
      const res = await api.programs.deactivate();
      if (res.deactivated) {
        setOpSuccess(`Deactivated ${res.prior_program_slug}`);
      }
      await refresh();
    } catch (err) {
      setOpError(err instanceof APIError ? err.message : 'Deactivation failed');
    } finally {
      setIsMutating(null);
    }
  };

  const handleContinueToChat = () => {
    router.push('/chat');
  };

  // ─── Loading / error states ──────────────────────────────────────────

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

  return (
    <section className="space-y-6">
      {/* First-run banner */}
      {isFirstRun && (
        <div className="rounded-lg border border-primary/30 bg-primary/5 p-4">
          <div className="flex items-start gap-3">
            <Sparkles className="w-5 h-5 text-primary shrink-0 mt-0.5" />
            <div className="flex-1 min-w-0">
              <h3 className="text-sm font-medium">Welcome to YARNNN</h3>
              <p className="text-xs text-muted-foreground mt-1">
                Pick a program to fork its starting substrate, or continue without
                one — you can activate any time from this page.
              </p>
            </div>
            <button
              type="button"
              onClick={handleContinueToChat}
              className="text-sm font-medium text-primary hover:text-primary/80 flex items-center gap-1 shrink-0"
            >
              Continue to chat <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      )}

      {/* Active program panel */}
      <div>
        <h2 className="text-lg font-semibold mb-2">Active program</h2>
        {activeProgram ? (
          <div className="rounded-lg border border-border bg-card p-4">
            <div className="flex items-start justify-between gap-3">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <h3 className="text-sm font-medium">{activeProgram.title}</h3>
                  {activeProgram.current_phase && (
                    <span className="text-[10px] uppercase tracking-wider text-muted-foreground/60">
                      {activeProgram.current_phase}
                    </span>
                  )}
                </div>
                {activeProgram.tagline && (
                  <p className="text-xs text-muted-foreground mt-1">{activeProgram.tagline}</p>
                )}
                <p className="text-xs text-muted-foreground/70 mt-2">
                  Activation state:{' '}
                  <span className="font-mono">{state.activation_state}</span>
                </p>
              </div>
              <button
                type="button"
                onClick={handleDeactivate}
                disabled={isMutating !== null}
                className="px-3 py-1.5 text-xs font-medium border border-border rounded-md hover:bg-muted/20 disabled:opacity-40 flex items-center gap-1.5 shrink-0"
                title="Drop the bundle marker. Operator-authored content stays."
              >
                {isMutating === 'deactivate' ? (
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                ) : (
                  <Power className="w-3.5 h-3.5" />
                )}
                Deactivate
              </button>
            </div>
          </div>
        ) : (
          <div className="rounded-lg border border-dashed border-border bg-muted/10 px-4 py-3">
            <p className="text-sm text-muted-foreground">
              No program activated. Pick one below or continue running the kernel as-is.
            </p>
          </div>
        )}
      </div>

      {/* Capability gaps */}
      {state.capability_gaps.length > 0 && (
        <div>
          <h2 className="text-lg font-semibold mb-2">Capability gaps</h2>
          <p className="text-xs text-muted-foreground mb-3">
            Your active program declares capabilities that need a connected platform.
            Until connected, autonomous execution is paused — chat still works in
            knowledge mode.
          </p>
          <div className="space-y-2">
            {state.capability_gaps.map((gap) => (
              <div
                key={`${gap.capability}-${gap.requires_platform}`}
                className="rounded-md border border-border bg-card px-3 py-2 flex items-center justify-between gap-3"
              >
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-medium">{gap.capability}</div>
                  <div className="text-xs text-muted-foreground">
                    requires{' '}
                    <code className="text-xs">{gap.requires_platform}</code>
                  </div>
                </div>
                {gap.connected ? (
                  <span className="text-xs text-green-700 dark:text-green-400 flex items-center gap-1 shrink-0">
                    <Check className="w-3.5 h-3.5" />
                    Connected
                  </span>
                ) : (
                  <a
                    href="/connectors"
                    className="text-xs font-medium text-primary hover:text-primary/80 flex items-center gap-1 shrink-0"
                  >
                    <Link2 className="w-3.5 h-3.5" />
                    Connect
                  </a>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Available programs */}
      <div>
        <h2 className="text-lg font-semibold mb-2">
          {activeProgram ? 'Switch program' : 'Available programs'}
        </h2>
        <p className="text-xs text-muted-foreground mb-3">
          {activeProgram
            ? 'Switching forks the new bundle on top — your authored content is preserved per ADR-209.'
            : 'Activating forks the bundle’s reference workspace into yours.'}
        </p>
        <div className="space-y-2">
          {state.available_programs.map((p) => (
            <ProgramRow
              key={p.slug}
              program={p}
              isActive={p.slug === state.active_program_slug}
              isMutating={isMutating === p.slug}
              disabled={isMutating !== null && isMutating !== p.slug}
              onActivate={() => handleActivate(p.slug)}
            />
          ))}
        </div>
      </div>

      {/* Substrate status */}
      <div>
        <h2 className="text-lg font-semibold mb-2">Substrate status</h2>
        <p className="text-xs text-muted-foreground mb-3">
          Per-file state of your authored workspace substrate. Authoring routes
          through chat — open in Files to view raw markdown.
        </p>
        <div className="grid gap-2">
          {(Object.keys(FILE_LABELS) as Array<keyof WorkspaceState['substrate_status']>).map(
            (key) => (
              <SubstrateRow
                key={key}
                label={FILE_LABELS[key]}
                path={FILE_PATHS[key]}
                status={state.substrate_status[key]}
              />
            )
          )}
        </div>
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
    </section>
  );
}

// ─── Components ──────────────────────────────────────────────────────────

function ProgramRow({
  program,
  isActive,
  isMutating,
  disabled,
  onActivate,
}: {
  program: ProgramItem;
  isActive: boolean;
  isMutating: boolean;
  disabled: boolean;
  onActivate: () => void;
}) {
  const interactive = !program.deferred && !isActive;
  return (
    <div
      className={`rounded-lg border px-4 py-3 ${
        isActive ? 'border-primary/50 bg-primary/5' : 'border-border bg-card'
      }`}
    >
      <div className="flex items-start gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <h3 className="text-sm font-medium">{program.title}</h3>
            {isActive && (
              <span className="text-[10px] uppercase tracking-wider px-1.5 py-0.5 rounded bg-primary/15 text-primary">
                Active
              </span>
            )}
            {program.deferred && (
              <span className="text-[10px] uppercase tracking-wider px-1.5 py-0.5 rounded bg-muted text-muted-foreground/70">
                Coming soon
              </span>
            )}
            {program.current_phase && !program.deferred && !isActive && (
              <span className="text-[10px] uppercase tracking-wider text-muted-foreground/60">
                {program.current_phase}
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
              <ArrowRight className="w-3.5 h-3.5" />
            )}
            {isActive ? 'Re-fork' : 'Activate'}
          </button>
        )}
      </div>
    </div>
  );
}

function SubstrateRow({
  label,
  path,
  status,
}: {
  label: string;
  path: string;
  status: FileStatus;
}) {
  const stateBadge =
    status.state === 'authored' ? (
      <span className="text-[10px] uppercase tracking-wider px-1.5 py-0.5 rounded bg-green-500/15 text-green-700 dark:text-green-400">
        Authored
      </span>
    ) : status.state === 'skeleton' ? (
      <span className="text-[10px] uppercase tracking-wider px-1.5 py-0.5 rounded bg-amber-500/15 text-amber-700 dark:text-amber-400">
        Skeleton
      </span>
    ) : (
      <span className="text-[10px] uppercase tracking-wider px-1.5 py-0.5 rounded bg-destructive/15 text-destructive">
        Missing
      </span>
    );

  const filesHref = `/context?path=${encodeURIComponent(path)}`;

  return (
    <div className="rounded-md border border-border bg-card px-3 py-2 flex items-center justify-between gap-3">
      <div className="flex items-center gap-2 flex-1 min-w-0">
        <FileText className="w-3.5 h-3.5 text-muted-foreground shrink-0" />
        <div className="min-w-0">
          <div className="text-sm font-medium truncate">{label}</div>
          <div className="text-xs text-muted-foreground truncate font-mono">{path}</div>
        </div>
      </div>
      <div className="flex items-center gap-2 shrink-0">
        {stateBadge}
        <a
          href={filesHref}
          className="text-xs text-muted-foreground hover:text-foreground flex items-center gap-1"
        >
          Open <ExternalLink className="w-3 h-3" />
        </a>
      </div>
    </div>
  );
}
