'use client';

/**
 * WorkspaceStateView — single modal surface for every workspace-state scenario.
 *
 * ADR-165 v7 (2026-04-09): The `empty` lens value dissolved. "Add context" is
 * now a peer lens (`context`) alongside briefing/recent/gaps, and the gate
 * behavior (cold-start lock) is decoupled from the lens name — it is driven
 * by `isEmpty` (the workspace-state boolean) alone. Four peer tabs, one
 * uniform component. The old "empty is exclusive" conflation is gone.
 *
 * Soft gate: on cold start (`isEmpty === true`), the switcher is still
 * hidden so the new user has a single focused decision to make, but the
 * lens value is just `context` like any other — not a special "empty" state.
 * The gate is a property of workspace state, not a property of the tab.
 *
 * ADR-165 v6 (2026-04-08): Rendered as a TP-directed MODAL, not an inline
 * topContent overlay. TP opens it via the workspace-state marker; the user
 * opens it via the input-row icon. Closed = gone (backdrop + Esc + close
 * button all dismiss). Discovery responsibility moves entirely to TP — no
 * cold-start auto-open from the frontend.
 *
 * The component picks its lead view from `lead` (passed in) when TP opens
 * it via the workspace-state marker, OR computes a deterministic lead from
 * agents+tasks when the user opens it manually via the input-row icon.
 *
 * Lead views (all peers):
 *   - context  → ContextSetup (onboarding on cold start, re-entry thereafter)
 *   - briefing → What changed (DailyBriefing)
 *   - recent   → What's running (top tasks by updated_at)
 *   - gaps     → Coverage gaps (domain agents without tasks)
 */

import { useMemo, useState, useEffect } from 'react';
import {
  X,
  ClipboardList,
  Compass,
  Newspaper,
  Sparkles,
  CheckCircle2,
  Clock3,
  PauseCircle,
  AlertCircle,
} from 'lucide-react';
import { ContextSetup } from './ContextSetup';
import { DailyBriefing } from '@/components/home/DailyBriefing';
import { taskModeLabel, type Agent, type Task } from '@/types';
import { cn } from '@/lib/utils';

export type WorkspaceStateLead = 'context' | 'briefing' | 'recent' | 'gaps';

interface WorkspaceStateViewProps {
  open: boolean;
  /** Lead view to render. If null, the component computes a deterministic lead from data. */
  lead: WorkspaceStateLead | null;
  agents: Agent[];
  tasks: Task[];
  dataLoading: boolean;
  /** Workspace has no identity yet (drives auto-gate behavior). */
  isEmpty: boolean;
  /** Optional reason TP passed when opening the surface. */
  reason?: string | null;
  onClose: () => void;
  onContextSubmit: (message: string) => void;
}

/**
 * Compute a deterministic lead view from current workspace state.
 * Used when the user opens the surface manually (no TP directive).
 *
 * `context` is the cold-start default — an empty workspace has nothing
 * meaningful in briefing/recent/gaps, so capture is the only useful view.
 */
function computeLead(
  isEmpty: boolean,
  agents: Agent[],
  tasks: Task[],
): WorkspaceStateLead {
  if (isEmpty) return 'context';

  const domainAgents = agents.filter(
    (a) => (a.agent_class || 'domain-steward') === 'domain-steward',
  );
  const agentsWithoutTasks = domainAgents.filter((agent) => {
    const slug =
      agent.slug ||
      agent.title.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)/g, '');
    return !tasks.some((task) => task.agent_slugs?.includes(slug));
  });
  if (agentsWithoutTasks.length > 0) return 'gaps';

  if (tasks.length > 0) return 'briefing';
  return 'recent';
}

export function WorkspaceStateView({
  open,
  lead,
  agents,
  tasks,
  dataLoading,
  isEmpty,
  reason,
  onClose,
  onContextSubmit,
}: WorkspaceStateViewProps) {
  // Active lens — initialized from `lead` prop or computed from data.
  const initialLead = lead ?? computeLead(isEmpty, agents, tasks);
  const [activeLens, setActiveLens] = useState<WorkspaceStateLead>(initialLead);

  // When the lead prop changes (TP opens with a different view), follow it.
  useEffect(() => {
    if (lead) setActiveLens(lead);
  }, [lead]);

  // Esc closes the modal. Body scroll lock while open.
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    window.addEventListener('keydown', onKey);
    return () => {
      document.body.style.overflow = prevOverflow;
      window.removeEventListener('keydown', onKey);
    };
  }, [open, onClose]);

  if (!open) return null;

  // Soft gate: switcher visibility is driven by workspace state ONLY, not by
  // the active lens. On cold start we hide the switcher so the new user has a
  // single focused decision (capture context). Once workspace has any content,
  // all four tabs are reachable — including `context` as a peer for re-entry.
  const showLensSwitcher = !isEmpty;

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-foreground/40 px-4 py-[10vh] backdrop-blur-sm animate-in fade-in duration-150"
      role="dialog"
      aria-modal="true"
      aria-label="Workspace state"
      onClick={(e) => {
        // Backdrop click closes; clicks inside the panel are stopped below.
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <section
        className="w-full max-w-2xl animate-in fade-in zoom-in-95 duration-200"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="rounded-xl border border-border bg-background shadow-2xl">
          {/* Header — title + reason + close */}
          <header className="flex items-start justify-between border-b border-border px-4 py-2.5">
            <div className="min-w-0">
              <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground/70">
                Workspace state
              </p>
              {reason ? (
                <p className="mt-0.5 text-sm text-foreground">{reason}</p>
              ) : null}
            </div>
            <button
              type="button"
              onClick={onClose}
              className="rounded p-1 text-muted-foreground/40 hover:bg-muted hover:text-muted-foreground"
              aria-label="Close workspace state"
            >
              <X className="h-3.5 w-3.5" />
            </button>
          </header>

          {/* Lens switcher — hidden only on cold start (soft gate via isEmpty) */}
          {showLensSwitcher && (
            <nav
              aria-label="Workspace state lenses"
              className="flex items-center gap-1 border-b border-border px-2 py-1.5"
            >
              <LensButton
                active={activeLens === 'briefing'}
                icon={Newspaper}
                label="What changed"
                onClick={() => setActiveLens('briefing')}
              />
              <LensButton
                active={activeLens === 'recent'}
                icon={ClipboardList}
                label="Running"
                onClick={() => setActiveLens('recent')}
              />
              <LensButton
                active={activeLens === 'gaps'}
                icon={Compass}
                label="Coverage"
                onClick={() => setActiveLens('gaps')}
              />
              <LensButton
                active={activeLens === 'context'}
                icon={Sparkles}
                label="Add context"
                onClick={() => setActiveLens('context')}
              />
            </nav>
          )}

          {/* Active lens content */}
          <div className="max-h-[60vh] overflow-y-auto">
            {activeLens === 'context' ? (
              <ContextLead onSubmit={onContextSubmit} />
            ) : activeLens === 'briefing' ? (
              <BriefingLead agents={agents} tasks={tasks} />
            ) : activeLens === 'recent' ? (
              <RecentLead agents={agents} tasks={tasks} loading={dataLoading} />
            ) : (
              <GapsLead agents={agents} tasks={tasks} loading={dataLoading} />
            )}
          </div>
        </div>
      </section>
    </div>
  );
}

// =============================================================================
// Lens switcher button
// =============================================================================

interface LensButtonProps {
  active: boolean;
  icon: React.ElementType;
  label: string;
  onClick: () => void;
}

function LensButton({ active, icon: Icon, label, onClick }: LensButtonProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        'flex items-center gap-1.5 rounded-md px-2.5 py-1 text-xs font-medium transition-colors',
        active
          ? 'bg-foreground text-background'
          : 'text-muted-foreground hover:bg-muted hover:text-foreground',
      )}
    >
      <Icon className="h-3.5 w-3.5" />
      <span>{label}</span>
    </button>
  );
}

// =============================================================================
// Lead view: Context (identity capture + re-entry)
// =============================================================================
// On cold start this renders under a hidden switcher (the soft gate — driven
// by `isEmpty` in the parent, not by this lens value). Once workspace has
// any content, the switcher shows and this tab becomes a peer lens for
// re-entry. Same component, two moments — the lens value is uniform.

function ContextLead({ onSubmit }: { onSubmit: (message: string) => void }) {
  return (
    <div className="p-3">
      <ContextSetup onSubmit={onSubmit} embedded />
    </div>
  );
}

// =============================================================================
// Lead view: Briefing
// =============================================================================

function BriefingLead({ agents, tasks }: { agents: Agent[]; tasks: Task[] }) {
  return (
    <div className="p-3">
      <DailyBriefing
        agents={agents}
        tasks={tasks}
        hasMessages={false}
        forceExpanded
      />
    </div>
  );
}

// =============================================================================
// Lead view: Recent work
// =============================================================================

function agentTitleForTask(task: Task, agents: Agent[]) {
  const slug = task.agent_slugs?.[0];
  return agents.find((agent) => agent.slug === slug)?.title || slug || 'TP';
}

function formatRelativeTime(value?: string) {
  if (!value) return null;
  const then = new Date(value).getTime();
  if (Number.isNaN(then)) return null;
  const diff = Date.now() - then;
  const future = diff < 0;
  const abs = Math.abs(diff);
  const mins = Math.floor(abs / 60000);
  if (mins < 1) return future ? 'soon' : 'just now';
  if (mins < 60) return future ? `in ${mins}m` : `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return future ? `in ${hours}h` : `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return future ? `in ${days}d` : `${days}d ago`;
}

function RecentLead({
  agents,
  tasks,
  loading,
}: {
  agents: Agent[];
  tasks: Task[];
  loading: boolean;
}) {
  const visibleTasks = useMemo(
    () =>
      tasks
        .slice()
        .sort(
          (a, b) =>
            new Date(b.updated_at || b.created_at).getTime() -
            new Date(a.updated_at || a.created_at).getTime(),
        )
        .slice(0, 6),
    [tasks],
  );

  if (loading) {
    return (
      <div className="px-5 py-8 text-sm text-muted-foreground">
        Loading current work...
      </div>
    );
  }

  if (visibleTasks.length === 0) {
    return (
      <div className="px-5 py-8">
        <p className="text-sm font-medium">No work is running yet.</p>
        <p className="mt-1 text-sm text-muted-foreground">
          Tell TP what you want watched, prepared, or produced.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-2 p-4">
      {visibleTasks.map((task) => {
        const active = task.status === 'active';
        const completed = task.status === 'completed';
        const Icon = completed ? CheckCircle2 : active ? Clock3 : PauseCircle;
        const lastSignal = formatRelativeTime(task.last_run_at || task.updated_at);

        return (
          <div
            key={task.id}
            className="rounded-lg border border-border/70 bg-muted/20 p-3"
          >
            <div className="flex items-start gap-2">
              <Icon
                className={cn(
                  'mt-0.5 h-4 w-4 shrink-0',
                  active ? 'text-green-600' : 'text-muted-foreground',
                )}
              />
              <div className="min-w-0 flex-1">
                <div className="flex min-w-0 items-center gap-2">
                  <p className="truncate text-sm font-medium">{task.title}</p>
                  <span className="shrink-0 rounded border border-border bg-background px-1.5 py-0.5 text-[10px] text-muted-foreground">
                    {taskModeLabel(task.mode)}
                  </span>
                </div>
                <p className="mt-1 truncate text-xs text-muted-foreground">
                  {agentTitleForTask(task, agents)}
                  {task.objective?.deliverable
                    ? ` -> ${task.objective.deliverable}`
                    : ''}
                </p>
              </div>
              {lastSignal && (
                <span className="shrink-0 text-xs text-muted-foreground/60">
                  {lastSignal}
                </span>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}

// =============================================================================
// Lead view: Coverage gaps
// =============================================================================

function GapsLead({
  agents,
  tasks,
  loading,
}: {
  agents: Agent[];
  tasks: Task[];
  loading: boolean;
}) {
  const domainAgents = agents.filter(
    (agent) => (agent.agent_class || 'domain-steward') === 'domain-steward',
  );
  const agentsWithoutTasks = domainAgents.filter((agent) => {
    const slug =
      agent.slug ||
      agent.title.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)/g, '');
    return !tasks.some((task) => task.agent_slugs?.includes(slug));
  });
  // ADR-166: task_class → output_kind. "context" → "accumulates_context".
  const contextTasks = tasks.filter(
    (task) => task.output_kind === 'accumulates_context',
  ).length;

  if (loading) {
    return (
      <div className="px-5 py-8 text-sm text-muted-foreground">
        Checking context...
      </div>
    );
  }

  return (
    <div className="space-y-4 p-4">
      <div>
        <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground/60">
          Coverage
        </p>
        <div className="mt-2 grid grid-cols-2 gap-2">
          <div className="rounded-lg border border-border/70 bg-muted/20 p-3">
            <p className="text-xl font-semibold">{domainAgents.length}</p>
            <p className="text-xs text-muted-foreground">domain agents</p>
          </div>
          <div className="rounded-lg border border-border/70 bg-muted/20 p-3">
            <p className="text-xl font-semibold">{contextTasks}</p>
            <p className="text-xs text-muted-foreground">context tasks</p>
          </div>
        </div>
      </div>

      {agentsWithoutTasks.length > 0 ? (
        <div>
          <div className="mb-2 flex items-center gap-1.5 text-sm font-medium">
            <AlertCircle className="h-4 w-4 text-amber-500" />
            Needs setup
          </div>
          <div className="space-y-1.5">
            {agentsWithoutTasks.slice(0, 5).map((agent) => (
              <div
                key={agent.id}
                className="rounded-md border border-border/70 px-3 py-2 text-sm text-muted-foreground"
              >
                <span className="font-medium text-foreground">{agent.title}</span>{' '}
                has no assigned work yet.
              </div>
            ))}
          </div>
        </div>
      ) : (
        <div className="rounded-lg border border-border/70 bg-muted/20 p-3">
          <div className="flex items-center gap-1.5 text-sm font-medium">
            <CheckCircle2 className="h-4 w-4 text-green-600" />
            Coverage looks ready
          </div>
          <p className="mt-1 text-sm text-muted-foreground">
            TP has at least one work path for every domain agent.
          </p>
        </div>
      )}
    </div>
  );
}
