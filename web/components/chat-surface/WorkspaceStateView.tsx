'use client';

/**
 * WorkspaceStateView — Overview modal for /chat (ADR-165 v8).
 *
 * Four peer tabs, all read-only, each mirroring a slice of TP's compact
 * index (format_compact_index, ADR-159):
 *
 *   [Eye]      What I know     → workspace richness across identity/brand/team/work/knowledge/platforms/budget
 *   [Bell]     Heads up        → gap + flag signals TP wants to surface, with "Ask TP" one-click prompts
 *   [History]  Last time       → cross-session memory (AWARENESS.md + recent sessions)
 *   [Activity] Team activity   → recent runs + coming up (thin glance — full view lives in /work)
 *
 * No write forms. No isEmpty prop. No soft gate. Tabs are always visible when
 * the modal is open. Default tab on manual open is `overview` — the honest
 * "show me the state" answer.
 *
 * The Onboarding modal is a separate sibling surface (OnboardingModal.tsx).
 * This modal does NOT handle cold-start capture.
 *
 * The only action affordance in this modal is the "Ask TP" button in the
 * Heads up tab, which sends a pre-composed prompt to TP via sendMessage.
 * The modal closes on click and the user sees TP's response in the chat
 * stream. This preserves the single intelligence layer (ADR-156) — the
 * modal never calls tools directly, all write intent routes through chat.
 */

import { useEffect, useMemo, useState } from 'react';
import {
  X,
  Eye,
  Bell,
  History,
  Activity,
  CheckCircle2,
  Clock3,
  AlertCircle,
  Sparkles,
  PauseCircle,
  ArrowUpRight,
  FileText,
  Users,
  Zap,
  ClipboardList,
  FolderOpen,
} from 'lucide-react';
import Link from 'next/link';
import { api } from '@/lib/api/client';
import { getAgentSlug } from '@/lib/agent-identity';
import { MarkdownRenderer } from '@/components/shared/MarkdownRenderer';
import { taskModeLabel, type Agent, type Task } from '@/types';
import { cn } from '@/lib/utils';
import type { WorkspaceStateLead } from '@/lib/workspace-state-meta';

interface WorkspaceStateViewProps {
  open: boolean;
  /** Which tab to open on first mount. If null, defaults to `overview`. */
  lead: WorkspaceStateLead | null;
  agents: Agent[];
  tasks: Task[];
  dataLoading: boolean;
  /** Optional reason TP passed when opening the surface (rendered in header). */
  reason?: string | null;
  onClose: () => void;
  /**
   * Called when the user clicks "Ask TP" in the Heads up tab.
   * Implementation should call sendMessage(prompt) and close the modal.
   */
  onAskTP: (prompt: string) => void;
  /**
   * Called when the user clicks the identity-empty "Ask TP" card,
   * which routes to opening the Onboarding modal instead of chat.
   */
  onOpenOnboarding: () => void;
  /**
   * Called when the user clicks "Set up work" from the idle-agents Heads Up flag.
   * Opens TaskSetupModal, pre-filled with idle agent names as notes.
   */
  onOpenTaskSetup: (initialNotes: string) => void;
}

// =============================================================================
// Component
// =============================================================================

export function WorkspaceStateView({
  open,
  lead,
  agents,
  tasks,
  dataLoading,
  reason,
  onClose,
  onAskTP,
  onOpenOnboarding,
  onOpenTaskSetup,
}: WorkspaceStateViewProps) {
  // Active tab — initialized from `lead` prop, falls back to `overview`.
  const initialLead = lead ?? 'overview';
  const [activeTab, setActiveTab] = useState<WorkspaceStateLead>(initialLead);

  // When the lead prop changes (TP opens with a different tab), follow it.
  useEffect(() => {
    if (lead) setActiveTab(lead);
  }, [lead]);

  // Esc closes the modal. Body scroll lock while open.
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    window.addEventListener('keydown', onKey);
    return () => {
      document.body.style.overflow = prevOverflow;
      window.removeEventListener('keydown', onKey);
    };
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-foreground/40 px-4 py-[10vh] backdrop-blur-sm animate-in fade-in duration-150"
      role="dialog"
      aria-modal="true"
      aria-label="Overview"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <section
        className="w-full max-w-2xl animate-in fade-in zoom-in-95 duration-200"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="rounded-xl border border-border bg-background shadow-2xl">
          {/* Header — title + optional reason + close */}
          <header className="flex items-start justify-between border-b border-border px-4 py-2.5">
            <div className="min-w-0">
              <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground/70">
                Overview
              </p>
              {reason ? (
                <p className="mt-0.5 text-sm text-foreground">{reason}</p>
              ) : null}
            </div>
            <button
              type="button"
              onClick={onClose}
              className="rounded p-1 text-muted-foreground/40 hover:bg-muted hover:text-muted-foreground"
              aria-label="Close overview"
            >
              <X className="h-3.5 w-3.5" />
            </button>
          </header>

          {/* Tab bar — always visible. Four peer tabs in TP's voice. */}
          <nav
            aria-label="Overview tabs"
            className="flex items-center gap-1 border-b border-border px-2 py-1.5"
          >
            <TabButton
              active={activeTab === 'overview'}
              icon={Eye}
              label="What I know"
              onClick={() => setActiveTab('overview')}
            />
            <TabButton
              active={activeTab === 'flags'}
              icon={Bell}
              label="Heads up"
              onClick={() => setActiveTab('flags')}
            />
            <TabButton
              active={activeTab === 'recap'}
              icon={History}
              label="Last time"
              onClick={() => setActiveTab('recap')}
            />
            <TabButton
              active={activeTab === 'activity'}
              icon={Activity}
              label="Team activity"
              onClick={() => setActiveTab('activity')}
            />
          </nav>

          {/* Active tab content */}
          <div className="max-h-[60vh] overflow-y-auto">
            {activeTab === 'overview' && (
              <OverviewTab agents={agents} tasks={tasks} loading={dataLoading} onAskTP={onAskTP} onClose={onClose} />
            )}
            {activeTab === 'flags' && (
              <FlagsTab
                agents={agents}
                tasks={tasks}
                loading={dataLoading}
                onAskTP={onAskTP}
                onOpenOnboarding={onOpenOnboarding}
                onClose={onClose}
                onOpenTaskSetup={onOpenTaskSetup}
              />
            )}
            {activeTab === 'recap' && <RecapTab />}
            {activeTab === 'activity' && (
              <ActivityTab agents={agents} tasks={tasks} loading={dataLoading} />
            )}
          </div>
        </div>
      </section>
    </div>
  );
}

// =============================================================================
// Tab button
// =============================================================================

interface TabButtonProps {
  active: boolean;
  icon: React.ElementType;
  label: string;
  onClick: () => void;
}

function TabButton({ active, icon: Icon, label, onClick }: TabButtonProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        'flex items-center gap-1.5 rounded-md px-2.5 py-1 text-xs font-medium transition-colors',
        active
          ? 'bg-foreground text-background'
          : 'text-muted-foreground hover:bg-muted hover:text-foreground',
      )}
    >
      <Icon className="h-3.5 w-3.5" />
      <span>{label}</span>
    </button>
  );
}

// =============================================================================
// Tab 1 — "What I know" — the honest mirror
// =============================================================================

interface ProfileInfo {
  name?: string | null;
  role?: string | null;
  company?: string | null;
}

interface BrandInfo {
  exists: boolean;
  richness: 'empty' | 'sparse' | 'rich';
}

function classifyRichness(content: string | null | undefined): 'empty' | 'sparse' | 'rich' {
  if (!content || !content.trim()) return 'empty';
  const stripped = content.trim();
  if (stripped.length < 100 || stripped.split('\n').length < 3) return 'sparse';
  return 'rich';
}

function richnessBadge(richness: 'empty' | 'sparse' | 'rich') {
  const cls =
    richness === 'rich'
      ? 'bg-green-500/10 text-green-700 dark:text-green-400'
      : richness === 'sparse'
        ? 'bg-amber-500/10 text-amber-700 dark:text-amber-400'
        : 'bg-muted text-muted-foreground';
  const label = richness === 'rich' ? 'Rich' : richness === 'sparse' ? 'Sparse' : 'Empty';
  return (
    <span className={cn('rounded px-1.5 py-0.5 text-[10px] font-medium', cls)}>
      {label}
    </span>
  );
}

function OverviewTab({
  agents,
  tasks,
  loading,
  onAskTP,
  onClose,
}: {
  agents: Agent[];
  tasks: Task[];
  loading: boolean;
  onAskTP: (prompt: string) => void;
  onClose: () => void;
}) {
  const [profile, setProfile] = useState<ProfileInfo | null>(null);
  const [brand, setBrand] = useState<BrandInfo | null>(null);
  const [platformCount, setPlatformCount] = useState<number>(0);
  const [fetching, setFetching] = useState(true);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setFetching(true);
      try {
        const [p, b, i] = await Promise.all([
          api.profile.get().catch(() => null),
          api.brand.get().catch(() => ({ content: null, exists: false })),
          api.integrations.list().catch(() => ({ integrations: [] })),
        ]);
        if (cancelled) return;
        setProfile(p);
        setBrand({
          exists: !!(b as { exists?: boolean }).exists,
          richness: classifyRichness((b as { content?: string | null }).content),
        });
        const connected = (i.integrations || []).filter(
          (it: { status: string }) => it.status === 'active' || it.status === 'connected',
        );
        setPlatformCount(connected.length);
      } catch {
        // Silently degrade — the tab still renders with what it has
      } finally {
        if (!cancelled) setFetching(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  if (loading || fetching) {
    return (
      <div className="px-5 py-8 text-sm text-muted-foreground">Reading your workspace...</div>
    );
  }

  const identityRichness: 'empty' | 'sparse' | 'rich' = profile
    ? classifyRichness(
        [profile.name, profile.role, profile.company].filter(Boolean).join(' '),
      )
    : 'empty';

  const domainAgents = agents.filter(
    (a) => {
        const cls = a.agent_class || 'specialist';
        return cls === 'specialist' || cls === 'domain-steward';
      },
  );
  const BOT_ROLES: ReadonlySet<string> = new Set(['slack_bot', 'notion_bot', 'github_bot']);
  const bots = agents.filter((a) => BOT_ROLES.has(a.role as string));

  const activeTasks = tasks.filter((t) => t.status === 'active');
  const pausedTasks = tasks.filter((t) => t.status === 'paused');

  const contextTasks = tasks.filter((t) => t.output_kind === 'accumulates_context');
  const deliverableTasks = tasks.filter((t) => t.output_kind === 'produces_deliverable');

  return (
    <div className="space-y-4 p-4">
      <p className="text-xs text-muted-foreground/70">
        Here's everything I currently know about your workspace.
      </p>

      {/* Identity & Brand */}
      <section>
        <h3 className="text-[10px] font-medium uppercase tracking-wide text-muted-foreground/60">
          About you
        </h3>
        <div className="mt-2 space-y-1.5">
          <OverviewRow
            label="Identity"
            value={
              profile?.name || profile?.role || profile?.company
                ? [profile.name, profile.role, profile.company].filter(Boolean).join(' · ')
                : 'Not captured yet'
            }
            badge={richnessBadge(identityRichness)}
            href="/context"
          />
          <OverviewRow
            label="Brand"
            value={brand?.exists ? 'Captured' : 'Not captured yet'}
            badge={richnessBadge(brand?.richness || 'empty')}
            href="/context"
          />
        </div>
      </section>

      {/* Team */}
      <section>
        <h3 className="text-[10px] font-medium uppercase tracking-wide text-muted-foreground/60">
          Team
        </h3>
        <div className="mt-2 grid grid-cols-2 gap-2">
          <OverviewStat
            icon={Users}
            value={domainAgents.length}
            label={`${domainAgents.length === 1 ? 'specialist' : 'specialists'}`}
            href="/agents"
          />
          <OverviewStat
            icon={Zap}
            value={bots.length}
            label={`platform ${bots.length === 1 ? 'bot' : 'bots'}`}
            href="/agents"
          />
        </div>
      </section>

      {/* Work */}
      <section>
        <h3 className="text-[10px] font-medium uppercase tracking-wide text-muted-foreground/60">
          Work
        </h3>
        <div className="mt-2 grid grid-cols-2 gap-2">
          <OverviewStat
            icon={Clock3}
            value={activeTasks.length}
            label={`active ${activeTasks.length === 1 ? 'task' : 'tasks'}`}
            href={activeTasks.length > 0 ? '/work' : undefined}
            onEmpty={() => { onClose(); onAskTP('I have no active tasks yet. What should my team be working on?'); }}
          />
          <OverviewStat
            icon={PauseCircle}
            value={pausedTasks.length}
            label={`paused ${pausedTasks.length === 1 ? 'task' : 'tasks'}`}
            href={pausedTasks.length > 0 ? '/work' : undefined}
          />
        </div>
      </section>

      {/* Knowledge */}
      <section>
        <h3 className="text-[10px] font-medium uppercase tracking-wide text-muted-foreground/60">
          Knowledge
        </h3>
        <div className="mt-2 grid grid-cols-2 gap-2">
          <OverviewStat
            icon={FolderOpen}
            value={contextTasks.length}
            label={`context ${contextTasks.length === 1 ? 'track' : 'tracks'}`}
            href={contextTasks.length > 0 ? '/context' : undefined}
            onEmpty={() => { onClose(); onAskTP('I have no context tracking tasks yet. Which domains should my team be tracking?'); }}
          />
          <OverviewStat
            icon={ClipboardList}
            value={deliverableTasks.length}
            label={`${deliverableTasks.length === 1 ? 'report' : 'reports'}`}
            href={deliverableTasks.length > 0 ? '/work' : undefined}
            onEmpty={() => { onClose(); onAskTP('I have no report tasks yet. What kind of recurring reports would be useful for my workspace?'); }}
          />
        </div>
      </section>

      {/* Platforms */}
      <section>
        <h3 className="text-[10px] font-medium uppercase tracking-wide text-muted-foreground/60">
          Platforms
        </h3>
        <div className="mt-2">
          <OverviewRow
            label="Connected"
            value={
              platformCount === 0
                ? 'None yet'
                : `${platformCount} ${platformCount === 1 ? 'integration' : 'integrations'}`
            }
            href="/context"
          />
        </div>
      </section>
    </div>
  );
}

function OverviewRow({
  label,
  value,
  badge,
  href,
}: {
  label: string;
  value: string;
  badge?: React.ReactNode;
  href?: string;
}) {
  const content = (
    <div className="flex items-center justify-between gap-2 rounded-md border border-border/60 bg-muted/10 px-3 py-2 text-sm transition-colors hover:bg-muted/30">
      <div className="flex min-w-0 items-center gap-2">
        <span className="text-xs text-muted-foreground">{label}</span>
        <span className="truncate text-foreground/90">{value}</span>
      </div>
      <div className="flex shrink-0 items-center gap-2">
        {badge}
        {href && <ArrowUpRight className="h-3 w-3 text-muted-foreground/40" />}
      </div>
    </div>
  );
  return href ? <Link href={href}>{content}</Link> : content;
}

function OverviewStat({
  icon: Icon,
  value,
  label,
  href,
  onEmpty,
}: {
  icon: React.ElementType;
  value: number;
  label: string;
  href?: string;
  onEmpty?: () => void;
}) {
  const isEmpty = value === 0 && !!onEmpty;
  const content = (
    <div className={cn(
      'rounded-md border border-border/60 bg-muted/10 p-3 transition-colors hover:bg-muted/30',
      isEmpty && 'cursor-pointer',
    )}>
      <div className="flex items-center gap-2">
        <Icon className="h-3.5 w-3.5 text-muted-foreground/60" />
        <span className="text-lg font-semibold tabular-nums">{value}</span>
      </div>
      <p className="mt-0.5 text-[11px] text-muted-foreground">{label}</p>
    </div>
  );
  if (href) return <Link href={href}>{content}</Link>;
  if (isEmpty) return <button type="button" onClick={onEmpty} className="text-left w-full">{content}</button>;
  return content;
}

// =============================================================================
// Tab 2 — "Heads up" — gap + flag signals
// =============================================================================

interface FlagCard {
  id: string;
  severity: 'info' | 'warn' | 'alert';
  title: string;
  detail?: string;
  action?: {
    label: string;
    onClick: () => void;
  };
}

function FlagsTab({
  agents,
  tasks,
  loading,
  onAskTP,
  onOpenOnboarding,
  onClose,
  onOpenTaskSetup,
}: {
  agents: Agent[];
  tasks: Task[];
  loading: boolean;
  onAskTP: (prompt: string) => void;
  onOpenOnboarding: () => void;
  onClose: () => void;
  onOpenTaskSetup: (initialNotes: string) => void;
}) {
  const [identityMissing, setIdentityMissing] = useState<boolean>(false);
  const [fetching, setFetching] = useState(true);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const profile = await api.profile.get().catch(() => null);
        if (cancelled) return;
        const hasIdentity = !!(
          profile &&
          (profile.name?.trim() || profile.role?.trim() || profile.company?.trim())
        );
        setIdentityMissing(!hasIdentity);
      } catch {
        setIdentityMissing(false);
      } finally {
        if (!cancelled) setFetching(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const flags = useMemo<FlagCard[]>(() => {
    const items: FlagCard[] = [];

    // Identity empty → opens Onboarding modal
    if (identityMissing) {
      items.push({
        id: 'identity-empty',
        severity: 'info',
        title: "I don't know much about you yet",
        detail: 'A few quick details will help me infer your context.',
        action: {
          label: 'Tell me about yourself',
          onClick: onOpenOnboarding,
        },
      });
    }

    // No tasks yet
    if (tasks.length === 0) {
      items.push({
        id: 'no-tasks',
        severity: 'info',
        title: 'Nothing is running yet',
        detail: 'Your team is ready — they just need something to work on.',
        action: {
          label: 'Help me set up my first task',
          onClick: () =>
            onAskTP(
              'Help me set up my first task. What do you suggest based on my workspace?',
            ),
        },
      });
    }

    // Domain agents without tasks
    const domainAgents = agents.filter(
      (a) => {
        const cls = a.agent_class || 'specialist';
        return cls === 'specialist' || cls === 'domain-steward';
      },
    );
    const idle = domainAgents.filter((agent) => {
      const slug = getAgentSlug(agent);
      return !tasks.some((t) => t.agent_slugs?.includes(slug));
    });
    if (idle.length > 0) {
      const names = idle
        .slice(0, 3)
        .map((a) => a.title)
        .join(', ');
      items.push({
        id: 'agents-idle',
        severity: 'info',
        title: `${idle.length} ${idle.length === 1 ? 'agent has' : 'agents have'} no work yet`,
        detail: names,
        action: {
          label: 'Set up work for them',
          onClick: () => {
            onClose();
            onOpenTaskSetup(`${names} ${idle.length === 1 ? 'has' : 'have'} no tasks yet.`);
          },
        },
      });
    }

    // Stale tasks — haven't run in a while given their schedule
    const SCHEDULE_HOURS: Record<string, number> = {
      daily: 24,
      weekly: 24 * 7,
      biweekly: 24 * 14,
      monthly: 24 * 30,
    };
    const now = Date.now();
    const stale = tasks.filter((t) => {
      if (t.status !== 'active') return false;
      const schedule = (t.schedule || '').toLowerCase();
      const hours = SCHEDULE_HOURS[schedule];
      if (!hours) return false;
      if (!t.last_run_at) return false;
      const lastRun = new Date(t.last_run_at).getTime();
      if (Number.isNaN(lastRun)) return false;
      return now - lastRun > hours * 2 * 60 * 60 * 1000;
    });
    if (stale.length > 0) {
      items.push({
        id: 'stale-tasks',
        severity: 'warn',
        title: `${stale.length} ${stale.length === 1 ? 'task hasn\u2019t' : 'tasks haven\u2019t'} run in a while`,
        detail: stale
          .slice(0, 3)
          .map((t) => t.title)
          .join(', '),
        action: {
          label: 'Look into why',
          onClick: () =>
            onAskTP(
              `${stale.length} of my tasks haven't run recently. Can you check what's going on?`,
            ),
        },
      });
    }

    return items;
  }, [identityMissing, agents, tasks, onAskTP, onOpenOnboarding, onClose, onOpenTaskSetup]);

  if (loading || fetching) {
    return (
      <div className="px-5 py-8 text-sm text-muted-foreground">Checking in on things...</div>
    );
  }

  if (flags.length === 0) {
    return (
      <div className="px-5 py-10 text-center">
        <CheckCircle2 className="mx-auto h-8 w-8 text-green-500/80" />
        <p className="mt-2 text-sm font-medium text-foreground">Nothing worth flagging right now.</p>
        <p className="mt-1 text-xs text-muted-foreground">Your team is running steady. I'll pipe up if anything changes.</p>
      </div>
    );
  }

  return (
    <div className="space-y-2 p-4">
      <p className="text-xs text-muted-foreground/70">Here are a few things I'd like you to notice.</p>
      {flags.map((flag) => (
        <FlagCardView key={flag.id} flag={flag} />
      ))}
    </div>
  );
}

function FlagCardView({ flag }: { flag: FlagCard }) {
  const iconCls =
    flag.severity === 'alert'
      ? 'text-red-500'
      : flag.severity === 'warn'
        ? 'text-amber-500'
        : 'text-muted-foreground/60';
  return (
    <div className="rounded-lg border border-border/70 bg-muted/10 p-3">
      <div className="flex items-start gap-2">
        <AlertCircle className={cn('mt-0.5 h-4 w-4 shrink-0', iconCls)} />
        <div className="min-w-0 flex-1">
          <p className="text-sm font-medium text-foreground">{flag.title}</p>
          {flag.detail && (
            <p className="mt-0.5 truncate text-xs text-muted-foreground">{flag.detail}</p>
          )}
          {flag.action && (
            <button
              type="button"
              onClick={flag.action.onClick}
              className="mt-2 inline-flex items-center gap-1 rounded border border-border bg-background px-2 py-1 text-[11px] font-medium text-foreground hover:bg-muted"
            >
              <Sparkles className="h-3 w-3" />
              {flag.action.label}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

// =============================================================================
// Tab 3 — "Last time" — cross-session memory
// =============================================================================

interface RecentSession {
  id: string;
  created_at: string;
  preview?: string;
}

function RecapTab() {
  const [awareness, setAwareness] = useState<string | null>(null);
  const [sessions, setSessions] = useState<RecentSession[]>([]);
  const [fetching, setFetching] = useState(true);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [fileResp, historyResp] = await Promise.all([
          api.workspace
            .getFile('/workspace/AWARENESS.md')
            .catch(() => null),
          api.chat.globalHistory(5).catch(() => ({ sessions: [] })),
        ]);
        if (cancelled) return;
        const content = fileResp?.content?.trim() || null;
        setAwareness(content && content.length > 0 ? content : null);
        const raw = (historyResp.sessions || []) as Array<{
          id: string;
          created_at: string;
          messages?: Array<{ role: string; content: string }>;
        }>;
        setSessions(
          raw.map((s) => {
            const firstUser = s.messages?.find((m) => m.role === 'user');
            return {
              id: s.id,
              created_at: s.created_at,
              preview: firstUser?.content?.slice(0, 120),
            };
          }),
        );
      } catch {
        if (!cancelled) {
          setAwareness(null);
          setSessions([]);
        }
      } finally {
        if (!cancelled) setFetching(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  if (fetching) {
    return (
      <div className="px-5 py-8 text-sm text-muted-foreground">Flipping back through my notes...</div>
    );
  }

  if (!awareness && sessions.length === 0) {
    return (
      <div className="px-5 py-10 text-center">
        <History className="mx-auto h-8 w-8 text-muted-foreground/40" />
        <p className="mt-2 text-sm font-medium text-foreground">This is our first conversation.</p>
        <p className="mt-1 text-xs text-muted-foreground">
          I'll start keeping notes between sessions so we can pick up where we left off.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4 p-4">
      <p className="text-xs text-muted-foreground/70">Here's what I remember from before.</p>

      {awareness && (
        <section>
          <h3 className="flex items-center gap-1.5 text-[10px] font-medium uppercase tracking-wide text-muted-foreground/60">
            <FileText className="h-3 w-3" />
            My shift notes
          </h3>
          <div className="mt-2 rounded-lg border border-border/70 bg-muted/10 p-3">
            <div className="prose prose-sm max-w-none dark:prose-invert text-xs">
              <MarkdownRenderer content={awareness.length > 1000 ? awareness.slice(0, 1000) + '\u2026' : awareness} />
            </div>
          </div>
        </section>
      )}

      {sessions.length > 0 && (
        <section>
          <h3 className="text-[10px] font-medium uppercase tracking-wide text-muted-foreground/60">
            Recent sessions
          </h3>
          <div className="mt-2 space-y-1.5">
            {sessions.map((s) => (
              <div
                key={s.id}
                className="rounded-md border border-border/60 bg-muted/10 px-3 py-2"
              >
                <p className="text-[11px] text-muted-foreground/70">
                  {formatRelativeTime(s.created_at) || s.created_at.slice(0, 10)}
                </p>
                {s.preview && (
                  <p className="mt-0.5 truncate text-xs text-foreground/80">{s.preview}</p>
                )}
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}

// =============================================================================
// Tab 4 — "Team activity" — recent runs + coming up
// =============================================================================

function formatRelativeTime(value?: string): string | null {
  if (!value) return null;
  const then = new Date(value).getTime();
  if (Number.isNaN(then)) return null;
  const diff = Date.now() - then;
  const future = diff < 0;
  const abs = Math.abs(diff);
  const mins = Math.floor(abs / 60000);
  if (mins < 1) return future ? 'soon' : 'just now';
  if (mins < 60) return future ? `in ${mins}m` : `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return future ? `in ${hours}h` : `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return future ? `in ${days}d` : `${days}d ago`;
}

function agentTitleFor(task: Task, agents: Agent[]): string {
  const slug = task.agent_slugs?.[0];
  if (!slug) return 'TP';
  const agent = agents.find((a) => getAgentSlug(a) === slug);
  return agent?.title || slug;
}

function ActivityTab({
  agents,
  tasks,
  loading,
}: {
  agents: Agent[];
  tasks: Task[];
  loading: boolean;
}) {
  const recentRuns = useMemo(() => {
    return tasks
      .filter((t) => !!t.last_run_at)
      .sort(
        (a, b) =>
          new Date(b.last_run_at || '').getTime() -
          new Date(a.last_run_at || '').getTime(),
      )
      .slice(0, 5);
  }, [tasks]);

  const comingUp = useMemo(() => {
    return tasks
      .filter((t) => t.status === 'active' && !!t.next_run_at)
      .sort(
        (a, b) =>
          new Date(a.next_run_at || '').getTime() -
          new Date(b.next_run_at || '').getTime(),
      )
      .slice(0, 5);
  }, [tasks]);

  if (loading) {
    return (
      <div className="px-5 py-8 text-sm text-muted-foreground">Peeking at your team...</div>
    );
  }

  if (recentRuns.length === 0 && comingUp.length === 0) {
    return (
      <div className="px-5 py-10 text-center">
        <Activity className="mx-auto h-8 w-8 text-muted-foreground/40" />
        <p className="mt-2 text-sm font-medium text-foreground">Your team hasn't run anything yet.</p>
        <p className="mt-1 text-xs text-muted-foreground">
          Once tasks are set up, you'll see recent runs and what's coming up here.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4 p-4">
      <p className="text-xs text-muted-foreground/70">Here's what your team has been up to.</p>

      {recentRuns.length > 0 && (
        <section>
          <h3 className="text-[10px] font-medium uppercase tracking-wide text-muted-foreground/60">
            Recent runs
          </h3>
          <div className="mt-2 space-y-1.5">
            {recentRuns.map((task) => (
              <TaskRow
                key={`run-${task.id}`}
                task={task}
                agents={agents}
                timestamp={task.last_run_at}
                icon={CheckCircle2}
                tone="positive"
              />
            ))}
          </div>
        </section>
      )}

      {comingUp.length > 0 && (
        <section>
          <h3 className="text-[10px] font-medium uppercase tracking-wide text-muted-foreground/60">
            Coming up
          </h3>
          <div className="mt-2 space-y-1.5">
            {comingUp.map((task) => (
              <TaskRow
                key={`next-${task.id}`}
                task={task}
                agents={agents}
                timestamp={task.next_run_at}
                icon={Clock3}
                tone="neutral"
              />
            ))}
          </div>
        </section>
      )}

      <div className="pt-1">
        <Link
          href="/work"
          className="inline-flex items-center gap-1 text-[11px] text-muted-foreground hover:text-foreground"
        >
          <ArrowUpRight className="h-3 w-3" />
          See all work
        </Link>
      </div>
    </div>
  );
}

function TaskRow({
  task,
  agents,
  timestamp,
  icon: Icon,
  tone,
}: {
  task: Task;
  agents: Agent[];
  timestamp?: string | null;
  icon: React.ElementType;
  tone: 'positive' | 'neutral';
}) {
  const agentLabel = agentTitleFor(task, agents);
  const rel = formatRelativeTime(timestamp || undefined);
  return (
    <Link
      href={`/work?task=${encodeURIComponent(task.slug)}`}
      className="flex items-start gap-2 rounded-md border border-border/60 bg-muted/10 p-2.5 text-sm transition-colors hover:bg-muted/30"
    >
      <Icon
        className={cn(
          'mt-0.5 h-3.5 w-3.5 shrink-0',
          tone === 'positive' ? 'text-green-600' : 'text-muted-foreground/60',
        )}
      />
      <div className="min-w-0 flex-1">
        <div className="flex min-w-0 items-center gap-2">
          <p className="truncate text-sm font-medium text-foreground">{task.title}</p>
          <span className="shrink-0 rounded border border-border bg-background px-1.5 py-0.5 text-[10px] text-muted-foreground">
            {taskModeLabel(task.mode)}
          </span>
        </div>
        <p className="mt-0.5 truncate text-[11px] text-muted-foreground">{agentLabel}</p>
      </div>
      {rel && <span className="shrink-0 text-[11px] text-muted-foreground/60">{rel}</span>}
    </Link>
  );
}
