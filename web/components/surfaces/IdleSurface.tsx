'use client';

/**
 * ADR-023: Supervisor Desk Architecture
 * IdleSurface - Dashboard view showing all domains
 *
 * Priority order (calm control room, not alarm board):
 * 1. System Status - at-a-glance health overview
 * 2. Upcoming Schedule - what's generating soon (primary focus)
 * 3. Attention Items - things needing input (secondary)
 * 4. Quick Actions - create, browse context
 *
 * ADR-033: Platform-First Onboarding
 * - no_platforms: Full platform onboarding prompt
 * - platforms_syncing: Dashboard with sync progress banner
 * - active: Normal dashboard
 */

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import {
  Clock,
  Loader2,
  Pause,
  AlertCircle,
  Calendar,
  FileText,
  ChevronRight,
  CheckCircle2,
  TrendingUp,
  TrendingDown,
  Minus,
  Plus,
} from 'lucide-react';
import { api } from '@/lib/api/client';
import { ORCHESTRATOR_ROUTE } from '@/lib/routes';
import { useDesk } from '@/contexts/DeskContext';
import { usePlatformOnboardingState } from '@/hooks/usePlatformOnboardingState';
import {
  PlatformOnboardingPrompt,
  PlatformSyncingBanner,
  NoPlatformsBanner,
} from '@/components/PlatformOnboardingPrompt';
import { PlatformCardGrid } from '@/components/ui/PlatformCardGrid';
import type { PlatformSummary } from '@/components/ui/PlatformCard';
import { formatDistanceToNow } from 'date-fns';
import { ROLE_LABELS } from '@/lib/constants/agents';
import type { Agent, ScheduleConfig, Document as DocType } from '@/types';

// Format schedule to human readable string
function formatSchedule(schedule?: ScheduleConfig): string | null {
  if (!schedule) return null;
  const { frequency, day, time } = schedule;
  if (frequency === 'daily') return `Daily${time ? ` at ${time}` : ''}`;
  if (frequency === 'weekly') return `Weekly${day ? ` on ${day}` : ''}`;
  if (frequency === 'biweekly') return `Every 2 weeks${day ? ` on ${day}` : ''}`;
  if (frequency === 'monthly') return `Monthly${day ? ` on ${day}` : ''}`;
  if (frequency === 'custom') return 'Custom schedule';
  return frequency;
}

interface DashboardData {
  agents: Agent[];
  memoryCount: number;
  recentDocs: DocType[];
}

export function IdleSurface() {
  const router = useRouter();
  const { setSurface, attention, refreshAttention } = useDesk();

  // ADR-033: Platform-first onboarding state
  const {
    state: onboardingState,
    isLoading: onboardingLoading,
    platformCount,
    platforms,
    hasSyncingPlatforms,
    dismiss: dismissBanner,
    isDismissed,
  } = usePlatformOnboardingState();

  const [loading, setLoading] = useState(true);
  const [data, setData] = useState<DashboardData | null>(null);

  useEffect(() => {
    loadDashboardData();
  }, []);

  const loadDashboardData = async () => {
    try {
      const [agents, memories, docsResult] = await Promise.all([
        api.agents.list().catch(() => []),
        api.userMemories.list().catch(() => []),
        api.documents.list().catch(() => ({ documents: [] })),
      ]);

      setData({
        agents: agents || [],
        memoryCount: memories?.length || 0,
        recentDocs: (docsResult.documents || []).slice(0, 3),
      });
    } catch (err) {
      console.error('Failed to load dashboard:', err);
    } finally {
      setLoading(false);
    }
  };

  // =============================================================================
  // Platform-First Onboarding Callbacks (ADR-033)
  // =============================================================================

  const handleConnectPlatforms = () => {
    // Navigate to settings/integrations
    window.location.href = '/settings';
  };

  const handleSkipOnboarding = () => {
    // Dismiss the onboarding prompt and let user start chatting
    dismissBanner();
  };

  // =============================================================================
  // Loading State
  // =============================================================================

  if (loading || onboardingLoading) {
    return (
      <div className="h-full flex items-center justify-center">
        <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  // =============================================================================
  // Platform-First Onboarding: Full Welcome Experience (ADR-033)
  // =============================================================================

  // Show full platform onboarding if:
  // 1. Onboarding state is no_platforms (no integrations connected)
  // 2. User hasn't dismissed the onboarding
  // Note: We no longer use "no agents" as a fallback - users with platforms
  // but no agents should see the dashboard with platform cards, not onboarding.
  const showPlatformOnboarding =
    !isDismissed && onboardingState === 'no_platforms';

  if (showPlatformOnboarding) {
    return (
      <div className="h-full flex items-center justify-center overflow-auto">
        <PlatformOnboardingPrompt
          onConnectPlatforms={handleConnectPlatforms}
          onSkip={handleSkipOnboarding}
        />
      </div>
    );
  }

  // =============================================================================
  // Active Dashboard
  // =============================================================================

  const activeAgents = data?.agents.filter((d) => d.status === 'active') || [];
  const pausedAgents = data?.agents.filter((d) => d.status === 'paused') || [];

  // Sort active agents by next_run_at (soonest first)
  const upcomingAgents = [...activeAgents].sort((a, b) => {
    if (!a.next_run_at) return 1;
    if (!b.next_run_at) return -1;
    return new Date(a.next_run_at).getTime() - new Date(b.next_run_at).getTime();
  });

  // Find next scheduled agent for status strip
  const nextAgent = upcomingAgents[0];

  // Calculate overall quality trend
  const qualityTrends = activeAgents
    .map((d) => d.quality_trend)
    .filter(Boolean);
  const overallQuality =
    qualityTrends.length === 0
      ? 'stable'
      : qualityTrends.includes('declining')
        ? 'declining'
        : qualityTrends.includes('improving')
          ? 'improving'
          : 'stable';

  // ADR-033: Show syncing banner if platforms are connected but still importing
  const showSyncingBanner = !isDismissed && onboardingState === 'platforms_syncing';

  // Show subtle "connect platforms" banner for users with agents but no platforms
  const showNoPlatformsBanner =
    !isDismissed &&
    platformCount === 0 &&
    data?.agents &&
    data.agents.length > 0;

  return (
    <div className="h-full overflow-auto">
      <div className="max-w-3xl mx-auto px-4 md:px-6 py-6 space-y-6">
        {/* ADR-033: Platform Syncing Banner */}
        {showSyncingBanner && (
          <PlatformSyncingBanner
            syncingCount={hasSyncingPlatforms ? 1 : platformCount}
            onViewProgress={() => window.location.href = '/settings'}
          />
        )}

        {/* ADR-033: No Platforms Banner (for existing users) */}
        {showNoPlatformsBanner && (
          <NoPlatformsBanner
            onConnect={handleConnectPlatforms}
            onDismiss={dismissBanner}
          />
        )}

        {/* System Status Strip */}
        {activeAgents.length > 0 && (
          <div className="flex items-center gap-4 px-4 py-3 bg-muted/30 rounded-lg text-sm">
            <div className="flex items-center gap-2 text-green-600 dark:text-green-500">
              <CheckCircle2 className="w-4 h-4" />
              <span>{activeAgents.length} active</span>
            </div>
            {pausedAgents.length > 0 && (
              <div className="flex items-center gap-2 text-muted-foreground">
                <Pause className="w-3.5 h-3.5" />
                <span>{pausedAgents.length} paused</span>
              </div>
            )}
            <span className="text-muted-foreground">·</span>
            {nextAgent?.next_run_at && (
              <div className="flex items-center gap-1.5 text-muted-foreground">
                <Clock className="w-3.5 h-3.5" />
                <span>
                  Next:{' '}
                  <span className="text-foreground">{nextAgent.title}</span>{' '}
                  {formatDistanceToNow(new Date(nextAgent.next_run_at), { addSuffix: true })}
                </span>
              </div>
            )}
            {overallQuality !== 'stable' && (
              <>
                <span className="text-muted-foreground">·</span>
                <div className="flex items-center gap-1.5">
                  {overallQuality === 'improving' ? (
                    <TrendingUp className="w-3.5 h-3.5 text-green-500" />
                  ) : (
                    <TrendingDown className="w-3.5 h-3.5 text-amber-500" />
                  )}
                  <span className="text-muted-foreground">
                    Quality {overallQuality}
                  </span>
                </div>
              </>
            )}
          </div>
        )}

        {/* ADR-033: Platform Cards - Forest View */}
        <PlatformCardGrid
          onPlatformClick={(platform: PlatformSummary) => {
            // ADR-037: Navigate to integration route
            router.push(`/integrations/${platform.provider}`);
          }}
        />

        {/* Upcoming Schedule (primary focus) */}
        <DashboardSection
          icon={<Calendar className="w-4 h-4" />}
          title="Upcoming Schedule"
          action={
            data && data.agents.length > 0 ? (
              <button
                onClick={() => router.push('/agents')}
                className="text-xs text-muted-foreground hover:text-foreground flex items-center gap-1"
              >
                All agents ({data.agents.length})
                <ChevronRight className="w-3 h-3" />
              </button>
            ) : undefined
          }
        >
          {upcomingAgents.length > 0 ? (
            upcomingAgents.slice(0, 5).map((d) => (
              <AgentCard
                key={d.id}
                agent={d}
                onClick={() => router.push(`/agents/${d.id}`)}
              />
            ))
          ) : (
            <div className="text-center py-8 text-muted-foreground">
              <Calendar className="w-8 h-8 mx-auto mb-2 opacity-50" />
              <p className="text-sm">No scheduled agents yet</p>
              <p className="text-xs mt-1">Ask TP to help you set one up</p>
            </div>
          )}
        </DashboardSection>

        {/* Needs Attention (secondary) */}
        {attention.length > 0 && (
          <DashboardSection
            icon={<AlertCircle className="w-4 h-4 text-amber-500" />}
            title={`Review Staged (${attention.length})`}
          >
            <div className="space-y-2">
              {attention.map((item) => (
                <button
                  key={item.runId}
                  onClick={() =>
                    setSurface({
                      type: 'agent-review',
                      agentId: item.agentId,
                      runId: item.runId,
                    })
                  }
                  className="w-full p-3 border border-amber-200 dark:border-amber-900 bg-amber-50/50 dark:bg-amber-950/20 rounded-lg hover:bg-amber-100 dark:hover:bg-amber-950/40 text-left"
                >
                  <div className="flex items-center justify-between">
                    <span className="text-sm">{item.title}</span>
                    <span className="text-xs text-muted-foreground">
                      {formatDistanceToNow(new Date(item.stagedAt), { addSuffix: true })}
                    </span>
                  </div>
                </button>
              ))}
            </div>
          </DashboardSection>
        )}

        {/* Quick Actions */}
        <div className="grid grid-cols-2 gap-3">
          {/* Create Agent - Primary (ADR-035: Full-screen surface) */}
          <button
            onClick={() => router.push(`${ORCHESTRATOR_ROUTE}?create`)}
            className="p-4 border-2 border-dashed border-primary/30 rounded-lg hover:border-primary/50 hover:bg-primary/5 text-left"
          >
            <div className="flex items-center gap-2 mb-1">
              <Plus className="w-4 h-4 text-primary" />
              <span className="text-sm font-medium">New Agent</span>
            </div>
            <p className="text-xs text-muted-foreground">Set up recurring work</p>
          </button>

          {/* Documents - ADR-037: Navigate to route */}
          <button
            onClick={() => router.push('/docs')}
            className="p-4 border border-border rounded-lg hover:bg-muted text-left"
          >
            <div className="flex items-center gap-2 mb-1">
              <FileText className="w-4 h-4 text-muted-foreground" />
              <span className="text-sm font-medium">Documents</span>
            </div>
            <p className="text-xs text-muted-foreground">
              {data?.recentDocs?.length || 0} uploaded
            </p>
          </button>
        </div>
      </div>
    </div>
  );
}

// =============================================================================
// Sub-components
// =============================================================================

function DashboardSection({
  icon,
  title,
  action,
  children,
}: {
  icon?: React.ReactNode;
  title: string;
  action?: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <div>
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-sm font-medium flex items-center gap-2">
          {icon}
          {title}
        </h2>
        {action}
      </div>
      <div className="space-y-2">{children}</div>
    </div>
  );
}

function AgentCard({
  agent,
  onClick,
}: {
  agent: Agent;
  onClick: () => void;
}) {
  const typeLabel =
    ROLE_LABELS[agent.role] || agent.role;

  // Quality indicator
  const QualityIndicator = () => {
    if (!agent.quality_trend) return null;
    if (agent.quality_trend === 'improving') {
      return (
        <span title="Quality improving">
          <TrendingUp className="w-3 h-3 text-green-500" />
        </span>
      );
    }
    if (agent.quality_trend === 'declining') {
      return (
        <span title="Quality declining">
          <TrendingDown className="w-3 h-3 text-amber-500" />
        </span>
      );
    }
    return (
      <span title="Quality stable">
        <Minus className="w-3 h-3 text-muted-foreground" />
      </span>
    );
  };

  return (
    <button
      onClick={onClick}
      className="w-full p-3 border border-border rounded-lg hover:bg-muted text-left"
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          {agent.status === 'paused' ? (
            <Pause className="w-3 h-3 text-amber-500" />
          ) : (
            <span className="w-2 h-2 rounded-full bg-green-500" />
          )}
          <div>
            <div className="flex items-center gap-2">
              <span className="text-sm font-medium">{agent.title}</span>
              <QualityIndicator />
            </div>
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <span className="px-1.5 py-0.5 bg-muted rounded text-[10px] font-medium">
                {typeLabel}
              </span>
              {formatSchedule(agent.schedule) && (
                <span>{formatSchedule(agent.schedule)}</span>
              )}
            </div>
          </div>
        </div>
        {agent.next_run_at && (
          <span className="text-xs text-muted-foreground flex items-center gap-1">
            <Clock className="w-3 h-3" />
            {formatDistanceToNow(new Date(agent.next_run_at), { addSuffix: true })}
          </span>
        )}
      </div>
    </button>
  );
}
