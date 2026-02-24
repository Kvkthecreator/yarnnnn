'use client';

/**
 * ADR-066: Deliverable Detail Page — Content-First, Delivery-First
 *
 * Layout:
 * 1. Header (title, schedule, destination, controls)
 * 2. Content area (rendered markdown — the hero)
 * 3. Execution details (status, timestamp, version, sources)
 * 4. Schedule section (next run, run now)
 * 5. Delivery history (version list, click to switch content)
 */

import { useState, useEffect, useCallback } from 'react';
import { useRouter, useParams } from 'next/navigation';
import ReactMarkdown from 'react-markdown';
import {
  Loader2,
  Play,
  Pause,
  Settings,
  CheckCircle2,
  XCircle,
  ChevronLeft,
  MessageSquare,
  Mail,
  FileText,
  ExternalLink,
  RefreshCw,
  BarChart3,
  Sparkles,
  Copy,
  Clock,
  Database,
} from 'lucide-react';
import { api } from '@/lib/api/client';
import { formatDistanceToNow, format } from 'date-fns';
import { cn } from '@/lib/utils';
import { DeliverableSettingsModal } from '@/components/modals/DeliverableSettingsModal';
import type { Deliverable, DeliverableVersion, SourceSnapshot } from '@/types';

// =============================================================================
// Helpers
// =============================================================================

const PLATFORM_EMOJI: Record<string, string> = {
  slack: '💬',
  gmail: '📧',
  email: '📧',
  notion: '📝',
  calendar: '📅',
  synthesis: '📊',
};

const PLATFORM_ICON: Record<string, React.ComponentType<{ className?: string }>> = {
  slack: MessageSquare,
  gmail: Mail,
  email: Mail,
  notion: FileText,
};

function getPlatformEmoji(deliverable: Deliverable): string {
  const cls = deliverable.type_classification;
  if (cls?.binding === 'cross_platform' || cls?.binding === 'hybrid' || cls?.binding === 'research') {
    return '📊';
  }
  const platform = cls?.primary_platform || deliverable.destination?.platform;
  return PLATFORM_EMOJI[platform || ''] || '📊';
}

function formatSchedule(deliverable: Deliverable): string {
  const s = deliverable.schedule;
  if (!s) return 'No schedule';
  const time = s.time || '09:00';
  const day = s.day
    ? s.day.charAt(0).toUpperCase() + s.day.slice(1)
    : s.frequency === 'monthly' ? '1st' : '';

  switch (s.frequency) {
    case 'daily': return `Daily at ${time}`;
    case 'weekly': return `${day || 'Weekly'} at ${time}`;
    case 'biweekly': return `Every 2 weeks, ${day} at ${time}`;
    case 'monthly': return `Monthly on the ${day} at ${time}`;
    default: return s.frequency || 'Custom';
  }
}

function formatDestination(deliverable: Deliverable): string | null {
  const dest = deliverable.destination;
  if (!dest) return null;
  const target = dest.target;
  if (target?.includes('@')) return target;
  if (target?.startsWith('#')) return target;
  if (target === 'dm') return 'DM';
  return null;
}

function getStatusBadge(version: DeliverableVersion) {
  const status = version.delivery_status || version.status;
  if (status === 'delivered') {
    return (
      <span className="inline-flex items-center gap-1 text-xs text-green-600 dark:text-green-400 bg-green-50 dark:bg-green-900/30 px-2 py-0.5 rounded-full">
        <CheckCircle2 className="w-3 h-3" />
        Delivered
      </span>
    );
  }
  if (status === 'failed') {
    return (
      <span className="inline-flex items-center gap-1 text-xs text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/30 px-2 py-0.5 rounded-full">
        <XCircle className="w-3 h-3" />
        Failed
      </span>
    );
  }
  if (status === 'generating') {
    return (
      <span className="inline-flex items-center gap-1 text-xs text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-900/30 px-2 py-0.5 rounded-full">
        <Loader2 className="w-3 h-3 animate-spin" />
        Generating
      </span>
    );
  }
  return <span className="text-xs text-muted-foreground">{status}</span>;
}

function getVersionTimestamp(version: DeliverableVersion): string {
  const ts = version.delivered_at || version.created_at;
  return format(new Date(ts), 'MMM d, h:mm a');
}

function wordCount(text: string): number {
  return text.trim().split(/\s+/).filter(Boolean).length;
}

function SourcePills({ snapshots }: { snapshots: SourceSnapshot[] }) {
  if (!snapshots || snapshots.length === 0) return null;
  return (
    <span className="inline-flex items-center gap-1.5 text-xs text-muted-foreground">
      <Database className="w-3 h-3" />
      {snapshots.map((s, i) => (
        <span key={i} className="inline-flex items-center gap-0.5">
          {i > 0 && <span className="text-border">·</span>}
          <span>{PLATFORM_EMOJI[s.platform] || '📄'}</span>
          <span>{s.resource_name || s.resource_id}</span>
          {s.item_count != null && (
            <span className="text-muted-foreground/60">({s.item_count})</span>
          )}
        </span>
      ))}
    </span>
  );
}

// =============================================================================
// Main Component
// =============================================================================

export default function DeliverableDetailPage() {
  const params = useParams<{ id: string }>();
  const id = params.id;
  const router = useRouter();

  // Data
  const [loading, setLoading] = useState(true);
  const [deliverable, setDeliverable] = useState<Deliverable | null>(null);
  const [versions, setVersions] = useState<DeliverableVersion[]>([]);
  const [settingsOpen, setSettingsOpen] = useState(false);

  // UI
  const [selectedIdx, setSelectedIdx] = useState(0);
  const [copied, setCopied] = useState(false);
  const [running, setRunning] = useState(false);

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

  const selectedVersion = versions[selectedIdx] || null;
  const content = selectedVersion?.final_content || selectedVersion?.draft_content || '';

  // Gates
  const isPlatformBound = deliverable?.type_classification?.binding === 'platform_bound';
  const hasSources = (deliverable?.sources?.length ?? 0) > 0;
  const missingSourcesWarning = isPlatformBound && !hasSources;

  // ==========================================================================
  // Actions
  // ==========================================================================

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
      await loadDeliverable();
      setSelectedIdx(0);
    } catch (err) {
      console.error('Failed to run deliverable:', err);
    } finally {
      setRunning(false);
    }
  };

  const handleCopy = async () => {
    if (!content) return;
    await navigator.clipboard.writeText(content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  // ==========================================================================
  // Loading / Not found
  // ==========================================================================

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

  const destDisplay = formatDestination(deliverable);
  const DestIcon = deliverable.destination ? PLATFORM_ICON[deliverable.destination.platform] : null;

  return (
    <div className="h-full overflow-auto">
      <div className="max-w-3xl mx-auto px-4 md:px-6 py-6 space-y-5">

        {/* ================================================================ */}
        {/* Header                                                          */}
        {/* ================================================================ */}
        <div className="flex items-start justify-between">
          <div className="flex items-start gap-3">
            <button
              onClick={() => router.push('/deliverables')}
              className="p-2 -ml-2 mt-0.5 hover:bg-muted rounded-lg transition-colors"
              title="Back to Deliverables"
            >
              <ChevronLeft className="w-5 h-5" />
            </button>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-xl">{getPlatformEmoji(deliverable)}</span>
                <h1 className="text-xl font-semibold">{deliverable.title}</h1>
                {deliverable.origin === 'signal_emergent' && (
                  <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400">
                    <Sparkles className="w-3 h-3" />
                    Signal
                  </span>
                )}
                {deliverable.origin === 'analyst_suggested' && (
                  <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400">
                    <BarChart3 className="w-3 h-3" />
                    Suggested
                  </span>
                )}
              </div>
              <div className="flex items-center gap-2 text-sm text-muted-foreground mt-0.5">
                <span>{formatSchedule(deliverable)}</span>
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
          <div className="flex items-center gap-2 shrink-0">
            {deliverable.status === 'paused' ? (
              <span className="text-xs text-amber-600 bg-amber-50 dark:bg-amber-900/20 px-2 py-1 rounded-full flex items-center gap-1">
                <Pause className="w-3 h-3" /> Paused
              </span>
            ) : (
              <span className="text-xs text-green-600 bg-green-50 dark:bg-green-900/20 px-2 py-1 rounded-full flex items-center gap-1">
                <Play className="w-3 h-3" /> Active
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

        {/* ================================================================ */}
        {/* Content Area (Hero)                                             */}
        {/* ================================================================ */}
        {selectedVersion ? (
          <>
            {/* Failed state */}
            {(selectedVersion.status === 'failed' || selectedVersion.delivery_status === 'failed') ? (
              <div className="border border-red-200 dark:border-red-800 rounded-lg overflow-hidden">
                <div className="px-4 py-3 bg-red-50 dark:bg-red-900/20 flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <XCircle className="w-4 h-4 text-red-600 dark:text-red-400" />
                    <span className="text-sm font-medium text-red-700 dark:text-red-400">Delivery failed</span>
                    {selectedVersion.delivery_error && (
                      <span className="text-sm text-red-600/70 dark:text-red-400/70">— {selectedVersion.delivery_error}</span>
                    )}
                  </div>
                  <button
                    onClick={handleRunNow}
                    disabled={running}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm border border-red-300 dark:border-red-700 rounded-md hover:bg-red-100 dark:hover:bg-red-900/30 disabled:opacity-50 transition-colors"
                  >
                    {running ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <RefreshCw className="w-3.5 h-3.5" />}
                    Retry
                  </button>
                </div>
                {content && (
                  <div className="p-5 prose prose-sm dark:prose-invert max-w-none prose-headings:mt-4 prose-headings:mb-2 prose-p:my-1.5 prose-ul:my-1.5 prose-li:my-0.5">
                    <ReactMarkdown>{content}</ReactMarkdown>
                  </div>
                )}
              </div>
            ) : selectedVersion.status === 'generating' ? (
              /* Generating state */
              <div className="border border-border rounded-lg p-8 flex flex-col items-center justify-center gap-3">
                <Loader2 className="w-6 h-6 animate-spin text-blue-500" />
                <p className="text-sm text-muted-foreground">Generating content...</p>
              </div>
            ) : (
              /* Delivered / content display */
              <div className="border border-border rounded-lg overflow-hidden">
                <div className="p-5 max-h-[600px] overflow-auto prose prose-sm dark:prose-invert max-w-none prose-headings:mt-4 prose-headings:mb-2 prose-p:my-1.5 prose-ul:my-1.5 prose-li:my-0.5">
                  <ReactMarkdown>{content || 'No content'}</ReactMarkdown>
                </div>
                {/* Action bar below content */}
                <div className="px-4 py-2.5 border-t border-border bg-muted/20 flex items-center justify-end gap-2">
                  <button
                    onClick={handleCopy}
                    className="inline-flex items-center gap-1.5 px-2.5 py-1 text-xs text-muted-foreground hover:text-foreground hover:bg-muted rounded transition-colors"
                    title="Copy raw content"
                  >
                    {copied ? <CheckCircle2 className="w-3.5 h-3.5 text-green-600" /> : <Copy className="w-3.5 h-3.5" />}
                    {copied ? 'Copied' : 'Copy'}
                  </button>
                  {selectedVersion.delivery_external_url && (
                    <a
                      href={selectedVersion.delivery_external_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1.5 px-2.5 py-1 text-xs text-muted-foreground hover:text-foreground hover:bg-muted rounded transition-colors"
                    >
                      <ExternalLink className="w-3.5 h-3.5" />
                      View in destination
                    </a>
                  )}
                </div>
              </div>
            )}

            {/* ============================================================ */}
            {/* Execution Details                                            */}
            {/* ============================================================ */}
            <div className="flex flex-wrap items-center gap-x-3 gap-y-1.5 text-xs text-muted-foreground px-1">
              {getStatusBadge(selectedVersion)}
              <span className="flex items-center gap-1">
                <Clock className="w-3 h-3" />
                {getVersionTimestamp(selectedVersion)}
              </span>
              <span>v{selectedVersion.version_number}</span>
              {content && <span>{wordCount(content).toLocaleString()} words</span>}
              {selectedVersion.source_snapshots && selectedVersion.source_snapshots.length > 0 && (
                <SourcePills snapshots={selectedVersion.source_snapshots} />
              )}
            </div>
          </>
        ) : (
          /* No versions empty state */
          <div className="border border-dashed border-border rounded-lg p-8 text-center">
            <FileText className="w-8 h-8 text-muted-foreground mx-auto mb-3" />
            <p className="text-muted-foreground mb-4">No deliveries yet</p>
            <button
              onClick={handleRunNow}
              disabled={running || deliverable.status === 'archived' || missingSourcesWarning}
              className="inline-flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground text-sm font-medium rounded-md hover:bg-primary/90 disabled:opacity-50"
            >
              {running ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
              {running ? 'Generating...' : 'Run Now'}
            </button>
          </div>
        )}

        {/* ================================================================ */}
        {/* Schedule                                                        */}
        {/* ================================================================ */}
        <div className="border border-border rounded-lg">
          <div className="px-4 py-3 border-b border-border bg-muted/30">
            <h2 className="text-sm font-medium">Schedule</h2>
          </div>
          {missingSourcesWarning && (
            <div className="px-4 py-2.5 bg-amber-50 dark:bg-amber-900/20 border-b border-amber-200 dark:border-amber-800 text-xs text-amber-800 dark:text-amber-300 flex items-center gap-2">
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

        {/* ================================================================ */}
        {/* Delivery History                                                */}
        {/* ================================================================ */}
        {versions.length > 1 && (
          <div className="border border-border rounded-lg">
            <div className="px-4 py-3 border-b border-border bg-muted/30">
              <h2 className="text-sm font-medium">Delivery History</h2>
            </div>
            <div className="divide-y divide-border">
              {versions.slice(0, 10).map((version, idx) => (
                <button
                  key={version.id}
                  onClick={() => setSelectedIdx(idx)}
                  className={cn(
                    "w-full px-4 py-2.5 flex items-center justify-between hover:bg-muted/50 transition-colors text-left",
                    idx === selectedIdx && "bg-primary/5 border-l-2 border-l-primary"
                  )}
                >
                  <div className="flex items-center gap-3">
                    <span className="text-xs text-muted-foreground w-6">v{version.version_number}</span>
                    <span className="text-sm">{getVersionTimestamp(version)}</span>
                    {getStatusBadge(version)}
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
              ))}
            </div>
            {versions.length > 10 && (
              <div className="px-4 py-2 text-center border-t border-border">
                <span className="text-xs text-muted-foreground">
                  Showing 10 of {versions.length} deliveries
                </span>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Settings Modal */}
      <DeliverableSettingsModal
        deliverable={deliverable}
        open={settingsOpen}
        onClose={() => setSettingsOpen(false)}
        onSaved={(updated) => setDeliverable(updated)}
        onArchived={() => router.push('/deliverables')}
      />
    </div>
  );
}
