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
  Trash2,
  AlertTriangle,
} from 'lucide-react';
import { api } from '@/lib/api/client';
import type {
  Agent,
  AgentUpdate,
} from '@/types';

interface AgentSettingsPanelProps {
  agent: Agent;
  onSaved: (updated: Agent) => void;
  onArchived?: () => void;
}

export function AgentSettingsPanel({
  agent,
  onSaved,
  onArchived,
}: AgentSettingsPanelProps) {
  const [saving, setSaving] = useState(false);
  const [archiving, setArchiving] = useState(false);
  const [showArchiveConfirm, setShowArchiveConfirm] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Form state
  const [title, setTitle] = useState(agent.title);

  // Reset form when agent changes
  useEffect(() => {
    setTitle(agent.title);
    setError(null);
  }, [agent]);

  const handleSave = async () => {
    setSaving(true);
    setError(null);

    try {
      const update: AgentUpdate = {
        title,
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
          disabled={saving || !title.trim()}
          className="w-full px-4 py-2 text-sm bg-primary text-primary-foreground rounded-md hover:bg-primary/90 disabled:opacity-50 flex items-center justify-center gap-2"
        >
          {saving && <Loader2 className="w-4 h-4 animate-spin" />}
          Save Changes
        </button>
      </div>
    </div>
  );
}
