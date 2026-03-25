'use client';

/**
 * Workfloor — ADR-139 v2: Output-First, Chat-as-Drawer
 *
 * Left: Output feed (reverse-chrono cards from all tasks)
 * Right: Agent roster (2×3 grid, living office) + quick stats + task list
 * Chat: Drawer (FAB + ⌘K, slides from right)
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
} from 'lucide-react';
import { useTP } from '@/contexts/TPContext';
import type { Agent, Task } from '@/types';
import { cn } from '@/lib/utils';
import { api } from '@/lib/api/client';
import { ChatDrawer } from '@/components/desk/ChatDrawer';

// =============================================================================
// Agent type config (ADR-140)
// =============================================================================

const TYPE_CONFIG: Record<string, { icon: typeof FlaskConical; color: string; bg: string; short: string }> = {
  research:   { icon: FlaskConical,  color: 'text-blue-500',   bg: 'bg-blue-500/10',   short: 'Research' },
  content:    { icon: FileText,      color: 'text-purple-500', bg: 'bg-purple-500/10', short: 'Content' },
  marketing:  { icon: TrendingUp,    color: 'text-pink-500',   bg: 'bg-pink-500/10',   short: 'Marketing' },
  crm:        { icon: Users,         color: 'text-orange-500', bg: 'bg-orange-500/10', short: 'CRM' },
  slack_bot:  { icon: MessageCircle, color: 'text-teal-500',   bg: 'bg-teal-500/10',   short: 'Slack' },
  notion_bot: { icon: BookOpen,      color: 'text-indigo-500', bg: 'bg-indigo-500/10', short: 'Notion' },
  // Legacy
  briefer:    { icon: FlaskConical,  color: 'text-blue-500',   bg: 'bg-blue-500/10',   short: 'Research' },
  monitor:    { icon: Eye,           color: 'text-green-500',  bg: 'bg-green-500/10',  short: 'Monitor' },
  researcher: { icon: FlaskConical,  color: 'text-blue-500',   bg: 'bg-blue-500/10',   short: 'Research' },
  analyst:    { icon: FlaskConical,  color: 'text-blue-500',   bg: 'bg-blue-500/10',   short: 'Research' },
  drafter:    { icon: FileText,      color: 'text-purple-500', bg: 'bg-purple-500/10', short: 'Content' },
  writer:     { icon: FileText,      color: 'text-purple-500', bg: 'bg-purple-500/10', short: 'Content' },
  custom:     { icon: Cog,           color: 'text-gray-500',   bg: 'bg-gray-500/10',   short: 'Custom' },
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
// Output Feed Card
// =============================================================================

function OutputCard({ task }: { task: Task }) {
  return (
    <Link
      href={`/tasks/${task.slug}`}
      className="block p-4 rounded-xl border border-border hover:border-primary/20 hover:bg-muted/30 transition-all"
    >
      <div className="flex items-center justify-between mb-1.5">
        <span className="text-sm font-medium">{task.title}</span>
        <span className="text-[10px] text-muted-foreground/50">
          {task.last_run_at ? formatRelativeTime(task.last_run_at) : ''}
        </span>
      </div>
      {task.agent_slugs?.[0] && (
        <span className="text-[11px] text-muted-foreground">{task.agent_slugs[0]}</span>
      )}
      {task.objective?.deliverable && (
        <p className="text-xs text-muted-foreground/60 mt-1 line-clamp-2">{task.objective.deliverable}</p>
      )}
      <div className="flex items-center gap-2 mt-2">
        <span className={cn(
          'w-1.5 h-1.5 rounded-full',
          task.status === 'active' ? 'bg-green-500' : task.status === 'paused' ? 'bg-amber-500' : 'bg-gray-400'
        )} />
        <span className="text-[10px] text-muted-foreground">{task.schedule || 'unscheduled'}</span>
      </div>
    </Link>
  );
}

// =============================================================================
// Agent Desk Card (2×3 roster grid)
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
        'flex flex-col items-center justify-center p-3 rounded-xl border transition-all hover:shadow-sm',
        'border-border', config.bg,
      )}
    >
      <div className="relative mb-1.5">
        <Icon className={cn('w-5 h-5', config.color)} />
        <span className={cn('absolute -top-0.5 -right-0.5 w-2 h-2 rounded-full border border-background', dotColor)} />
      </div>
      <span className="text-[11px] font-medium text-center truncate w-full">{config.short}</span>
      <span className="text-[9px] text-muted-foreground/50 mt-0.5">
        {isRunning ? 'working...' : agent.last_run_at ? formatRelativeTime(agent.last_run_at) : 'idle'}
      </span>
    </Link>
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
  const activeTasks = tasks.filter(t => t.status !== 'archived');
  const tasksWithOutput = activeTasks
    .filter(t => t.last_run_at)
    .sort((a, b) => new Date(b.last_run_at!).getTime() - new Date(a.last_run_at!).getTime());

  const loading = agentsLoading || tasksLoading;

  return (
    <div className="h-full flex overflow-hidden">
      {/* ===== Left: Output Feed ===== */}
      <div className="flex-1 overflow-y-auto p-6">
        <div className="max-w-2xl mx-auto">
          {bootstrapProvider && (
            <div className="flex items-center gap-3 p-4 rounded-lg border border-primary/20 bg-primary/5 mb-6">
              <div className="flex-1">
                <p className="text-sm font-medium">Connected {bootstrapProvider.charAt(0).toUpperCase() + bootstrapProvider.slice(1)}!</p>
                <p className="text-xs text-muted-foreground">Syncing your data...</p>
              </div>
              <button onClick={() => setBootstrapProvider(null)} className="text-muted-foreground hover:text-foreground"><X className="w-4 h-4" /></button>
            </div>
          )}

          {loading ? (
            <div className="flex items-center justify-center py-16">
              <Loader2 className="w-5 h-5 animate-spin text-muted-foreground" />
            </div>
          ) : tasksWithOutput.length > 0 ? (
            <div className="space-y-3">
              <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Recent Output</p>
              {tasksWithOutput.map(task => <OutputCard key={task.id} task={task} />)}
            </div>
          ) : (
            <div className="py-16 text-center">
              <FileText className="w-10 h-10 text-muted-foreground/15 mx-auto mb-4" />
              <h2 className="text-lg font-medium mb-2">No outputs yet</h2>
              <p className="text-sm text-muted-foreground max-w-md mx-auto mb-6">
                Your team is ready. Press <kbd className="px-1.5 py-0.5 text-[10px] border border-border rounded bg-muted font-mono">⌘K</kbd> to chat and create your first task.
              </p>
              <div className="max-w-sm mx-auto space-y-2 text-left">
                {['Weekly competitive intelligence', 'Daily Slack recap', 'Monthly investor update'].map(prompt => (
                  <div key={prompt} className="flex items-center gap-2 p-3 rounded-lg border border-dashed border-border/50 text-left opacity-60">
                    <MessageCircle className="w-3.5 h-3.5 text-muted-foreground/40 shrink-0" />
                    <span className="text-xs text-muted-foreground">&ldquo;{prompt}&rdquo;</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* ===== Right: Roster + Stats ===== */}
      <div className="hidden lg:flex lg:flex-col w-[340px] border-l border-border bg-muted/20 overflow-y-auto shrink-0">
        <div className="p-4 space-y-6">
          {/* Agent Roster 2×3 */}
          <div>
            <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-3">
              Your Team {activeAgents.length > 0 && <span className="opacity-50">({activeAgents.length})</span>}
            </p>
            {agentsLoading ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="w-4 h-4 animate-spin text-muted-foreground" />
              </div>
            ) : activeAgents.length > 0 ? (
              <div className="grid grid-cols-3 gap-2">
                {activeAgents.slice(0, 6).map(agent => <AgentDeskCard key={agent.id} agent={agent} />)}
              </div>
            ) : (
              <div className="grid grid-cols-3 gap-2">
                {['Research', 'Content', 'Mktg', 'CRM', 'Slack', 'Notion'].map(name => (
                  <div key={name} className="flex flex-col items-center justify-center p-3 rounded-xl border border-dashed border-border/50 opacity-30">
                    <span className="text-[10px] text-muted-foreground">{name}</span>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Quick Stats */}
          <div className="grid grid-cols-2 gap-2">
            <div className="p-3 rounded-lg border border-border bg-background">
              <div className="text-lg font-medium">{activeTasks.length}</div>
              <div className="text-[10px] text-muted-foreground">Tasks</div>
            </div>
            <div className="p-3 rounded-lg border border-border bg-background">
              <div className="text-lg font-medium">{activeAgents.length}</div>
              <div className="text-[10px] text-muted-foreground">Agents</div>
            </div>
          </div>

          {/* Task list */}
          {activeTasks.length > 0 && (
            <div>
              <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-2">Tasks</p>
              <div className="space-y-1">
                {activeTasks.map(task => (
                  <Link key={task.id} href={`/tasks/${task.slug}`} className="flex items-center justify-between px-2.5 py-2 rounded-lg hover:bg-muted/50 transition-colors text-xs">
                    <div className="flex items-center gap-2 min-w-0">
                      <span className={cn('w-1.5 h-1.5 rounded-full shrink-0', task.status === 'active' ? 'bg-green-500' : 'bg-amber-500')} />
                      <span className="truncate">{task.title}</span>
                    </div>
                    {task.schedule && <span className="text-muted-foreground/50 shrink-0 ml-2">{task.schedule}</span>}
                  </Link>
                ))}
              </div>
            </div>
          )}

          {/* Links */}
          <div className="flex gap-2">
            <Link href="/context" className="flex-1 text-center px-3 py-2 rounded-lg border border-border text-[11px] text-muted-foreground hover:bg-muted/50 transition-colors">Context</Link>
            <Link href="/integrations" className="flex-1 text-center px-3 py-2 rounded-lg border border-border text-[11px] text-muted-foreground hover:bg-muted/50 transition-colors">Platforms</Link>
          </div>
        </div>
      </div>

      {/* ===== Chat Drawer ===== */}
      <ChatDrawer />
    </div>
  );
}
