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
} from 'lucide-react';
import { api } from '@/lib/api/client';
import { cn } from '@/lib/utils';
import type {
  Deliverable,
  DeliverableUpdate,
  DataSource,
  ScheduleConfig,
  RecipientContext,
  ScheduleFrequency,
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

  // New source input
  const [newSourceType, setNewSourceType] = useState<'url' | 'description'>('url');
  const [newSourceValue, setNewSourceValue] = useState('');

  // Reset form when deliverable changes
  useEffect(() => {
    setTitle(deliverable.title);
    setSchedule(deliverable.schedule || { frequency: 'weekly', day: 'monday', time: '09:00' });
    setSources(deliverable.sources || []);
    setRecipient(deliverable.recipient_context || {});
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
              URLs, documents, or descriptions that inform this deliverable
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
                    ) : (
                      <FileText className="w-4 h-4 text-muted-foreground shrink-0" />
                    )}
                    <span className="flex-1 truncate">{source.value}</span>
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

            {/* Add new source */}
            <div className="flex gap-2">
              <select
                value={newSourceType}
                onChange={(e) => setNewSourceType(e.target.value as 'url' | 'description')}
                className="px-3 py-2 border border-border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary/20"
              >
                <option value="url">URL</option>
                <option value="description">Description</option>
              </select>
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
            </div>
          </div>

          {/* Recipient */}
          <div>
            <label className="block text-sm font-medium mb-1.5 flex items-center gap-1.5">
              <User className="w-4 h-4" />
              Recipient
            </label>
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
