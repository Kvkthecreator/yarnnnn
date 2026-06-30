'use client';

/**
 * AgentContentView — Canonical agent detail surface content.
 *
 * Rendering model (Phase I post-merge sweep, 2026-05-10):
 * - agent_class decides the top-level shell/context block
 * - assigned-work cards are universal — per ADR-261 D1's "one execution
 *   shape" + ADR-262 D1's slug-templated convention, every recurrence is
 *   report-shaped on disk. Highlights collapse to {active, total} counts;
 *   the legacy per-output_kind branching is gone.
 *
 * This mirrors WorkDetail's registry-driven approach instead of branching on
 * individual agent pages or legacy role names.
 */

import { useEffect, useState } from 'react';
import {
  ArrowUpRight,
  ChevronRight,
  FolderKanban,
  Sparkles,
  Loader2,
  // ADR-387 — Freddie grouped-nav pane icons
  User,
  Scale,
  ShieldCheck,
  Wallet,
  Crosshair,
  FileCode,
  Activity as ActivityIcon,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { MarkdownRenderer } from '@/components/shared/MarkdownRenderer';
import { AgentIcon } from './AgentIcon';
import { RevisionHistoryPanel } from '@/components/workspace/RevisionHistoryPanel';
import { SurfaceIdentityHeader } from '@/components/shell/SurfaceIdentityHeader';
import { SurfaceLink } from '@/components/shell/SurfaceLink';
import { formatRelativeTime } from '@/lib/formatting';
import { humanizeSchedule, scheduleDisplay } from '@/lib/schedule';
import { SubstrateTab } from './SubstrateTab';
import { FreddieActivityPanel } from './FreddieActivityPanel';
import { FreddieCapabilitiesPanel } from './FreddieCapabilitiesPanel';
import { SettingsPaneShell, type PaneGroup } from '@/components/settings/SettingsPaneShell';
// ADR-387 (2026-06-29): Freddie's pane absorbs the agent-scoped governance
// panes out of Workspace Settings. The same *Card full variants render here
// (a MOVE, not a copy — Workspace Settings loses them; Singular Implementation).
import { PrinciplesCard } from '@/components/workspace-concepts/PrinciplesCard';
import { AutonomyCard } from '@/components/workspace-concepts/AutonomyCard';
import { BudgetCard } from '@/components/workspace-concepts/BudgetCard';
import { ExpectedOutputCard } from '@/components/workspace-concepts/ExpectedOutputCard';
import {
  agentClassDescription,
  agentClassLabel,
  getAgentSlug,
  roleDisplayName,
  platformProviderForRole,
  roleTagline,
} from '@/lib/agent-identity';
import type { Agent, Recurrence } from '@/types';

interface AgentContentViewProps {
  agent: Agent;
  tasks: Recurrence[];
}

type AgentClass = NonNullable<Agent['agent_class']>;
// ADR-241: reviewer redirects to TP's Principles tab; the registry lookup
// returns Reviewer's data path through `/agents?agent=freddie` only as a
// legacy URL — handled by the redirect-effect in AgentContentView.
type RegistryAgentClass = Exclude<AgentClass, 'freddie'>;
// Phase I (post-merge sweep, 2026-05-10): `RecurrenceOutputKind` removed
// per ADR-261 D1's "one execution shape" — recurrences are no longer
// kind-classified. The agent shells highlight active task count instead
// of per-kind breakdowns.

interface AgentShellDescriptor {
  label: string;
  title: (agent: Agent) => string;
  description: (agent: Agent) => string;
  highlights: (agent: Agent, counts: TaskKindCounts) => string[];
}

interface RoleGuidanceDescriptor {
  bestFor: (agent: Agent) => string;
  does: (agent: Agent) => string[];
  doesnt: (agent: Agent) => string[];
  examples: (agent: Agent) => string[];
}

interface AgentEmptyStateDescriptor {
  title: (agent: Agent) => string;
  description: (agent: Agent) => string;
}



type TaskKindCounts = { active: number; total: number };

const EMPTY_TASK_COUNTS: TaskKindCounts = { active: 0, total: 0 };


// Phase I: per ADR-261 D1, recurrences are not kind-classified. Highlights
// collapse to "N active recurrences" (or "N recurrences" when none active).
function describeActiveRecurrences(counts: TaskKindCounts): string[] {
  if (counts.total === 0) return [];
  if (counts.active > 0) {
    return [`${counts.active} active ${counts.active === 1 ? 'recurrence' : 'recurrences'}`];
  }
  return [`${counts.total} ${counts.total === 1 ? 'recurrence' : 'recurrences'} (none active)`];
}

const _SPECIALIST_SHELL: AgentShellDescriptor = {
  label: 'Role',
  title: (agent) => roleTagline(agent.role) || roleDisplayName(agent.role),
  description: (agent) => agentClassDescription(agent.agent_class),
  highlights: (_, counts) => describeActiveRecurrences(counts),
};

const AGENT_SHELL_REGISTRY: Record<RegistryAgentClass, AgentShellDescriptor> = {
  'specialist': _SPECIALIST_SHELL,
  'domain-steward': _SPECIALIST_SHELL, // backward compat — v4 DB rows
  synthesizer: {
    label: 'Role',
    title: () => 'Assembles cross-domain updates',
    description: () => 'Reads what each specialist has learned and turns it into a report, brief, or executive update.',
    highlights: (_, counts) => describeActiveRecurrences(counts),
  },
  'platform-bot': {
    label: 'Role',
    title: (agent) => {
      const platform = roleDisplayName(agent.role).replace(' Bot', '');
      return `Connects to ${platform} and watches selected sources`;
    },
    description: (agent) => {
      const platform = roleDisplayName(agent.role).replace(' Bot', '');
      return `Manages your ${platform} connection and source selection. Add a digest recurrence to start pulling information in.`;
    },
    highlights: (_, counts) => describeActiveRecurrences(counts),
  },
};

const _SPECIALIST_EMPTY_STATE: AgentEmptyStateDescriptor = {
  title: () => 'No work assigned yet',
  description: () => 'Ask YARNNN to set up a recurrence for this specialist.',
};

const AGENT_EMPTY_STATE_REGISTRY: Record<RegistryAgentClass, AgentEmptyStateDescriptor> = {
  'specialist': _SPECIALIST_EMPTY_STATE,
  'domain-steward': _SPECIALIST_EMPTY_STATE, // backward compat
  synthesizer: {
    title: () => 'No work assigned yet',
    description: () => 'Ask YARNNN to create a reporting recurrence once the specialists have trackers running.',
  },
  'platform-bot': {
    title: () => 'Not watching anything yet',
    description: (agent) => {
      const platform = roleDisplayName(agent.role).replace(' Bot', '');
      return `Connect ${platform} above and select sources, then ask YARNNN to set up a platform-awareness recurrence.`;
    },
  },
};

const _SPECIALIST_GUIDANCE: RoleGuidanceDescriptor = {
  bestFor: (agent) => roleTagline(agent.role) || 'Doing one thing deeply and well.',
  does: () => [
    'Executes assigned invocations with full specialist focus',
    'Reads and writes context domain files',
    'Produces structured output (text, analysis, or visuals)',
  ],
  doesnt: () => [
    'Orchestrate other agents or manage the workforce',
    'Own cross-domain synthesis for the whole workspace',
    'Run workspace-wide maintenance policy',
  ],
  examples: (agent) => [
    `What should ${agent.title} focus on this week?`,
    `Run ${agent.title} on the latest data.`,
    `What has ${agent.title} produced recently?`,
  ],
};

const ROLE_GUIDANCE_REGISTRY: Record<RegistryAgentClass, RoleGuidanceDescriptor> = {
  'specialist': _SPECIALIST_GUIDANCE,
  'domain-steward': _SPECIALIST_GUIDANCE, // backward compat
  synthesizer: {
    bestFor: () => 'Combining specialist inputs into one coherent cross-domain readout.',
    does: () => [
      'Reads across multiple specialist domains',
      'Builds executive summaries and strategic updates',
      'Connects signals into one decision-ready narrative',
    ],
    doesnt: () => [
      'Own raw source harvesting from platforms',
      'Maintain a single domain folder as primary responsibility',
      'Run system maintenance and orchestration policy',
    ],
    examples: () => [
      'Create a weekly cross-domain executive update.',
      'Summarize risks and opportunities across all active domains.',
      'Draft a stakeholder-ready report using this week’s specialist outputs.',
    ],
  },
  'platform-bot': {
    bestFor: (agent) => {
      const platform = roleDisplayName(agent.role).replace(' Bot', '');
      return `Watching selected ${platform} sources and producing platform-specific digests or actions.`;
    },
    does: (agent) => {
      const platform = roleDisplayName(agent.role).replace(' Bot', '');
      return [
        `Monitors selected ${platform} sources`,
        'Extracts notable items into structured updates',
        'Runs platform-targeted recurrences (awareness or write-back)',
      ];
    },
    doesnt: () => [
      'Decide global workspace strategy',
      'Own broad cross-domain synthesis by itself',
      'Maintain unrelated domains outside its platform feed',
    ],
    examples: (agent) => {
      const platform = roleDisplayName(agent.role).replace(' Bot', '');
      return [
        `Summarize the top items from selected ${platform} sources this week.`,
        'Flag the most urgent signal and why it matters now.',
        'Draft a concise action update for the latest high-priority thread.',
      ];
    },
  },
};


function stripLeadingH1IfMatchesTitle(content: string, title: string): string {
  const lines = content.split('\n');
  let i = 0;
  while (i < lines.length && lines[i].trim() === '') i++;
  if (i >= lines.length) return content;

  const firstLine = lines[i].trim();
  if (!firstLine.startsWith('# ') || firstLine.startsWith('## ')) return content;

  const h1Text = firstLine.slice(2).trim();
  if (h1Text.toLowerCase() !== title.toLowerCase()) return content;

  let j = i + 1;
  while (j < lines.length && lines[j].trim() === '') j++;
  return lines.slice(j).join('\n');
}

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <h3 className="text-[11px] font-medium text-muted-foreground/60 mb-2">
      {children}
    </h3>
  );
}

function formatKeyLabel(value?: string | null, capitalize = true): string {
  if (!value) return '';
  const formatted = value.replace(/[_-]+/g, ' ').replace(/\s+/g, ' ').trim();
  if (!formatted) return '';
  return capitalize ? formatted.charAt(0).toUpperCase() + formatted.slice(1) : formatted;
}

function getTaskKindCounts(tasks: Recurrence[]): TaskKindCounts {
  // Phase I: collapsed from per-output_kind buckets to {active, total}
  // per ADR-261 D1's "one execution shape". Active = recurrence is
  // running (status='active' AND not paused).
  return tasks.reduce<TaskKindCounts>((counts, task) => {
    const live = task.status !== 'archived';
    if (live) counts.total += 1;
    if (live && task.status === 'active' && task.paused !== true) counts.active += 1;
    return counts;
  }, { ...EMPTY_TASK_COUNTS });
}

function normalizeCadenceLabel(schedule?: string | string[] | null): string {
  // ADR-268: list-form schedules are recurring by construction; the
  // canonical humanizeSchedule formats them as "N× · first" so the agent
  // panel shows a meaningful summary without dumping each member.
  return humanizeSchedule(schedule);
}

function summarizeRoleContract(agent: Agent, tasks: Recurrence[]) {
  const cls = (agent.agent_class || 'specialist') as RegistryAgentClass;
  const liveTasks = tasks.filter((task) => task.status !== 'archived');
  const activeTasks = liveTasks.filter((task) => task.status === 'active');

  const readDomains = Array.from(new Set(
    liveTasks.flatMap((task) => task.context_reads || []).map((d) => formatKeyLabel(d, false)),
  )).filter(Boolean);
  const writeDomains = Array.from(new Set(
    liveTasks.flatMap((task) => task.context_writes || []).map((d) => formatKeyLabel(d, false)),
  )).filter(Boolean);

  const inputs = (() => {
    const parts: string[] = [];
    if (readDomains.length > 0) parts.push(`Reads: ${readDomains.join(', ')}`);
    if (writeDomains.length > 0) parts.push(`Writes: ${writeDomains.join(', ')}`);
    if (parts.length > 0) return parts.join(' · ');

    if (cls === 'platform-bot') {
      const platform = roleDisplayName(agent.role).replace(' Bot', '');
      return `Selected ${platform} sources`;
    }
    if (cls === 'synthesizer') return 'Production Role domain outputs';
    return agent.context_domain
      ? `${formatKeyLabel(agent.context_domain, false)} context folder`
      : 'Assigned context domain';
  })();

  // Phase I: per ADR-261/262, every recurrence's output substrate lives at
  // /workspace/operation/reports/{slug}/{date}/output.md. Per-class label fallbacks
  // remain to provide useful agent-card guidance when no recurrences are
  // assigned yet.
  const outputs = (() => {
    if (liveTasks.length > 0) return 'Reports under /workspace/operation/reports/{slug}/';
    if (cls === 'platform-bot') return 'Platform digest and action outputs';
    if (cls === 'synthesizer') return 'Cross-domain reports';
    return 'Domain tracking updates and briefs';
  })();

  const triggers = (() => {
    // Phase I: trigger inference from schedule presence alone (per ADR-260
    // D2 three-trigger model; per ADR-261 D1 there is no `shape` field on
    // recurrences). Recurrence with schedule → Schedule; recurrence without
    // schedule → On demand (reactive / addressed).
    const triggerSet = new Set<string>();
    if (activeTasks.some((task) => task.schedule)) triggerSet.add('Schedule');
    if (activeTasks.some((task) => !task.schedule)) triggerSet.add('On demand');
    if (triggerSet.size === 0) triggerSet.add('On demand');
    return Array.from(triggerSet).join(', ');
  })();

  const cadence = (() => {
    const schedules = Array.from(new Set(
      activeTasks.map((task) => normalizeCadenceLabel(task.schedule)).filter(Boolean),
    ));
    if (schedules.length === 0) return activeTasks.length === 0 ? 'Not scheduled' : 'As needed';
    if (schedules.length === 1) return schedules[0];
    return `Mixed (${schedules.length})`;
  })();

  return { inputs, outputs, triggers, cadence };
}

function AgentMetadata({ agent, tasks }: { agent: Agent; tasks: Recurrence[] }) {
  const classLabel = agentClassLabel(agent.agent_class);
  const showClassLabel = classLabel.toLowerCase() !== agent.title.toLowerCase();
  const domain = agent.context_domain;
  const activeTaskCount = tasks.filter((task) => task.status === 'active').length;
  const lastRun = tasks
    .map((task) => task.last_run_at)
    .filter(Boolean)
    .sort()
    .reverse()[0] || agent.last_run_at || null;

  const segments: React.ReactNode[] = [];
  if (showClassLabel) segments.push(<span key="class">{classLabel}</span>);
  if (domain) {
    segments.push(
      <SurfaceLink
        key="domain"
        to="files"
        params={{ domain }}
        className="hover:text-foreground hover:underline"
      >
        {formatKeyLabel(domain)}
      </SurfaceLink>,
    );
  }
  segments.push(
    <span key="tasks">
      {activeTaskCount} active {activeTaskCount === 1 ? 'task' : 'tasks'}
    </span>,
  );
  if (lastRun) segments.push(<span key="last-run">Ran {formatRelativeTime(lastRun)}</span>);

  return (
    <div className="flex items-center gap-1.5 flex-wrap">
      {segments.map((segment, index) => (
        <span key={index} className="flex items-center gap-1.5">
          {index > 0 && <span className="text-muted-foreground/30">·</span>}
          {segment}
        </span>
      ))}
    </div>
  );
}

function AgentRoleBlock({ agent, tasks }: { agent: Agent; tasks: Recurrence[] }) {
  const descriptor = AGENT_SHELL_REGISTRY[(agent.agent_class || 'specialist') as RegistryAgentClass];
  const guidance = ROLE_GUIDANCE_REGISTRY[(agent.agent_class || 'specialist') as RegistryAgentClass];
  const contract = summarizeRoleContract(agent, tasks);
  const instructions = agent.agent_instructions
    ? stripLeadingH1IfMatchesTitle(agent.agent_instructions, agent.title).trim()
    : '';

  return (
    <div className="px-6 py-5 border-t border-border/40">
      <SectionLabel>{descriptor.label}</SectionLabel>
      <div className="rounded-lg border border-border/60 bg-muted/10 px-4 py-4">
        <div className="flex items-start gap-3">
          <div className="w-9 h-9 rounded-lg bg-background border border-border/60 flex items-center justify-center shrink-0">
            <AgentIcon role={agent.role} className="w-4 h-4 text-muted-foreground" />
          </div>
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2 flex-wrap">
              <h4 className="text-sm font-medium text-foreground">{descriptor.title(agent)}</h4>
            </div>
            <div className="mt-2 space-y-1 text-sm">
              <p className="text-muted-foreground">
                <span className="text-muted-foreground/70 font-medium">Purpose:</span>{' '}
                {descriptor.description(agent)}
              </p>
              <p className="text-muted-foreground">
                <span className="text-muted-foreground/70 font-medium">Best for:</span>{' '}
                {guidance.bestFor(agent)}
              </p>
            </div>

            <div className="mt-4 pt-4 border-t border-border/50">
              <p className="text-[11px] font-medium text-muted-foreground/60 mb-2">Operating contract</p>
              <dl className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-sm">
                <div>
                  <dt className="text-[11px] text-muted-foreground/60">Inputs</dt>
                  <dd className="text-muted-foreground mt-0.5">{contract.inputs}</dd>
                </div>
                <div>
                  <dt className="text-[11px] text-muted-foreground/60">Outputs</dt>
                  <dd className="text-muted-foreground mt-0.5">{contract.outputs}</dd>
                </div>
                <div>
                  <dt className="text-[11px] text-muted-foreground/60">Triggers</dt>
                  <dd className="text-muted-foreground mt-0.5">{contract.triggers}</dd>
                </div>
                <div>
                  <dt className="text-[11px] text-muted-foreground/60">Cadence</dt>
                  <dd className="text-muted-foreground mt-0.5">{contract.cadence}</dd>
                </div>
              </dl>
            </div>

            <div className="mt-4 pt-4 border-t border-border/50">
              <p className="text-[11px] font-medium text-muted-foreground/60 mb-2">Scope guardrails</p>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-sm">
                <div>
                  <p className="text-[11px] text-muted-foreground/60 mb-1">Does</p>
                  <ul className="space-y-1.5 text-muted-foreground list-disc pl-4">
                    {guidance.does(agent).slice(0, 3).map((item) => (
                      <li key={item}>{item}</li>
                    ))}
                  </ul>
                </div>
                <div>
                  <p className="text-[11px] text-muted-foreground/60 mb-1">Doesn’t</p>
                  <ul className="space-y-1.5 text-muted-foreground list-disc pl-4">
                    {guidance.doesnt(agent).slice(0, 3).map((item) => (
                      <li key={item}>{item}</li>
                    ))}
                  </ul>
                </div>
              </div>
            </div>

            <div className="mt-4 pt-4 border-t border-border/50">
              <p className="text-[11px] font-medium text-muted-foreground/60 mb-2">Try asking</p>
              <ul className="space-y-1.5 text-sm text-muted-foreground list-disc pl-4">
                {guidance.examples(agent).slice(0, 3).map((example) => (
                  <li key={example}>{example}</li>
                ))}
              </ul>
            </div>

            {instructions && (
              <details className="mt-4 pt-4 border-t border-border/50">
                <summary className="cursor-pointer text-[11px] font-medium text-muted-foreground/60">
                  Technical details
                </summary>
                <div className="mt-3 prose prose-sm max-w-none dark:prose-invert text-sm">
                  <MarkdownRenderer content={instructions} />
                </div>
              </details>
            )}

            {/* ADR-209 Phase 4: revision history for the agent's AGENT.md.
                The panel reads workspace_file_versions for /agents/{slug}/AGENT.md.
                Read-only on this surface — agent AGENT.md edits flow via
                primitives (ManageAgent update for identity changes;
                WriteFile(scope='workspace', path='agents/{slug}/...') per
                ADR-235 for direct file writes), not PATCH /api/workspace/file,
                so we hide the revert button to avoid a path-mismatch surprise. */}
            <div className="mt-4">
              <RevisionHistoryPanel
                path={`/agents/${getAgentSlug(agent)}/AGENT.md`}
                initiallyCollapsed
                revertDisabled
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function SpecialistFolderBlock({ agent, tasks }: { agent: Agent; tasks: Recurrence[] }) {
  // Show for specialists (v5) and domain-stewards (v4 backward compat) that have a context domain
  const isSpecialist = agent.agent_class === 'specialist' || agent.agent_class === 'domain-steward';
  if (!isSpecialist || !agent.context_domain) return null;

  // Phase I: per ADR-261 D1, recurrences are not kind-classified. Counting
  // active recurrences assigned to this specialist's domain (any active
  // recurrence — they all write to the domain via the universal substrate
  // shape).
  const activeTrackingTasks = tasks.filter((task) => task.status === 'active');
  const domainLabel = formatKeyLabel(agent.context_domain);
  const helperText = activeTrackingTasks.length > 0
    ? `${activeTrackingTasks.length} active ${activeTrackingTasks.length === 1 ? 'task is' : 'tasks are'} currently working in this folder.`
    : 'No task is working in this folder yet.';

  return (
    <div className="px-6 py-5 border-t border-border/40">
      <SectionLabel>Context folder</SectionLabel>
      <div className="rounded-lg border border-border/60 bg-background overflow-hidden">
        <div className="flex items-center gap-1.5 border-b border-border/50 bg-muted/10 px-3 py-2 text-[11px] text-muted-foreground">
          <span>Context</span>
          <ChevronRight className="w-3 h-3" />
          <span>{domainLabel}</span>
        </div>
        <div className="flex items-start gap-3 px-4 py-4">
          <div className="w-9 h-9 rounded-lg bg-muted/30 border border-border/60 flex items-center justify-center shrink-0">
            <FolderKanban className="w-4 h-4 text-muted-foreground" />
          </div>
          <div className="min-w-0 flex-1">
            <h4 className="text-sm font-medium text-foreground">This is where {agent.title} keeps its notes</h4>
            <p className="text-sm text-muted-foreground mt-1">{helperText}</p>
            <div className="flex items-center gap-2 mt-3 text-[12px] text-muted-foreground flex-wrap">
              <span className="inline-flex items-center rounded-md border border-border/50 bg-muted/10 px-2 py-1">
                {domainLabel}/
              </span>
              <SurfaceLink
                to="files"
                params={{ domain: agent.context_domain }}
                className="inline-flex items-center gap-1 hover:text-foreground"
              >
                View folder
                <ArrowUpRight className="w-3 h-3" />
              </SurfaceLink>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function platformManagementLabel(provider: string | null, connected: boolean): string {
  switch (provider) {
    case 'slack':
    case 'notion':
      return connected ? 'Open connectors' : 'Open connectors';
    case 'github':
      return connected ? 'Open connectors' : 'Connect platform';
    default:
      return 'Open connectors';
  }
}

function TasksBlock({ agent, tasks }: { agent: Agent; tasks: Recurrence[] }) {
  const agentSlug = getAgentSlug(agent);
  const descriptor = AGENT_EMPTY_STATE_REGISTRY[(agent.agent_class || 'specialist') as RegistryAgentClass];
  const platformProvider = agent.agent_class === 'platform-bot' ? platformProviderForRole(agent.role) : null;

  if (tasks.length === 0) {
    return (
      <div className="px-6 py-5 border-t border-border/40">
        <SectionLabel>Work</SectionLabel>
        <div className="rounded-lg border border-dashed border-border/50 bg-muted/5 px-4 py-4">
          <p className="text-sm font-medium text-foreground">{descriptor.title(agent)}</p>
          <p className="text-sm text-muted-foreground mt-1">{descriptor.description(agent)}</p>
          {platformProvider && (
            <div className="mt-3">
              <SurfaceLink
                to="connectors"
                className="inline-flex items-center gap-1 text-[12px] text-muted-foreground hover:text-foreground"
              >
                {platformManagementLabel(platformProvider, false)}
                <ArrowUpRight className="w-3 h-3" />
              </SurfaceLink>
            </div>
          )}
        </div>
      </div>
    );
  }

  const sorted = [...tasks].sort((a, b) => {
    const statusOrder: Record<string, number> = { active: 0, paused: 1, archived: 2 };
    const statusDelta = (statusOrder[a.status] ?? 3) - (statusOrder[b.status] ?? 3);
    if (statusDelta !== 0) return statusDelta;
    const aTime = a.last_run_at ? new Date(a.last_run_at).getTime() : 0;
    const bTime = b.last_run_at ? new Date(b.last_run_at).getTime() : 0;
    return bTime - aTime;
  });

  return (
    <div className="px-6 py-5 border-t border-border/40">
      <SectionLabel>Work · {tasks.length}</SectionLabel>
      <div className="rounded-md border border-border/60 divide-y divide-border/40 overflow-hidden">
        {sorted.map((task) => {
          const isInactive = task.status !== 'active';
          return (
            <SurfaceLink
              key={task.id}
              to="recurrence"
              params={{ task: task.slug, agent: agentSlug }}
              className={cn(
                'flex items-center justify-between gap-3 px-4 py-3 text-sm hover:bg-muted/40 transition-colors',
                isInactive && 'opacity-60',
              )}
            >
              <span className="font-medium truncate">{task.title}</span>
              <div className="flex items-center gap-2 shrink-0 text-[11px] text-muted-foreground">
                {task.schedule && <span className="capitalize">{scheduleDisplay(task.schedule)}</span>}
                {task.last_run_at && (
                  <>
                    {task.schedule && <span className="text-muted-foreground/30">·</span>}
                    <span>ran {formatRelativeTime(task.last_run_at)}</span>
                  </>
                )}
                <ArrowUpRight className="w-3 h-3 text-muted-foreground/40" />
              </div>
            </SurfaceLink>
          );
        })}
      </div>
    </div>
  );
}

function LearnedBlock({ agent }: { agent: Agent }) {
  const feedback = agent.agent_memory?.feedback;
  const reflections = agent.agent_memory?.reflections;
  if (!feedback && !reflections) return null;

  return (
    <div className="px-6 py-5 border-t border-border/40 space-y-5">
      {feedback && (
        <div>
          <SectionLabel>
            <span className="inline-flex items-center gap-1.5">
              <Sparkles className="w-3 h-3" />
              Learned from your feedback
            </span>
          </SectionLabel>
          <div className="rounded-lg border border-border/60 bg-muted/10 px-4 py-3">
            <div className="prose prose-sm max-w-none dark:prose-invert text-sm">
              <MarkdownRenderer content={feedback} />
            </div>
          </div>
        </div>
      )}
      {reflections && (
        <div>
          <SectionLabel>Recent reflections</SectionLabel>
          <div className="rounded-lg border border-border/60 bg-muted/10 px-4 py-3">
            <div className="prose prose-sm max-w-none dark:prose-invert text-sm">
              <MarkdownRenderer content={reflections} />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}


// ---------------------------------------------------------------------------
// Shared tab bar
// ---------------------------------------------------------------------------

// ADR-387: AgentTabBar (the flat Freddie tab bar) + TabDef DELETED — Freddie's
// surface now uses the grouped sidebar (FREDDIE_PANE_GROUPS) below. No other
// consumer existed (Singular Implementation — no dead code left behind).

// ---------------------------------------------------------------------------
// ADR-272 (2026-05-14): YarnnnDetail function DELETED. System Agent surface
// dissolved as a cockpit entity. The chat-mode LLM identity (formerly the
// `meta-cognitive` agent class) persists as substrate behind /feed but is
// filtered out of /api/agents responses and has no detail surface. System
// activity (recurrence health, last-run timestamps, mechanical vs judgment
// distinction) surfaces on /work Schedule tab.
// ---------------------------------------------------------------------------

// ---------------------------------------------------------------------------
// Reviewer detail (ADR-251 D4, expanded 2026-05-14): Identity · Principles ·
// Capabilities · Autonomy · Activity
//
// Five-tab structure reads top-to-bottom as operator orienting themselves
// to their Reviewer: who (Identity) → frame (Principles) → what it can
// produce (Capabilities) → how much delegation (Autonomy) → what it did
// (Activity).
//
// Capabilities tab added 2026-05-14: surfaces /workspace/operation/specs/*.md as
// first-class operator content (the Claude Code skills.md analog). Specs
// were entirely backend-internal before — Reviewer read them; operator
// had to manually browse /files to know they existed.
//
// Activity tab also added 2026-05-14 after audit found FreddieActivityPanel
// was rendering significantly stale data inside the Autonomy tab. Splitting
// supervision (Activity) from delegation config (Autonomy) per the
// lens-sharpening discipline canonized in WORKSPACE.md.
//
// Track Record + Decisions link-outs deleted in earlier passes —
// calibration headline already surfaces on cockpit PerformanceFace
// (ADR-228); raw files remain accessible via /files.
// ---------------------------------------------------------------------------

// ADR-387 (2026-06-29): Freddie's pane absorbs the agent-scoped governance
// out of Workspace Settings. ADR-297 had DELETED Autonomy + Principles tabs
// (moving them to atomic surfaces, later consolidated into Workspace
// Settings); ADR-387 RE-AFFIRMS ADR-251's thesis — these are the AGENT's
// settings — now that ADR-381/383 makes "the agent" (Freddie) a concrete
// identity-backed entity. The flat tab bar becomes a grouped sidebar
// (SettingsPaneShell grammar) grouped by SUBSTRATE ROOT-OWNERSHIP so the
// surface teaches the lock model (ADR-341): PERSONA (persona/ — the agent's
// own) · GRANT (governance/ — the ceiling the operator sets, the agent runs
// under) · CONTRACT (contract/ — what the operator declares it owes) ·
// OPERATION (specs) · SUPERVISION (activity).
//
// A MOVE not a copy: these panes are simultaneously removed from
// workspace-settings PANE_GROUPS (Singular Implementation, the ADR-297
// invariant). The param stays `agents.tab` (ADR-358 D6) so every existing
// deep-link (?agent=freddie&agents.tab=identity|activity, and the dangling
// HomeHeader autonomy deep-link ADR-297 had broken) keeps working — the
// autonomy/principles keys now RESOLVE instead of falling through.
// Freddie's grouped pane list — the shared PaneGroup shape (Singular
// Implementation: the same shell behind the Settings doors renders this).
const FREDDIE_PANE_GROUPS: PaneGroup[] = [
  {
    label: 'Persona',
    panes: [
      { key: 'identity', label: 'Identity', icon: User },
      { key: 'principles', label: 'Principles', icon: Scale },
    ],
  },
  {
    label: 'Grant',
    panes: [
      { key: 'autonomy', label: 'Autonomy', icon: ShieldCheck },
      { key: 'budget', label: 'Budget', icon: Wallet },
    ],
  },
  {
    label: 'Contract',
    panes: [{ key: 'expected-output', label: 'Expected Output', icon: Crosshair }],
  },
  {
    label: 'Operation',
    panes: [{ key: 'capabilities', label: 'Capabilities', icon: FileCode }],
  },
  {
    label: 'Supervision',
    panes: [{ key: 'activity', label: 'Activity', icon: ActivityIcon }],
  },
];
// Exported (ADR-387 §6.4) so the agents page can auto-select Freddie when a
// pane_of-delivered `agents.pane` is one of these — the generic mechanism sets
// the pane param but not `agents.agent=freddie`, so the page infers it.
export const FREDDIE_PANE_KEYS = FREDDIE_PANE_GROUPS.flatMap((g) => g.panes.map((p) => p.key));

/** ADR-387 — render one Freddie pane body. The *Card full variants are the
 *  SAME components Workspace Settings used (they leave there; Singular
 *  Implementation). Identity + Capabilities + Activity keep their existing
 *  Freddie-surface renderers. */
function renderFreddiePane(pane: string) {
  switch (pane) {
    case 'identity':
      return (
        <SubstrateTab
          title="Identity"
          path="/workspace/persona/IDENTITY.md"
          tagline="Freddie's persona — who occupies the seat. Operator-authored; shapes how it reasons (stewardship, and judgment when an operation runs)."
          editPrompt="I want to evolve Freddie's identity and persona. Walk me through the current declaration."
          emptyBody={
            <p className="text-center text-xs">
              No identity declared yet. Author Freddie's persona to shape
              how it reasons — Simons, Buffett, or your own original.
            </p>
          }
        />
      );
    case 'principles':
      return <PrinciplesCard variant="full" />;
    case 'autonomy':
      return <AutonomyCard variant="full" />;
    case 'budget':
      return <BudgetCard variant="full" />;
    case 'expected-output':
      return <ExpectedOutputCard variant="full" />;
    case 'capabilities':
      return <FreddieCapabilitiesPanel />;
    case 'activity':
      return <FreddieActivityPanel />;
    default:
      return null;
  }
}

function ReviewerDetail({ agent }: { agent: Agent }) {
  // ADR-358 D6: the Reviewer's sub-pane is THIS window's own deep-link state,
  // read/written via useSurfaceParam (no pathname flip). ADR-387 §6.4
  // (2026-06-30): the param is `agents.pane` — the name the generic pane_of
  // mechanism delivers (the 5 governance panes are now pane_of: agents, so
  // foregroundSurface('autonomy') reconciles agents.pane=autonomy here). This
  // mirrors the channels surface precedent exactly (windowSlug.pane). The
  // legacy `agents.tab` form is read as a fallback (the shell resolves
  // `{windowSlug}.pane ?? {windowSlug}.tab`), so the autonomy/principles
  // deep-links still RESOLVE — fixing the dangling HomeHeader autonomy link.
  //
  // ADR-387 grouped sidebar — now mounts the shared SettingsPaneShell
  // (Singular Implementation, the 2026-06-30 unification: Freddie's forked
  // sidebar copy is deleted). The shell owns the responsive drill-in + the
  // `agents.pane=` URL sync; Freddie passes its identity bar as `header` and
  // wraps each pane body in the prior `max-w-3xl px-6 py-5` card column.
  return (
    <SettingsPaneShell
      windowSlug="agents"
      paneGroups={FREDDIE_PANE_GROUPS}
      defaultPane="identity"
      navLabel="Freddie panes"
      header={
        <SurfaceIdentityHeader
          title="Freddie"
          metadata={
            <span className="text-xs text-muted-foreground">
              The system agent — stewards your substrate; judges proposed actions when an operation runs
            </span>
          }
        />
      }
      renderPane={(pane) => (
        <div className="max-w-3xl px-6 py-5">{renderFreddiePane(pane)}</div>
      )}
    />
  );
}

export function AgentContentView({ agent, tasks }: Omit<AgentContentViewProps, 'onCreateTask'>) {
  const cls = agent.agent_class || 'specialist';

  // ADR-272: meta-cognitive branch deleted. The orchestration LLM identity
  // is no longer cockpit-visible; filtered out at /api/agents (routes/agents.py).
  // reviewer = Reviewer first-class surface (ADR-251 D4): Identity · Principles · Autonomy.
  if (cls === 'freddie') {
    return <ReviewerDetail agent={agent} />;
  }

  // After the reviewer early return, cls is narrowed to RegistryAgentClass
  // (specialist | domain-steward | synthesizer | platform-bot).
  const isPlatformBot = cls === 'platform-bot';

  return (
    <div className="flex-1 overflow-auto">
      <SurfaceIdentityHeader
        title={agent.title}
        metadata={<AgentMetadata agent={agent} tasks={tasks} />}
      />
      <div className="max-w-3xl">
        <AgentRoleBlock agent={agent} tasks={tasks} />

        {/* Tasks: lightweight "currently assigned to" list, links out to /work */}
        <TasksBlock agent={agent} tasks={tasks} />
        {!isPlatformBot && <SpecialistFolderBlock agent={agent} tasks={tasks} />}

        {/* LearnedBlock: feedback distillation (specialists/bots only).
            Reviewer returns earlier. ADR-272: meta-cognitive branch dissolved. */}
        <LearnedBlock agent={agent} />
      </div>
    </div>
  );
}
