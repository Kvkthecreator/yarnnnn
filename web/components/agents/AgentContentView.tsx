'use client';

/**
 * AgentContentView — Canonical agent detail surface content.
 *
 * Rendering model:
 * - agent_class decides the top-level shell/context block
 * - task.output_kind decides the assigned-work card shape
 * - task.type_key can lightly specialize labels without forking the page
 *
 * This mirrors WorkDetail's registry-driven approach instead of branching on
 * individual agent pages or legacy role names.
 */

import { useEffect } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import Link from 'next/link';
import {
  ArrowUpRight,
  ChevronRight,
  FolderKanban,
  Sparkles,
  Loader2,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { MarkdownRenderer } from '@/components/shared/MarkdownRenderer';
import { AgentIcon } from './AgentIcon';
import { PrinciplesTab } from './PrinciplesTab';
import { MandateTab } from './MandateTab';
import { AutonomyTab } from './AutonomyTab';
import { RevisionHistoryPanel } from '@/components/workspace/RevisionHistoryPanel';
import { SurfaceIdentityHeader } from '@/components/shell/SurfaceIdentityHeader';
import { formatRelativeTime } from '@/lib/formatting';
import { CONTEXT_ROUTE, WORK_ROUTE } from '@/lib/routes';
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
// returns Reviewer's data path through `/agents?agent=reviewer` only as a
// legacy URL — handled by the redirect-effect in AgentContentView.
type RegistryAgentClass = Exclude<AgentClass, 'reviewer'>;
type RecurrenceOutputKind = NonNullable<Recurrence['output_kind']>;

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



type TaskKindCounts = Record<RecurrenceOutputKind, number>;

const EMPTY_TASK_COUNTS: TaskKindCounts = {
  accumulates_context: 0,
  produces_deliverable: 0,
  external_action: 0,
  system_maintenance: 0,
};


const _SPECIALIST_SHELL: AgentShellDescriptor = {
  label: 'Role',
  title: (agent) => roleTagline(agent.role) || roleDisplayName(agent.role),
  description: (agent) => agentClassDescription(agent.agent_class),
  highlights: (_, counts) => {
    const highlights: string[] = [];
    if (counts.accumulates_context > 0) {
      highlights.push(`${counts.accumulates_context} tracking ${counts.accumulates_context === 1 ? 'task' : 'tasks'}`);
    }
    if (counts.produces_deliverable > 0) {
      highlights.push(`${counts.produces_deliverable} deliverable ${counts.produces_deliverable === 1 ? 'task' : 'tasks'}`);
    }
    return highlights;
  },
};

const AGENT_SHELL_REGISTRY: Record<RegistryAgentClass, AgentShellDescriptor> = {
  'specialist': _SPECIALIST_SHELL,
  'domain-steward': _SPECIALIST_SHELL, // backward compat — v4 DB rows
  synthesizer: {
    label: 'Role',
    title: () => 'Assembles cross-domain updates',
    description: () => 'Reads what each specialist has learned and turns it into a report, brief, or executive update.',
    highlights: (_, counts) => {
      const highlights: string[] = [];
      if (counts.produces_deliverable > 0) {
        highlights.push(`${counts.produces_deliverable} deliverable ${counts.produces_deliverable === 1 ? 'task' : 'tasks'}`);
      }
      if (counts.accumulates_context > 0) {
        highlights.push(`${counts.accumulates_context} tracking ${counts.accumulates_context === 1 ? 'input' : 'inputs'}`);
      }
      return highlights;
    },
  },
  'platform-bot': {
    label: 'Role',
    title: (agent) => {
      const platform = roleDisplayName(agent.role).replace(' Bot', '');
      return `Connects to ${platform} and watches selected sources`;
    },
    description: (agent) => {
      const platform = roleDisplayName(agent.role).replace(' Bot', '');
      return `Manages your ${platform} connection and source selection. Add a digest task to start pulling information in.`;
    },
    highlights: (_, counts) => {
      const highlights: string[] = [];
      if (counts.accumulates_context > 0) {
        highlights.push(`${counts.accumulates_context} observation ${counts.accumulates_context === 1 ? 'task' : 'tasks'}`);
      }
      if (counts.external_action > 0) {
        highlights.push(`${counts.external_action} write-back ${counts.external_action === 1 ? 'task' : 'tasks'}`);
      }
      return highlights;
    },
  },
  'meta-cognitive': {
    label: 'Role',
    title: () => 'Keeps the workforce running',
    description: () => 'Handles orchestration, shared state, and system-level upkeep so the rest of the team can focus on domain work.',
    highlights: () => [],
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
  'meta-cognitive': {
    title: () => 'No back-office work yet',
    description: () => 'Back-office recurrences materialize on trigger (first proposal, platform connect, agent-hygiene threshold).',
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
  'meta-cognitive': {
    bestFor: () => 'Coordinating the workforce, recurrence hygiene, and system-level upkeep.',
    does: () => [
      'Monitors recurrence health and freshness across the workspace',
      'Runs back-office maintenance recurrences and orchestrations',
      'Surfaces operational signals for decision-making',
    ],
    doesnt: () => [
      'Own any single domain as a content specialist',
      'Produce domain reports as primary output',
      'Replace specialist analysis on domain topics',
    ],
    examples: () => [
      'Which recurrences are stale or at risk right now?',
      'What maintenance work should run next to keep things healthy?',
      'Give me a short operational status of the workforce.',
    ],
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
  return tasks.reduce<TaskKindCounts>((counts, task) => {
    const kind = task.output_kind;
    if (kind && kind in counts) counts[kind as RecurrenceOutputKind] += 1;
    return counts;
  }, { ...EMPTY_TASK_COUNTS });
}

function normalizeCadenceLabel(schedule?: string | null): string {
  if (!schedule) return '';
  const raw = schedule.trim();
  if (!raw) return '';
  if (/^[a-z-]+$/i.test(raw)) return formatKeyLabel(raw);
  if (/^(\*|[\d\/,-]+)(\s+(\*|[\d\/,-]+)){4}$/.test(raw)) return 'Custom';
  return raw;
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
    if (cls === 'meta-cognitive') return 'Workspace state, task health, and orchestration signals';
    if (cls === 'synthesizer') return 'Production Role domain outputs';
    return agent.context_domain
      ? `${formatKeyLabel(agent.context_domain, false)} context folder`
      : 'Assigned context domain';
  })();

  const outputKindLabels: Record<string, string> = {
    accumulates_context: 'Context updates',
    produces_deliverable: 'Reports and briefs',
    external_action: 'Platform actions',
    system_maintenance: 'Operational signals',
  };
  const outputs = (() => {
    const kinds = Array.from(new Set(liveTasks.map((task) => task.output_kind).filter(Boolean)));
    if (kinds.length > 0) return kinds.map((kind) => outputKindLabels[kind as string] || formatKeyLabel(kind as string)).join(', ');
    if (cls === 'platform-bot') return 'Platform digest and action outputs';
    if (cls === 'meta-cognitive') return 'Workforce and maintenance status outputs';
    if (cls === 'synthesizer') return 'Cross-domain reports';
    return 'Domain tracking updates and briefs';
  })();

  const triggers = (() => {
    // ADR-231: trigger inference from RecurrenceShape + schedule presence,
    // since `mode` (recurring/goal/reactive) was dropped per migration 164.
    // Action shape → events; deliverable/accumulation with schedule → Schedule;
    // anything without schedule → On demand.
    const triggerSet = new Set<string>();
    if (cls === 'meta-cognitive') triggerSet.add('Chat');
    if (activeTasks.some((task) => task.shape === 'action')) triggerSet.add('Events');
    if (activeTasks.some((task) => task.schedule && task.shape !== 'action')) triggerSet.add('Schedule');
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
      <Link
        key="domain"
        href={`${CONTEXT_ROUTE}?domain=${domain}`}
        className="hover:text-foreground hover:underline"
      >
        {formatKeyLabel(domain)}
      </Link>,
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

  const activeTrackingTasks = tasks.filter((task) => task.status === 'active' && task.output_kind === 'accumulates_context');
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
              <Link
                href={`${CONTEXT_ROUTE}?domain=${agent.context_domain}`}
                className="inline-flex items-center gap-1 hover:text-foreground"
              >
                View folder
                <ArrowUpRight className="w-3 h-3" />
              </Link>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function platformManagementHref(provider: string | null): string {
  return '/settings?tab=connectors';
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
              <Link
                href={platformManagementHref(platformProvider)}
                className="inline-flex items-center gap-1 text-[12px] text-muted-foreground hover:text-foreground"
              >
                {platformManagementLabel(platformProvider, false)}
                <ArrowUpRight className="w-3 h-3" />
              </Link>
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
          const href = `${WORK_ROUTE}?task=${encodeURIComponent(task.slug)}&agent=${encodeURIComponent(agentSlug)}`;
          const isInactive = task.status !== 'active';
          return (
            <Link
              key={task.id}
              href={href}
              className={cn(
                'flex items-center justify-between gap-3 px-4 py-3 text-sm hover:bg-muted/40 transition-colors',
                isInactive && 'opacity-60',
              )}
            >
              <span className="font-medium truncate">{task.title}</span>
              <div className="flex items-center gap-2 shrink-0 text-[11px] text-muted-foreground">
                {task.schedule && <span className="capitalize">{task.schedule}</span>}
                {task.last_run_at && (
                  <>
                    {task.schedule && <span className="text-muted-foreground/30">·</span>}
                    <span>ran {formatRelativeTime(task.last_run_at)}</span>
                  </>
                )}
                <ArrowUpRight className="w-3 h-3 text-muted-foreground/40" />
              </div>
            </Link>
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


// ADR-241 D2: Thinking Partner detail view is tab-based (Identity /
// ADR-236 Round 5+ extension (2026-04-30): TP detail tabs reorganized
// to surface TP's substrate. The legacy Tasks tab was always-empty for
// TP (recurrences never assign agent_slugs=['thinking-partner']) — DELETED.
// Replaced with substrate-shaped tabs that show what TP actually reads
// + uses: Mandate (gate for task creation, ADR-207), Autonomy (delegation
// posture, ADR-217), Principles (judgment framework, ADR-194 v2).
// Identity stays as the cockpit role/agent overview.
//
// Tab is URL-driven via ?tab= so deep-links round-trip cleanly. Each
// substrate tab uses the shared <SubstrateTab> shell for visual
// consistency.
type TPTab = 'identity' | 'mandate' | 'autonomy' | 'principles';
const TP_TABS: ReadonlyArray<{ id: TPTab; label: string }> = [
  { id: 'identity', label: 'Identity' },
  { id: 'mandate', label: 'Mandate' },
  { id: 'autonomy', label: 'Autonomy' },
  { id: 'principles', label: 'Principles' },
];

function ThinkingPartnerDetail({ agent, tasks }: { agent: Agent; tasks: Recurrence[] }) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const tabParam = searchParams.get('tab');
  const activeTab: TPTab =
    tabParam === 'mandate' || tabParam === 'autonomy' || tabParam === 'principles'
      ? tabParam
      : 'identity';

  const setTab = (tab: TPTab) => {
    const params = new URLSearchParams(searchParams.toString());
    params.set('tab', tab);
    router.replace(`/agents?${params.toString()}`, { scroll: false });
  };

  return (
    <div className="flex-1 overflow-auto">
      <SurfaceIdentityHeader
        title={agent.title}
        metadata={<AgentMetadata agent={agent} tasks={tasks} />}
      />
      {/* Tab bar — minimal, URL-driven */}
      <div className="border-b border-border px-4">
        <div className="flex gap-1 max-w-3xl">
          {TP_TABS.map((t) => (
            <button
              key={t.id}
              type="button"
              onClick={() => setTab(t.id)}
              className={cn(
                'px-3 py-2 text-xs font-medium border-b-2 transition-colors -mb-px',
                activeTab === t.id
                  ? 'border-foreground text-foreground'
                  : 'border-transparent text-muted-foreground hover:text-foreground',
              )}
            >
              {t.label}
            </button>
          ))}
        </div>
      </div>

      <div className="max-w-3xl px-4 py-4">
        {activeTab === 'identity' && (
          <AgentRoleBlock agent={agent} tasks={tasks} />
        )}
        {activeTab === 'mandate' && <MandateTab />}
        {activeTab === 'autonomy' && <AutonomyTab />}
        {activeTab === 'principles' && <PrinciplesTab />}
      </div>
    </div>
  );
}

export function AgentContentView({ agent, tasks }: Omit<AgentContentViewProps, 'onCreateTask'>) {
  const router = useRouter();
  const cls = agent.agent_class || 'specialist';

  // ADR-241 D3 + R1: legacy `?agent=reviewer` deep-links redirect to
  // TP's Principles tab. Substrate (Reviewer's principles.md) is the
  // same; only the surface label changes. This preserves existing
  // breadcrumbs and ADR-cross-link integrity (ADR-194 v2 chain).
  useEffect(() => {
    if (cls === 'reviewer') {
      router.replace('/agents?agent=thinking-partner&tab=principles', { scroll: false });
    }
  }, [cls, router]);

  if (cls === 'reviewer') {
    return (
      <div className="flex items-center justify-center h-full">
        <Loader2 className="w-5 h-5 animate-spin text-muted-foreground" />
      </div>
    );
  }

  // ADR-241 D2 + ADR-236 Round 5+ (2026-04-30): meta-cognitive
  // (Thinking Partner) gets the tab-based detail view. Other classes
  // keep the single-page rendering — the tab refactor only applies
  // to TP because TP is the persona with multiple operator-facing
  // substrate axes (Identity / Mandate / Autonomy / Principles).
  // Tasks tab DELETED per ADR-236 Round 5+ — recurrences never assign
  // agent_slugs=['thinking-partner']; tab was always-empty.
  if (cls === 'meta-cognitive') {
    return <ThinkingPartnerDetail agent={agent} tasks={tasks} />;
  }

  // After the meta-cognitive + reviewer early returns, cls is narrowed to
  // RegistryAgentClass (specialist | domain-steward | synthesizer | platform-bot).
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
            TP's meta-cognitive branch returned earlier; reviewer also
            returned earlier. */}
        <LearnedBlock agent={agent} />
      </div>
    </div>
  );
}
