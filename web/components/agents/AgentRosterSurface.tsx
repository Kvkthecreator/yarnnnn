'use client';

/**
 * AgentRosterSurface — Full-width roster view for /agents (ADR-167 + ADR-214).
 *
 * Post-ADR-235 D2 (2026-04-29) the chat surface no longer creates user-authored
 * Agents (`ManageAgent.create` removed). The Domain group is therefore
 * permanently empty in current canon; rendering it as an always-empty section
 * with a CTA that points back to chat is dead-end UX.
 *
 * The roster collapses to a flat two-card grid: YARNNN + Reviewer. Both are
 * systemic Agents scaffolded at signup (YARNNN as agents row, Reviewer as
 * filesystem substrate at /workspace/review/ and synthesized in the list
 * response per ADR-214). No grouping label is needed — the count is N=2 and
 * self-evident.
 *
 * If a future ADR re-introduces user-authored Agent creation (ADR-235 R4
 * deferral becomes resolved), the roster reintroduces grouping then. Today's
 * canonical shape: flat, always two cards.
 *
 * Production roles + integrations (formerly grouped here) are Orchestration,
 * not Agents (ADR-212). Production role composition appears on /work
 * task-detail; integrations are configured at /settings?tab=connectors.
 *
 * Per-card health glance:
 *   - Status indicator (active/paused)
 *   - Active task count
 *   - Last run (relative time, color-coded by freshness)
 *   - Approval rate (only if version_count >= 5, with trend)
 *
 * Click a card → onSelect(agentId) → page transitions to detail mode by
 * updating URL to `?agent={slug}`. Reviewer slug is "reviewer".
 */

import { useMemo } from 'react';
import { cn } from '@/lib/utils';
import { getAgentSlug, roleTagline } from '@/lib/agent-identity';
import { AgentIcon } from './AgentIcon';
import type { Agent, Recurrence } from '@/types';

interface AgentRosterSurfaceProps {
  agents: Agent[];
  tasks: Recurrence[];
  onSelect: (agentId: string) => void;
}

// ADR-235 D2: filter the roster to systemic Agents only. Origin is the
// truth per ADR-189 — system_bootstrap rows are systemic; user_configured
// rows are pre-ADR-235 historical and tolerated but not surfaced (the chat
// surface no longer creates them, so any remaining ones are legacy data).
// Reviewer arrives as a synthesized envelope with agent_class='reviewer'.
function isSystemicAgent(agent: Agent): boolean {
  if (agent.agent_class === 'reviewer') return true;
  if (agent.agent_class === 'meta-cognitive') return true;
  if (agent.origin === 'system_bootstrap') return true;
  return false;
}

function formatRelativeUntil(dateStr: string): string {
  const diff = new Date(dateStr).getTime() - Date.now();
  if (diff <= 0) return 'now';
  const mins = Math.floor(diff / 60000);
  if (mins < 60) return `in ${mins}m`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `in ${hours}h`;
  const days = Math.floor(hours / 24);
  if (days < 7) return `in ${days}d`;
  const weeks = Math.floor(days / 7);
  return `in ${weeks}w`;
}

function normalizeScheduleLabel(schedule?: string | null): string {
  if (!schedule) return '';
  const raw = schedule.trim();
  if (!raw) return '';
  if (/^[a-z-]+$/i.test(raw)) {
    return raw.charAt(0).toUpperCase() + raw.slice(1);
  }
  if (/^(\*|[\d\/,-]+)(\s+(\*|[\d\/,-]+)){4}$/.test(raw)) return 'Custom';
  return raw;
}

function fmtDomain(value?: string | null): string {
  if (!value) return '';
  return value.replace(/[_-]+/g, ' ').replace(/\s+/g, ' ').trim();
}

export function AgentRosterSurface({ agents, tasks, onSelect }: AgentRosterSurfaceProps) {
  // ADR-235 D2: roster collapses to a flat two-card grid (YARNNN + Reviewer).
  // No grouping header — the count is N=2 and self-evident. The Domain
  // group + its always-empty CTA card was removed when chat-surface
  // ManageAgent.create dissolved per ADR-235.
  const rosterAgents = useMemo(
    () => agents.filter(isSystemicAgent),
    [agents],
  );

  return (
    <div className="flex flex-col h-full overflow-auto">
      <div className="px-6 py-6 max-w-5xl">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {rosterAgents.map(agent => (
            <AgentCard
              key={agent.id}
              agent={agent}
              tasks={tasks}
              onSelect={() => onSelect(agent.id)}
            />
          ))}
        </div>
      </div>
    </div>
  );
}

// ─── Card ───

function AgentCard({
  agent,
  tasks,
  onSelect,
}: {
  agent: Agent;
  tasks: Recurrence[];
  onSelect: () => void;
}) {
  const slug = getAgentSlug(agent);
  const agentTasks = tasks.filter(t => t.agent_slugs?.includes(slug));
  const activeTasks = agentTasks.filter(t => t.status === 'active');
  const mostRecentTask = [...agentTasks]
    .sort((a, b) => (b.last_run_at ?? '').localeCompare(a.last_run_at ?? ''))
    .find(t => t.status === 'active') ?? activeTasks[0] ?? agentTasks[0] ?? null;
  const cls = agent.agent_class || 'specialist';
  // ADR-231: paused is a recurrence flag, not an agent flag. An agent is
  // operator-effectively "paused" when every assigned recurrence is paused.
  const isPaused = agentTasks.length > 0 && agentTasks.every((t) => t.paused === true);
  const hasNoTasks = agentTasks.length === 0;
  const operationalTasks = activeTasks.length > 0
    ? activeTasks
    : agentTasks.filter(t => t.status !== 'archived');

  const scheduleSet = Array.from(new Set(
    operationalTasks.map(t => normalizeScheduleLabel(t.schedule)).filter(Boolean),
  ));
  const frequencyLabel =
    scheduleSet.length === 0
      ? null
      : scheduleSet.length === 1
        ? scheduleSet[0]
        : `Mixed (${scheduleSet.length})`;

  const nextRun = operationalTasks
    .map(t => t.next_run_at)
    .filter((v): v is string => Boolean(v))
    .map(v => new Date(v))
    .filter(d => !Number.isNaN(d.getTime()))
    .sort((a, b) => a.getTime() - b.getTime())[0] ?? null;

  const statusTone = isPaused
    ? {
        label: 'Paused',
        dot: 'bg-amber-500',
        text: 'text-amber-700 dark:text-amber-300',
      }
    : activeTasks.length > 0
      ? {
          label: 'Active',
          dot: 'bg-emerald-500',
          text: 'text-emerald-700 dark:text-emerald-300',
        }
      : {
          label: 'Idle',
          dot: 'bg-muted-foreground/40',
          text: 'text-muted-foreground/70',
        };

  // Subline: human-readable domain for domain agents, systemic tagline for
  // YARNNN + Reviewer, role tagline otherwise.
  const subline = agent.context_domain
    ? `Tracks ${fmtDomain(agent.context_domain)}`
    : roleTagline(agent.role) || (
      cls === 'reviewer' ? 'Independent judgment on proposed actions'
      : cls === 'synthesizer' ? 'Assembles cross-domain reports'
      : cls === 'meta-cognitive' ? 'Orchestrates your workforce'
      : ''
    );

  return (
    <button
      onClick={onSelect}
      className={cn(
        'text-left rounded-lg border border-border/60 bg-background hover:bg-muted/30 hover:border-border transition-colors p-4',
        isPaused && 'opacity-60',
      )}
    >
      <div className="flex items-start gap-3">
        <div
          className={cn(
            'w-9 h-9 rounded-md flex items-center justify-center shrink-0',
            cls === 'meta-cognitive' ? 'bg-amber-500/10 text-amber-600 dark:text-amber-400' :
            cls === 'reviewer' ? 'bg-rose-500/10 text-rose-600 dark:text-rose-400' :
            cls === 'platform-bot' ? 'bg-blue-500/10 text-blue-600 dark:text-blue-400' :
            cls === 'synthesizer' ? 'bg-purple-500/10 text-purple-600 dark:text-purple-400' :
            'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400',
          )}
        >
          <AgentIcon role={agent.role} className="w-5 h-5" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className={cn('h-2 w-2 rounded-full shrink-0', statusTone.dot)} />
            <h4 className="text-sm font-semibold truncate">{agent.title}</h4>
          </div>
          {subline && (
            <p className="text-[11px] text-muted-foreground/60 truncate mt-0.5">
              {subline}
            </p>
          )}
        </div>
      </div>

      {/* Status row */}
      <div className="flex items-start justify-between gap-3 mt-3 pt-3 border-t border-border/40">
        <div className="flex flex-wrap items-center gap-2 min-w-0">
          <span
            className={cn(
              'inline-flex items-center gap-1 rounded-full border border-border/50 bg-muted/10 px-2 py-0.5 text-[10px]',
              statusTone.text,
            )}
          >
            <span className={cn('h-1.5 w-1.5 rounded-full', statusTone.dot)} />
            <span className="text-muted-foreground/70">Status</span>
            <span className="font-medium">{statusTone.label}</span>
          </span>
          {frequencyLabel && (
            <span className="text-[11px] text-muted-foreground/60">
              Frequency: {frequencyLabel}
            </span>
          )}
          <span className="text-[11px] text-muted-foreground/60">
            Next: {nextRun ? formatRelativeUntil(nextRun.toISOString()) : 'not scheduled'}
          </span>
        </div>
        {hasNoTasks ? (
          <span className="text-[11px] text-muted-foreground/40 italic shrink-0 ml-2">
            No tasks assigned yet
          </span>
        ) : (
          <div className="flex items-center justify-end gap-2 min-w-0 ml-2">
            <span className="text-[11px] text-muted-foreground/60 shrink-0">
              {activeTasks.length} active {activeTasks.length === 1 ? 'task' : 'tasks'}
            </span>
            {mostRecentTask && (
              <>
                <span className="text-muted-foreground/20">·</span>
                <span className="text-[11px] text-muted-foreground/50 truncate text-right">
                  {mostRecentTask.title}
                </span>
              </>
            )}
          </div>
        )}
      </div>
    </button>
  );
}
