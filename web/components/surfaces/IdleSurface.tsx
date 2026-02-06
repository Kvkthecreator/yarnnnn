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
 * Handles three onboarding states:
 * - cold_start: Full welcome experience (WelcomePrompt)
 * - minimal_context: Normal dashboard with context banner
 * - active: Normal dashboard
 */

import { useState, useEffect, useRef } from 'react';
import {
  Clock,
  Loader2,
  Pause,
  AlertCircle,
  Calendar,
  Brain,
  FileText,
  ChevronRight,
  CheckCircle2,
  TrendingUp,
  TrendingDown,
  Minus,
  Plus,
  FolderOpen,
} from 'lucide-react';
import { api } from '@/lib/api/client';
import { useDesk } from '@/contexts/DeskContext';
import { useTP } from '@/contexts/TPContext';
import { useOnboardingState } from '@/hooks/useOnboardingState';
import { WelcomePrompt, MinimalContextBanner } from '@/components/WelcomePrompt';
import { formatDistanceToNow } from 'date-fns';
import type { Deliverable, ScheduleConfig, Work, Document as DocType } from '@/types';

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

// Deliverable type labels for display
const DELIVERABLE_TYPE_LABELS: Record<string, string> = {
  status_report: 'Status Report',
  stakeholder_update: 'Stakeholder Update',
  research_brief: 'Research Brief',
  meeting_summary: 'Meeting Summary',
  custom: 'Custom',
  client_proposal: 'Client Proposal',
  performance_self_assessment: 'Self-Assessment',
  newsletter_section: 'Newsletter',
  changelog: 'Changelog',
  one_on_one_prep: '1:1 Prep',
  board_update: 'Board Update',
  // ADR-029 Phase 3: Email-specific types
  inbox_summary: 'Inbox Summary',
  reply_draft: 'Reply Draft',
  follow_up_tracker: 'Follow-up Tracker',
  thread_summary: 'Thread Summary',
};

interface DashboardData {
  deliverables: Deliverable[];
  recentWork: Work[];
  memoryCount: number;
  recentDocs: DocType[];
}

export function IdleSurface() {
  const { setSurface, attention } = useDesk();
  const { sendMessage } = useTP();
  const {
    state: onboardingState,
    isLoading: onboardingLoading,
    memoryCount,
    dismiss: dismissBanner,
    isDismissed,
    reload: reloadOnboardingState,
  } = useOnboardingState();

  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [data, setData] = useState<DashboardData | null>(null);
  const [pasteModalOpen, setPasteModalOpen] = useState(false);
  const [pasteContent, setPasteContent] = useState('');
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    loadDashboardData();
  }, []);

  const loadDashboardData = async () => {
    try {
      const [deliverables, workResult, memories, docsResult] = await Promise.all([
        api.deliverables.list().catch(() => []),
        api.work.listAll({ limit: 5 }).catch(() => ({ work: [] })),
        api.userMemories.list().catch(() => []),
        api.documents.list().catch(() => ({ documents: [] })),
      ]);

      setData({
        deliverables: deliverables || [],
        recentWork: (workResult.work || []).slice(0, 5),
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
  // WelcomePrompt Callbacks
  // =============================================================================

  const handleUpload = () => {
    fileInputRef.current?.click();
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploading(true);
    try {
      await api.documents.upload(file);
      // Reload both dashboard data and onboarding state to transition out of cold_start
      await Promise.all([
        loadDashboardData(),
        reloadOnboardingState(),
      ]);
    } catch (err) {
      console.error('Failed to upload document:', err);
      alert('Failed to upload. Please try again.');
    } finally {
      setUploading(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  const handlePaste = () => {
    setPasteModalOpen(true);
  };

  const handlePasteSubmit = async () => {
    if (!pasteContent.trim()) return;

    // Send pasted content to TP as context
    await sendMessage(`Here's some context about me and my work:\n\n${pasteContent}`);
    setPasteModalOpen(false);
    setPasteContent('');
    // Reload to check if we've transitioned out of cold_start
    await Promise.all([
      loadDashboardData(),
      reloadOnboardingState(),
    ]);
  };

  const handleStart = () => {
    // Focus the TP input - dismiss welcome and let user start typing
    dismissBanner();
  };

  const handleSelectPrompt = (prompt: string) => {
    // Send the starter prompt to TP
    sendMessage(prompt);
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
  // Cold Start: Full Welcome Experience
  // =============================================================================

  // Show full welcome if:
  // 1. Onboarding state is cold_start
  // 2. No deliverables exist (fallback check)
  // 3. User hasn't dismissed the welcome
  const showColdStart =
    !isDismissed &&
    (onboardingState === 'cold_start' ||
      (!data?.deliverables || data.deliverables.length === 0));

  if (showColdStart) {
    return (
      <div className="h-full flex items-center justify-center overflow-auto">
        {/* Hidden file input for upload */}
        <input
          ref={fileInputRef}
          type="file"
          onChange={handleFileChange}
          className="hidden"
          accept=".pdf,.doc,.docx,.txt,.md"
        />

        {uploading ? (
          <div className="text-center">
            <Loader2 className="w-8 h-8 animate-spin text-primary mx-auto mb-4" />
            <p className="text-sm text-muted-foreground">Uploading and processing...</p>
          </div>
        ) : (
          <WelcomePrompt
            onUpload={handleUpload}
            onPaste={handlePaste}
            onStart={handleStart}
            onSelectPrompt={handleSelectPrompt}
          />
        )}

        {/* Paste Modal */}
        {pasteModalOpen && (
          <div className="fixed inset-0 z-50 flex items-center justify-center">
            <div
              className="absolute inset-0 bg-black/50"
              onClick={() => setPasteModalOpen(false)}
            />
            <div className="relative bg-background rounded-2xl shadow-xl max-w-lg w-full mx-4 p-6">
              <h3 className="text-lg font-semibold mb-2">Paste context</h3>
              <p className="text-sm text-muted-foreground mb-4">
                Share information about yourself, your work, or your preferences.
              </p>
              <textarea
                value={pasteContent}
                onChange={(e) => setPasteContent(e.target.value)}
                placeholder="e.g., I'm a product manager at a fintech startup. I send weekly status reports to my team every Monday..."
                className="w-full h-40 p-3 border border-border rounded-lg text-sm resize-none focus:outline-none focus:ring-2 focus:ring-primary/20"
                autoFocus
              />
              <div className="flex justify-end gap-2 mt-4">
                <button
                  onClick={() => setPasteModalOpen(false)}
                  className="px-4 py-2 text-sm text-muted-foreground hover:text-foreground"
                >
                  Cancel
                </button>
                <button
                  onClick={handlePasteSubmit}
                  disabled={!pasteContent.trim()}
                  className="px-4 py-2 text-sm bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 disabled:opacity-50"
                >
                  Share with TP
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    );
  }

  // =============================================================================
  // Active Dashboard
  // =============================================================================

  const activeDeliverables = data?.deliverables.filter((d) => d.status === 'active') || [];
  const pausedDeliverables = data?.deliverables.filter((d) => d.status === 'paused') || [];

  // Sort active deliverables by next_run_at (soonest first)
  const upcomingDeliverables = [...activeDeliverables].sort((a, b) => {
    if (!a.next_run_at) return 1;
    if (!b.next_run_at) return -1;
    return new Date(a.next_run_at).getTime() - new Date(b.next_run_at).getTime();
  });

  // Find next scheduled deliverable for status strip
  const nextDeliverable = upcomingDeliverables[0];

  // Calculate overall quality trend
  const qualityTrends = activeDeliverables
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

  // Show minimal context banner if user has some context but not much
  const showMinimalContextBanner =
    !isDismissed && onboardingState === 'minimal_context';

  return (
    <div className="h-full overflow-auto">
      <div className="max-w-3xl mx-auto px-4 md:px-6 py-6 space-y-6">
        {/* Minimal Context Banner */}
        {showMinimalContextBanner && (
          <MinimalContextBanner
            memoryCount={memoryCount}
            onDismiss={dismissBanner}
          />
        )}

        {/* System Status Strip */}
        {activeDeliverables.length > 0 && (
          <div className="flex items-center gap-4 px-4 py-3 bg-muted/30 rounded-lg text-sm">
            <div className="flex items-center gap-2 text-green-600 dark:text-green-500">
              <CheckCircle2 className="w-4 h-4" />
              <span>{activeDeliverables.length} active</span>
            </div>
            {pausedDeliverables.length > 0 && (
              <div className="flex items-center gap-2 text-muted-foreground">
                <Pause className="w-3.5 h-3.5" />
                <span>{pausedDeliverables.length} paused</span>
              </div>
            )}
            <span className="text-muted-foreground">·</span>
            {nextDeliverable?.next_run_at && (
              <div className="flex items-center gap-1.5 text-muted-foreground">
                <Clock className="w-3.5 h-3.5" />
                <span>
                  Next:{' '}
                  <span className="text-foreground">{nextDeliverable.title}</span>{' '}
                  {formatDistanceToNow(new Date(nextDeliverable.next_run_at), { addSuffix: true })}
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

        {/* Upcoming Schedule (primary focus) */}
        <DashboardSection
          icon={<Calendar className="w-4 h-4" />}
          title="Upcoming Schedule"
          action={
            data && data.deliverables.length > 0 ? (
              <button
                onClick={() => setSurface({ type: 'deliverable-list' })}
                className="text-xs text-muted-foreground hover:text-foreground flex items-center gap-1"
              >
                All deliverables ({data.deliverables.length})
                <ChevronRight className="w-3 h-3" />
              </button>
            ) : undefined
          }
        >
          {upcomingDeliverables.length > 0 ? (
            upcomingDeliverables.slice(0, 5).map((d) => (
              <DeliverableCard
                key={d.id}
                deliverable={d}
                onClick={() => setSurface({ type: 'deliverable-detail', deliverableId: d.id })}
              />
            ))
          ) : (
            <div className="text-center py-8 text-muted-foreground">
              <Calendar className="w-8 h-8 mx-auto mb-2 opacity-50" />
              <p className="text-sm">No scheduled deliverables yet</p>
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
                  key={item.versionId}
                  onClick={() =>
                    setSurface({
                      type: 'deliverable-review',
                      deliverableId: item.deliverableId,
                      versionId: item.versionId,
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

        {/* Recent Work */}
        {data?.recentWork && data.recentWork.length > 0 && (
          <DashboardSection
            icon={<FileText className="w-4 h-4" />}
            title="Recent Work"
            action={
              <button
                onClick={() => setSurface({ type: 'work-list' })}
                className="text-xs text-muted-foreground hover:text-foreground flex items-center gap-1"
              >
                View all
                <ChevronRight className="w-3 h-3" />
              </button>
            }
          >
            {data.recentWork.slice(0, 3).map((w) => (
              <button
                key={w.id}
                onClick={() => setSurface({ type: 'work-output', workId: w.id })}
                disabled={w.status !== 'completed'}
                className={`w-full p-3 border border-border rounded-lg text-left ${
                  w.status === 'completed' ? 'hover:bg-muted' : 'opacity-60'
                }`}
              >
                <div className="flex items-center justify-between">
                  <div>
                    <span className="text-sm font-medium">{w.task}</span>
                    <p className="text-xs text-muted-foreground">{w.agent_type}</p>
                  </div>
                  <span className="text-xs text-muted-foreground">
                    {formatDistanceToNow(new Date(w.created_at), { addSuffix: true })}
                  </span>
                </div>
              </button>
            ))}
          </DashboardSection>
        )}

        {/* Quick Actions */}
        <div className="grid grid-cols-3 gap-3">
          {/* Create Deliverable - Primary */}
          <button
            onClick={() => sendMessage('Help me create a new deliverable')}
            className="p-4 border-2 border-dashed border-primary/30 rounded-lg hover:border-primary/50 hover:bg-primary/5 text-left"
          >
            <div className="flex items-center gap-2 mb-1">
              <Plus className="w-4 h-4 text-primary" />
              <span className="text-sm font-medium">New Deliverable</span>
            </div>
            <p className="text-xs text-muted-foreground">Set up recurring work</p>
          </button>

          {/* Context */}
          <button
            onClick={() => setSurface({ type: 'context-browser', scope: 'user' })}
            className="p-4 border border-border rounded-lg hover:bg-muted text-left"
          >
            <div className="flex items-center gap-2 mb-1">
              <Brain className="w-4 h-4 text-muted-foreground" />
              <span className="text-sm font-medium">Context</span>
            </div>
            <p className="text-xs text-muted-foreground">
              {data?.memoryCount || 0} memories
            </p>
          </button>

          {/* Documents */}
          <button
            onClick={() => setSurface({ type: 'document-list' })}
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

function DeliverableCard({
  deliverable,
  onClick,
}: {
  deliverable: Deliverable;
  onClick: () => void;
}) {
  const typeLabel =
    DELIVERABLE_TYPE_LABELS[deliverable.deliverable_type] || deliverable.deliverable_type;

  // Quality indicator
  const QualityIndicator = () => {
    if (!deliverable.quality_trend) return null;
    if (deliverable.quality_trend === 'improving') {
      return (
        <span title="Quality improving">
          <TrendingUp className="w-3 h-3 text-green-500" />
        </span>
      );
    }
    if (deliverable.quality_trend === 'declining') {
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
          {deliverable.status === 'paused' ? (
            <Pause className="w-3 h-3 text-amber-500" />
          ) : (
            <span className="w-2 h-2 rounded-full bg-green-500" />
          )}
          <div>
            <div className="flex items-center gap-2">
              <span className="text-sm font-medium">{deliverable.title}</span>
              <QualityIndicator />
            </div>
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <span className="px-1.5 py-0.5 bg-muted rounded text-[10px] font-medium">
                {typeLabel}
              </span>
              {deliverable.project_name && (
                <span className="flex items-center gap-1">
                  <FolderOpen className="w-3 h-3" />
                  {deliverable.project_name}
                </span>
              )}
              {formatSchedule(deliverable.schedule) && (
                <span>{formatSchedule(deliverable.schedule)}</span>
              )}
            </div>
          </div>
        </div>
        {deliverable.next_run_at && (
          <span className="text-xs text-muted-foreground flex items-center gap-1">
            <Clock className="w-3 h-3" />
            {formatDistanceToNow(new Date(deliverable.next_run_at), { addSuffix: true })}
          </span>
        )}
      </div>
    </button>
  );
}
