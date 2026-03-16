'use client';

/**
 * Supervision Dashboard — Agent Health + Composer Activity
 *
 * Landing page showing ambient awareness of autonomous agent work:
 * 1. Agent health grid (maturity, status, last run)
 * 2. Composer activity feed (lifecycle actions, bootstraps)
 * 3. Attention banner (auto-paused agents, failed runs)
 * 4. Summary stats (counts, maturity distribution)
 *
 * Replaced the ChatFirstDesk (now at /orchestrator).
 * See docs/design/SUPERVISION-DASHBOARD.md for design rationale.
 */

import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import {
  Loader2,
  MessageSquare,
  AlertTriangle,
  XCircle,
  Pause,
  ArrowRight,
  Sparkles,
  HeartPulse,
  Globe,
  Brain,
  TrendingDown,
  TrendingUp,
  Plus,
  Clock,
  CheckCircle2,
  Circle,
} from 'lucide-react';
import { api } from '@/lib/api/client';
import { ORCHESTRATOR_ROUTE } from '@/lib/routes';
import { getPlatformIcon } from '@/components/ui/PlatformIcons';
import { SKILL_LABELS } from '@/lib/constants/agents';
import { formatDistanceToNow, format, isToday, isTomorrow } from 'date-fns';
import { cn } from '@/lib/utils';
import type { Skill } from '@/types';

// =============================================================================
// Types
// =============================================================================

type DashboardData = Awaited<ReturnType<typeof api.dashboard.getSummary>>;
type AgentHealth = DashboardData['agents'][number];
type ComposerAction = DashboardData['composer_actions'][number];
type AttentionItem = DashboardData['attention'][number];

// =============================================================================
// Maturity badge
// =============================================================================

const MATURITY_CONFIG = {
  mature: { label: 'Mature', color: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400' },
  developing: { label: 'Developing', color: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400' },
  nascent: { label: 'Nascent', color: 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400' },
};

function MaturityBadge({ maturity }: { maturity: string }) {
  const config = MATURITY_CONFIG[maturity as keyof typeof MATURITY_CONFIG] ?? MATURITY_CONFIG.nascent;
  return (
    <span className={cn('text-xs px-1.5 py-0.5 rounded font-medium', config.color)}>
      {config.label}
    </span>
  );
}

// =============================================================================
// Agent source icon helper
// =============================================================================

function getAgentSourceIcon(agent: AgentHealth): React.ReactNode {
  const providers: string[] = [];
  for (const s of agent.sources ?? []) {
    if (s.provider) {
      const p = s.provider === 'google'
        ? (s.resource_id?.startsWith('label:') ? 'gmail' : 'calendar')
        : s.provider;
      if (!providers.includes(p)) providers.push(p);
    }
  }
  if (providers.length === 0) {
    return agent.skill === 'research'
      ? <Globe className="w-4 h-4 text-muted-foreground" />
      : <Brain className="w-4 h-4 text-muted-foreground" />;
  }
  return getPlatformIcon(providers[0], 'w-4 h-4');
}

// =============================================================================
// Helpers
// =============================================================================

function formatNextRun(dateStr: string): string {
  const date = new Date(dateStr);
  if (isToday(date)) return `Today ${format(date, 'h:mma').toLowerCase()}`;
  if (isTomorrow(date)) return `Tomorrow ${format(date, 'h:mma').toLowerCase()}`;
  return format(date, 'EEE h:mma').toLowerCase();
}

// =============================================================================
// Page Component
// =============================================================================

export default function DashboardPage() {
  const router = useRouter();
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [connecting, setConnecting] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const result = await api.dashboard.getSummary();
        if (!cancelled) {
          setData(result);
          setLoading(false);
        }
      } catch (e) {
        if (!cancelled) {
          setError(e instanceof Error ? e.message : 'Failed to load dashboard');
          setLoading(false);
        }
      }
    }
    load();
    return () => { cancelled = true; };
  }, []);

  // ADR-113: Trigger OAuth directly from dashboard (no redirect to context page)
  const handleConnect = useCallback(async (platform: string) => {
    setConnecting(platform);
    try {
      const authProvider = platform === 'calendar' ? 'google' : platform;
      const result = await api.integrations.getAuthorizationUrl(authProvider);
      window.location.href = result.authorization_url;
    } catch (err) {
      console.error(`Failed to initiate ${platform} OAuth:`, err);
      setConnecting(null);
    }
  }, []);

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center">
        <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="h-full flex items-center justify-center">
        <p className="text-destructive">{error || 'Failed to load dashboard'}</p>
      </div>
    );
  }

  const { agents, composer_actions, attention, connected_platforms, heartbeat_pulse, progression, stats } = data;
  const hasNoPlatforms = connected_platforms.length === 0;
  const hasNoAgents = agents.length === 0;

  // Empty state: no platforms connected yet
  if (hasNoPlatforms && hasNoAgents) {
    return (
      <div className="h-full overflow-auto">
        <div className="max-w-2xl mx-auto px-4 md:px-6 py-12 space-y-8">
          <div className="text-center">
            <h1 className="text-2xl font-bold">Welcome to YARNNN</h1>
            <p className="text-muted-foreground mt-2">
              Connect your work platforms and YARNNN will create agents that
              deliver recurring insights — automatically.
            </p>
          </div>

          {/* Primary path: connect platforms — ADR-113: OAuth directly, auto-selects sources */}
          <div className="space-y-3">
            <h2 className="text-sm font-medium text-muted-foreground uppercase tracking-wide">Connect a platform to get started</h2>
            <div className="grid grid-cols-2 gap-3">
              {(['slack', 'gmail', 'notion', 'calendar'] as const).map((platform) => (
                <button
                  key={platform}
                  onClick={() => handleConnect(platform)}
                  disabled={connecting !== null}
                  className={cn(
                    "flex items-center gap-3 p-4 rounded-lg border border-border hover:bg-muted/50 hover:border-primary/30 transition-colors text-left",
                    connecting === platform && "opacity-70",
                  )}
                >
                  {connecting === platform
                    ? <Loader2 className="w-5 h-5 animate-spin text-muted-foreground" />
                    : getPlatformIcon(platform, 'w-5 h-5')
                  }
                  <span className="text-sm font-medium capitalize">{platform === 'calendar' ? 'Google Calendar' : platform}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Divider */}
          <div className="flex items-center gap-3">
            <div className="flex-1 border-t border-border" />
            <span className="text-xs text-muted-foreground">or</span>
            <div className="flex-1 border-t border-border" />
          </div>

          {/* Alternative path: ask Orchestrator */}
          <button
            onClick={() => router.push(ORCHESTRATOR_ROUTE)}
            className="w-full flex items-center gap-3 p-4 rounded-lg border border-border hover:bg-muted/50 hover:border-primary/30 transition-colors text-left"
          >
            <MessageSquare className="w-5 h-5 text-primary" />
            <div>
              <p className="text-sm font-medium">Ask the Orchestrator</p>
              <p className="text-xs text-muted-foreground">Create agents for topics, research, or tasks — no platform needed</p>
            </div>
            <ArrowRight className="w-4 h-4 text-muted-foreground ml-auto shrink-0" />
          </button>
        </div>
      </div>
    );
  }

  // Transitional state: platforms connected but no agents yet
  // ADR-113: Sources auto-selected, sync in progress — show progress, not source selection CTA
  if (hasNoAgents) {
    const unconnected = (['slack', 'gmail', 'notion', 'calendar'] as const).filter(
      (p) => !connected_platforms.includes(p === 'calendar' ? 'google' : p) && !connected_platforms.includes(p)
    );

    return (
      <div className="h-full overflow-auto">
        <div className="max-w-2xl mx-auto px-4 md:px-6 py-12 space-y-8">
          <div className="text-center">
            <h1 className="text-2xl font-bold">Dashboard</h1>
            <p className="text-muted-foreground mt-2">
              Your platforms are syncing. Agents will appear here automatically.
            </p>
          </div>

          {/* Connected platforms summary */}
          <div className="flex items-center justify-center gap-3">
            {connected_platforms.map((p) => (
              <div key={p} className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-green-50 dark:bg-green-950/20 border border-green-200 dark:border-green-900/40">
                {getPlatformIcon(p, 'w-4 h-4')}
                <span className="text-xs font-medium text-green-700 dark:text-green-400 capitalize">{p}</span>
              </div>
            ))}
          </div>

          {/* Actions */}
          <div className="grid gap-3">
            {/* Connect more platforms (if any unconnected) */}
            {unconnected.length > 0 && (
              <div className="p-4 rounded-lg border border-dashed border-border">
                <p className="text-sm font-medium mb-3">Connect more platforms</p>
                <div className="flex flex-wrap gap-2">
                  {unconnected.map((platform) => (
                    <button
                      key={platform}
                      onClick={() => handleConnect(platform)}
                      disabled={connecting !== null}
                      className="inline-flex items-center gap-2 px-3 py-1.5 text-xs rounded-md border border-border hover:bg-muted/50 transition-colors"
                    >
                      {connecting === platform
                        ? <Loader2 className="w-3.5 h-3.5 animate-spin" />
                        : getPlatformIcon(platform, 'w-3.5 h-3.5')
                      }
                      <span className="capitalize">{platform === 'calendar' ? 'Calendar' : platform}</span>
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Refine sources (optional, not prerequisite) */}
            <button
              onClick={() => router.push('/context')}
              className="flex items-center gap-3 p-4 rounded-lg border border-border hover:bg-muted/50 transition-colors text-left"
            >
              <Plus className="w-5 h-5 text-muted-foreground" />
              <div>
                <p className="text-sm font-medium">Customize synced sources</p>
                <p className="text-xs text-muted-foreground">Add or remove specific channels, labels, or pages</p>
              </div>
              <ArrowRight className="w-4 h-4 text-muted-foreground ml-auto shrink-0" />
            </button>

            <button
              onClick={() => router.push(ORCHESTRATOR_ROUTE)}
              className="flex items-center gap-3 p-4 rounded-lg border border-border hover:bg-muted/50 transition-colors text-left"
            >
              <MessageSquare className="w-5 h-5 text-primary" />
              <div>
                <p className="text-sm font-medium">Ask the Orchestrator</p>
                <p className="text-xs text-muted-foreground">Create or configure agents through conversation</p>
              </div>
              <ArrowRight className="w-4 h-4 text-muted-foreground ml-auto shrink-0" />
            </button>
          </div>
        </div>
      </div>
    );
  }

  // Normal state: agents exist — supervision dashboard
  return (
    <div className="h-full overflow-auto">
      <div className="max-w-4xl mx-auto px-4 md:px-6 py-6 space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold">Dashboard</h1>
            <p className="text-sm text-muted-foreground mt-1">
              Your agent workforce at a glance
            </p>
          </div>
          <button
            onClick={() => router.push(ORCHESTRATOR_ROUTE)}
            className="inline-flex items-center gap-2 px-4 py-2 text-sm bg-primary text-primary-foreground rounded-md hover:bg-primary/90"
          >
            <MessageSquare className="w-4 h-4" />
            Ask Orchestrator
          </button>
        </div>

        {/* Attention Banner */}
        {attention.length > 0 && (
          <div className="space-y-2">
            {attention.map((item, i) => (
              <AttentionBanner key={i} item={item} onClick={() => router.push(`/agents/${item.agent_id}`)} />
            ))}
          </div>
        )}

        {/* Stats Row */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <StatCard label="Active Agents" value={stats.active_agents} subtext={`${stats.total_agents} total`} />
          <StatCard label="Runs This Week" value={stats.runs_this_week} />
          <StatCard
            label="Mature"
            value={stats.maturity_distribution.mature}
            subtext={`${stats.maturity_distribution.developing} developing`}
          />
          <StatCard
            label="Nascent"
            value={stats.maturity_distribution.nascent}
            subtext="need more runs"
          />
        </div>

        {/* System Pulse — last heartbeat status */}
        <div className="flex items-center gap-3 px-4 py-2.5 rounded-lg border border-border bg-card text-sm">
          <HeartPulse className="w-4 h-4 text-muted-foreground shrink-0" />
          {heartbeat_pulse ? (
            <>
              <span className="text-muted-foreground">Last heartbeat</span>
              <span className="font-medium">
                {formatDistanceToNow(new Date(heartbeat_pulse.last_run_at), { addSuffix: true })}
              </span>
              {heartbeat_pulse.lifecycle_actions.length > 0 ? (
                <span className="text-xs px-1.5 py-0.5 rounded bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400">
                  {heartbeat_pulse.lifecycle_actions.length} action{heartbeat_pulse.lifecycle_actions.length !== 1 ? 's' : ''}
                </span>
              ) : (
                <span className="text-xs text-muted-foreground">All healthy</span>
              )}
              {heartbeat_pulse.agents_assessed > 0 && (
                <span className="text-xs text-muted-foreground ml-auto">
                  {heartbeat_pulse.agents_assessed} agents assessed
                </span>
              )}
            </>
          ) : (
            <>
              <span className="text-muted-foreground">System heartbeat</span>
              <span className="text-xs text-muted-foreground">Scheduled — runs daily at midnight UTC</span>
            </>
          )}
        </div>

        {/* Progression — value chain milestones for newer users */}
        {progression && (
          <ProgressionBar progression={progression} />
        )}

        {/* Agent Health Grid */}
        <section>
          <h2 className="text-lg font-semibold mb-3">Agent Health</h2>
          <div className="grid gap-3">
            {agents.map((agent) => (
              <AgentHealthCard
                key={agent.id}
                agent={agent}
                onClick={() => router.push(`/agents/${agent.id}`)}
              />
            ))}
          </div>
        </section>

        {/* Composer Activity Feed */}
        {composer_actions.length > 0 && (
          <section>
            <h2 className="text-lg font-semibold mb-3">Composer Activity</h2>
            <div className="space-y-2">
              {composer_actions.map((action, i) => (
                <ComposerActionCard key={i} action={action} onClick={
                  action.agent_id ? () => router.push(`/agents/${action.agent_id}`) : undefined
                } />
              ))}
            </div>
          </section>
        )}
      </div>
    </div>
  );
}

// =============================================================================
// Sub-components
// =============================================================================

function StatCard({ label, value, subtext }: { label: string; value: number; subtext?: string }) {
  return (
    <div className="p-4 rounded-lg border border-border bg-card">
      <p className="text-2xl font-bold">{value}</p>
      <p className="text-sm font-medium text-muted-foreground">{label}</p>
      {subtext && <p className="text-xs text-muted-foreground mt-0.5">{subtext}</p>}
    </div>
  );
}

function AttentionBanner({ item, onClick }: { item: AttentionItem; onClick: () => void }) {
  const icon = item.type === 'auto_paused'
    ? <Pause className="w-4 h-4" />
    : item.type === 'failed'
      ? <XCircle className="w-4 h-4" />
      : <AlertTriangle className="w-4 h-4" />;

  return (
    <button
      onClick={onClick}
      className="w-full flex items-center gap-3 p-3 rounded-lg border border-amber-200 bg-amber-50 dark:border-amber-900/50 dark:bg-amber-950/20 hover:bg-amber-100 dark:hover:bg-amber-950/30 text-left"
    >
      <span className="text-amber-600 dark:text-amber-400">{icon}</span>
      <span className="text-sm flex-1">{item.message}</span>
      <ArrowRight className="w-4 h-4 text-muted-foreground" />
    </button>
  );
}

function AgentHealthCard({ agent, onClick }: { agent: AgentHealth; onClick: () => void }) {
  const isPaused = agent.status === 'paused';
  const skillLabel = SKILL_LABELS[agent.skill as Skill] ?? agent.skill;

  return (
    <button
      onClick={onClick}
      className={cn(
        'w-full flex items-center gap-3 p-3 rounded-lg border border-border hover:bg-muted/50 text-left transition-colors',
        isPaused && 'opacity-60',
      )}
    >
      {/* Platform icon + status dot */}
      <div className="relative shrink-0">
        {getAgentSourceIcon(agent)}
        <span className={cn(
          'absolute -bottom-0.5 -right-0.5 w-2 h-2 rounded-full border border-background',
          isPaused ? 'bg-amber-400' : 'bg-green-500',
        )} />
      </div>

      {/* Title + skill */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium truncate">{agent.title}</span>
          {agent.origin && agent.origin !== 'user_configured' && (
            <span className="text-xs px-1.5 py-0.5 rounded bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400">
              Auto
            </span>
          )}
        </div>
        <div className="flex items-center gap-2 text-xs text-muted-foreground mt-0.5">
          <span>{skillLabel}</span>
          {agent.total_runs > 0 && (
            <>
              <span>&middot;</span>
              <span>{agent.total_runs} runs</span>
            </>
          )}
          {agent.approval_rate !== null && (
            <>
              <span>&middot;</span>
              <span>{Math.round(agent.approval_rate * 100)}% approved</span>
            </>
          )}
        </div>
      </div>

      {/* Maturity + timing */}
      <div className="flex items-center gap-2 shrink-0">
        {agent.edit_trend !== null && (
          agent.edit_trend < 0
            ? <span title="Improving (less editing)"><TrendingDown className="w-3.5 h-3.5 text-green-500" /></span>
            : agent.edit_trend > 0
              ? <span title="More editing needed"><TrendingUp className="w-3.5 h-3.5 text-amber-500" /></span>
              : null
        )}
        <MaturityBadge maturity={agent.maturity} />
        <div className="flex flex-col items-end gap-0.5">
          {agent.last_run_at && (
            <span className="text-xs text-muted-foreground whitespace-nowrap">
              {formatDistanceToNow(new Date(agent.last_run_at), { addSuffix: true })}
            </span>
          )}
          {agent.next_run_at && agent.status === 'active' && (
            <span className="text-xs text-muted-foreground/70 whitespace-nowrap">
              Next: {formatNextRun(agent.next_run_at)}
            </span>
          )}
        </div>
      </div>
    </button>
  );
}

function ComposerActionCard({ action, onClick }: { action: ComposerAction; onClick?: () => void }) {
  const icon = action.type === 'created'
    ? <Sparkles className="w-4 h-4 text-amber-500" />
    : action.type === 'paused'
      ? <Pause className="w-4 h-4 text-amber-500" />
      : <HeartPulse className="w-4 h-4 text-muted-foreground" />;

  const Wrapper = onClick ? 'button' : 'div';

  return (
    <Wrapper
      onClick={onClick}
      className={cn(
        'flex items-start gap-3 p-3 rounded-lg border border-border text-left',
        onClick && 'hover:bg-muted/50 cursor-pointer',
      )}
    >
      <span className="mt-0.5 shrink-0">{icon}</span>
      <div className="flex-1 min-w-0">
        <p className="text-sm">{action.summary || `${action.type}: ${action.agent_title || 'Agent'}`}</p>
        <p className="text-xs text-muted-foreground mt-0.5">
          {formatDistanceToNow(new Date(action.created_at), { addSuffix: true })}
        </p>
      </div>
      {onClick && <ArrowRight className="w-4 h-4 text-muted-foreground mt-0.5 shrink-0" />}
    </Wrapper>
  );
}

type Progression = NonNullable<DashboardData['progression']>;

function ProgressionBar({ progression }: { progression: Progression }) {
  const milestones = [
    { label: 'Platform connected', done: progression.platforms_connected > 0 },
    { label: 'First agent running', done: progression.active_agents > 0 },
    { label: '10+ runs completed', done: progression.total_runs >= 10 },
    { label: 'Agent developing', done: progression.has_developing_agent },
    { label: 'Agent mature', done: progression.has_mature_agent },
  ];
  const completed = milestones.filter((m) => m.done).length;

  return (
    <div className="p-4 rounded-lg border border-border bg-card space-y-3">
      <div className="flex items-center justify-between">
        <p className="text-sm font-medium">Getting started</p>
        <span className="text-xs text-muted-foreground">{completed}/{milestones.length}</span>
      </div>
      <div className="flex gap-1.5">
        {milestones.map((m, i) => (
          <div
            key={i}
            className={cn(
              'h-1.5 flex-1 rounded-full',
              m.done ? 'bg-primary' : 'bg-muted',
            )}
          />
        ))}
      </div>
      <div className="flex flex-wrap gap-x-4 gap-y-1">
        {milestones.map((m, i) => (
          <div key={i} className="flex items-center gap-1.5">
            {m.done
              ? <CheckCircle2 className="w-3.5 h-3.5 text-primary" />
              : <Circle className="w-3.5 h-3.5 text-muted-foreground/40" />
            }
            <span className={cn('text-xs', m.done ? 'text-foreground' : 'text-muted-foreground')}>
              {m.label}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
