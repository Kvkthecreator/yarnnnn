'use client';

/**
 * ADR-066: Deliverable Detail Page — Content-First, Delivery-First
 * ADR-087 Phase 3: Tabbed sections for instructions, memory, sessions
 *
 * Layout:
 * 1. Header (title, schedule, destination, mode badge, controls)
 * 2. Content area (rendered markdown — the hero)
 * 3. Execution details (status, timestamp, version, sources)
 * 4. Schedule section (next run, run now)
 * 5. Tabbed sections: History | Instructions | Memory | Sessions
 */

import { useState, useEffect, useCallback, useRef } from 'react';
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
  Repeat,
  Target,
  Brain,
  PenLine,
  History,
} from 'lucide-react';
import { api } from '@/lib/api/client';
import { formatDistanceToNow, format } from 'date-fns';
import { cn } from '@/lib/utils';
import { DeliverableSettingsModal } from '@/components/modals/DeliverableSettingsModal';
import type { Deliverable, DeliverableVersion, DeliverableSession, SourceSnapshot } from '@/types';

// =============================================================================
// Helpers
// =============================================================================

const PLATFORM_EMOJI: Record<string, string> = {
  slack: '\u{1F4AC}',
  gmail: '\u{1F4E7}',
  email: '\u{1F4E7}',
  notion: '\u{1F4DD}',
  calendar: '\u{1F4C5}',
  synthesis: '\u{1F4CA}',
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
    return '\u{1F4CA}';
  }
  const platform = cls?.primary_platform || deliverable.destination?.platform;
  return PLATFORM_EMOJI[platform || ''] || '\u{1F4CA}';
}

function formatSchedule(deliverable: Deliverable): string {
  if (deliverable.mode === 'goal') return 'Goal';
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
          {i > 0 && <span className="text-border">&middot;</span>}
          <span>{PLATFORM_EMOJI[s.platform] || '\u{1F4C4}'}</span>
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
// Tab Types
// =============================================================================

type TabId = 'history' | 'instructions' | 'memory' | 'sessions';

const TABS: { id: TabId; label: string; icon: React.ComponentType<{ className?: string }> }[] = [
  { id: 'history', label: 'History', icon: History },
  { id: 'instructions', label: 'Instructions', icon: PenLine },
  { id: 'memory', label: 'Memory', icon: Brain },
  { id: 'sessions', label: 'Sessions', icon: MessageSquare },
];

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
  const [sessions, setSessions] = useState<DeliverableSession[]>([]);
  const [settingsOpen, setSettingsOpen] = useState(false);

  // UI
  const [selectedIdx, setSelectedIdx] = useState(0);
  const [copied, setCopied] = useState(false);
  const [running, setRunning] = useState(false);
  const [activeTab, setActiveTab] = useState<TabId>('history');

  // Instructions editor
  const [instructions, setInstructions] = useState('');
  const [instructionsSaving, setInstructionsSaving] = useState(false);
  const [instructionsSaved, setInstructionsSaved] = useState(false);
  const saveTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const loadDeliverable = useCallback(async () => {
    try {
      const detail = await api.deliverables.get(id);
      setDeliverable(detail.deliverable);
      setVersions(detail.versions);
      setInstructions(detail.deliverable.deliverable_instructions || '');
    } catch (err) {
      console.error('Failed to load deliverable:', err);
    } finally {
      setLoading(false);
    }
  }, [id]);

  // Load sessions on tab switch
  const loadSessions = useCallback(async () => {
    try {
      const data = await api.deliverables.listSessions(id);
      setSessions(data);
    } catch (err) {
      console.error('Failed to load sessions:', err);
    }
  }, [id]);

  useEffect(() => {
    loadDeliverable();
  }, [loadDeliverable]);

  useEffect(() => {
    if (activeTab === 'sessions' && sessions.length === 0) {
      loadSessions();
    }
  }, [activeTab, sessions.length, loadSessions]);

  const selectedVersion = versions[selectedIdx] || null;
  const content = selectedVersion?.final_content || selectedVersion?.draft_content || '';

  // Gates
  const isPlatformBound = deliverable?.type_classification?.binding === 'platform_bound';
  const hasSources = (deliverable?.sources?.length ?? 0) > 0;
  const missingSourcesWarning = isPlatformBound && !hasSources;
  const isGoalMode = deliverable?.mode === 'goal';

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

  // Instructions auto-save (debounced)
  const handleInstructionsChange = (value: string) => {
    setInstructions(value);
    setInstructionsSaved(false);
    if (saveTimerRef.current) clearTimeout(saveTimerRef.current);
    saveTimerRef.current = setTimeout(() => saveInstructions(value), 2000);
  };

  const saveInstructions = async (value: string) => {
    if (!deliverable) return;
    setInstructionsSaving(true);
    try {
      await api.deliverables.update(id, { deliverable_instructions: value });
      setDeliverable({ ...deliverable, deliverable_instructions: value });
      setInstructionsSaved(true);
      setTimeout(() => setInstructionsSaved(false), 3000);
    } catch (err) {
      console.error('Failed to save instructions:', err);
    } finally {
      setInstructionsSaving(false);
    }
  };

  const handleInstructionsBlur = () => {
    if (saveTimerRef.current) clearTimeout(saveTimerRef.current);
    if (instructions !== (deliverable?.deliverable_instructions || '')) {
      saveInstructions(instructions);
    }
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
  const memory = deliverable.deliverable_memory;
  const observations = memory?.observations || [];
  const goal = memory?.goal;

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
                {/* Mode badge */}
                {isGoalMode ? (
                  <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400">
                    <Target className="w-3 h-3" />
                    Goal
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400">
                    <Repeat className="w-3 h-3" />
                    Recurring
                  </span>
                )}
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
                    <span>&rarr;</span>
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
                      <span className="text-sm text-red-600/70 dark:text-red-400/70">&mdash; {selectedVersion.delivery_error}</span>
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
              {running ? 'Generating...' : isGoalMode ? 'Generate Update' : 'Run Now'}
            </button>
          </div>
        )}

        {/* ================================================================ */}
        {/* Schedule (hidden for goal mode)                                 */}
        {/* ================================================================ */}
        {!isGoalMode && (
          <div className="border border-border rounded-lg">
            <div className="px-4 py-3 border-b border-border bg-muted/30">
              <h2 className="text-sm font-medium">Schedule</h2>
            </div>
            {missingSourcesWarning && (
              <div className="px-4 py-2.5 bg-amber-50 dark:bg-amber-900/20 border-b border-amber-200 dark:border-amber-800 text-xs text-amber-800 dark:text-amber-300 flex items-center gap-2">
                <span className="shrink-0">&#9888;</span>
                No sources configured &mdash; open Settings to select which {deliverable.type_classification?.primary_platform ?? 'platform'} content to monitor.
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
        )}

        {/* Goal progress (for goal mode) */}
        {isGoalMode && goal && (
          <div className="border border-border rounded-lg">
            <div className="px-4 py-3 border-b border-border bg-muted/30">
              <h2 className="text-sm font-medium">Goal Progress</h2>
            </div>
            <div className="p-4 space-y-2">
              <p className="text-sm">{goal.description}</p>
              <p className="text-xs text-muted-foreground">Status: {goal.status}</p>
              {goal.milestones && goal.milestones.length > 0 && (
                <ul className="text-xs text-muted-foreground space-y-1 mt-2">
                  {goal.milestones.map((m, i) => (
                    <li key={i} className="flex items-center gap-2">
                      <span className="w-1.5 h-1.5 rounded-full bg-muted-foreground/40 shrink-0" />
                      {m}
                    </li>
                  ))}
                </ul>
              )}
              <button
                onClick={handleRunNow}
                disabled={running || deliverable.status === 'archived'}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm border border-border rounded-md hover:bg-muted disabled:opacity-50 mt-2 transition-colors"
              >
                {running ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Play className="w-3.5 h-3.5" />}
                Generate Update
              </button>
            </div>
          </div>
        )}

        {/* ================================================================ */}
        {/* Tabbed Sections (ADR-087 Phase 3)                               */}
        {/* ================================================================ */}
        <div className="border border-border rounded-lg overflow-hidden">
          {/* Tab bar */}
          <div className="flex border-b border-border bg-muted/30">
            {TABS.map((tab) => {
              const Icon = tab.icon;
              const isActive = activeTab === tab.id;
              // Badge counts
              let badge: string | null = null;
              if (tab.id === 'history' && versions.length > 0) badge = String(versions.length);
              if (tab.id === 'memory' && observations.length > 0) badge = String(observations.length);

              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={cn(
                    "flex items-center gap-1.5 px-4 py-2.5 text-sm transition-colors relative",
                    isActive
                      ? "text-foreground font-medium"
                      : "text-muted-foreground hover:text-foreground"
                  )}
                >
                  <Icon className="w-3.5 h-3.5" />
                  {tab.label}
                  {badge && (
                    <span className="text-[10px] bg-muted text-muted-foreground px-1.5 py-0.5 rounded-full">
                      {badge}
                    </span>
                  )}
                  {isActive && (
                    <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-primary" />
                  )}
                </button>
              );
            })}
          </div>

          {/* Tab content */}
          <div className="min-h-[120px]">
            {/* History tab */}
            {activeTab === 'history' && (
              versions.length > 0 ? (
                <div>
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
              ) : (
                <div className="p-6 text-center text-sm text-muted-foreground">
                  No deliveries yet.
                </div>
              )
            )}

            {/* Instructions tab */}
            {activeTab === 'instructions' && (
              <div className="p-4">
                <textarea
                  value={instructions}
                  onChange={(e) => handleInstructionsChange(e.target.value)}
                  onBlur={handleInstructionsBlur}
                  placeholder="Add instructions for how the agent should approach this deliverable. Examples:&#10;&#10;Use formal tone for this board report.&#10;Always include an executive summary section.&#10;Focus on trend analysis rather than raw numbers.&#10;The audience is the executive team."
                  className="w-full min-h-[160px] px-3 py-2 text-sm font-mono bg-background border border-border rounded-md focus:outline-none focus:ring-2 focus:ring-primary/20 resize-y placeholder:text-muted-foreground/60"
                />
                <div className="flex items-center justify-end mt-2 h-5">
                  {instructionsSaving && (
                    <span className="text-xs text-muted-foreground flex items-center gap-1">
                      <Loader2 className="w-3 h-3 animate-spin" /> Saving...
                    </span>
                  )}
                  {instructionsSaved && !instructionsSaving && (
                    <span className="text-xs text-green-600 flex items-center gap-1">
                      <CheckCircle2 className="w-3 h-3" /> Saved
                    </span>
                  )}
                </div>
              </div>
            )}

            {/* Memory tab */}
            {activeTab === 'memory' && (
              <div className="p-4">
                {observations.length === 0 && !goal ? (
                  <p className="text-sm text-muted-foreground text-center py-4">
                    No observations yet. The agent accumulates knowledge as it processes content for this deliverable.
                  </p>
                ) : (
                  <div className="space-y-3">
                    {goal && (
                      <div className="p-3 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-md">
                        <div className="flex items-center gap-2 mb-1">
                          <Target className="w-3.5 h-3.5 text-blue-600 dark:text-blue-400" />
                          <span className="text-xs font-medium text-blue-700 dark:text-blue-400">Goal</span>
                        </div>
                        <p className="text-sm">{goal.description}</p>
                        <p className="text-xs text-muted-foreground mt-1">Status: {goal.status}</p>
                      </div>
                    )}
                    {observations.map((obs, i) => (
                      <div key={i} className="p-3 bg-muted/30 border border-border rounded-md">
                        <div className="flex items-center gap-2 text-xs text-muted-foreground mb-1">
                          <span>{obs.date}</span>
                          {obs.source && (
                            <>
                              <span className="text-border">&middot;</span>
                              <span>{obs.source}</span>
                            </>
                          )}
                        </div>
                        <p className="text-sm">{obs.note}</p>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* Sessions tab */}
            {activeTab === 'sessions' && (
              <div className="p-4">
                {sessions.length === 0 ? (
                  <p className="text-sm text-muted-foreground text-center py-4">
                    No scoped conversations yet. Chat with this deliverable open to build session history.
                  </p>
                ) : (
                  <div className="space-y-2">
                    {sessions.map((session) => (
                      <div key={session.id} className="p-3 bg-muted/30 border border-border rounded-md">
                        <div className="flex items-center justify-between mb-1">
                          <span className="text-xs text-muted-foreground">
                            {format(new Date(session.created_at), 'MMM d, h:mm a')}
                          </span>
                          <span className="text-xs text-muted-foreground">
                            {session.message_count} message{session.message_count !== 1 ? 's' : ''}
                          </span>
                        </div>
                        {session.summary ? (
                          <p className="text-sm line-clamp-2">{session.summary}</p>
                        ) : (
                          <p className="text-sm text-muted-foreground italic">No summary</p>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Settings Modal */}
      <DeliverableSettingsModal
        deliverable={deliverable}
        open={settingsOpen}
        onClose={() => setSettingsOpen(false)}
        onSaved={(updated) => {
          setDeliverable(updated);
          setInstructions(updated.deliverable_instructions || '');
        }}
        onArchived={() => router.push('/deliverables')}
      />
    </div>
  );
}
