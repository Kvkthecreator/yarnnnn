'use client';

/**
 * Dashboard — ADR-122 Phase 5: Project-first
 *
 * All agents belong to projects. PM agents hidden (infrastructure).
 * Projects with nested contributor agents, connected platforms,
 * attention banners.
 */

import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import {
  Loader2,
  MessageSquare,
  XCircle,
  Pause,
  ArrowRight,
  Briefcase,
  Globe,
  Brain,
  ChevronRight,
} from 'lucide-react';
import { api } from '@/lib/api/client';
import { ORCHESTRATOR_ROUTE } from '@/lib/routes';
import { getPlatformIcon } from '@/components/ui/PlatformIcons';
import { ROLE_LABELS } from '@/lib/constants/agents';
import { formatDistanceToNow } from 'date-fns';
import { cn } from '@/lib/utils';
import type { Role } from '@/types';

// =============================================================================
// Types
// =============================================================================

type DashboardData = Awaited<ReturnType<typeof api.dashboard.getSummary>>;
type DashboardProject = DashboardData['projects'][number];
type DashboardAgent = DashboardProject['agents'][number];
type AttentionItem = DashboardData['attention'][number];

// =============================================================================
// Project type labels (mirrors PROJECT_TYPE_REGISTRY display_name)
// =============================================================================

const TYPE_LABELS: Record<string, string> = {
  slack_digest: 'Slack Recap',
  gmail_digest: 'Gmail Recap',
  notion_digest: 'Notion Recap',
  cross_platform_synthesis: 'Cross-Platform Insights',
  custom: 'Custom Project',
};

// =============================================================================
// Helpers
// =============================================================================

function getAgentIcon(agent: DashboardAgent): React.ReactNode {
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
    return agent.role === 'research'
      ? <Globe className="w-4 h-4 text-muted-foreground" />
      : <Brain className="w-4 h-4 text-muted-foreground" />;
  }
  return getPlatformIcon(providers[0], 'w-4 h-4');
}

function getProjectIcon(project: DashboardProject): React.ReactNode {
  // Platform projects get platform icon; others get folder icon
  const typeKey = project.type_key;
  if (typeKey === 'slack_digest') return getPlatformIcon('slack', 'w-5 h-5');
  if (typeKey === 'gmail_digest') return getPlatformIcon('gmail', 'w-5 h-5');
  if (typeKey === 'notion_digest') return getPlatformIcon('notion', 'w-5 h-5');
  return <Briefcase className="w-5 h-5 text-muted-foreground" />;
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

  const { projects, connected_platforms, attention } = data;
  const hasNoPlatforms = connected_platforms.length === 0;
  const hasNoWork = projects.length === 0;

  // ── Empty state: no platforms connected ──────────────────────────────
  if (hasNoPlatforms && hasNoWork) {
    return (
      <div className="h-full overflow-auto">
        <div className="max-w-2xl mx-auto px-4 md:px-6 py-12 space-y-8">
          <div className="text-center">
            <h1 className="text-2xl font-bold">Welcome to YARNNN</h1>
            <p className="text-muted-foreground mt-2">
              Connect your work platforms and YARNNN will create projects that
              deliver recurring insights — automatically.
            </p>
          </div>

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

          <div className="flex items-center gap-3">
            <div className="flex-1 border-t border-border" />
            <span className="text-xs text-muted-foreground">or</span>
            <div className="flex-1 border-t border-border" />
          </div>

          <button
            onClick={() => router.push(ORCHESTRATOR_ROUTE)}
            className="w-full flex items-center gap-3 p-4 rounded-lg border border-border hover:bg-muted/50 hover:border-primary/30 transition-colors text-left"
          >
            <MessageSquare className="w-5 h-5 text-primary" />
            <div>
              <p className="text-sm font-medium">Ask the Orchestrator</p>
              <p className="text-xs text-muted-foreground">Create projects for topics, research, or tasks — no platform needed</p>
            </div>
            <ArrowRight className="w-4 h-4 text-muted-foreground ml-auto shrink-0" />
          </button>
        </div>
      </div>
    );
  }

  // ── Transitional: platforms connected but no work yet ────────────────
  if (hasNoWork) {
    const unconnected = (['slack', 'gmail', 'notion', 'calendar'] as const).filter(
      (p) => !connected_platforms.includes(p === 'calendar' ? 'google' : p) && !connected_platforms.includes(p)
    );

    return (
      <div className="h-full overflow-auto">
        <div className="max-w-2xl mx-auto px-4 md:px-6 py-12 space-y-8">
          <div className="text-center">
            <h1 className="text-2xl font-bold">Dashboard</h1>
            <p className="text-muted-foreground mt-2">
              Your platforms are syncing. Projects will appear here automatically.
            </p>
          </div>

          <div className="flex items-center justify-center gap-3">
            {connected_platforms.map((p) => (
              <div key={p} className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-green-50 dark:bg-green-950/20 border border-green-200 dark:border-green-900/40">
                {getPlatformIcon(p, 'w-4 h-4')}
                <span className="text-xs font-medium text-green-700 dark:text-green-400 capitalize">{p}</span>
              </div>
            ))}
          </div>

          <div className="grid gap-3">
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

            <button
              onClick={() => router.push(ORCHESTRATOR_ROUTE)}
              className="flex items-center gap-3 p-4 rounded-lg border border-border hover:bg-muted/50 transition-colors text-left"
            >
              <MessageSquare className="w-5 h-5 text-primary" />
              <div>
                <p className="text-sm font-medium">Ask the Orchestrator</p>
                <p className="text-xs text-muted-foreground">Create or configure projects through conversation</p>
              </div>
              <ArrowRight className="w-4 h-4 text-muted-foreground ml-auto shrink-0" />
            </button>
          </div>
        </div>
      </div>
    );
  }

  // ── Normal state: project-first dashboard ────────────────────────────
  return (
    <div className="h-full overflow-auto">
      <div className="max-w-4xl mx-auto px-4 md:px-6 py-6 space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold">Dashboard</h1>
          </div>
          <button
            onClick={() => router.push(ORCHESTRATOR_ROUTE)}
            className="inline-flex items-center gap-2 px-4 py-2 text-sm bg-primary text-primary-foreground rounded-md hover:bg-primary/90"
          >
            <MessageSquare className="w-4 h-4" />
            Ask Orchestrator
          </button>
        </div>

        {/* Attention banners */}
        {attention.length > 0 && (
          <div className="space-y-2">
            {attention.map((item, i) => (
              <AttentionBanner
                key={i}
                item={item}
                onClick={() => {
                  if (item.project_slug) {
                    router.push(`/projects/${item.project_slug}`);
                  } else {
                    router.push(`/agents/${item.agent_id}`);
                  }
                }}
              />
            ))}
          </div>
        )}

        {/* Projects */}
        {projects.length > 0 && (
          <section className="space-y-3">
            {projects.map((project) => (
              <ProjectCard
                key={project.project_slug}
                project={project}
                onClick={() => router.push(`/projects/${project.project_slug}`)}
                onAgentClick={(id) => router.push(`/agents/${id}`)}
              />
            ))}
          </section>
        )}

      </div>
    </div>
  );
}

// =============================================================================
// Sub-components
// =============================================================================

function AttentionBanner({ item, onClick }: { item: AttentionItem; onClick: () => void }) {
  const icon = item.type === 'auto_paused'
    ? <Pause className="w-4 h-4" />
    : <XCircle className="w-4 h-4" />;

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

function ProjectCard({
  project,
  onClick,
  onAgentClick,
}: {
  project: DashboardProject;
  onClick: () => void;
  onAgentClick: (id: string) => void;
}) {
  const typeLabel = project.type_key ? TYPE_LABELS[project.type_key] || project.type_key : null;
  const activeAgents = project.agents.filter((a) => a.status === 'active');
  const pausedAgents = project.agents.filter((a) => a.status === 'paused');

  return (
    <div className="rounded-lg border border-border bg-card overflow-hidden">
      {/* Project header — clickable */}
      <button
        onClick={onClick}
        className="w-full flex items-center gap-3 p-4 hover:bg-muted/50 transition-colors text-left"
      >
        <div className="shrink-0">
          {getProjectIcon(project)}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="text-sm font-semibold truncate">{project.title}</span>
            {typeLabel && (
              <span className="text-xs px-1.5 py-0.5 rounded bg-muted text-muted-foreground shrink-0">
                {typeLabel}
              </span>
            )}
          </div>
          {project.purpose && (
            <p className="text-xs text-muted-foreground mt-0.5 truncate">{project.purpose}</p>
          )}
        </div>
        {project.updated_at && (
          <span className="text-xs text-muted-foreground shrink-0">
            {formatDistanceToNow(new Date(project.updated_at), { addSuffix: true })}
          </span>
        )}
        <ChevronRight className="w-4 h-4 text-muted-foreground shrink-0" />
      </button>

      {/* Nested agents */}
      {project.agents.length > 0 && (
        <div className="border-t border-border">
          {project.agents.map((agent) => (
            <button
              key={agent.id}
              onClick={(e) => { e.stopPropagation(); onAgentClick(agent.id); }}
              className="w-full flex items-center gap-3 px-4 py-2.5 hover:bg-muted/30 transition-colors text-left border-b border-border last:border-b-0"
            >
              <div className="w-5 flex justify-center shrink-0">
                {getAgentIcon(agent)}
              </div>
              <span className="text-sm truncate flex-1">
                {agent.title}
              </span>
              <span className="text-xs text-muted-foreground">
                {ROLE_LABELS[agent.role as Role] ?? agent.role}
              </span>
              {agent.status === 'paused' && (
                <span className="text-xs px-1.5 py-0.5 rounded bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400">
                  Paused
                </span>
              )}
              {agent.last_run_at && (
                <span className="text-xs text-muted-foreground shrink-0">
                  {formatDistanceToNow(new Date(agent.last_run_at), { addSuffix: true })}
                </span>
              )}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

