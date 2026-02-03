'use client';

/**
 * ADR-023: Supervisor Desk Architecture
 * ContextEditorSurface - Edit a single memory
 */

import { useState, useEffect } from 'react';
import { Loader2, ArrowLeft, Save, Trash2 } from 'lucide-react';
import { api } from '@/lib/api/client';
import { useDesk } from '@/contexts/DeskContext';
import type { Memory } from '@/types';

interface ContextEditorSurfaceProps {
  memoryId: string;
}

export function ContextEditorSurface({ memoryId }: ContextEditorSurfaceProps) {
  const { setSurface } = useDesk();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [memory, setMemory] = useState<Memory | null>(null);
  const [content, setContent] = useState('');
  const [tags, setTags] = useState<string[]>([]);

  useEffect(() => {
    loadMemory();
  }, [memoryId]);

  const loadMemory = async () => {
    setLoading(true);
    try {
      // Try to get from user memories
      const userMemories = await api.userMemories.list();
      const found = userMemories.find((m) => m.id === memoryId);

      if (found) {
        setMemory(found);
        setContent(found.content);
        setTags(found.tags || []);
      }
    } catch (err) {
      console.error('Failed to load memory:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    if (!memory) return;

    setSaving(true);
    try {
      await api.memories.update(memoryId, {
        content,
        tags,
      });
      // Go back to browser
      setSurface({ type: 'context-browser', scope: 'user' });
    } catch (err) {
      console.error('Failed to save memory:', err);
      alert('Failed to save. Please try again.');
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!memory) return;
    if (!confirm('Are you sure you want to delete this memory?')) return;

    setSaving(true);
    try {
      await api.memories.delete(memoryId);
      setSurface({ type: 'context-browser', scope: 'user' });
    } catch (err) {
      console.error('Failed to delete memory:', err);
      alert('Failed to delete. Please try again.');
    } finally {
      setSaving(false);
    }
  };

  const goBack = () => {
    setSurface({ type: 'context-browser', scope: 'user' });
  };

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center">
        <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (!memory) {
    return (
      <div className="h-full flex items-center justify-center text-muted-foreground">
        Memory not found
      </div>
    );
  }

  const hasChanges = content !== memory.content;

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="shrink-0 h-14 border-b border-border flex items-center justify-between px-4">
        <div className="flex items-center gap-3">
          <button onClick={goBack} className="p-1.5 hover:bg-muted rounded">
            <ArrowLeft className="w-4 h-4" />
          </button>
          <h1 className="font-medium">Edit Memory</h1>
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
              <label className="block text-sm font-medium mb-2">Content</label>
              <textarea
                value={content}
                onChange={(e) => setContent(e.target.value)}
                rows={6}
                className="w-full px-3 py-2 border border-border rounded-md bg-background text-sm resize-y focus:outline-none focus:ring-2 focus:ring-primary/20"
              />
            </div>

            <div>
              <label className="block text-sm font-medium mb-2">Tags</label>
              <div className="flex flex-wrap gap-2">
                {tags.map((tag, i) => (
                  <span
                    key={i}
                    className="inline-flex items-center gap-1 px-2 py-1 text-xs bg-muted rounded-full"
                  >
                    {tag}
                    <button
                      onClick={() => setTags((prev) => prev.filter((_, idx) => idx !== i))}
                      className="hover:text-red-600"
                    >
                      &times;
                    </button>
                  </span>
                ))}
                <input
                  type="text"
                  placeholder="Add tag..."
                  className="px-2 py-1 text-xs border border-border rounded-full bg-background focus:outline-none focus:ring-2 focus:ring-primary/20 w-24"
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && e.currentTarget.value.trim()) {
                      setTags((prev) => [...prev, e.currentTarget.value.trim()]);
                      e.currentTarget.value = '';
                    }
                  }}
                />
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
