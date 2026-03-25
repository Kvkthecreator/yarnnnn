'use client';

/**
 * Workfloor — ADR-139 v2 (revised): Agent-First, Chat-as-Drawer
 *
 * Left: Agent roster (living office — 2×3 grid with liveness) + quick stats
 * Right: Tabbed panel (Tasks | Context | Platforms) — fully rendered, even empty states
 * Chat: Drawer (FAB + ⌘K)
 *
 * Outputs are task-specific (on /tasks/[slug]), not on workfloor.
 * Panels are resizable via WorkspaceLayout.
 */

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import { HOME_ROUTE } from '@/lib/routes';
import {
  Loader2,
  FileText,
  FlaskConical,
  Eye,
  PenTool,
  Cog,
  TrendingUp,
  Users,
  MessageCircle,
  BookOpen,
  X,
  FolderOpen,
  Link2,
  ListChecks,
  ChevronRight,
  Clock,
} from 'lucide-react';
import { useTP } from '@/contexts/TPContext';
import type { Agent, Task } from '@/types';
import { cn } from '@/lib/utils';
import { api } from '@/lib/api/client';
import { WorkspaceLayout, type WorkspacePanelTab } from '@/components/desk/WorkspaceLayout';
import { ChatDrawer } from '@/components/desk/ChatDrawer';
import ReactMarkdown from 'react-markdown';

// =============================================================================
// Agent type config (ADR-140)
// =============================================================================

const TYPE_CONFIG: Record<string, { icon: typeof FlaskConical; color: string; bg: string; border: string; short: string }> = {
  research:   { icon: FlaskConical,  color: 'text-blue-500',   bg: 'bg-blue-500/8',   border: 'border-blue-500/20',   short: 'Research' },
  content:    { icon: FileText,      color: 'text-purple-500', bg: 'bg-purple-500/8', border: 'border-purple-500/20', short: 'Content' },
  marketing:  { icon: TrendingUp,    color: 'text-pink-500',   bg: 'bg-pink-500/8',   border: 'border-pink-500/20',   short: 'Marketing' },
  crm:        { icon: Users,         color: 'text-orange-500', bg: 'bg-orange-500/8', border: 'border-orange-500/20', short: 'CRM' },
  slack_bot:  { icon: MessageCircle, color: 'text-teal-500',   bg: 'bg-teal-500/8',   border: 'border-teal-500/20',   short: 'Slack' },
  notion_bot: { icon: BookOpen,      color: 'text-indigo-500', bg: 'bg-indigo-500/8', border: 'border-indigo-500/20', short: 'Notion' },
  // Legacy
  briefer:    { icon: FlaskConical,  color: 'text-blue-500',   bg: 'bg-blue-500/8',   border: 'border-blue-500/20',   short: 'Research' },
  monitor:    { icon: Eye,           color: 'text-green-500',  bg: 'bg-green-500/8',  border: 'border-green-500/20',  short: 'Monitor' },
  researcher: { icon: FlaskConical,  color: 'text-blue-500',   bg: 'bg-blue-500/8',   border: 'border-blue-500/20',   short: 'Research' },
  analyst:    { icon: FlaskConical,  color: 'text-blue-500',   bg: 'bg-blue-500/8',   border: 'border-blue-500/20',   short: 'Research' },
  drafter:    { icon: FileText,      color: 'text-purple-500', bg: 'bg-purple-500/8', border: 'border-purple-500/20', short: 'Content' },
  writer:     { icon: FileText,      color: 'text-purple-500', bg: 'bg-purple-500/8', border: 'border-purple-500/20', short: 'Content' },
  custom:     { icon: Cog,           color: 'text-gray-500',   bg: 'bg-gray-500/8',   border: 'border-gray-500/20',   short: 'Custom' },
};

function getType(role: string) {
  return TYPE_CONFIG[role] || TYPE_CONFIG.custom;
}

function formatRelativeTime(dateStr: string): string {
  const now = Date.now();
  const then = new Date(dateStr).getTime();
  const diff = now - then;
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

// =============================================================================
// Agent Desk Card (roster grid)
// =============================================================================

function AgentDeskCard({ agent }: { agent: Agent }) {
  const config = getType(agent.role);
  const Icon = config.icon;
  const isRunning = agent.latest_version_status === 'generating';
  const isPaused = agent.status === 'paused';
  const hasFailed = agent.latest_version_status === 'failed';
  const dotColor = isRunning ? 'bg-blue-500 animate-pulse' : isPaused ? 'bg-gray-400' : hasFailed ? 'bg-red-500' : 'bg-green-500';

  return (
    <Link
      href={`/agents/${agent.id}`}
      className={cn(
        'flex flex-col items-center justify-center p-4 rounded-xl border transition-all hover:shadow-md',
        config.border, config.bg,
      )}
    >
      <div className="relative mb-2">
        <div className={cn('w-10 h-10 rounded-lg flex items-center justify-center border bg-background', config.border)}>
          <Icon className={cn('w-5 h-5', config.color)} />
        </div>
        <span className={cn('absolute -top-0.5 -right-0.5 w-2.5 h-2.5 rounded-full border-2 border-background', dotColor)} />
      </div>
      <span className="text-xs font-medium text-center">{agent.title}</span>
      <span className="text-[10px] text-muted-foreground mt-0.5">{config.short}</span>
      <span className="text-[9px] text-muted-foreground/50 mt-1">
        {isRunning ? 'working...' : agent.last_run_at ? formatRelativeTime(agent.last_run_at) : 'idle'}
      </span>
    </Link>
  );
}

// =============================================================================
// Right Panel: Tasks Tab
// =============================================================================

function TasksTab({ tasks }: { tasks: Task[] }) {
  const active = tasks.filter(t => t.status !== 'archived');

  return (
    <div className="p-3 space-y-2">
      <p className="text-[10px] text-muted-foreground/50 uppercase tracking-wider">
        /tasks/ — {active.length} task{active.length !== 1 ? 's' : ''}
      </p>
      {active.length > 0 ? (
        <div className="space-y-1">
          {active.map(task => (
            <Link
              key={task.id}
              href={`/tasks/${task.slug}`}
              className="flex items-center justify-between px-3 py-2.5 rounded-lg border border-border hover:bg-muted/50 transition-colors"
            >
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <span className={cn('w-1.5 h-1.5 rounded-full shrink-0', task.status === 'active' ? 'bg-green-500' : 'bg-amber-500')} />
                  <span className="text-sm truncate">{task.title}</span>
                </div>
                <div className="flex items-center gap-3 ml-[14px] mt-0.5 text-[10px] text-muted-foreground/60">
                  {task.schedule && <span>{task.schedule}</span>}
                  {task.last_run_at && <span>{formatRelativeTime(task.last_run_at)}</span>}
                  {task.agent_slugs?.[0] && <span>{task.agent_slugs[0]}</span>}
                </div>
              </div>
              <ChevronRight className="w-3.5 h-3.5 text-muted-foreground/30 shrink-0" />
            </Link>
          ))}
        </div>
      ) : (
        <div className="py-6 text-center border border-dashed border-border/50 rounded-lg">
          <ListChecks className="w-6 h-6 text-muted-foreground/15 mx-auto mb-2" />
          <p className="text-xs text-muted-foreground/50">No tasks yet</p>
          <p className="text-[10px] text-muted-foreground/30 mt-0.5">Press ⌘K → &ldquo;create a task&rdquo;</p>
        </div>
      )}
    </div>
  );
}

// =============================================================================
// Right Panel: Context Tab
// =============================================================================

function ContextTab() {
  const [identity, setIdentity] = useState<Record<string, string> | null>(null);
  const [brand, setBrand] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      api.profile.get().catch(() => null),
      api.brand.get().catch(() => ({ content: null, exists: false })),
    ]).then(([profile, brandData]) => {
      setIdentity(profile);
      if (brandData?.exists) setBrand(brandData.content);
      setLoading(false);
    });
  }, []);

  if (loading) return <div className="flex items-center justify-center p-6"><Loader2 className="w-4 h-4 animate-spin text-muted-foreground" /></div>;

  const files = [
    { name: 'IDENTITY.md', content: identity?.name ? `${identity.name}${identity.role ? ` — ${identity.role}` : ''}${identity.company ? ` at ${identity.company}` : ''}` : null },
    { name: 'BRAND.md', content: brand },
    { name: 'CONTEXT.md', content: null },
    { name: 'preferences.md', content: null },
    { name: 'notes.md', content: null },
  ];

  return (
    <div className="p-3 space-y-2">
      <p className="text-[10px] text-muted-foreground/50 uppercase tracking-wider">/workspace/ — identity &amp; preferences</p>
      <div className="space-y-1.5">
        {files.map(f => (
          <div
            key={f.name}
            className={cn(
              'px-3 py-2 rounded-lg border text-xs',
              f.content ? 'border-border bg-background' : 'border-dashed border-border/40'
            )}
          >
            <span className={cn('font-medium', f.content ? '' : 'text-muted-foreground/40')}>{f.name}</span>
            {f.content ? (
              <p className="text-muted-foreground truncate mt-0.5">{f.content}</p>
            ) : (
              <p className="text-muted-foreground/25 mt-0.5">Empty</p>
            )}
          </div>
        ))}
      </div>

      {/* Knowledge */}
      <div className="mt-3">
        <p className="text-[10px] text-muted-foreground/50 uppercase tracking-wider mb-1.5">/knowledge/</p>
        <Link href="/context" className="block px-3 py-2 rounded-lg border border-dashed border-border/40 text-xs text-muted-foreground/40 hover:bg-muted/30 transition-colors">
          Browse knowledge base →
        </Link>
      </div>
    </div>
  );
}

// =============================================================================
// Right Panel: Platforms Tab
// =============================================================================

function PlatformsTab() {
  const [platforms, setPlatforms] = useState<Array<{ provider: string; status: string; workspace_name: string | null; resource_count: number }>>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.integrations.getSummary()
      .then(res => setPlatforms(res.platforms))
      .catch(() => [])
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="flex items-center justify-center p-6"><Loader2 className="w-4 h-4 animate-spin text-muted-foreground" /></div>;

  return (
    <div className="p-3 space-y-2">
      <p className="text-[10px] text-muted-foreground/50 uppercase tracking-wider">Connected platforms</p>

      {['slack', 'notion'].map(provider => {
        const p = platforms.find(pl => pl.provider === provider);
        const connected = p && (p.status === 'active' || p.status === 'connected');
        return (
          <Link
            key={provider}
            href={connected ? `/context/${provider}` : '/integrations'}
            className={cn(
              'flex items-center justify-between px-3 py-2.5 rounded-lg border transition-colors',
              connected ? 'border-border hover:bg-muted/50' : 'border-dashed border-border/40 hover:bg-muted/20'
            )}
          >
            <div className="flex items-center gap-2.5">
              <Link2 className={cn('w-4 h-4', connected ? 'text-muted-foreground' : 'text-muted-foreground/30')} />
              <div>
                <span className={cn('text-sm capitalize', connected ? 'font-medium' : 'text-muted-foreground/40')}>{provider}</span>
                {p?.workspace_name && <span className="text-[10px] text-muted-foreground block">{p.workspace_name}</span>}
              </div>
            </div>
            <div className="flex items-center gap-1.5">
              {connected && <span className="text-[10px] text-muted-foreground">{p?.resource_count} sources</span>}
              <span className={cn('w-2 h-2 rounded-full', connected ? 'bg-green-500' : 'bg-gray-300')} />
            </div>
          </Link>
        );
      })}

      <Link href="/integrations" className="block text-center px-3 py-2 text-[10px] text-muted-foreground/50 hover:text-muted-foreground transition-colors">
        Manage integrations →
      </Link>
    </div>
  );
}

// =============================================================================
// Main Page
// =============================================================================

export default function WorkfloorPage() {
  const { loadScopedHistory } = useTP();
  const searchParams = useSearchParams();
  const router = useRouter();

  const [agents, setAgents] = useState<Agent[]>([]);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [agentsLoading, setAgentsLoading] = useState(true);
  const [tasksLoading, setTasksLoading] = useState(true);
  const [bootstrapProvider, setBootstrapProvider] = useState<string | null>(null);

  useEffect(() => { loadScopedHistory(); }, [loadScopedHistory]);

  useEffect(() => {
    api.agents.list().then(setAgents).catch(() => []).finally(() => setAgentsLoading(false));
    api.tasks.list().then(setTasks).catch(() => []).finally(() => setTasksLoading(false));
  }, []);

  useEffect(() => {
    const provider = searchParams?.get('provider');
    const connStatus = searchParams?.get('status');
    if (provider && connStatus === 'connected') {
      setBootstrapProvider(provider);
      router.replace(HOME_ROUTE, { scroll: false });
    }
  }, [searchParams, router]);

  const activeAgents = agents.filter(a => a.status !== 'archived');

  // Panel tabs for the right side
  const panelTabs: WorkspacePanelTab[] = [
    { id: 'tasks', label: 'Tasks', content: <TasksTab tasks={tasks} /> },
    { id: 'context', label: 'Context', content: <ContextTab /> },
    { id: 'platforms', label: 'Platforms', content: <PlatformsTab /> },
  ];

  return (
    <>
      <WorkspaceLayout
        identity={{ icon: <FlaskConical className="w-5 h-5" />, label: 'Workfloor' }}
        panelTabs={panelTabs}
        panelDefaultOpen={true}
        panelDefaultPct={40}
      >
        {/* ===== Left: Agent Roster (Living Office) ===== */}
        <div className="flex-1 overflow-y-auto p-6">
          <div className="max-w-2xl mx-auto">
            {/* Bootstrap banner */}
            {bootstrapProvider && (
              <div className="flex items-center gap-3 p-4 rounded-lg border border-primary/20 bg-primary/5 mb-6">
                <div className="flex-1">
                  <p className="text-sm font-medium">Connected {bootstrapProvider.charAt(0).toUpperCase() + bootstrapProvider.slice(1)}!</p>
                  <p className="text-xs text-muted-foreground">Syncing your data...</p>
                </div>
                <button onClick={() => setBootstrapProvider(null)} className="text-muted-foreground hover:text-foreground"><X className="w-4 h-4" /></button>
              </div>
            )}

            {/* Agent roster header */}
            <div className="flex items-center justify-between mb-4">
              <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
                Your Team {activeAgents.length > 0 && <span className="opacity-50">({activeAgents.length})</span>}
              </p>
              {activeAgents.length > 0 && (() => {
                const working = activeAgents.filter(a => a.latest_version_status === 'generating');
                const ready = activeAgents.filter(a => a.status === 'active' && a.latest_version_status !== 'generating');
                const paused = activeAgents.filter(a => a.status === 'paused');
                return (
                  <div className="flex items-center gap-3 text-[10px]">
                    {working.length > 0 && <span className="flex items-center gap-1 text-blue-500"><span className="w-1.5 h-1.5 rounded-full bg-blue-500 animate-pulse" />{working.length} working</span>}
                    {ready.length > 0 && <span className="flex items-center gap-1 text-green-500"><span className="w-1.5 h-1.5 rounded-full bg-green-500" />{ready.length} ready</span>}
                    {paused.length > 0 && <span className="flex items-center gap-1 text-amber-500"><span className="w-1.5 h-1.5 rounded-full bg-amber-500" />{paused.length} paused</span>}
                  </div>
                );
              })()}
            </div>

            {/* Agent grid */}
            {agentsLoading ? (
              <div className="flex items-center justify-center py-16">
                <Loader2 className="w-5 h-5 animate-spin text-muted-foreground" />
              </div>
            ) : activeAgents.length > 0 ? (
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                {activeAgents.map(agent => <AgentDeskCard key={agent.id} agent={agent} />)}
              </div>
            ) : (
              /* Empty roster */
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                {['Research', 'Content', 'Marketing', 'CRM', 'Slack', 'Notion'].map(name => (
                  <div key={name} className="flex flex-col items-center justify-center p-4 rounded-xl border border-dashed border-border/40 opacity-30">
                    <div className="w-10 h-10 rounded-lg border border-dashed border-border/40 flex items-center justify-center mb-2">
                      <Cog className="w-4 h-4 text-muted-foreground/30" />
                    </div>
                    <span className="text-xs text-muted-foreground/40">{name}</span>
                    <span className="text-[9px] text-muted-foreground/25 mt-0.5">idle</span>
                  </div>
                ))}
              </div>
            )}

            {/* Quick stats */}
            <div className="grid grid-cols-3 gap-3 mt-6">
              <div className="p-3 rounded-lg border border-border bg-muted/20 text-center">
                <div className="text-xl font-medium">{activeAgents.length}</div>
                <div className="text-[10px] text-muted-foreground">Agents</div>
              </div>
              <div className="p-3 rounded-lg border border-border bg-muted/20 text-center">
                <div className="text-xl font-medium">{tasks.filter(t => t.status !== 'archived').length}</div>
                <div className="text-[10px] text-muted-foreground">Tasks</div>
              </div>
              <div className="p-3 rounded-lg border border-border bg-muted/20 text-center">
                <div className="text-xl font-medium">{tasks.filter(t => t.last_run_at).length}</div>
                <div className="text-[10px] text-muted-foreground">Outputs</div>
              </div>
            </div>

            {/* Empty state hint */}
            {activeAgents.length > 0 && tasks.filter(t => t.status !== 'archived').length === 0 && (
              <div className="mt-8 text-center">
                <p className="text-sm text-muted-foreground mb-2">Your team is ready. Create a task to get started.</p>
                <p className="text-[10px] text-muted-foreground/40">
                  Press <kbd className="px-1.5 py-0.5 text-[9px] border border-border rounded bg-muted font-mono">⌘K</kbd> to chat
                </p>
              </div>
            )}
          </div>
        </div>
      </WorkspaceLayout>

      {/* Chat Drawer (outside WorkspaceLayout to overlay properly) */}
      <ChatDrawer />
    </>
  );
}
