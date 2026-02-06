'use client';

/**
 * DeliverableSettingsModal - Full modal for editing deliverable configuration
 *
 * Editable fields:
 * - Title
 * - Schedule (frequency, day, time)
 * - Data sources (add/remove URLs, descriptions)
 * - Recipient context
 * - Status (pause/archive)
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
} from 'lucide-react';
import Link from 'next/link';
import { api } from '@/lib/api/client';
import { cn } from '@/lib/utils';
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
  GovernanceLevel,
} from '@/types';

interface DeliverableSettingsModalProps {
  deliverable: Deliverable;
  open: boolean;
  onClose: () => void;
  onSaved: (updated: Deliverable) => void;
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

const DELIVERABLE_TYPE_LABELS: Record<string, string> = {
  status_report: 'Status Report',
  stakeholder_update: 'Stakeholder Update',
  research_brief: 'Research Brief',
  meeting_summary: 'Meeting Summary',
  custom: 'Custom',
  client_proposal: 'Client Proposal',
  performance_self_assessment: 'Performance Self-Assessment',
  newsletter_section: 'Newsletter Section',
  changelog: 'Changelog',
  one_on_one_prep: '1:1 Prep',
  board_update: 'Board Update',
  // ADR-029 Phase 3: Email-specific types
  inbox_summary: 'Inbox Summary',
  reply_draft: 'Reply Draft',
  follow_up_tracker: 'Follow-up Tracker',
  thread_summary: 'Thread Summary',
};

// ADR-028: Governance options
const GOVERNANCE_OPTIONS: { value: GovernanceLevel; label: string; description: string }[] = [
  { value: 'manual', label: 'Manual', description: 'You click export after approving' },
  { value: 'semi_auto', label: 'Semi-auto', description: 'Auto-delivers after you approve' },
  { value: 'full_auto', label: 'Full-auto', description: 'Delivers immediately (skip review)' },
];

const PLATFORM_ICONS: Record<string, React.ReactNode> = {
  slack: <Slack className="w-4 h-4" />,
  notion: <FileCode className="w-4 h-4" />,
  gmail: <Mail className="w-4 h-4" />,  // ADR-029
  download: <Download className="w-4 h-4" />,
};

export function DeliverableSettingsModal({
  deliverable,
  open,
  onClose,
  onSaved,
}: DeliverableSettingsModalProps) {
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Form state
  const [title, setTitle] = useState(deliverable.title);
  const [schedule, setSchedule] = useState<ScheduleConfig>(
    deliverable.schedule || { frequency: 'weekly', day: 'monday', time: '09:00' }
  );
  const [sources, setSources] = useState<DataSource[]>(deliverable.sources || []);
  const [recipient, setRecipient] = useState<RecipientContext>(
    deliverable.recipient_context || {}
  );
  // ADR-028: Destination and governance state
  const [destination, setDestination] = useState<Destination | undefined>(
    deliverable.destination
  );
  const [governance, setGovernance] = useState<GovernanceLevel>(
    deliverable.governance || 'manual'
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

  // Reset form when deliverable changes
  useEffect(() => {
    setTitle(deliverable.title);
    setSchedule(deliverable.schedule || { frequency: 'weekly', day: 'monday', time: '09:00' });
    setSources(deliverable.sources || []);
    setRecipient(deliverable.recipient_context || {});
    setDestination(deliverable.destination);
    setGovernance(deliverable.governance || 'manual');
    setError(null);
  }, [deliverable]);

  const handleSave = async () => {
    setSaving(true);
    setError(null);

    try {
      const update: DeliverableUpdate = {
        title,
        schedule,
        sources,
        recipient_context: recipient,
        destination,
        governance,
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

  const addSource = () => {
    // ADR-029 Phase 2: Handle integration_import sources
    if (newSourceType === 'integration_import') {
      const newSource: DataSource = {
        type: 'integration_import',
        value: `${newSourceProvider}:${newSourceQuery}`,
        label: `${newSourceProvider.charAt(0).toUpperCase() + newSourceProvider.slice(1)} - ${newSourceQuery}`,
        provider: newSourceProvider,
        source: newSourceQuery,
        filters: Object.keys(newSourceFilters).length > 0 ? newSourceFilters : undefined,
      };
      setSources([...sources, newSource]);
      setNewSourceQuery('inbox');
      setNewSourceFilters({});
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

          {/* Title */}
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

          {/* Schedule */}
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

          {/* Data Sources */}
          <div>
            <label className="block text-sm font-medium mb-1.5">Data Sources</label>
            <p className="text-xs text-muted-foreground mb-3">
              URLs, documents, descriptions, or integration data that inform this deliverable
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
                      {source.type === 'integration_import' && source.filters && Object.keys(source.filters).length > 0 && (
                        <span className="text-xs text-muted-foreground ml-1">
                          (filtered)
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

          {/* Recipient */}
          <div>
            <label className="block text-sm font-medium mb-1.5 flex items-center gap-1.5">
              <User className="w-4 h-4" />
              Recipient
            </label>
            <p className="text-xs text-muted-foreground mb-3">
              This personalizes the content for your audience (not used for email delivery)
            </p>
            <div className="space-y-3">
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
          </div>

          {/* ADR-028: Delivery Destination */}
          <div>
            <label className="block text-sm font-medium mb-1.5 flex items-center gap-1.5">
              <Send className="w-4 h-4" />
              Delivery
            </label>
            <p className="text-xs text-muted-foreground mb-3">
              Where should approved versions be delivered?
            </p>

            {/* Current destination display */}
            {destination ? (
              <div className="p-3 bg-muted/50 rounded-md mb-3">
                <div className="flex items-center gap-2">
                  {PLATFORM_ICONS[destination.platform] || <Send className="w-4 h-4" />}
                  <span className="text-sm font-medium capitalize">{destination.platform}</span>
                  {destination.target && (
                    <span className="text-sm text-muted-foreground">→ {destination.target}</span>
                  )}
                  <button
                    onClick={() => setDestination(undefined)}
                    className="ml-auto p-1 hover:bg-muted rounded text-muted-foreground hover:text-red-600"
                    title="Remove destination"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            ) : (
              <div className="p-3 border border-dashed border-border rounded-md text-center text-sm text-muted-foreground mb-3">
                No destination configured — manual export only
              </div>
            )}

            {/* Governance selector */}
            <div className="space-y-2">
              <label className="block text-xs font-medium text-muted-foreground">
                Delivery mode
              </label>
              <div className="grid grid-cols-3 gap-2">
                {GOVERNANCE_OPTIONS.map((opt) => (
                  <button
                    key={opt.value}
                    type="button"
                    onClick={() => setGovernance(opt.value)}
                    className={cn(
                      "p-2 rounded-md border text-left transition-colors",
                      governance === opt.value
                        ? "border-primary bg-primary/5"
                        : "border-border hover:border-muted-foreground/50"
                    )}
                  >
                    <div className="text-xs font-medium">{opt.label}</div>
                    <div className="text-[10px] text-muted-foreground mt-0.5">{opt.description}</div>
                  </button>
                ))}
              </div>
              {!destination && governance !== 'manual' && (
                <p className="text-xs text-amber-600 flex items-center gap-1 mt-1">
                  <AlertTriangle className="w-3 h-3" />
                  Configure a destination to enable auto-delivery
                </p>
              )}
            </div>

            {/* Link to integrations */}
            <Link
              href="/settings?tab=integrations"
              className="text-xs text-primary hover:underline inline-flex items-center gap-1 mt-3"
              onClick={onClose}
            >
              Manage integrations (Slack, Notion, Gmail)
              <ExternalLink className="w-3 h-3" />
            </Link>
          </div>

          {/* Email Notifications Info */}
          <div className="p-3 bg-muted/50 rounded-md">
            <div className="flex items-start gap-3">
              <Mail className="w-4 h-4 text-muted-foreground mt-0.5" />
              <div className="flex-1">
                <p className="text-sm text-muted-foreground">
                  Email notifications are sent to your account email when this deliverable is ready.
                </p>
                <Link
                  href="/settings?tab=notifications"
                  className="text-sm text-primary hover:underline inline-flex items-center gap-1 mt-1"
                  onClick={onClose}
                >
                  Manage notifications
                  <ExternalLink className="w-3 h-3" />
                </Link>
              </div>
            </div>
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
            disabled={saving || !title.trim()}
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
