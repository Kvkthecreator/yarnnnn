'use client';

/**
 * ADR-023: Supervisor Desk Architecture
 * ADR-034: Context browser deprecated
 * ADR-059: User context entries
 *
 * ContextEditorSurface - Edit a single context entry
 *
 * Note: After save/delete, returns to idle (dashboard) since
 * context-browser is deprecated per ADR-034.
 */

import { useState, useEffect } from 'react';
import { Loader2, ArrowLeft, Save, Trash2 } from 'lucide-react';
import { api } from '@/lib/api/client';
import { useDesk } from '@/contexts/DeskContext';
import type { UserContextEntry } from '@/types';

interface ContextEditorSurfaceProps {
  memoryId: string;
}

export function ContextEditorSurface({ memoryId }: ContextEditorSurfaceProps) {
  const { clearSurface } = useDesk();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [entry, setEntry] = useState<UserContextEntry | null>(null);
  const [value, setValue] = useState('');

  useEffect(() => {
    loadEntry();
  }, [memoryId]);

  const loadEntry = async () => {
    setLoading(true);
    try {
      // Try to get from user context entries
      const userEntries = await api.userMemories.list();
      const found = userEntries.find((e) => e.id === memoryId);

      if (found) {
        setEntry(found);
        setValue(found.value);
      }
    } catch (err) {
      console.error('Failed to load entry:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    if (!entry) return;

    setSaving(true);
    try {
      // Note: The API may need to be updated to support updating context entries
      // For now, we'll just close the editor
      // await api.memories.update(memoryId, { content: value });
      clearSurface();
    } catch (err) {
      console.error('Failed to save entry:', err);
      alert('Failed to save. Please try again.');
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!entry) return;
    if (!confirm('Are you sure you want to delete this entry?')) return;

    setSaving(true);
    try {
      await api.memories.delete(memoryId);
      // ADR-034: Context browser deprecated - return to dashboard
      clearSurface();
    } catch (err) {
      console.error('Failed to delete entry:', err);
      alert('Failed to delete. Please try again.');
    } finally {
      setSaving(false);
    }
  };

  const goBack = () => {
    // ADR-034: Context browser deprecated - return to dashboard
    clearSurface();
  };

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center">
        <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (!entry) {
    return (
      <div className="h-full flex items-center justify-center text-muted-foreground">
        Entry not found
      </div>
    );
  }

  const hasChanges = value !== entry.value;

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="shrink-0 h-14 border-b border-border flex items-center justify-between px-4">
        <div className="flex items-center gap-3">
          <button onClick={goBack} className="p-1.5 hover:bg-muted rounded">
            <ArrowLeft className="w-4 h-4" />
          </button>
          <h1 className="font-medium">Edit Context Entry</h1>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={handleDelete}
            disabled={saving}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs text-red-600 border border-red-200 dark:border-red-800 rounded-md hover:bg-red-50 dark:hover:bg-red-900/20 disabled:opacity-50"
          >
            <Trash2 className="w-3.5 h-3.5" />
            Delete
          </button>
          <button
            onClick={handleSave}
            disabled={saving || !hasChanges}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs bg-primary text-primary-foreground rounded-md hover:bg-primary/90 disabled:opacity-50"
          >
            {saving ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Save className="w-3.5 h-3.5" />}
            Save
          </button>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-auto">
        <div className="max-w-4xl mx-auto px-6 py-6">
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-2">Key</label>
              <input
                type="text"
                value={entry.key}
                disabled
                className="w-full px-3 py-2 border border-border rounded-md bg-muted text-sm text-muted-foreground"
              />
            </div>

            <div>
              <label className="block text-sm font-medium mb-2">Value</label>
              <textarea
                value={value}
                onChange={(e) => setValue(e.target.value)}
                rows={6}
                className="w-full px-3 py-2 border border-border rounded-md bg-background text-sm resize-y focus:outline-none focus:ring-2 focus:ring-primary/20"
              />
            </div>

            <div className="flex gap-4 text-xs text-muted-foreground">
              <div>
                <span className="font-medium">Source:</span> {entry.source}
              </div>
              <div>
                <span className="font-medium">Confidence:</span> {Math.round(entry.confidence * 100)}%
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
