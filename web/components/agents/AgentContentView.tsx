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

import Link from 'next/link';
import { useEffect, useState } from 'react';
import {
  ArrowUpRight,
  ChevronRight,
  FileText,
  FolderKanban,
  Hash,
  Link2,
  Loader2,
  Sparkles,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { MarkdownRenderer } from '@/components/shared/MarkdownRenderer';
import { WorkModeBadge } from '@/components/work/WorkModeBadge';
import { AgentIcon } from './AgentIcon';
import { SurfaceIdentityHeader } from '@/components/shell/SurfaceIdentityHeader';
import { Button } from '@/components/ui/button';
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
import { api } from '@/lib/api/client';
import { usePlatformData } from '@/hooks/usePlatformData';
import { useSourceSelection } from '@/hooks/useSourceSelection';
import { ResourceList } from '@/components/context/ResourceList';
import type { Agent, Task, LandscapeResource, PlatformProvider } from '@/types';

interface AgentContentViewProps {
  agent: Agent;
  tasks: Task[];
  onCreateTask?: () => void;
}

type AgentClass = NonNullable<Agent['agent_class']>;
type TaskOutputKind = NonNullable<Task['output_kind']>;

interface AgentShellDescriptor {
  label: string;
  title: (agent: Agent) => string;
  description: (agent: Agent) => string;
  highlights: (agent: Agent, counts: TaskKindCounts) => string[];
}

interface TaskCardDescriptor {
  label: string;
  badgeClass: string;
  summary: (task: Task) => string;
  details: (task: Task) => string[];
}

interface AgentEmptyStateDescriptor {
  title: (agent: Agent) => string;
  description: (agent: Agent) => string;
}

interface PlatformSummary {
  provider: string;
  status: string;
  workspace_name: string | null;
  connected_at: string;
  resource_count: number;
  resource_type: string;
  agent_count: number;
  activity_7d: number;
}

type TaskKindCounts = Record<TaskOutputKind, number>;

const EMPTY_TASK_COUNTS: TaskKindCounts = {
  accumulates_context: 0,
  produces_deliverable: 0,
  external_action: 0,
  system_maintenance: 0,
};

const TASK_TYPE_LABELS: Record<string, string> = {
  'track-competitors': 'Competitor tracker',
  'track-market': 'Market tracker',
  'track-relationships': 'Relationship tracker',
  'track-projects': 'Project tracker',
  'research-topics': 'Topic research',
  'slack-digest': 'Slack digest',
  'notion-digest': 'Notion digest',
  'github-digest': 'GitHub digest',
  'daily-update': 'Daily update',
  'competitive-intel-brief': 'Competitive brief',
  'market-report': 'Market report',
  'relationship-health-digest': 'Relationship digest',
  'stakeholder-update': 'Stakeholder update',
  'project-status-report': 'Project status report',
  'meeting-prep': 'Meeting prep',
  'slack-respond': 'Slack response',
  'notion-update': 'Notion update',
  'back-office-agent-hygiene': 'Agent hygiene',
  'back-office-workspace-cleanup': 'Workspace cleanup',
};

const AGENT_SHELL_REGISTRY: Record<AgentClass, AgentShellDescriptor> = {
  'domain-steward': {
    label: 'Role',
    title: (agent) => (
      agent.context_domain
        ? `Tracks ${formatKeyLabel(agent.context_domain, false)}`
        : roleDisplayName(agent.role)
    ),
    description: (agent) => (
      agent.context_domain
        ? `Builds up what we know about ${formatKeyLabel(agent.context_domain, false)} and turns that into reports and briefs.`
        : roleTagline(agent.role) || agentClassDescription(agent.agent_class)
    ),
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
  },
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

const AGENT_EMPTY_STATE_REGISTRY: Record<AgentClass, AgentEmptyStateDescriptor> = {
  'domain-steward': {
    title: () => 'No work assigned yet',
    description: (agent) => (
      agent.context_domain
        ? `Ask your thinking partner to set up a tracker for ${formatKeyLabel(agent.context_domain, false)}.`
        : 'Ask your thinking partner to set up a recurring tracker for this agent.'
    ),
  },
  synthesizer: {
    title: () => 'No work assigned yet',
    description: () => 'Ask your thinking partner to create a reporting task once the specialists have trackers running.',
  },
  'platform-bot': {
    title: () => 'Not watching anything yet',
    description: (agent) => {
      const platform = roleDisplayName(agent.role).replace(' Bot', '');
      return `Connect ${platform} above and select sources, then ask TP to set up a digest task.`;
    },
  },
  'meta-cognitive': {
    title: () => 'No maintenance tasks yet',
    description: () => 'Ask your thinking partner to set up the core workspace maintenance tasks.',
  },
};

const TASK_CARD_REGISTRY: Record<TaskOutputKind, TaskCardDescriptor> = {
  accumulates_context: {
    label: 'Tracking',
    badgeClass: 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-300',
    summary: (task) => trackingTaskSummary(task),
    details: (task) => [
      ...taskFolderDetails(task),
      ...(task.objective?.purpose ? [task.objective.purpose] : []),
    ].filter(Boolean),
  },
  produces_deliverable: {
    label: 'Deliverable',
    badgeClass: 'bg-violet-500/10 text-violet-700 dark:text-violet-300',
    summary: (task) => (
      task.objective?.deliverable ||
      task.objective?.format ||
      'Produces a user-facing deliverable'
    ),
    details: (task) => [
      ...taskFolderDetails(task),
      ...(task.objective?.audience ? [`Audience: ${task.objective.audience}`] : []),
      ...(task.objective?.purpose ? [task.objective.purpose] : []),
      ...(task.delivery ? [`Delivery: ${task.delivery}`] : []),
    ].filter(Boolean),
  },
  external_action: {
    label: 'Action',
    badgeClass: 'bg-blue-500/10 text-blue-700 dark:text-blue-300',
    summary: (task) => (
      task.objective?.deliverable ||
      task.delivery ||
      inferActionTarget(task) ||
      'Takes action on an external platform'
    ),
    details: (task) => [
      ...taskFolderDetails(task),
      ...(task.objective?.purpose ? [task.objective.purpose] : []),
      ...(inferActionTarget(task) ? [`Target: ${inferActionTarget(task)}`] : []),
    ].filter(Boolean),
  },
  system_maintenance: {
    label: 'Maintenance',
    badgeClass: 'bg-amber-500/10 text-amber-700 dark:text-amber-300',
    summary: (task) => task.objective?.purpose || 'Keeps the workspace and workforce coherent',
    details: (task) => [
      ...taskFolderDetails(task),
      ...(task.essential ? ['Essential anchor task'] : []),
      ...(task.objective?.deliverable ? [`Output: ${task.objective.deliverable}`] : []),
    ].filter(Boolean),
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
    <h3 className="text-[10px] uppercase tracking-wide text-muted-foreground/40 mb-2">
      {children}
    </h3>
  );
}

function readableDomainSummary(domains: string[] | undefined, fallback: string): string {
  if (!domains || domains.length === 0) return fallback;
  return domains.map((domain) => formatKeyLabel(domain, false)).join(', ');
}

function taskTypeLabel(typeKey?: string | null): string | null {
  if (!typeKey) return null;
  return TASK_TYPE_LABELS[typeKey] || typeKey.replace(/-/g, ' ');
}

function formatKeyLabel(value?: string | null, capitalize = true): string {
  if (!value) return '';
  const formatted = value.replace(/[_-]+/g, ' ').replace(/\s+/g, ' ').trim();
  if (!formatted) return '';
  return capitalize ? formatted.charAt(0).toUpperCase() + formatted.slice(1) : formatted;
}

function inferActionTarget(task: Task): string | null {
  if (task.type_key?.startsWith('slack-')) return 'Slack';
  if (task.type_key?.startsWith('notion-')) return 'Notion';
  return task.delivery || null;
}

function trackingTaskSummary(task: Task): string {
  if (task.context_writes?.length) {
    return `Working in ${readableDomainSummary(task.context_writes, 'this folder')}`;
  }
  if (task.context_reads?.length) {
    return `Working from ${readableDomainSummary(task.context_reads, 'this folder')}`;
  }
  return 'Maintains context';
}

function taskFolderDetails(task: Task): string[] {
  const details: string[] = [];
  const writes = task.context_writes || [];
  const reads = task.context_reads || [];

  if (task.output_kind === 'accumulates_context' && writes.length > 0) {
    details.push(`Working in folder: ${readableDomainSummary(writes, '')}`);
  } else if (task.output_kind === 'produces_deliverable' && reads.length > 0) {
    details.push(`Reads from folder: ${readableDomainSummary(reads, '')}`);
  } else if (reads.length > 0) {
    details.push(`Uses folder: ${readableDomainSummary(reads, '')}`);
  }

  if (writes.length > 0 && task.output_kind !== 'accumulates_context') {
    details.push(`Writes to folder: ${readableDomainSummary(writes, '')}`);
  }

  return details;
}

function getTaskKindCounts(tasks: Task[]): TaskKindCounts {
  return tasks.reduce<TaskKindCounts>((counts, task) => {
    const kind = task.output_kind;
    if (kind && kind in counts) counts[kind as TaskOutputKind] += 1;
    return counts;
  }, { ...EMPTY_TASK_COUNTS });
}

function AgentMetadata({ agent, tasks }: { agent: Agent; tasks: Task[] }) {
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

function AgentRoleBlock({ agent, tasks }: { agent: Agent; tasks: Task[] }) {
  const descriptor = AGENT_SHELL_REGISTRY[(agent.agent_class || 'domain-steward') as AgentClass];
  const counts = getTaskKindCounts(tasks);
  const highlights = descriptor.highlights(agent, counts);
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
            <p className="text-sm text-muted-foreground mt-1">
              {descriptor.description(agent)}
            </p>
            {highlights.length > 0 && (
              <div className="flex flex-wrap gap-2 mt-2">
                {highlights.map((highlight) => (
                  <span
                    key={highlight}
                    className="inline-flex items-center rounded-full bg-background px-2 py-1 text-[11px] text-muted-foreground border border-border/50"
                  >
                    {highlight}
                  </span>
                ))}
              </div>
            )}
            {instructions && (
              <div className="mt-4 pt-4 border-t border-border/50">
                <p className="text-[11px] uppercase tracking-wide text-muted-foreground/50 mb-2">
                  How I work
                </p>
                <div className="prose prose-sm max-w-none dark:prose-invert text-sm">
                  <MarkdownRenderer content={instructions} />
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function SpecialistFolderBlock({ agent, tasks }: { agent: Agent; tasks: Task[] }) {
  if (agent.agent_class !== 'domain-steward' || !agent.context_domain) return null;

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

function renderSlackMetadata(resource: LandscapeResource) {
  const memberCount =
    (resource.metadata?.member_count as number | undefined)
    ?? (resource.metadata?.num_members as number | undefined);
  if (memberCount === undefined && !resource.last_extracted_at && resource.items_extracted === 0) return null;

  return (
    <div className="text-xs text-muted-foreground">
      {memberCount !== undefined && <span>{memberCount.toLocaleString()} members</span>}
      {memberCount !== undefined && (resource.items_extracted > 0 || !!resource.last_extracted_at) && <span> • </span>}
      {(resource.items_extracted > 0 || !!resource.last_extracted_at) && (
        <span>
          {resource.items_extracted > 0 ? `${resource.items_extracted} items` : '0 new items'}
        </span>
      )}
    </div>
  );
}

function renderNotionMetadata(resource: LandscapeResource) {
  const parentType = resource.metadata?.parent_type as string | undefined;
  if (!parentType && resource.items_extracted === 0 && !resource.last_extracted_at) return null;

  return (
    <div className="text-xs text-muted-foreground">
      {parentType && (
        <span>
          {parentType === 'workspace' && 'Top-level page'}
          {parentType === 'page' && 'Nested page'}
          {parentType === 'database' && 'Database item'}
        </span>
      )}
      {parentType && (resource.items_extracted > 0 || !!resource.last_extracted_at) && <span> • </span>}
      {(resource.items_extracted > 0 || !!resource.last_extracted_at) && (
        <span>
          {resource.items_extracted > 0 ? `${resource.items_extracted} items` : '0 new items'}
        </span>
      )}
    </div>
  );
}

function platformSourceConfig(provider: PlatformProvider): {
  resourceLabel: string;
  resourceLabelSingular: string;
  resourceIcon: React.ReactNode;
  renderMetadata?: (resource: LandscapeResource) => React.ReactNode;
} | null {
  switch (provider) {
    case 'slack':
      return {
        resourceLabel: 'Channels',
        resourceLabelSingular: 'channel',
        resourceIcon: <Hash className="w-4 h-4" />,
        renderMetadata: renderSlackMetadata,
      };
    case 'notion':
      return {
        resourceLabel: 'Pages',
        resourceLabelSingular: 'page',
        resourceIcon: <FileText className="w-4 h-4" />,
        renderMetadata: renderNotionMetadata,
      };
    default:
      return null;
  }
}

function PlatformConnectionBlock({ agent }: { agent: Agent }) {
  const provider = platformProviderForRole(agent.role);
  const [summary, setSummary] = useState<PlatformSummary | null>(null);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      if (!provider) {
        setLoaded(true);
        return;
      }
      try {
        const result = await api.integrations.getSummary();
        const match = (result.platforms || []).find((platform) => platform.provider === provider) || null;
        if (!cancelled) setSummary(match);
      } catch {
        if (!cancelled) setSummary(null);
      } finally {
        if (!cancelled) setLoaded(true);
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, [provider]);

  if (!provider) return null;

  const connected = summary?.status === 'active';
  const manageHref = platformManagementHref(provider);
  const platformName = roleDisplayName(agent.role).replace(' Bot', '');

  return (
    <div className="px-6 py-5 border-t border-border/40">
      <SectionLabel>Connection</SectionLabel>
      <div className="rounded-lg border border-border/60 bg-background px-4 py-4">
        <div className="flex items-start gap-3">
          <div className="w-9 h-9 rounded-lg bg-muted/30 border border-border/60 flex items-center justify-center shrink-0">
            <Link2 className="w-4 h-4 text-muted-foreground" />
          </div>
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2 flex-wrap">
              <h4 className="text-sm font-medium text-foreground">{platformName} connection</h4>
              {loaded && (
                <span
                  className={cn(
                    'inline-flex rounded-full px-1.5 py-0.5 text-[10px] font-medium',
                    connected
                      ? 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-300'
                      : 'bg-amber-500/10 text-amber-700 dark:text-amber-300',
                  )}
                >
                  {connected ? 'connected' : 'not connected'}
                </span>
              )}
            </div>
            <p className="text-sm text-muted-foreground mt-1">
              {!loaded
                ? 'Checking current connection status.'
                : connected
                  ? summary?.workspace_name
                    ? `Connected to ${summary.workspace_name}. Choose sources here, then add the task that should watch or act on this platform.`
                    : 'Connected. Choose sources here, then add the task that should watch or act on this platform.'
                  : 'Not connected yet. Connect it in Settings > Connectors before assigning platform work.'}
            </p>
            <div className="flex flex-wrap gap-2 mt-3">
              <Link
                href={manageHref}
                className="inline-flex items-center gap-1 rounded-md border border-border/60 bg-muted/10 px-2.5 py-1.5 text-[12px] text-muted-foreground hover:text-foreground hover:bg-muted/20"
              >
                {platformManagementLabel(provider, connected)}
                <ArrowUpRight className="w-3 h-3" />
              </Link>
              {manageHref !== '/settings?tab=connectors' && (
                <Link
                  href="/settings?tab=connectors"
                  className="inline-flex items-center gap-1 rounded-md border border-border/60 bg-muted/10 px-2.5 py-1.5 text-[12px] text-muted-foreground hover:text-foreground hover:bg-muted/20"
                >
                  Connectors settings
                  <ArrowUpRight className="w-3 h-3" />
                </Link>
              )}
            </div>
            {loaded && (
              <div className="flex flex-wrap gap-2 mt-3">
                {connected && summary?.resource_count != null && (
                  <span className="inline-flex rounded-full bg-muted px-2 py-1 text-[11px] text-muted-foreground">
                    {summary.resource_count} selected {summary.resource_type || 'resources'}
                  </span>
                )}
                {connected && summary?.activity_7d != null && (
                  <span className="inline-flex rounded-full bg-muted px-2 py-1 text-[11px] text-muted-foreground">
                    {summary.activity_7d} events in the last 7d
                  </span>
                )}
                {!connected && (
                  <span className="inline-flex rounded-full bg-muted px-2 py-1 text-[11px] text-muted-foreground">
                    No platform connection detected
                  </span>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function PlatformSourcesBlock({ agent }: { agent: Agent }) {
  const provider = platformProviderForRole(agent.role) as PlatformProvider | null;
  const config = provider ? platformSourceConfig(provider) : null;
  const data = usePlatformData(provider || 'slack', { skipResources: !config });
  const sourceSelection = useSourceSelection({
    platform: provider || 'slack',
    resources: data.resources,
    selectedIds: data.selectedIds,
    originalIds: data.originalIds,
    setSelectedIds: data.setSelectedIds,
    setOriginalIds: data.setOriginalIds,
    reload: data.reload,
  });

  if (!provider || !config) return null;

  if (data.loading) {
    return (
      <div className="px-6 py-5 border-t border-border/40">
        <SectionLabel>Source selection</SectionLabel>
        <div className="rounded-lg border border-border/60 bg-background px-4 py-6 flex items-center gap-3 text-sm text-muted-foreground">
          <Loader2 className="w-4 h-4 animate-spin" />
          Loading available sources...
        </div>
      </div>
    );
  }

  if (!data.integration) return null;

  return (
    <div className="px-6 py-5 border-t border-border/40">
      <SectionLabel>Source selection</SectionLabel>
      <p className="text-sm text-muted-foreground mb-3 px-1">
        Choose which {config.resourceLabel.toLowerCase()} should feed this bot. This is the canonical management surface for platform-source selection.
      </p>
      <ResourceList
        resourceLabel={config.resourceLabel}
        resourceLabelSingular={config.resourceLabelSingular}
        resourceIcon={config.resourceIcon}
        workspaceName={data.integration.workspace_name}
        resources={data.resources}
        tierLimits={data.tierLimits}
        selectedIds={data.selectedIds}
        hasChanges={sourceSelection.hasChanges}
        atLimit={sourceSelection.atLimit}
        limit={sourceSelection.limit}
        saving={sourceSelection.saving}
        error={sourceSelection.error || data.error}
        onToggle={sourceSelection.handleToggle}
        onSave={sourceSelection.handleSave}
        onDiscard={sourceSelection.handleDiscard}
        renderMetadata={config.renderMetadata}
        platformLabel={roleDisplayName(agent.role).replace(' Bot', '')}
      />
    </div>
  );
}

function TaskCard({ task, agentSlug }: { task: Task; agentSlug: string }) {
  const descriptor = TASK_CARD_REGISTRY[task.output_kind as TaskOutputKind] || TASK_CARD_REGISTRY.produces_deliverable;
  const typeLabel = taskTypeLabel(task.type_key);
  const details = descriptor.details(task);
  const manageHref = `${WORK_ROUTE}?task=${encodeURIComponent(task.slug)}&agent=${encodeURIComponent(agentSlug)}`;

  return (
    <div
      className={cn(
        'rounded-lg border border-border/40 bg-background px-3 py-3',
        task.status !== 'active' && 'opacity-70',
      )}
    >
      <div className="flex items-center gap-2 flex-wrap">
        <span className={cn('inline-flex rounded-full px-1.5 py-0.5 text-[10px] font-medium', descriptor.badgeClass)}>
          {descriptor.label}
        </span>
        {typeLabel && (
          <span className="inline-flex rounded-full bg-muted px-1.5 py-0.5 text-[10px] text-muted-foreground">
            {typeLabel}
          </span>
        )}
        <WorkModeBadge mode={task.mode} />
        {task.essential && (
          <span className="inline-flex rounded-full bg-amber-500/10 px-1.5 py-0.5 text-[10px] text-amber-700">
            essential
          </span>
        )}
        {task.status === 'paused' && (
          <span className="inline-flex rounded-full bg-amber-500/10 px-1.5 py-0.5 text-[10px] text-amber-700">
            paused
          </span>
        )}
      </div>

      <div className="flex items-start justify-between gap-3 mt-2">
        <div className="flex-1 min-w-0">
          <span className="text-sm font-medium">{task.title}</span>
          <p className="text-[12px] text-muted-foreground mt-0.5">
            {descriptor.summary(task)}
          </p>
          <div className="flex items-center gap-2 mt-1.5 text-[11px] text-muted-foreground flex-wrap">
            {task.schedule && <span className="truncate">{task.schedule}</span>}
            {task.schedule && task.last_run_at && <span className="text-muted-foreground/30">·</span>}
            {task.last_run_at && <span>Ran {formatRelativeTime(task.last_run_at)}</span>}
            {!task.last_run_at && !task.schedule && <span>Never run</span>}
          </div>
          {details.length > 0 && (
            <div className="flex flex-wrap gap-1.5 mt-2">
              {details.map((detail) => (
                <span
                  key={detail}
                  className="inline-flex rounded-md border border-border/50 bg-muted/10 px-2 py-1 text-[11px] text-muted-foreground"
                >
                  {detail}
                </span>
              ))}
            </div>
          )}
        </div>
        <Link
          href={manageHref}
          className="shrink-0 inline-flex items-center gap-1 rounded-md border border-border/60 bg-muted/10 px-2.5 py-1.5 text-[12px] text-muted-foreground hover:text-foreground hover:bg-muted/20 transition-colors"
        >
          Manage
          <ArrowUpRight className="w-3 h-3" />
        </Link>
      </div>
    </div>
  );
}

function EmptyAssignedWork({ agent, onCreateTask }: { agent: Agent; onCreateTask?: () => void }) {
  const descriptor = AGENT_EMPTY_STATE_REGISTRY[(agent.agent_class || 'domain-steward') as AgentClass];
  const platformProvider = agent.agent_class === 'platform-bot' ? platformProviderForRole(agent.role) : null;
  const managementHref = platformManagementHref(platformProvider);

  return (
    <div className="rounded-lg border border-dashed border-border/60 bg-muted/10 px-4 py-4">
      <h4 className="text-sm font-medium text-foreground">{descriptor.title(agent)}</h4>
      <p className="text-sm text-muted-foreground mt-1">
        {descriptor.description(agent)}
      </p>
      <div className="mt-4 flex flex-wrap items-center gap-2">
        {platformProvider && (
          <Link
            href={managementHref}
            className="inline-flex items-center gap-1 rounded-md border border-border/60 bg-muted/10 px-2.5 py-1.5 text-[12px] text-muted-foreground hover:text-foreground hover:bg-muted/20 transition-colors"
          >
            {platformManagementLabel(platformProvider, false)}
            <ArrowUpRight className="w-3 h-3" />
          </Link>
        )}
        {onCreateTask && (
          <button
            type="button"
            onClick={onCreateTask}
            className="inline-flex items-center gap-1 rounded-md border border-border/60 bg-muted/10 px-2.5 py-1.5 text-[12px] text-muted-foreground hover:text-foreground hover:bg-muted/20 transition-colors"
          >
            Ask TP to set this up
            <ArrowUpRight className="w-3 h-3" />
          </button>
        )}
      </div>
    </div>
  );
}

function TasksBlock({ agent, tasks, onCreateTask }: { agent: Agent; tasks: Task[]; onCreateTask?: () => void }) {
  const agentSlug = getAgentSlug(agent);

  if (tasks.length === 0) {
    return (
      <div className="px-6 py-5 border-t border-border/40">
        <SectionLabel>Work</SectionLabel>
        <EmptyAssignedWork agent={agent} onCreateTask={onCreateTask} />
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
      <div className="space-y-2">
        {sorted.map((task) => (
          <TaskCard key={task.id} task={task} agentSlug={agentSlug} />
        ))}
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


export function AgentContentView({ agent, tasks, onCreateTask }: AgentContentViewProps) {
  const cls = agent.agent_class || 'domain-steward';
  const isPlatformBot = cls === 'platform-bot';
  const isMetaCognitive = cls === 'meta-cognitive';

  return (
    <div className="flex-1 overflow-auto">
      <SurfaceIdentityHeader
        title={agent.title}
        metadata={<AgentMetadata agent={agent} tasks={tasks} />}
        actions={!isMetaCognitive && onCreateTask ? (
          <Button size="sm" onClick={onCreateTask}>
            Create Task
          </Button>
        ) : undefined}
      />
      <div className="max-w-3xl">
        <AgentRoleBlock agent={agent} tasks={tasks} />

        {/* Platform bots: connection + sources come before tasks (you need to connect first) */}
        {isPlatformBot && <PlatformConnectionBlock agent={agent} />}
        {isPlatformBot && <PlatformSourcesBlock agent={agent} />}

        {/* Domain-stewards: tasks first, then folder (work is the point; folder is where it lives) */}
        <TasksBlock agent={agent} tasks={tasks} onCreateTask={onCreateTask} />
        {!isPlatformBot && <SpecialistFolderBlock agent={agent} tasks={tasks} />}

        {/* TP doesn't have feedback distillation — suppress for meta-cognitive */}
        {!isMetaCognitive && <LearnedBlock agent={agent} />}
      </div>
    </div>
  );
}
