'use client';

/**
 * ADR-023: Supervisor Desk Architecture
 * IdleSurface - Dashboard view showing all domains
 *
 * Handles three onboarding states:
 * - cold_start: Full welcome experience (WelcomePrompt)
 * - minimal_context: Normal dashboard with context banner
 * - active: Normal dashboard
 */

import { useState, useEffect, useRef } from 'react';
import { Clock, Loader2, Pause, AlertCircle, Briefcase, Brain, FileText, ChevronRight } from 'lucide-react';
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
      // Reload dashboard data and transition out of cold_start
      await loadDashboardData();
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
    await loadDashboardData();
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

  // Show minimal context banner if user has some context but not much
  const showMinimalContextBanner =
    !isDismissed && onboardingState === 'minimal_context';

  return (
    <div className="h-full overflow-auto">
      <div className="max-w-3xl mx-auto px-6 py-6 space-y-8">
        {/* Minimal Context Banner */}
        {showMinimalContextBanner && (
          <MinimalContextBanner
            memoryCount={memoryCount}
            onDismiss={dismissBanner}
          />
        )}

        {/* Needs Attention */}
        {attention.length > 0 && (
          <DashboardSection
            icon={<AlertCircle className="w-4 h-4 text-amber-500" />}
            title={`Needs Attention (${attention.length})`}
          >
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
                className="w-full p-3 border border-amber-200 dark:border-amber-900 bg-amber-50 dark:bg-amber-950/30 rounded-lg hover:bg-amber-100 dark:hover:bg-amber-950/50 text-left"
              >
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium">{item.title}</span>
                  <span className="text-xs text-muted-foreground">
                    staged {formatDistanceToNow(new Date(item.stagedAt), { addSuffix: false })} ago
                  </span>
                </div>
              </button>
            ))}
          </DashboardSection>
        )}

        {/* Deliverables */}
        <DashboardSection
          icon={<Briefcase className="w-4 h-4" />}
          title="Deliverables"
          action={
            data && data.deliverables.length > 3 ? (
              <button
                onClick={() => setSurface({ type: 'deliverable-list' })}
                className="text-xs text-muted-foreground hover:text-foreground flex items-center gap-1"
              >
                View all ({data.deliverables.length})
                <ChevronRight className="w-3 h-3" />
              </button>
            ) : undefined
          }
        >
          {activeDeliverables.slice(0, 5).map((d) => (
            <DeliverableCard
              key={d.id}
              deliverable={d}
              onClick={() => setSurface({ type: 'deliverable-detail', deliverableId: d.id })}
            />
          ))}
          {pausedDeliverables.length > 0 && (
            <p className="text-xs text-muted-foreground pt-2">
              + {pausedDeliverables.length} paused
            </p>
          )}
        </DashboardSection>

        {/* Recent Work */}
        {data?.recentWork && data.recentWork.length > 0 && (
          <DashboardSection
            icon={<Briefcase className="w-4 h-4" />}
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

        {/* Quick Links */}
        <div className="grid grid-cols-2 gap-4">
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
            <span className="text-sm font-medium">{deliverable.title}</span>
            {formatSchedule(deliverable.schedule) && (
              <p className="text-xs text-muted-foreground">{formatSchedule(deliverable.schedule)}</p>
            )}
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
