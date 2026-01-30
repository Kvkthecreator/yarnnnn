'use client';

/**
 * ADR-013: Conversation + Surfaces
 * Context Surface - displays memories, documents, project state
 */

import { useEffect, useState } from 'react';
import {
  Loader2,
  FileText,
  MessageCircle,
  Upload,
  Tag,
  Star,
  Trash2,
  Brain,
} from 'lucide-react';
import { api } from '@/lib/api/client';
import { useProjectContext } from '@/contexts/ProjectContext';
import type { SurfaceData } from '@/types/surfaces';
import type { Memory } from '@/types';

interface ContextSurfaceProps {
  data: SurfaceData | null;
}

const SOURCE_TYPE_LABELS: Record<string, { label: string; icon: React.ReactNode }> = {
  manual: { label: 'manual', icon: <FileText className="w-3 h-3" /> },
  chat: { label: 'from chat', icon: <MessageCircle className="w-3 h-3" /> },
  bulk: { label: 'imported', icon: <Upload className="w-3 h-3" /> },
  document: { label: 'from doc', icon: <FileText className="w-3 h-3" /> },
  import: { label: 'imported', icon: <Upload className="w-3 h-3" /> },
};

export function ContextSurface({ data }: ContextSurfaceProps) {
  const { activeProject } = useProjectContext();
  const [userMemories, setUserMemories] = useState<Memory[]>([]);
  const [projectMemories, setProjectMemories] = useState<Memory[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'project' | 'user'>('project');

  const projectId = data?.projectId || activeProject?.id;

  useEffect(() => {
    loadMemories();
  }, [projectId]);

  const loadMemories = async () => {
    setLoading(true);
    try {
      // Load user memories
      const userMems = await api.userMemories.list();
      setUserMemories(userMems);

      // Load project memories if we have a project
      if (projectId) {
        const projMems = await api.projectMemories.list(projectId);
        setProjectMemories(projMems);
      }
    } catch (err) {
      console.error('Failed to load memories:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (memoryId: string, isProjectMemory: boolean) => {
    try {
      await api.memories.delete(memoryId);
      if (isProjectMemory) {
        setProjectMemories((prev) => prev.filter((m) => m.id !== memoryId));
      } else {
        setUserMemories((prev) => prev.filter((m) => m.id !== memoryId));
      }
    } catch (err) {
      console.error('Failed to delete memory:', err);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  const memories = activeTab === 'project' ? projectMemories : userMemories;
  const showProjectTab = projectId && projectMemories.length > 0;

  return (
    <div className="p-4">
      {/* Tab selector */}
      <div className="flex gap-1 mb-4 border-b border-border">
        {showProjectTab && (
          <button
            onClick={() => setActiveTab('project')}
            className={`px-3 py-2 text-sm font-medium border-b-2 transition-colors ${
              activeTab === 'project'
                ? 'border-primary text-primary'
                : 'border-transparent text-muted-foreground hover:text-foreground'
            }`}
          >
            Project ({projectMemories.length})
          </button>
        )}
        <button
          onClick={() => setActiveTab('user')}
          className={`px-3 py-2 text-sm font-medium border-b-2 transition-colors ${
            activeTab === 'user'
              ? 'border-primary text-primary'
              : 'border-transparent text-muted-foreground hover:text-foreground'
          }`}
        >
          About You ({userMemories.length})
        </button>
      </div>

      {/* Memories list */}
      {memories.length === 0 ? (
        <div className="text-center py-8 text-muted-foreground">
          <Brain className="w-12 h-12 mx-auto mb-3 opacity-50" />
          <p className="text-sm">No context here yet.</p>
          <p className="text-xs mt-1">
            Context is extracted from your conversations.
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {memories.map((memory) => {
            const sourceConfig = memory.source_type
              ? SOURCE_TYPE_LABELS[memory.source_type]
              : SOURCE_TYPE_LABELS.manual;

            return (
              <div
                key={memory.id}
                className="p-3 border border-border rounded-lg hover:border-muted-foreground/30 transition-colors group"
              >
                <div className="flex justify-between items-start gap-2">
                  <div className="flex-1 min-w-0">
                    {/* Tags and metadata */}
                    <div className="flex items-center gap-2 mb-2 flex-wrap">
                      {memory.tags.slice(0, 3).map((tag) => (
                        <span
                          key={tag}
                          className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium text-primary bg-primary/10"
                        >
                          <Tag className="w-3 h-3" />
                          {tag}
                        </span>
                      ))}
                      {memory.tags.length > 3 && (
                        <span className="text-xs text-muted-foreground">
                          +{memory.tags.length - 3} more
                        </span>
                      )}
                      {memory.importance >= 0.8 && (
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium text-yellow-600 bg-yellow-50">
                          <Star className="w-3 h-3" />
                          Important
                        </span>
                      )}
                    </div>
                    {/* Content */}
                    <p className="text-sm">{memory.content}</p>
                    {/* Source */}
                    <div className="flex items-center gap-1 mt-2 text-xs text-muted-foreground">
                      {sourceConfig.icon}
                      <span>{sourceConfig.label}</span>
                    </div>
                  </div>
                  {/* Delete button */}
                  <button
                    onClick={() => handleDelete(memory.id, activeTab === 'project')}
                    className="p-1 text-muted-foreground hover:text-destructive opacity-0 group-hover:opacity-100 transition-opacity shrink-0"
                    title="Delete memory"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
