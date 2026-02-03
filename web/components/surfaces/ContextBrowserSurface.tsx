'use client';

/**
 * ADR-023: Supervisor Desk Architecture
 * ContextBrowserSurface - Browse memories/context
 */

import { useState, useEffect, useRef, useCallback } from 'react';
import { Loader2, Plus, Edit, Trash2, Tag } from 'lucide-react';
import { api } from '@/lib/api/client';
import { useDesk } from '@/contexts/DeskContext';
import { formatDistanceToNow } from 'date-fns';
import type { Memory } from '@/types';

interface ContextBrowserSurfaceProps {
  scope: 'user' | 'deliverable' | 'project';
  scopeId?: string;
}

export function ContextBrowserSurface({ scope, scopeId }: ContextBrowserSurfaceProps) {
  const { setSurface } = useDesk();
  const [loading, setLoading] = useState(true);
  const [memories, setMemories] = useState<Memory[]>([]);
  const [deleting, setDeleting] = useState<string | null>(null);
  const loadedRef = useRef<string | null>(null);

  // Memoize load function to track what we've already loaded
  const loadMemories = useCallback(async () => {
    const loadKey = `${scope}:${scopeId || 'none'}`;

    // Skip if we've already loaded this exact scope/scopeId combination
    if (loadedRef.current === loadKey && memories.length > 0) {
      return;
    }

    setLoading(true);
    try {
      // For user scope, use userMemories; for project scope, use projectMemories
      if (scope === 'user') {
        const data = await api.userMemories.list();
        setMemories(data);
      } else if (scope === 'project' && scopeId) {
        const data = await api.projectMemories.list(scopeId);
        setMemories(data);
      } else {
        // TODO: Handle deliverable scope when API supports it
        setMemories([]);
      }
      loadedRef.current = loadKey;
    } catch (err) {
      console.error('Failed to load memories:', err);
    } finally {
      setLoading(false);
    }
  }, [scope, scopeId, memories.length]);

  useEffect(() => {
    loadMemories();
  }, [loadMemories]);

  const handleDelete = async (memoryId: string) => {
    if (!confirm('Are you sure you want to delete this memory?')) return;

    setDeleting(memoryId);
    try {
      // Memory delete works for both user and project memories
      await api.memories.delete(memoryId);
      setMemories((prev) => prev.filter((m) => m.id !== memoryId));
    } catch (err) {
      console.error('Failed to delete memory:', err);
      alert('Failed to delete memory');
    } finally {
      setDeleting(null);
    }
  };

  // Group memories by tag
  const groupedMemories: Record<string, Memory[]> = {};
  memories.forEach((m) => {
    const tag = m.tags?.[0] || 'General';
    if (!groupedMemories[tag]) groupedMemories[tag] = [];
    groupedMemories[tag].push(m);
  });

  return (
    <div className="h-full overflow-auto">
      <div className="max-w-4xl mx-auto px-6 py-6">
        {/* Inline header with count and add button */}
        <div className="flex items-center justify-between mb-6">
          <p className="text-sm text-muted-foreground">
            {loading ? 'Loading...' : `${memories.length} memor${memories.length === 1 ? 'y' : 'ies'}`}
          </p>
          <button className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs border border-border rounded-md hover:bg-muted">
            <Plus className="w-3.5 h-3.5" />
            Add
          </button>
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
          </div>
        ) : memories.length === 0 ? (
          <div className="text-center py-12">
            <p className="text-muted-foreground mb-4">No memories yet</p>
            <p className="text-sm text-muted-foreground">
              Tell TP things you want it to remember, like your preferences, company info, or
              important context.
            </p>
          </div>
        ) : (
          <div className="space-y-6">
            {Object.entries(groupedMemories).map(([tag, tagMemories]) => (
              <div key={tag}>
                <h2 className="text-sm font-medium mb-3 flex items-center gap-2">
                  <Tag className="w-3.5 h-3.5" />
                  {tag.charAt(0).toUpperCase() + tag.slice(1)}
                </h2>

                <div className="space-y-2">
                  {tagMemories.map((memory) => (
                    <div
                      key={memory.id}
                      className="p-4 border border-border rounded-lg bg-muted/30"
                    >
                      <p className="text-sm whitespace-pre-wrap">{memory.content}</p>

                      <div className="mt-3 flex items-center justify-between">
                        <span className="text-xs text-muted-foreground">
                          {formatDistanceToNow(new Date(memory.created_at), { addSuffix: true })}
                        </span>

                        <div className="flex items-center gap-1">
                          <button
                            onClick={() =>
                              setSurface({ type: 'context-editor', memoryId: memory.id })
                            }
                            className="p-1.5 hover:bg-background rounded"
                          >
                            <Edit className="w-3.5 h-3.5 text-muted-foreground" />
                          </button>
                          <button
                            onClick={() => handleDelete(memory.id)}
                            disabled={deleting === memory.id}
                            className="p-1.5 hover:bg-background rounded"
                          >
                            {deleting === memory.id ? (
                              <Loader2 className="w-3.5 h-3.5 animate-spin" />
                            ) : (
                              <Trash2 className="w-3.5 h-3.5 text-muted-foreground hover:text-red-600" />
                            )}
                          </button>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
