'use client';

/**
 * ADR-066: Deliverable Detail Page — Delivery-First, No Governance
 *
 * Shows delivery history and automation controls.
 * No approve/reject workflow - deliverables deliver immediately.
 *
 * Key elements:
 * - Latest Delivery with status (delivered/failed)
 * - Delivery History (replaces "Previous Versions")
 * - Schedule controls (Pause/Resume, Run Now)
 * - Settings modal for configuration
 */

import { useState, useEffect, useCallback } from 'react';
import { useRouter, useParams } from 'next/navigation';
import {
  Loader2,
  Play,
  Pause,
  Settings,
  Clock,
  Check,
  Copy,
  CheckCircle2,
  XCircle,
  ChevronLeft,
  ChevronDown,
  ChevronRight,
  MessageSquare,
  Mail,
  FileText,
  Download,
  ExternalLink,
  RefreshCw,
  BarChart3,
} from 'lucide-react';
import { api } from '@/lib/api/client';
import { formatDistanceToNow, format } from 'date-fns';
import { cn } from '@/lib/utils';
import { DeliverableSettingsModal } from '@/components/modals/DeliverableSettingsModal';
import { SourceSnapshotsSummary } from '@/components/deliverables/SourceSnapshotsSummary';
import type { Deliverable, DeliverableVersion } from '@/types';

// =============================================================================
// Platform Config
// =============================================================================

const PLATFORM_ICONS: Record<string, React.ComponentType<{ className?: string }>> = {
  gmail: Mail,
  email: Mail,
  slack: MessageSquare,
  notion: FileText,
  download: Download,
};

const PLATFORM_LABELS: Record<string, string> = {
  gmail: 'Gmail',
  email: 'Email',
  slack: 'Slack',
  notion: 'Notion',
  download: 'Download',
};

const PLATFORM_BADGES: Record<string, { icon: React.ComponentType<{ className?: string }>; label: string }> = {
  slack: { icon: MessageSquare, label: '💬' },
  gmail: { icon: Mail, label: '📧' },
  email: { icon: Mail, label: '📧' },
  notion: { icon: FileText, label: '📝' },
  synthesis: { icon: BarChart3, label: '📊' },
};

// =============================================================================
// Main Component
// =============================================================================

export default function DeliverableDetailPage() {
  const params = useParams<{ id: string }>();
  const id = params.id;
  const router = useRouter();

  // Data state
  const [loading, setLoading] = useState(true);
  const [deliverable, setDeliverable] = useState<Deliverable | null>(null);
  const [versions, setVersions] = useState<DeliverableVersion[]>([]);
  const [settingsOpen, setSettingsOpen] = useState(false);

  // UI state
  const [copied, setCopied] = useState(false);
  const [running, setRunning] = useState(false);
  const [expandedVersionId, setExpandedVersionId] = useState<string | null>(null);

  // Load deliverable data
  const loadDeliverable = useCallback(async () => {
    try {
      const detail = await api.deliverables.get(id);
      setDeliverable(detail.deliverable);
      setVersions(detail.versions);
    } catch (err) {
      console.error('Failed to load deliverable:', err);
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    loadDeliverable();
  }, [loadDeliverable]);

  // Get the latest version
  const latestVersion = versions[0];

  // Gate: platform-bound deliverable with no sources configured can't produce useful output
  const isPlatformBound = deliverable?.type_classification?.binding === 'platform_bound';
  const hasSources = (deliverable?.sources?.length ?? 0) > 0;
  const missingSourcesWarning = isPlatformBound && !hasSources;

  // =============================================================================
  // Actions
  // =============================================================================

  const handleTogglePause = async () => {
    if (!deliverable) return;

    try {
      const newStatus = deliverable.status === 'paused' ? 'active' : 'paused';
      await api.deliverables.update(id, { status: newStatus });
      setDeliverable({ ...deliverable, status: newStatus });
    } catch (err) {
      console.error('Failed to update status:', err);
    }
  };

  const handleRunNow = async () => {
    if (!deliverable) return;

    setRunning(true);
    try {
      await api.deliverables.run(id);
      // Refresh to see the new version
      await loadDeliverable();
    } catch (err) {
      console.error('Failed to run deliverable:', err);
      alert('Failed to run. Please try again.');
    } finally {
      setRunning(false);
    }
  };

  const handleRetry = async (versionId: string) => {
    // For now, just run a new version
    await handleRunNow();
  };

  const handleCopy = async (content: string) => {
    await navigator.clipboard.writeText(content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleSettingsSaved = (updated: Deliverable) => {
    setDeliverable(updated);
  };

  // =============================================================================
  // Helpers
  // =============================================================================

  const getPlatformBadge = () => {
    const classification = deliverable?.type_classification;
    if (classification?.binding === 'cross_platform' || classification?.binding === 'hybrid') {
      return '📊';
    }
    const platform = classification?.primary_platform || deliverable?.destination?.platform;
    if (platform === 'slack') return '💬';
    if (platform === 'gmail' || platform === 'email') return '📧';
    if (platform === 'notion') return '📝';
    return '📊';
  };

  const formatSchedule = () => {
    if (!deliverable?.schedule) return 'No schedule';
    const s = deliverable.schedule;
    const time = s.time || '09:00';
    const day = s.day
      ? s.day.charAt(0).toUpperCase() + s.day.slice(1)
      : s.frequency === 'monthly' ? '1st' : 'Monday';

    switch (s.frequency) {
      case 'daily': return `Daily at ${time}`;
      case 'weekly': return `Weekly on ${day} at ${time}`;
      case 'biweekly': return `Every 2 weeks on ${day} at ${time}`;
      case 'monthly': return `Monthly on the ${day} at ${time}`;
      default: return s.frequency || 'Custom';
    }
  };

  const formatDestination = () => {
    const dest = deliverable?.destination;
    if (!dest) return null;
    const platform = PLATFORM_LABELS[dest.platform] || dest.platform;
    const target = dest.target;
    if (target === 'dm') return `${platform} DM`;
    if (target?.includes('@')) return target;
    if (target?.startsWith('#')) return `${platform} ${target}`;
    return platform;
  };

  // ADR-066: Delivery status badges (not governance status)
  const getDeliveryStatusBadge = (version: DeliverableVersion) => {
    const status = version.status;
    // Map legacy statuses to delivery-first model
    if (status === 'delivered' || status === 'approved') {
      return (
        <span className="inline-flex items-center gap-1 text-xs text-green-600 bg-green-50 dark:bg-green-900/30 px-2 py-0.5 rounded-full">
          <CheckCircle2 className="w-3 h-3" />
          Delivered
        </span>
      );
    }
    if (status === 'failed' || status === 'rejected') {
      return (
        <span className="inline-flex items-center gap-1 text-xs text-red-600 bg-red-50 dark:bg-red-900/30 px-2 py-0.5 rounded-full">
          <XCircle className="w-3 h-3" />
          Failed
        </span>
      );
    }
    if (status === 'generating') {
      return (
        <span className="inline-flex items-center gap-1 text-xs text-blue-600 bg-blue-50 dark:bg-blue-900/30 px-2 py-0.5 rounded-full">
          <Loader2 className="w-3 h-3 animate-spin" />
          Generating
        </span>
      );
    }
    // Legacy staged/reviewing - treat as delivered for display
    if (status === 'staged' || status === 'reviewing') {
      return (
        <span className="inline-flex items-center gap-1 text-xs text-green-600 bg-green-50 dark:bg-green-900/30 px-2 py-0.5 rounded-full">
          <CheckCircle2 className="w-3 h-3" />
          Delivered
        </span>
      );
    }
    return <span className="text-xs text-muted-foreground">{status}</span>;
  };

  const getDeliveryTimestamp = (version: DeliverableVersion) => {
    // Prefer delivered_at, fall back to approved_at, then created_at
    const timestamp = version.delivered_at || version.approved_at || version.created_at;
    return format(new Date(timestamp), 'MMM d, h:mm a');
  };

  // =============================================================================
  // Render
  // =============================================================================

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center">
        <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (!deliverable) {
    return (
      <div className="h-full flex flex-col items-center justify-center gap-4">
        <FileText className="w-8 h-8 text-muted-foreground" />
        <p className="text-muted-foreground">Deliverable not found</p>
        <button onClick={() => router.push('/deliverables')} className="text-sm text-primary hover:underline">
          Back to Deliverables
        </button>
      </div>
    );
  }

  const DestIcon = deliverable.destination ? PLATFORM_ICONS[deliverable.destination.platform] : null;
  const destDisplay = formatDestination();
  const platformBadge = getPlatformBadge();

  return (
    <div className="h-full overflow-auto">
      <div className="max-w-4xl mx-auto px-4 md:px-6 py-6">
        {/* Header with Platform Badge */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <button
              onClick={() => router.push('/deliverables')}
              className="p-2 -ml-2 hover:bg-muted rounded-lg transition-colors"
              title="Back to Deliverables"
            >
              <ChevronLeft className="w-5 h-5" />
            </button>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-xl">{platformBadge}</span>
                <h1 className="text-xl font-semibold">{deliverable.title}</h1>
              </div>
              <div className="flex items-center gap-2 text-sm text-muted-foreground mt-0.5">
                <span>{formatSchedule()}</span>
                {destDisplay && (
                  <>
                    <span>→</span>
                    <span className="flex items-center gap-1">
                      {DestIcon && <DestIcon className="w-3.5 h-3.5" />}
                      {destDisplay}
                    </span>
                  </>
                )}
              </div>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {/* Schedule Status Badge */}
            {deliverable.status === 'paused' ? (
              <span className="text-xs text-amber-600 bg-amber-50 dark:bg-amber-900/20 px-2 py-1 rounded-full flex items-center gap-1">
                <Pause className="w-3 h-3" />
                Paused
              </span>
            ) : (
              <span className="text-xs text-green-600 bg-green-50 dark:bg-green-900/20 px-2 py-1 rounded-full flex items-center gap-1">
                <Play className="w-3 h-3" />
                Active
              </span>
            )}
            <button
              onClick={handleTogglePause}
              className={cn(
                "p-2 border border-border rounded-md hover:bg-muted transition-colors",
                deliverable.status === 'paused' && "text-amber-600 border-amber-300 bg-amber-50 dark:bg-amber-900/20"
              )}
              title={deliverable.status === 'paused' ? 'Resume' : 'Pause'}
            >
              {deliverable.status === 'paused' ? <Play className="w-4 h-4" /> : <Pause className="w-4 h-4" />}
            </button>
            <button
              onClick={() => setSettingsOpen(true)}
              className="p-2 border border-border rounded-md hover:bg-muted transition-colors"
              title="Settings"
            >
              <Settings className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Latest Delivery Section */}
        {latestVersion ? (
          <div className="border border-border rounded-lg mb-6 overflow-hidden">
            {/* Header */}
            <div className="px-4 py-3 border-b border-border bg-muted/30 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <h2 className="text-sm font-medium">Latest Delivery</h2>
                {getDeliveryStatusBadge(latestVersion)}
              </div>
              <div className="flex items-center gap-2 text-xs text-muted-foreground">
                <span>{getDeliveryTimestamp(latestVersion)}</span>
                {/* External link if available */}
                {latestVersion.delivery_external_url && (
                  <a
                    href={latestVersion.delivery_external_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="ml-2 p-1.5 hover:bg-muted rounded transition-colors text-primary"
                    title="View in destination"
                  >
                    <ExternalLink className="w-3.5 h-3.5" />
                  </a>
                )}
              </div>
            </div>

            {/* Source Snapshots */}
            {latestVersion.source_snapshots && latestVersion.source_snapshots.length > 0 && (
              <div className="px-4 py-3 border-b border-border bg-muted/20">
                <SourceSnapshotsSummary snapshots={latestVersion.source_snapshots} compact />
              </div>
            )}

            {/* Content Preview (collapsible) */}
            <details className="group">
              <summary className="px-4 py-3 cursor-pointer hover:bg-muted/30 flex items-center gap-2 text-sm text-muted-foreground">
                <ChevronRight className="w-4 h-4 transition-transform group-open:rotate-90" />
                Show content
              </summary>
              <div className="px-4 pb-4">
                <div className="relative">
                  <pre className="text-sm bg-muted/50 rounded-md p-4 overflow-auto max-h-[400px] whitespace-pre-wrap font-mono">
                    {latestVersion.final_content || latestVersion.draft_content || 'No content'}
                  </pre>
                  <button
                    onClick={() => handleCopy(latestVersion.final_content || latestVersion.draft_content || '')}
                    className="absolute top-2 right-2 p-1.5 bg-background/80 hover:bg-muted rounded transition-colors"
                    title="Copy content"
                  >
                    {copied ? <CheckCircle2 className="w-4 h-4 text-green-600" /> : <Copy className="w-4 h-4" />}
                  </button>
                </div>
              </div>
            </details>

            {/* Failed delivery - show retry option */}
            {(latestVersion.status === 'failed' || latestVersion.status === 'rejected') && (
              <div className="px-4 py-3 border-t border-border bg-red-50/50 dark:bg-red-900/10">
                <div className="flex items-center justify-between">
                  <div className="text-sm">
                    <span className="text-red-600 font-medium">Delivery failed</span>
                    {latestVersion.delivery_error && (
                      <span className="text-muted-foreground ml-2">— {latestVersion.delivery_error}</span>
                    )}
                  </div>
                  <button
                    onClick={() => handleRetry(latestVersion.id)}
                    disabled={running}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm border border-border rounded-md hover:bg-muted disabled:opacity-50 transition-colors"
                  >
                    {running ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <RefreshCw className="w-3.5 h-3.5" />}
                    Retry
                  </button>
                </div>
              </div>
            )}
          </div>
        ) : (
          /* No versions yet */
          <div className="border border-dashed border-border rounded-lg mb-6 p-8 text-center">
            <FileText className="w-8 h-8 text-muted-foreground mx-auto mb-3" />
            <p className="text-muted-foreground mb-4">No deliveries yet</p>
            <button
              onClick={handleRunNow}
              disabled={running || deliverable.status === 'archived'}
              className="inline-flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground text-sm font-medium rounded-md hover:bg-primary/90 disabled:opacity-50"
            >
              {running ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
              {running ? 'Generating...' : 'Run Now'}
            </button>
          </div>
        )}

        {/* Delivery History */}
        {versions.length > 1 && (
          <div className="border border-border rounded-lg mb-6">
            <div className="px-4 py-3 border-b border-border bg-muted/30">
              <h2 className="text-sm font-medium">Delivery History</h2>
            </div>
            <div className="divide-y divide-border">
              {versions.slice(1, 10).map((version) => (
                <div key={version.id}>
                  <button
                    onClick={() => setExpandedVersionId(expandedVersionId === version.id ? null : version.id)}
                    className="w-full px-4 py-3 flex items-center justify-between hover:bg-muted/50 transition-colors"
                  >
                    <div className="flex items-center gap-3">
                      {expandedVersionId === version.id ? (
                        <ChevronDown className="w-4 h-4 text-muted-foreground" />
                      ) : (
                        <ChevronRight className="w-4 h-4 text-muted-foreground" />
                      )}
                      <span className="text-sm">{getDeliveryTimestamp(version)}</span>
                      {getDeliveryStatusBadge(version)}
                    </div>
                    {version.delivery_external_url && (
                      <a
                        href={version.delivery_external_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        onClick={(e) => e.stopPropagation()}
                        className="p-1.5 hover:bg-muted rounded transition-colors text-primary"
                        title="View in destination"
                      >
                        <ExternalLink className="w-3.5 h-3.5" />
                      </a>
                    )}
                  </button>
                  {expandedVersionId === version.id && (
                    <div className="px-4 pb-4 pl-11">
                      {version.source_snapshots && version.source_snapshots.length > 0 && (
                        <div className="mb-3">
                          <SourceSnapshotsSummary snapshots={version.source_snapshots} compact />
                        </div>
                      )}
                      <pre className="text-xs text-muted-foreground bg-muted/50 rounded-md p-3 overflow-auto max-h-[200px] whitespace-pre-wrap">
                        {version.final_content || version.draft_content || 'No content'}
                      </pre>
                      {(version.status === 'failed' || version.status === 'rejected') && version.delivery_error && (
                        <p className="mt-2 text-xs text-red-600">
                          Error: {version.delivery_error}
                        </p>
                      )}
                    </div>
                  )}
                </div>
              ))}
            </div>
            {versions.length > 10 && (
              <div className="px-4 py-2 text-center border-t border-border">
                <span className="text-xs text-muted-foreground">
                  Showing 9 of {versions.length - 1} previous deliveries
                </span>
              </div>
            )}
          </div>
        )}

        {/* Schedule Section */}
        <div className="border border-border rounded-lg">
          <div className="px-4 py-3 border-b border-border bg-muted/30">
            <h2 className="text-sm font-medium">Schedule</h2>
          </div>
          {missingSourcesWarning && (
            <div className="px-4 py-2.5 bg-amber-50 border-b border-amber-200 text-xs text-amber-800 flex items-center gap-2">
              <span className="shrink-0">⚠</span>
              No sources configured — open Settings to select which {deliverable.type_classification?.primary_platform ?? 'platform'} content to monitor.
            </div>
          )}
          <div className="p-4 flex items-center justify-between">
            <div>
              {deliverable.next_run_at ? (
                <>
                  <p className="text-sm">
                    Next: <span className="font-medium">{format(new Date(deliverable.next_run_at), 'EEE, MMM d')} at {format(new Date(deliverable.next_run_at), 'h:mm a')}</span>
                  </p>
                  <p className="text-xs text-muted-foreground mt-0.5">
                    {formatDistanceToNow(new Date(deliverable.next_run_at), { addSuffix: true })}
                  </p>
                </>
              ) : (
                <p className="text-sm text-muted-foreground">No scheduled runs</p>
              )}
            </div>
            <button
              onClick={handleRunNow}
              disabled={running || deliverable.status === 'archived' || missingSourcesWarning}
              title={missingSourcesWarning ? 'Add sources in Settings before running' : undefined}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm border border-border rounded-md hover:bg-muted disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {running ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Play className="w-3.5 h-3.5" />}
              Run Now
            </button>
          </div>
        </div>
      </div>

      {/* Settings Modal */}
      <DeliverableSettingsModal
        deliverable={deliverable}
        open={settingsOpen}
        onClose={() => setSettingsOpen(false)}
        onSaved={handleSettingsSaved}
        onArchived={() => router.push('/deliverables')}
      />
    </div>
  );
}
