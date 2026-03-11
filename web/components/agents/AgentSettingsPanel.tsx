'use client';

/**
 * AgentSettingsPanel - ADR-066: Simplified Settings
 *
 * Configuration panel rendered inside the workspace drawer.
 * Refactored from AgentSettingsModal — modal wrapper removed,
 * same form state and save logic preserved.
 *
 * Sections:
 * 1. Destination (where does this go?) - REQUIRED
 * 2. Title (what is it called?)
 * 3. Schedule (when does it run?) — hidden for proactive/coordinator
 * 4. Data Sources (what informs it?)
 * 5. Recipient Context (collapsed/advanced)
 * 6. Archive (danger zone)
 */

import { useState, useEffect } from 'react';
import {
  Loader2,
  Link as LinkIcon,
  FileText,
  Plus,
  Trash2,
  Clock,
  AlertTriangle,
  Mail,
  Send,
  Slack,
  FileCode,
  Calendar,
  CheckCircle2,
  Globe,
} from 'lucide-react';
import { api } from '@/lib/api/client';
import { cn } from '@/lib/utils';
import type {
  Agent,
  AgentUpdate,
  DataSource,
  DataSourceType,
  IntegrationProvider,
  ScheduleConfig,
  ScheduleFrequency,
  Destination,
} from '@/types';

interface AgentSettingsPanelProps {
  agent: Agent;
  onSaved: (updated: Agent) => void;
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

export function AgentSettingsPanel({
  agent,
  onSaved,
  onArchived,
}: AgentSettingsPanelProps) {
  const [saving, setSaving] = useState(false);
  const [archiving, setArchiving] = useState(false);
  const [showArchiveConfirm, setShowArchiveConfirm] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // User email for email-first default
  const [userEmail, setUserEmail] = useState<string | null>(null);

  // Form state
  const [title, setTitle] = useState(agent.title);
  const [schedule, setSchedule] = useState<ScheduleConfig>(
    agent.schedule || { frequency: 'weekly', day: 'monday', time: '09:00' }
  );
  const [sources, setSources] = useState<DataSource[]>(agent.sources || []);
  // recipient_context moved to Instructions panel (ADR-087 Phase 3)
  const [destination, setDestination] = useState<Destination | undefined>(
    agent.destination
  );
  // New source input
  const [newSourceType, setNewSourceType] = useState<DataSourceType>('integration_import');
  const [newSourceValue, setNewSourceValue] = useState('');
  const [newSourceProvider, setNewSourceProvider] = useState<IntegrationProvider>('gmail');
  const [newSourceQuery, setNewSourceQuery] = useState('inbox');

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

  // Reset form when agent changes
  useEffect(() => {
    setTitle(agent.title);
    setSchedule(agent.schedule || { frequency: 'weekly', day: 'monday', time: '09:00' });
    setSources(agent.sources || []);
    const dest = agent.destination;
    if (!dest || !dest.target) {
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
  }, [agent, userEmail]);

  const handleSave = async () => {
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
      const update: AgentUpdate = {
        title,
        schedule,
        sources,
        destination: finalDestination,
      };

      await api.agents.update(agent.id, update);

      onSaved({
        ...agent,
        ...update,
      });
    } catch (err) {
      console.error('Failed to update agent:', err);
      setError('Failed to save changes. Please try again.');
    } finally {
      setSaving(false);
    }
  };

  const handleArchive = async () => {
    setArchiving(true);
    setError(null);

    try {
      await api.agents.delete(agent.id);
      onArchived?.();
    } catch (err) {
      console.error('Failed to archive agent:', err);
      setError('Failed to archive. Please try again.');
    } finally {
      setArchiving(false);
      setShowArchiveConfirm(false);
    }
  };

  const addSource = () => {
    if (newSourceType === 'integration_import') {
      const newSource: DataSource = {
        type: 'integration_import',
        value: `${newSourceProvider}:${newSourceQuery}`,
        label: `${newSourceProvider.charAt(0).toUpperCase() + newSourceProvider.slice(1)} - ${newSourceQuery}`,
        provider: newSourceProvider,
        source: newSourceQuery,
      };
      setSources([...sources, newSource]);
      setNewSourceQuery('inbox');
      return;
    }

    if (!newSourceValue.trim()) return;

    const newSource: DataSource = {
      type: newSourceType,
      value: newSourceValue.trim(),
      label: undefined,
    };

    setSources([...sources, newSource]);
    setNewSourceValue('');
  };

  const removeSource = (index: number) => {
    setSources(sources.filter((_, i) => i !== index));
  };

  const showSchedule = !['proactive', 'coordinator'].includes(agent.mode || 'recurring');
  const showDaySelector = schedule.frequency === 'weekly' || schedule.frequency === 'biweekly';

  return (
    <div className="flex flex-col h-full">
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-6">
        {/* Error */}
        {error && (
          <div className="p-3 bg-red-50 border border-red-200 rounded-md text-sm text-red-700 flex items-center gap-2">
            <AlertTriangle className="w-4 h-4" />
            {error}
          </div>
        )}

        {/* DESTINATION */}
        <div className="p-4 bg-primary/5 border border-primary/20 rounded-lg">
          <div className="flex items-center gap-2 mb-3">
            <Send className="w-4 h-4 text-primary" />
            <label className="text-sm font-medium">
              Destination
              <span className="text-red-500 ml-1">*</span>
            </label>
          </div>

          <div className="flex items-center gap-3 p-3 bg-background rounded-md border border-border">
            <div className="shrink-0 text-red-500">
              <Mail className="w-4 h-4" />
            </div>
            <div className="flex-1 min-w-0">
              <div className="text-sm font-medium">Email</div>
              <div className="text-xs text-muted-foreground truncate">
                → {destination?.target || userEmail || 'Loading...'}
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2 mt-3 text-xs text-muted-foreground">
            <CheckCircle2 className="w-3.5 h-3.5 text-green-500" />
            <span>Agents will be sent to your email</span>
          </div>
        </div>

        {/* TITLE */}
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

        {/* SCHEDULE */}
        {showSchedule && (
          <div>
            <label className="block text-sm font-medium mb-1.5 flex items-center gap-1.5">
              <Clock className="w-4 h-4" />
              Schedule
            </label>
            <div className="grid grid-cols-3 gap-3">
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

              <input
                type="time"
                value={schedule.time || '09:00'}
                onChange={(e) => setSchedule({ ...schedule, time: e.target.value })}
                className="px-3 py-2 border border-border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary/20"
              />
            </div>
          </div>
        )}

        {/* DATA SOURCES */}
        <div>
          <label className="block text-sm font-medium mb-1.5">Data Sources</label>
          <p className="text-xs text-muted-foreground mb-3">
            What context should inform this agent?
          </p>

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
                    source.provider === 'slack' ? (
                      <Slack className="w-4 h-4 text-purple-500 shrink-0" />
                    ) : source.provider === 'gmail' ? (
                      <Mail className="w-4 h-4 text-red-500 shrink-0" />
                    ) : source.provider === 'notion' ? (
                      <FileText className="w-4 h-4 text-amber-600 shrink-0" />
                    ) : source.provider === 'calendar' || (source.provider as string) === 'google' ? (
                      <Calendar className="w-4 h-4 text-blue-500 shrink-0" />
                    ) : source.provider === 'yarnnn' ? (
                      <Globe className="w-4 h-4 text-indigo-500 shrink-0" />
                    ) : (
                      <FileCode className="w-4 h-4 text-gray-500 shrink-0" />
                    )
                  ) : (
                    <FileText className="w-4 h-4 text-muted-foreground shrink-0" />
                  )}
                  <span className="flex-1 truncate">
                    {source.resource_name || source.label || source.value || source.resource_id || 'Unknown source'}
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

          {/* Add new source */}
          <div className="space-y-3">
            <div className="flex gap-2">
              <select
                value={newSourceType}
                onChange={(e) => setNewSourceType(e.target.value as DataSourceType)}
                className="px-3 py-2 border border-border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary/20"
              >
                <option value="integration_import">Integration</option>
                <option value="description">Description</option>
              </select>

              {newSourceType === 'description' && (
                <>
                  <input
                    type="text"
                    value={newSourceValue}
                    onChange={(e) => setNewSourceValue(e.target.value)}
                    placeholder="Describe the source..."
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
                  </>
                )}

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

        {/* Recipient Context moved to Instructions panel (ADR-087 Phase 3) */}

        {/* ARCHIVE */}
        <div className="pt-4 mt-4 border-t border-border">
          {!showArchiveConfirm ? (
            <button
              onClick={() => setShowArchiveConfirm(true)}
              className="text-sm text-red-600 hover:text-red-700 flex items-center gap-1.5"
            >
              <Trash2 className="w-4 h-4" />
              Archive this agent
            </button>
          ) : (
            <div className="p-3 bg-red-50 dark:bg-red-950/30 border border-red-200 dark:border-red-800 rounded-md">
              <p className="text-sm text-red-800 dark:text-red-200 mb-3">
                Are you sure? This will stop all scheduled runs. You can&apos;t undo this.
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

      {/* Save button at bottom */}
      <div className="px-4 py-3 border-t border-border bg-muted/30 shrink-0">
        <button
          onClick={handleSave}
          disabled={saving || !title.trim() || !destination}
          className="w-full px-4 py-2 text-sm bg-primary text-primary-foreground rounded-md hover:bg-primary/90 disabled:opacity-50 flex items-center justify-center gap-2"
        >
          {saving && <Loader2 className="w-4 h-4 animate-spin" />}
          Save Changes
        </button>
      </div>
    </div>
  );
}
