'use client';

/**
 * DeliverableSettingsModal - ADR-066: Simplified Settings
 *
 * Configuration-only modal. Review happens on the detail page.
 *
 * Sections:
 * 1. Destination (where does this go?) - REQUIRED
 * 2. Title (what is it called?)
 * 3. Schedule (when does it run?)
 * 4. Data Sources (what informs it?)
 *
 * Recipient Context collapsed as advanced option.
 * Governance fixed to "manual" (draft mode).
 */

import { useState, useEffect } from 'react';
import {
  X,
  Loader2,
  Link as LinkIcon,
  FileText,
  Plus,
  Trash2,
  Clock,
  User,
  AlertTriangle,
  Mail,
  ExternalLink,
  Send,
  Slack,
  FileCode,
  Download,
  Calendar,
  CheckCircle2,
} from 'lucide-react';
import Link from 'next/link';
import { api } from '@/lib/api/client';
import { cn } from '@/lib/utils';
// ADR-066: Removed DestinationSelector - using email-first approach
import type {
  Deliverable,
  DeliverableUpdate,
  DataSource,
  DataSourceType,
  IntegrationProvider,
  ScheduleConfig,
  RecipientContext,
  ScheduleFrequency,
  Destination,
  IntegrationSourceScope,
  ScopeMode,
} from '@/types';

interface DeliverableSettingsModalProps {
  deliverable: Deliverable;
  open: boolean;
  onClose: () => void;
  onSaved: (updated: Deliverable) => void;
  onArchived?: () => void;
}

const FREQUENCY_OPTIONS: { value: ScheduleFrequency; label: string }[] = [
  { value: 'daily', label: 'Daily' },
  { value: 'weekly', label: 'Weekly' },
  { value: 'biweekly', label: 'Every 2 weeks' },
  { value: 'monthly', label: 'Monthly' },
];

const DAY_OPTIONS = [
  { value: 'monday', label: 'Monday' },
  { value: 'tuesday', label: 'Tuesday' },
  { value: 'wednesday', label: 'Wednesday' },
  { value: 'thursday', label: 'Thursday' },
  { value: 'friday', label: 'Friday' },
  { value: 'saturday', label: 'Saturday' },
  { value: 'sunday', label: 'Sunday' },
];

// ADR-082: 8 active type labels (deprecated types fall through to raw name)
const DELIVERABLE_TYPE_LABELS: Record<string, string> = {
  slack_channel_digest: 'Channel Digest',
  gmail_inbox_brief: 'Inbox Brief',
  notion_page_summary: 'Page Summary',
  meeting_prep: 'Meeting Prep',
  weekly_calendar_preview: 'Week Preview',
  status_report: 'Status Report',
  research_brief: 'Research Brief',
  custom: 'Custom',
};

const PLATFORM_ICONS: Record<string, React.ReactNode> = {
  slack: <Slack className="w-4 h-4" />,
  notion: <FileCode className="w-4 h-4" />,
  gmail: <Mail className="w-4 h-4" />,
  download: <Download className="w-4 h-4" />,
  google: <Calendar className="w-4 h-4" />,
  calendar: <Calendar className="w-4 h-4" />,
};

const PLATFORM_COLORS: Record<string, string> = {
  slack: 'text-purple-500',
  notion: 'text-gray-700',
  gmail: 'text-red-500',
  download: 'text-blue-500',
  google: 'text-blue-500',
  calendar: 'text-blue-500',
};

export function DeliverableSettingsModal({
  deliverable,
  open,
  onClose,
  onSaved,
  onArchived,
}: DeliverableSettingsModalProps) {
  const [saving, setSaving] = useState(false);
  const [archiving, setArchiving] = useState(false);
  const [showArchiveConfirm, setShowArchiveConfirm] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // User email for email-first default
  const [userEmail, setUserEmail] = useState<string | null>(null);

  // Form state
  const [title, setTitle] = useState(deliverable.title);
  const [schedule, setSchedule] = useState<ScheduleConfig>(
    deliverable.schedule || { frequency: 'weekly', day: 'monday', time: '09:00' }
  );
  const [sources, setSources] = useState<DataSource[]>(deliverable.sources || []);
  const [recipient, setRecipient] = useState<RecipientContext>(
    deliverable.recipient_context || {}
  );
  // ADR-066: Destination defaults to user's email (email-first)
  const [destination, setDestination] = useState<Destination | undefined>(
    deliverable.destination
  );
  // New source input - ADR-029 Phase 2: Extended for integration_import
  const [newSourceType, setNewSourceType] = useState<DataSourceType>('url');
  const [newSourceValue, setNewSourceValue] = useState('');
  const [newSourceProvider, setNewSourceProvider] = useState<IntegrationProvider>('gmail');
  const [newSourceQuery, setNewSourceQuery] = useState('inbox');
  const [newSourceFilters, setNewSourceFilters] = useState<{
    from?: string;
    subject_contains?: string;
    after?: string;
  }>({});
  // ADR-030: Scope configuration for integration sources
  const [newSourceScope, setNewSourceScope] = useState<IntegrationSourceScope>({
    mode: 'delta',
    fallback_days: 7,
    max_items: 200,
  });

  // Load user email for email-first default
  useEffect(() => {
    const loadUserEmail = async () => {
      try {
        const { createClient } = await import('@/lib/supabase/client');
        const supabase = createClient();
        const { data: { user } } = await supabase.auth.getUser();
        if (user?.email) {
          setUserEmail(user.email);
        }
      } catch (err) {
        console.error('Failed to load user email:', err);
      }
    };
    loadUserEmail();
  }, []);

  // Reset form when deliverable changes
  useEffect(() => {
    setTitle(deliverable.title);
    setSchedule(deliverable.schedule || { frequency: 'weekly', day: 'monday', time: '09:00' });
    setSources(deliverable.sources || []);
    setRecipient(deliverable.recipient_context || {});
    // ADR-066: Default to user's email if destination is incomplete
    const dest = deliverable.destination;
    if (!dest || !dest.target) {
      // Set default email destination once we have user email
      if (userEmail) {
        setDestination({
          platform: 'email',
          target: userEmail,
          format: 'send',
        });
      } else {
        setDestination(dest);
      }
    } else {
      setDestination(dest);
    }
    setError(null);
  }, [deliverable, userEmail]);

  const handleSave = async () => {
    // ADR-066: Ensure destination has email default
    let finalDestination = destination;
    if (!finalDestination || !finalDestination.target) {
      if (userEmail) {
        finalDestination = {
          platform: 'email',
          target: userEmail,
          format: 'send',
        };
      } else {
        setError('Unable to determine delivery email. Please try again.');
        return;
      }
    }

    setSaving(true);
    setError(null);

    try {
      const update: DeliverableUpdate = {
        title,
        schedule,
        sources,
        recipient_context: recipient,
        destination: finalDestination,
      };

      await api.deliverables.update(deliverable.id, update);

      // Return updated deliverable
      onSaved({
        ...deliverable,
        ...update,
      });
      onClose();
    } catch (err) {
      console.error('Failed to update deliverable:', err);
      setError('Failed to save changes. Please try again.');
    } finally {
      setSaving(false);
    }
  };

  const handleArchive = async () => {
    setArchiving(true);
    setError(null);

    try {
      await api.deliverables.delete(deliverable.id);
      onArchived?.();
      onClose();
    } catch (err) {
      console.error('Failed to archive deliverable:', err);
      setError('Failed to archive. Please try again.');
    } finally {
      setArchiving(false);
      setShowArchiveConfirm(false);
    }
  };

  const addSource = () => {
    // ADR-029 Phase 2 + ADR-030: Handle integration_import sources with scope
    if (newSourceType === 'integration_import') {
      const newSource: DataSource = {
        type: 'integration_import',
        value: `${newSourceProvider}:${newSourceQuery}`,
        label: `${newSourceProvider.charAt(0).toUpperCase() + newSourceProvider.slice(1)} - ${newSourceQuery}`,
        provider: newSourceProvider,
        source: newSourceQuery,
        filters: Object.keys(newSourceFilters).length > 0 ? newSourceFilters : undefined,
        scope: newSourceScope,
      };
      setSources([...sources, newSource]);
      setNewSourceQuery('inbox');
      setNewSourceFilters({});
      setNewSourceScope({ mode: 'delta', fallback_days: 7, max_items: 200 });
      return;
    }

    if (!newSourceValue.trim()) return;

    const newSource: DataSource = {
      type: newSourceType,
      value: newSourceValue.trim(),
      label: newSourceType === 'url' ? new URL(newSourceValue).hostname : undefined,
    };

    setSources([...sources, newSource]);
    setNewSourceValue('');
  };

  const removeSource = (index: number) => {
    setSources(sources.filter((_, i) => i !== index));
  };

  if (!open) return null;

  const showDaySelector = schedule.frequency === 'weekly' || schedule.frequency === 'biweekly';

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/50" onClick={onClose} />

      {/* Modal */}
      <div className="relative bg-background rounded-lg shadow-xl w-full max-w-lg max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-border">
          <div>
            <h2 className="text-lg font-semibold">Deliverable Settings</h2>
            <p className="text-sm text-muted-foreground">
              {DELIVERABLE_TYPE_LABELS[deliverable.deliverable_type] || deliverable.deliverable_type}
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-muted rounded-md text-muted-foreground"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto px-6 py-4 space-y-6">
          {/* Error */}
          {error && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-md text-sm text-red-700 flex items-center gap-2">
              <AlertTriangle className="w-4 h-4" />
              {error}
            </div>
          )}

          {/* ============================================ */}
          {/* STEP 1: DESTINATION (ADR-066 Email-First) */}
          {/* ============================================ */}
          <div className="p-4 bg-primary/5 border border-primary/20 rounded-lg">
            <div className="flex items-center gap-2 mb-3">
              <Send className="w-4 h-4 text-primary" />
              <label className="text-sm font-medium">
                Destination
                <span className="text-red-500 ml-1">*</span>
              </label>
            </div>

            {/* Email-first: Simple destination display */}
            <div className="flex items-center gap-3 p-3 bg-background rounded-md border border-border">
              <div className="shrink-0 text-red-500">
                <Mail className="w-4 h-4" />
              </div>
              <div className="flex-1 min-w-0">
                <div className="text-sm font-medium">
                  Email
                </div>
                <div className="text-xs text-muted-foreground truncate">
                  → {destination?.target || userEmail || 'Loading...'}
                </div>
              </div>
            </div>

            {/* Delivery confirmation */}
            <div className="flex items-center gap-2 mt-3 text-xs text-muted-foreground">
              <CheckCircle2 className="w-3.5 h-3.5 text-green-500" />
              <span>Deliverables will be sent to your email</span>
            </div>
          </div>

          {/* ============================================ */}
          {/* STEP 2: TITLE */}
          {/* ============================================ */}
          <div>
            <label className="block text-sm font-medium mb-1.5">Title</label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="w-full px-3 py-2 border border-border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary/20"
              placeholder="e.g., Weekly Status Report"
            />
          </div>

          {/* ============================================ */}
          {/* STEP 3: SCHEDULE */}
          {/* ============================================ */}
          <div>
            <label className="block text-sm font-medium mb-1.5 flex items-center gap-1.5">
              <Clock className="w-4 h-4" />
              Schedule
            </label>
            <div className="grid grid-cols-3 gap-3">
              {/* Frequency */}
              <select
                value={schedule.frequency}
                onChange={(e) =>
                  setSchedule({ ...schedule, frequency: e.target.value as ScheduleFrequency })
                }
                className="px-3 py-2 border border-border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary/20"
              >
                {FREQUENCY_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>

              {/* Day (for weekly/biweekly) */}
              {showDaySelector && (
                <select
                  value={schedule.day || 'monday'}
                  onChange={(e) => setSchedule({ ...schedule, day: e.target.value })}
                  className="px-3 py-2 border border-border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary/20"
                >
                  {DAY_OPTIONS.map((opt) => (
                    <option key={opt.value} value={opt.value}>
                      {opt.label}
                    </option>
                  ))}
                </select>
              )}

              {/* Time */}
              <input
                type="time"
                value={schedule.time || '09:00'}
                onChange={(e) => setSchedule({ ...schedule, time: e.target.value })}
                className="px-3 py-2 border border-border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary/20"
              />
            </div>
          </div>

          {/* ============================================ */}
          {/* STEP 4: DATA SOURCES */}
          {/* ============================================ */}
          <div>
            <label className="block text-sm font-medium mb-1.5">Data Sources</label>
            <p className="text-xs text-muted-foreground mb-3">
              What context should inform this deliverable?
            </p>

            {/* Existing sources */}
            {sources.length > 0 && (
              <div className="space-y-2 mb-3">
                {sources.map((source, index) => (
                  <div
                    key={index}
                    className="flex items-center gap-2 p-2 bg-muted/50 rounded-md text-sm"
                  >
                    {source.type === 'url' ? (
                      <LinkIcon className="w-4 h-4 text-muted-foreground shrink-0" />
                    ) : source.type === 'integration_import' ? (
                      source.provider === 'gmail' ? (
                        <Mail className="w-4 h-4 text-red-500 shrink-0" />
                      ) : source.provider === 'slack' ? (
                        <Slack className="w-4 h-4 text-purple-500 shrink-0" />
                      ) : (
                        <FileCode className="w-4 h-4 text-gray-500 shrink-0" />
                      )
                    ) : (
                      <FileText className="w-4 h-4 text-muted-foreground shrink-0" />
                    )}
                    <span className="flex-1 truncate">
                      {source.label || source.value}
                      {source.type === 'integration_import' && (
                        <span className="text-xs text-muted-foreground ml-1">
                          {source.scope?.mode === 'delta' ? '(delta)' : source.scope?.mode === 'fixed_window' ? `(${source.scope.recency_days || 7}d)` : ''}
                          {source.filters && Object.keys(source.filters).length > 0 ? ' filtered' : ''}
                        </span>
                      )}
                    </span>
                    <button
                      onClick={() => removeSource(index)}
                      className="p-1 hover:bg-muted rounded text-muted-foreground hover:text-red-600"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                ))}
              </div>
            )}

            {/* Add new source - Type selector */}
            <div className="space-y-3">
              <div className="flex gap-2">
                <select
                  value={newSourceType}
                  onChange={(e) => setNewSourceType(e.target.value as DataSourceType)}
                  className="px-3 py-2 border border-border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary/20"
                >
                  <option value="url">URL</option>
                  <option value="description">Description</option>
                  <option value="integration_import">Integration</option>
                </select>

                {/* URL/Description input */}
                {newSourceType !== 'integration_import' && (
                  <>
                    <input
                      type={newSourceType === 'url' ? 'url' : 'text'}
                      value={newSourceValue}
                      onChange={(e) => setNewSourceValue(e.target.value)}
                      placeholder={newSourceType === 'url' ? 'https://...' : 'Describe the source...'}
                      className="flex-1 px-3 py-2 border border-border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary/20"
                      onKeyDown={(e) => e.key === 'Enter' && addSource()}
                    />
                    <button
                      onClick={addSource}
                      disabled={!newSourceValue.trim()}
                      className="px-3 py-2 bg-muted hover:bg-muted/80 rounded-md disabled:opacity-50"
                    >
                      <Plus className="w-4 h-4" />
                    </button>
                  </>
                )}

                {/* Integration import selector */}
                {newSourceType === 'integration_import' && (
                  <select
                    value={newSourceProvider}
                    onChange={(e) => {
                      setNewSourceProvider(e.target.value as IntegrationProvider);
                      setNewSourceQuery(e.target.value === 'gmail' ? 'inbox' : '');
                    }}
                    className="px-3 py-2 border border-border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary/20"
                  >
                    <option value="gmail">Gmail</option>
                    <option value="slack">Slack</option>
                    <option value="notion">Notion</option>
                  </select>
                )}
              </div>

              {/* Integration import configuration */}
              {newSourceType === 'integration_import' && (
                <div className="p-3 border border-border rounded-md space-y-3 bg-muted/30">
                  {/* Gmail-specific options */}
                  {newSourceProvider === 'gmail' && (
                    <>
                      <div>
                        <label className="block text-xs font-medium mb-1">Source</label>
                        <select
                          value={newSourceQuery}
                          onChange={(e) => setNewSourceQuery(e.target.value)}
                          className="w-full px-3 py-2 border border-border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary/20"
                        >
                          <option value="inbox">Inbox (recent messages)</option>
                          <option value="query:is:unread">Unread messages</option>
                          <option value="query:is:starred">Starred messages</option>
                          <option value="query:in:sent">Sent messages</option>
                        </select>
                      </div>
                      <div className="grid grid-cols-2 gap-2">
                        <div>
                          <label className="block text-xs font-medium mb-1">From (optional)</label>
                          <input
                            type="text"
                            value={newSourceFilters.from || ''}
                            onChange={(e) => setNewSourceFilters({ ...newSourceFilters, from: e.target.value || undefined })}
                            placeholder="sender@example.com"
                            className="w-full px-2 py-1.5 border border-border rounded-md text-xs focus:outline-none focus:ring-2 focus:ring-primary/20"
                          />
                        </div>
                        <div>
                          <label className="block text-xs font-medium mb-1">Subject contains</label>
                          <input
                            type="text"
                            value={newSourceFilters.subject_contains || ''}
                            onChange={(e) => setNewSourceFilters({ ...newSourceFilters, subject_contains: e.target.value || undefined })}
                            placeholder="keyword"
                            className="w-full px-2 py-1.5 border border-border rounded-md text-xs focus:outline-none focus:ring-2 focus:ring-primary/20"
                          />
                        </div>
                      </div>
                      <div>
                        <label className="block text-xs font-medium mb-1">Time range</label>
                        <select
                          value={newSourceFilters.after || ''}
                          onChange={(e) => setNewSourceFilters({ ...newSourceFilters, after: e.target.value || undefined })}
                          className="w-full px-2 py-1.5 border border-border rounded-md text-xs focus:outline-none focus:ring-2 focus:ring-primary/20"
                        >
                          <option value="">All time</option>
                          <option value="1d">Last 24 hours</option>
                          <option value="7d">Last 7 days</option>
                          <option value="14d">Last 14 days</option>
                          <option value="30d">Last 30 days</option>
                        </select>
                      </div>
                    </>
                  )}

                  {/* Slack-specific options */}
                  {newSourceProvider === 'slack' && (
                    <div>
                      <label className="block text-xs font-medium mb-1">Channel ID</label>
                      <input
                        type="text"
                        value={newSourceQuery}
                        onChange={(e) => setNewSourceQuery(e.target.value)}
                        placeholder="C01234567"
                        className="w-full px-2 py-1.5 border border-border rounded-md text-xs focus:outline-none focus:ring-2 focus:ring-primary/20"
                      />
                      <p className="text-[10px] text-muted-foreground mt-1">
                        Enter the Slack channel ID to pull messages from
                      </p>
                    </div>
                  )}

                  {/* Notion-specific options */}
                  {newSourceProvider === 'notion' && (
                    <div>
                      <label className="block text-xs font-medium mb-1">Page ID</label>
                      <input
                        type="text"
                        value={newSourceQuery}
                        onChange={(e) => setNewSourceQuery(e.target.value)}
                        placeholder="abc123..."
                        className="w-full px-2 py-1.5 border border-border rounded-md text-xs focus:outline-none focus:ring-2 focus:ring-primary/20"
                      />
                      <p className="text-[10px] text-muted-foreground mt-1">
                        Enter the Notion page ID to pull content from
                      </p>
                    </div>
                  )}

                  {/* ADR-030: Scope configuration for delta extraction */}
                  <div className="pt-3 border-t border-border">
                    <label className="block text-xs font-medium mb-2">
                      Extraction Mode
                    </label>
                    <div className="grid grid-cols-2 gap-2 mb-3">
                      <button
                        type="button"
                        onClick={() => setNewSourceScope({ ...newSourceScope, mode: 'delta' })}
                        className={cn(
                          "p-2 rounded-md border text-left transition-colors",
                          newSourceScope.mode === 'delta'
                            ? "border-primary bg-primary/5"
                            : "border-border hover:border-muted-foreground/50"
                        )}
                      >
                        <div className="text-xs font-medium">Delta</div>
                        <div className="text-[10px] text-muted-foreground">
                          Since last run
                        </div>
                      </button>
                      <button
                        type="button"
                        onClick={() => setNewSourceScope({ ...newSourceScope, mode: 'fixed_window' })}
                        className={cn(
                          "p-2 rounded-md border text-left transition-colors",
                          newSourceScope.mode === 'fixed_window'
                            ? "border-primary bg-primary/5"
                            : "border-border hover:border-muted-foreground/50"
                        )}
                      >
                        <div className="text-xs font-medium">Fixed Window</div>
                        <div className="text-[10px] text-muted-foreground">
                          Always last N days
                        </div>
                      </button>
                    </div>

                    <div className="grid grid-cols-2 gap-2">
                      {newSourceScope.mode === 'delta' ? (
                        <div>
                          <label className="block text-[10px] font-medium text-muted-foreground mb-1">
                            Fallback (first run)
                          </label>
                          <select
                            value={newSourceScope.fallback_days || 7}
                            onChange={(e) => setNewSourceScope({
                              ...newSourceScope,
                              fallback_days: parseInt(e.target.value)
                            })}
                            className="w-full px-2 py-1.5 border border-border rounded-md text-xs"
                          >
                            <option value={1}>1 day</option>
                            <option value={3}>3 days</option>
                            <option value={7}>7 days</option>
                            <option value={14}>14 days</option>
                            <option value={30}>30 days</option>
                          </select>
                        </div>
                      ) : (
                        <div>
                          <label className="block text-[10px] font-medium text-muted-foreground mb-1">
                            Window size
                          </label>
                          <select
                            value={newSourceScope.recency_days || 7}
                            onChange={(e) => setNewSourceScope({
                              ...newSourceScope,
                              recency_days: parseInt(e.target.value)
                            })}
                            className="w-full px-2 py-1.5 border border-border rounded-md text-xs"
                          >
                            <option value={1}>1 day</option>
                            <option value={3}>3 days</option>
                            <option value={7}>7 days</option>
                            <option value={14}>14 days</option>
                            <option value={30}>30 days</option>
                          </select>
                        </div>
                      )}
                      <div>
                        <label className="block text-[10px] font-medium text-muted-foreground mb-1">
                          Max items
                        </label>
                        <select
                          value={newSourceScope.max_items || 200}
                          onChange={(e) => setNewSourceScope({
                            ...newSourceScope,
                            max_items: parseInt(e.target.value)
                          })}
                          className="w-full px-2 py-1.5 border border-border rounded-md text-xs"
                        >
                          <option value={50}>50</option>
                          <option value={100}>100</option>
                          <option value={200}>200</option>
                          <option value={500}>500</option>
                        </select>
                      </div>
                    </div>
                  </div>

                  <button
                    onClick={addSource}
                    disabled={!newSourceQuery.trim()}
                    className="w-full px-3 py-2 bg-primary text-primary-foreground hover:bg-primary/90 rounded-md text-sm disabled:opacity-50"
                  >
                    Add Integration Source
                  </button>
                </div>
              )}
            </div>
          </div>

          {/* ============================================ */}
          {/* STEP 5: RECIPIENT (Collapsed/Advanced) */}
          {/* ============================================ */}
          <details className="group">
            <summary className="cursor-pointer text-sm font-medium flex items-center gap-1.5 py-2 list-none">
              <User className="w-4 h-4" />
              Recipient Context
              <span className="text-xs text-muted-foreground ml-2">(optional)</span>
            </summary>
            <div className="pt-3 space-y-3">
              <p className="text-xs text-muted-foreground">
                This personalizes the content for your audience
              </p>
              <input
                type="text"
                value={recipient.name || ''}
                onChange={(e) => setRecipient({ ...recipient, name: e.target.value })}
                placeholder="Name (e.g., Sarah, Board)"
                className="w-full px-3 py-2 border border-border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary/20"
              />
              <input
                type="text"
                value={recipient.role || ''}
                onChange={(e) => setRecipient({ ...recipient, role: e.target.value })}
                placeholder="Role (e.g., Manager, Investor)"
                className="w-full px-3 py-2 border border-border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary/20"
              />
              <textarea
                value={recipient.notes || ''}
                onChange={(e) => setRecipient({ ...recipient, notes: e.target.value })}
                placeholder="Notes (e.g., prefers bullet points, wants metrics upfront)"
                rows={2}
                className="w-full px-3 py-2 border border-border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary/20 resize-none"
              />
            </div>
          </details>

          {/* ============================================ */}
          {/* DANGER ZONE: Archive */}
          {/* ============================================ */}
          <div className="pt-4 mt-4 border-t border-border">
            {!showArchiveConfirm ? (
              <button
                onClick={() => setShowArchiveConfirm(true)}
                className="text-sm text-red-600 hover:text-red-700 flex items-center gap-1.5"
              >
                <Trash2 className="w-4 h-4" />
                Archive this deliverable
              </button>
            ) : (
              <div className="p-3 bg-red-50 dark:bg-red-950/30 border border-red-200 dark:border-red-800 rounded-md">
                <p className="text-sm text-red-800 dark:text-red-200 mb-3">
                  Are you sure? This will stop all scheduled runs. You can't undo this.
                </p>
                <div className="flex items-center gap-2">
                  <button
                    onClick={handleArchive}
                    disabled={archiving}
                    className="px-3 py-1.5 text-sm bg-red-600 text-white rounded-md hover:bg-red-700 disabled:opacity-50 flex items-center gap-1.5"
                  >
                    {archiving && <Loader2 className="w-3 h-3 animate-spin" />}
                    Yes, archive it
                  </button>
                  <button
                    onClick={() => setShowArchiveConfirm(false)}
                    disabled={archiving}
                    className="px-3 py-1.5 text-sm border border-border rounded-md hover:bg-muted"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-border bg-muted/30">
          <button
            onClick={onClose}
            disabled={saving}
            className="px-4 py-2 text-sm border border-border rounded-md hover:bg-muted"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={saving || !title.trim() || !destination}
            className="px-4 py-2 text-sm bg-primary text-primary-foreground rounded-md hover:bg-primary/90 disabled:opacity-50 flex items-center gap-2"
          >
            {saving && <Loader2 className="w-4 h-4 animate-spin" />}
            Save Changes
          </button>
        </div>
      </div>
    </div>
  );
}
