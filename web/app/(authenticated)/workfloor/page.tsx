'use client';

/**
 * Workfloor — ADR-139 v2: Agent-First Living Office
 *
 * Left: Agent roster as living office rooms — spatial cards with desk metaphor
 * Right: Tabbed panel (Tasks | Context | Platforms) — fully rendered with empty states
 * Chat: Drawer (FAB + ⌘K)
 */

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import { HOME_ROUTE } from '@/lib/routes';
import {
  Loader2,
  FileText,
  FlaskConical,
  TrendingUp,
  Users,
  MessageCircle,
  BookOpen,
  X,
  Link2,
  ListChecks,
  ChevronRight,
  LayoutGrid,
  Cog,
} from 'lucide-react';
import { useTP } from '@/contexts/TPContext';
import type { Agent, Task } from '@/types';
import { cn } from '@/lib/utils';
import { api } from '@/lib/api/client';
import { WorkspaceLayout, type WorkspacePanelTab } from '@/components/desk/WorkspaceLayout';
import { ChatDrawer } from '@/components/desk/ChatDrawer';

// =============================================================================
// Agent type config (ADR-140)
// =============================================================================

const TYPE_CONFIG: Record<string, { icon: typeof FlaskConical; color: string; accent: string; bgRoom: string; short: string; label: string }> = {
  research:   { icon: FlaskConical,  color: 'text-blue-500',   accent: 'border-blue-400/30',  bgRoom: 'from-blue-50 to-blue-100/50 dark:from-blue-950/30 dark:to-blue-900/20',   short: 'Res', label: 'Research' },
  content:    { icon: FileText,      color: 'text-purple-500', accent: 'border-purple-400/30', bgRoom: 'from-purple-50 to-purple-100/50 dark:from-purple-950/30 dark:to-purple-900/20', short: 'Con', label: 'Content' },
  marketing:  { icon: TrendingUp,    color: 'text-pink-500',   accent: 'border-pink-400/30',   bgRoom: 'from-pink-50 to-pink-100/50 dark:from-pink-950/30 dark:to-pink-900/20',   short: 'Mkt', label: 'Marketing' },
  crm:        { icon: Users,         color: 'text-orange-500', accent: 'border-orange-400/30', bgRoom: 'from-orange-50 to-orange-100/50 dark:from-orange-950/30 dark:to-orange-900/20', short: 'CRM', label: 'CRM' },
  slack_bot:  { icon: MessageCircle, color: 'text-teal-500',   accent: 'border-teal-400/30',   bgRoom: 'from-teal-50 to-teal-100/50 dark:from-teal-950/30 dark:to-teal-900/20',   short: 'Slk', label: 'Slack Bot' },
  notion_bot: { icon: BookOpen,      color: 'text-indigo-500', accent: 'border-indigo-400/30', bgRoom: 'from-indigo-50 to-indigo-100/50 dark:from-indigo-950/30 dark:to-indigo-900/20', short: 'Ntn', label: 'Notion Bot' },
  // Legacy
  briefer:    { icon: FlaskConical,  color: 'text-blue-500',   accent: 'border-blue-400/30',  bgRoom: 'from-blue-50 to-blue-100/50 dark:from-blue-950/30 dark:to-blue-900/20',   short: 'Res', label: 'Research' },
  researcher: { icon: FlaskConical,  color: 'text-blue-500',   accent: 'border-blue-400/30',  bgRoom: 'from-blue-50 to-blue-100/50 dark:from-blue-950/30 dark:to-blue-900/20',   short: 'Res', label: 'Research' },
  analyst:    { icon: FlaskConical,  color: 'text-blue-500',   accent: 'border-blue-400/30',  bgRoom: 'from-blue-50 to-blue-100/50 dark:from-blue-950/30 dark:to-blue-900/20',   short: 'Res', label: 'Research' },
  drafter:    { icon: FileText,      color: 'text-purple-500', accent: 'border-purple-400/30', bgRoom: 'from-purple-50 to-purple-100/50 dark:from-purple-950/30 dark:to-purple-900/20', short: 'Con', label: 'Content' },
  writer:     { icon: FileText,      color: 'text-purple-500', accent: 'border-purple-400/30', bgRoom: 'from-purple-50 to-purple-100/50 dark:from-purple-950/30 dark:to-purple-900/20', short: 'Con', label: 'Content' },
  custom:     { icon: Cog,           color: 'text-gray-500',   accent: 'border-gray-400/30',  bgRoom: 'from-gray-50 to-gray-100/50 dark:from-gray-950/30 dark:to-gray-900/20',   short: 'Cst', label: 'Custom' },
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
// Agent Office Room Card
// =============================================================================

function AgentRoomCard({ agent, tasks }: { agent: Agent; tasks: Task[] }) {
  const config = getType(agent.role);
  const Icon = config.icon;
  const isRunning = agent.latest_version_status === 'generating';
  const isPaused = agent.status === 'paused';
  const hasFailed = agent.latest_version_status === 'failed';

  const statusDot = isRunning ? 'bg-blue-500 animate-pulse' : isPaused ? 'bg-amber-400' : hasFailed ? 'bg-red-500' : 'bg-emerald-500';

  // Find tasks assigned to this agent
  const agentSlug = agent.slug || agent.title.toLowerCase().replace(/\s+/g, '-');
  const assignedTasks = tasks.filter(t =>
    t.status !== 'archived' && t.agent_slugs?.includes(agentSlug)
  );
  const activeTask = assignedTasks[0]; // Show the first/primary task on the desk

  return (
    <Link
      href={`/agents/${agent.id}`}
      className={cn(
        'relative flex flex-col rounded-2xl border-2 p-4 transition-all hover:shadow-lg hover:-translate-y-0.5 bg-gradient-to-br overflow-hidden min-h-[140px]',
        config.accent, config.bgRoom,
      )}
    >
      {/* Status light */}
      <div className="absolute top-3 right-3">
        <span className={cn('block w-2.5 h-2.5 rounded-full', statusDot)} />
      </div>

      {/* Agent identity — icon + name */}
      <div className="flex items-center gap-2.5 mb-3">
        <div className={cn(
          'w-10 h-10 rounded-lg flex items-center justify-center bg-background/80 backdrop-blur-sm border shadow-sm shrink-0',
          config.accent,
        )}>
          <Icon className={cn('w-5 h-5', config.color)} />
        </div>
        <div className="min-w-0">
          <span className="text-sm font-semibold leading-tight block truncate">{agent.title}</span>
          <span className="text-[10px] text-muted-foreground/60">{config.label}</span>
        </div>
      </div>

      {/* What's on the desk — live task */}
      <div className="mt-auto">
        {isRunning && activeTask ? (
          <div className="px-2 py-1.5 rounded-lg bg-blue-500/10 border border-blue-500/20">
            <p className="text-[10px] text-blue-600 dark:text-blue-400 font-medium truncate">
              Working: {activeTask.title}
            </p>
          </div>
        ) : activeTask ? (
          <div className="px-2 py-1.5 rounded-lg bg-background/60 border border-border/50">
            <p className="text-[10px] text-muted-foreground/60 truncate">
              {activeTask.title}
            </p>
            {activeTask.last_run_at && (
              <p className="text-[9px] text-muted-foreground/30">{formatRelativeTime(activeTask.last_run_at)}</p>
            )}
          </div>
        ) : (
          <div className="px-2 py-1.5 rounded-lg border border-dashed border-border/30">
            <p className="text-[10px] text-muted-foreground/25 italic">No task assigned</p>
          </div>
        )}
      </div>
    </Link>
  );
}

// =============================================================================
// TP Room Card — The Orchestrator's Office
// Distinct from AgentRoomCard: opens chat drawer, not a detail page.
// =============================================================================

function TPRoomCard({ onOpenChat }: { onOpenChat: () => void }) {
  return (
    <button
      onClick={onOpenChat}
      className={cn(
        'relative flex flex-col rounded-2xl border-2 p-4 transition-all hover:shadow-lg hover:-translate-y-0.5 bg-gradient-to-br overflow-hidden text-left',
        'border-primary/20 from-primary/5 to-primary/10',
      )}
    >
      {/* Always-on indicator */}
      <div className="absolute top-3 right-3 flex items-center gap-1.5">
        <span className="w-2 h-2 rounded-full bg-primary animate-pulse" />
        <span className="text-[9px] font-medium text-primary/60 uppercase tracking-wider">Online</span>
      </div>

      <div className="mb-3 mt-1">
        <div className="w-12 h-12 rounded-xl flex items-center justify-center bg-primary/10 border border-primary/20 shadow-sm">
          <MessageCircle className="w-6 h-6 text-primary" />
        </div>
      </div>

      <span className="text-sm font-semibold leading-tight">Orchestrator</span>
      <span className="text-[11px] text-muted-foreground/70 mt-0.5">TP — your thinking partner</span>

      <div className="mt-auto pt-3 text-[10px] text-primary/50">
        <span>⌘K to chat</span>
      </div>
    </button>
  );
}

// Empty desk placeholder
function EmptyRoomCard({ label }: { label: string }) {
  return (
    <div className="flex flex-col rounded-2xl border-2 border-dashed border-border/30 p-4 opacity-25">
      <div className="w-12 h-12 rounded-xl border-2 border-dashed border-border/30 flex items-center justify-center mb-3 mt-1">
        <Cog className="w-5 h-5 text-muted-foreground/30" />
      </div>
      <span className="text-sm font-medium text-muted-foreground/40">{label}</span>
      <span className="text-[11px] text-muted-foreground/25 mt-0.5">Empty desk</span>
    </div>
  );
}

// =============================================================================
// Right Panel Tabs
// =============================================================================

function TasksTab({ tasks }: { tasks: Task[] }) {
  const active = tasks.filter(t => t.status !== 'archived');
  return (
    <div className="p-3 space-y-2">
      {active.length > 0 ? (
        <div className="space-y-1">
          {active.map(task => (
            <Link key={task.id} href={`/tasks/${task.slug}`} className="flex items-center justify-between px-3 py-2.5 rounded-lg hover:bg-muted/50 transition-colors">
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <span className={cn('w-1.5 h-1.5 rounded-full shrink-0', task.status === 'active' ? 'bg-green-500' : 'bg-amber-500')} />
                  <span className="text-sm truncate">{task.title}</span>
                </div>
                <div className="flex items-center gap-3 ml-[14px] mt-0.5 text-[10px] text-muted-foreground/60">
                  {task.schedule && <span>{task.schedule}</span>}
                  {task.last_run_at && <span>{formatRelativeTime(task.last_run_at)}</span>}
                </div>
              </div>
              <ChevronRight className="w-3.5 h-3.5 text-muted-foreground/20 shrink-0" />
            </Link>
          ))}
        </div>
      ) : (
        <div className="py-8 text-center">
          <ListChecks className="w-6 h-6 text-muted-foreground/10 mx-auto mb-2" />
          <p className="text-xs text-muted-foreground/40">No tasks yet</p>
          <p className="text-[10px] text-muted-foreground/25 mt-0.5">⌘K → &ldquo;create a task&rdquo;</p>
        </div>
      )}
    </div>
  );
}

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

  if (loading) return <div className="flex items-center justify-center p-8"><Loader2 className="w-4 h-4 animate-spin text-muted-foreground" /></div>;

  const files = [
    { name: 'IDENTITY.md', content: identity?.name ? `${identity.name}${identity.role ? ` — ${identity.role}` : ''}` : null },
    { name: 'BRAND.md', content: brand ? brand.slice(0, 80) + (brand.length > 80 ? '...' : '') : null },
    { name: 'CONTEXT.md', content: null },
    { name: 'preferences.md', content: null },
    { name: 'notes.md', content: null },
  ];

  return (
    <div className="p-3 space-y-1.5">
      {files.map(f => (
        <div key={f.name} className={cn('px-3 py-2 rounded-lg text-xs', f.content ? 'bg-background border border-border' : 'border border-dashed border-border/30')}>
          <span className={cn('font-medium', f.content ? '' : 'text-muted-foreground/30')}>{f.name}</span>
          {f.content ? <p className="text-muted-foreground truncate mt-0.5">{f.content}</p> : <p className="text-muted-foreground/20 mt-0.5">Empty</p>}
        </div>
      ))}
      <Link href="/context" className="block text-center px-3 py-2 text-[10px] text-muted-foreground/40 hover:text-muted-foreground transition-colors mt-2">
        Browse full context →
      </Link>
    </div>
  );
}

function PlatformsTab() {
  const [platforms, setPlatforms] = useState<Array<{ provider: string; status: string; workspace_name: string | null; resource_count: number }>>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.integrations.getSummary().then(res => setPlatforms(res.platforms)).catch(() => []).finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="flex items-center justify-center p-8"><Loader2 className="w-4 h-4 animate-spin text-muted-foreground" /></div>;

  return (
    <div className="p-3 space-y-1.5">
      {['slack', 'notion'].map(provider => {
        const p = platforms.find(pl => pl.provider === provider);
        const connected = p && (p.status === 'active' || p.status === 'connected');
        return (
          <Link key={provider} href={connected ? `/context/${provider}` : '/settings?tab=connectors'} className={cn('flex items-center justify-between px-3 py-2.5 rounded-lg transition-colors', connected ? 'bg-background border border-border hover:bg-muted/50' : 'border border-dashed border-border/30 hover:bg-muted/10')}>
            <div className="flex items-center gap-2.5">
              <Link2 className={cn('w-4 h-4', connected ? 'text-muted-foreground' : 'text-muted-foreground/20')} />
              <div>
                <span className={cn('text-sm capitalize', connected ? 'font-medium' : 'text-muted-foreground/30')}>{provider}</span>
                {p?.workspace_name && <span className="text-[10px] text-muted-foreground block">{p.workspace_name}</span>}
              </div>
            </div>
            <div className="flex items-center gap-1.5">
              {connected && <span className="text-[10px] text-muted-foreground">{p?.resource_count} sources</span>}
              <span className={cn('w-2 h-2 rounded-full', connected ? 'bg-emerald-500' : 'bg-gray-300')} />
            </div>
          </Link>
        );
      })}
      <Link href="/settings?tab=connectors" className="block text-center px-3 py-2 text-[10px] text-muted-foreground/40 hover:text-muted-foreground transition-colors mt-2">
        Manage connections →
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
  const [chatOpen, setChatOpen] = useState(false);

  useEffect(() => { loadScopedHistory(); }, [loadScopedHistory]);
  useEffect(() => {
    api.agents.list().then(setAgents).catch(() => []).finally(() => setAgentsLoading(false));
    api.tasks.list().then(setTasks).catch(() => []).finally(() => setTasksLoading(false));
  }, []);
  useEffect(() => {
    const provider = searchParams?.get('provider');
    if (provider && searchParams?.get('status') === 'connected') {
      setBootstrapProvider(provider);
      router.replace(HOME_ROUTE, { scroll: false });
    }
  }, [searchParams, router]);

  const activeAgents = agents.filter(a => a.status !== 'archived');

  const panelTabs: WorkspacePanelTab[] = [
    { id: 'tasks', label: 'Tasks', content: <TasksTab tasks={tasks} /> },
    { id: 'context', label: 'Context', content: <ContextTab /> },
    { id: 'platforms', label: 'Platforms', content: <PlatformsTab /> },
  ];

  return (
    <>
      <WorkspaceLayout
        identity={{ icon: <LayoutGrid className="w-5 h-5" />, label: 'Workfloor' }}
        panelTabs={panelTabs}
        panelDefaultOpen={true}
        panelDefaultPct={35}
      >
        <div className="flex-1 overflow-y-auto p-6">
          <div className="max-w-3xl mx-auto">
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

            {/* TP — Orchestrator's Office (distinct from agent grid) */}
            <div className="mb-6">
              <TPRoomCard onOpenChat={() => setChatOpen(true)} />
            </div>

            {/* Agent Floor — status bar + grid */}
            <div className="flex items-center justify-between mb-3">
              <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
                Agents {activeAgents.length > 0 && <span className="opacity-50">({activeAgents.length})</span>}
              </p>
              {activeAgents.length > 0 && (
                <div className="flex items-center gap-3 text-[10px]">
                  {(() => {
                    const working = activeAgents.filter(a => a.latest_version_status === 'generating').length;
                    const ready = activeAgents.filter(a => a.status === 'active' && a.latest_version_status !== 'generating').length;
                    const paused = activeAgents.filter(a => a.status === 'paused').length;
                    return (
                      <>
                        {working > 0 && <span className="flex items-center gap-1 text-blue-500 font-medium"><span className="w-1.5 h-1.5 rounded-full bg-blue-500 animate-pulse" />{working} working</span>}
                        {ready > 0 && <span className="flex items-center gap-1 text-emerald-500"><span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />{ready} ready</span>}
                        {paused > 0 && <span className="flex items-center gap-1 text-amber-500"><span className="w-1.5 h-1.5 rounded-full bg-amber-400" />{paused} paused</span>}
                      </>
                    );
                  })()}
                </div>
              )}
            </div>

            {agentsLoading ? (
              <div className="flex items-center justify-center py-16">
                <Loader2 className="w-5 h-5 animate-spin text-muted-foreground" />
              </div>
            ) : activeAgents.length > 0 ? (
              <div className="grid grid-cols-2 lg:grid-cols-3 gap-4">
                {activeAgents.map(agent => <AgentRoomCard key={agent.id} agent={agent} tasks={tasks} />)}
              </div>
            ) : (
              <div className="grid grid-cols-2 lg:grid-cols-3 gap-4">
                {['Research', 'Content', 'Marketing', 'CRM', 'Slack Bot', 'Notion Bot'].map(name => (
                  <EmptyRoomCard key={name} label={name} />
                ))}
              </div>
            )}

            {/* Stats + hint */}
            <div className="mt-6 text-center text-[10px] text-muted-foreground/40">
              {tasks.filter(t => t.status !== 'archived').length > 0 ? (
                <span>{activeAgents.length} agents · {tasks.filter(t => t.status !== 'archived').length} tasks · {tasks.filter(t => t.last_run_at).length} outputs</span>
              ) : activeAgents.length > 0 ? (
                <p>
                  Team is ready. Press <kbd className="px-1.5 py-0.5 text-[9px] border border-border rounded bg-muted font-mono">⌘K</kbd> to create tasks.
                </p>
              ) : null}
            </div>
          </div>
        </div>
      </WorkspaceLayout>
      <ChatDrawer isOpen={chatOpen} onOpenChange={setChatOpen} />
    </>
  );
}
