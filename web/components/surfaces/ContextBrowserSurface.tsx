'use client';

/**
 * ADR-023: Supervisor Desk Architecture
 * ADR-024: Context Classification Layer
 *
 * ContextBrowserSurface - Browse memories/context across all projects
 *
 * Tab-based layout:
 * - "Personal" tab: User-scoped memories (project_id = null)
 * - Project tabs: Browse any project's scoped memories
 *
 * Features:
 * - Project selector dropdown to browse any project's context
 * - Search filtering across content and tags
 * - Tags displayed inline on each memory card
 */

import { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import {
  Loader2,
  Plus,
  Edit,
  Trash2,
  User,
  Folder,
  Search,
  X,
  ChevronDown,
  Check,
} from 'lucide-react';
import { api } from '@/lib/api/client';
import { useDesk } from '@/contexts/DeskContext';
import { useTP } from '@/contexts/TPContext';
import { formatDistanceToNow } from 'date-fns';
import { cn } from '@/lib/utils';
import type { Memory, Project } from '@/types';

interface ContextBrowserSurfaceProps {
  scope: 'user' | 'deliverable' | 'project';
  scopeId?: string;
}

// Memory card component for consistent rendering
function MemoryCard({
  memory,
  onEdit,
  onDelete,
  isDeleting,
}: {
  memory: Memory;
  onEdit: () => void;
  onDelete: () => void;
  isDeleting: boolean;
}) {
  return (
    <div className="group p-3 border border-border rounded-lg bg-background hover:border-border/80 transition-colors">
      {/* Content */}
      <p className="text-sm leading-relaxed whitespace-pre-wrap">{memory.content}</p>

      {/* Footer: tags + meta + actions */}
      <div className="mt-2 flex items-center justify-between gap-2">
        <div className="flex items-center gap-2 min-w-0 flex-1">
          {/* Tags (all of them) */}
          {memory.tags && memory.tags.length > 0 && (
            <div className="flex items-center gap-1 flex-wrap">
              {memory.tags.map((tag, i) => (
                <span
                  key={i}
                  className="px-1.5 py-0.5 text-[10px] rounded bg-muted text-muted-foreground"
                >
                  {tag}
                </span>
              ))}
            </div>
          )}

          {/* Timestamp */}
          <span className="text-[10px] text-muted-foreground/60 shrink-0">
            {formatDistanceToNow(new Date(memory.created_at), { addSuffix: true })}
          </span>
        </div>

        {/* Actions - visible on hover */}
        <div className="flex items-center gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity">
          <button
            onClick={onEdit}
            className="p-1 hover:bg-muted rounded"
            title="Edit"
          >
            <Edit className="w-3 h-3 text-muted-foreground" />
          </button>
          <button
            onClick={onDelete}
            disabled={isDeleting}
            className="p-1 hover:bg-muted rounded"
            title="Delete"
          >
            {isDeleting ? (
              <Loader2 className="w-3 h-3 animate-spin" />
            ) : (
              <Trash2 className="w-3 h-3 text-muted-foreground hover:text-red-500" />
            )}
          </button>
        </div>
      </div>
    </div>
  );
}

// Memory list component
function MemoryList({
  memories,
  emptyMessage,
  onEdit,
  onDelete,
  deletingId,
}: {
  memories: Memory[];
  emptyMessage: string;
  onEdit: (memoryId: string) => void;
  onDelete: (memoryId: string) => void;
  deletingId: string | null;
}) {
  if (memories.length === 0) {
    return (
      <p className="text-sm text-muted-foreground text-center py-8">
        {emptyMessage}
      </p>
    );
  }

  return (
    <div className="space-y-2">
      {memories.map((memory) => (
        <MemoryCard
          key={memory.id}
          memory={memory}
          onEdit={() => onEdit(memory.id)}
          onDelete={() => onDelete(memory.id)}
          isDeleting={deletingId === memory.id}
        />
      ))}
    </div>
  );
}

// Project selector dropdown component
function ProjectSelector({
  projects,
  selectedProjectId,
  onSelect,
  isLoading,
}: {
  projects: Project[];
  selectedProjectId: string | null;
  onSelect: (projectId: string | null) => void;
  isLoading: boolean;
}) {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Close on outside click
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const selectedProject = projects.find((p) => p.id === selectedProjectId);
  const buttonLabel = selectedProject?.name || 'Select project...';

  return (
    <div ref={dropdownRef} className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        disabled={isLoading}
        className={cn(
          'inline-flex items-center gap-1.5 px-3 py-2 text-sm font-medium border-b-2 -mb-px transition-colors',
          selectedProjectId
            ? 'border-primary text-foreground'
            : 'border-transparent text-muted-foreground hover:text-foreground'
        )}
      >
        <Folder className="w-3.5 h-3.5" />
        <span className="max-w-[120px] truncate">{buttonLabel}</span>
        <ChevronDown className={cn('w-3.5 h-3.5 transition-transform', isOpen && 'rotate-180')} />
      </button>

      {isOpen && (
        <div className="absolute top-full left-0 mt-1 w-56 bg-background border border-border rounded-md shadow-lg z-50 py-1 max-h-64 overflow-auto">
          {isLoading ? (
            <div className="px-3 py-2 text-sm text-muted-foreground">
              <Loader2 className="w-4 h-4 animate-spin inline mr-2" />
              Loading...
            </div>
          ) : projects.length === 0 ? (
            <div className="px-3 py-2 text-sm text-muted-foreground">
              No projects yet
            </div>
          ) : (
            projects.map((project) => (
              <button
                key={project.id}
                onClick={() => {
                  onSelect(project.id);
                  setIsOpen(false);
                }}
                className={cn(
                  'w-full px-3 py-2 text-sm text-left hover:bg-muted flex items-center justify-between gap-2',
                  selectedProjectId === project.id && 'bg-muted/50'
                )}
              >
                <span className="truncate">{project.name}</span>
                {selectedProjectId === project.id && (
                  <Check className="w-3.5 h-3.5 text-primary shrink-0" />
                )}
              </button>
            ))
          )}
        </div>
      )}
    </div>
  );
}

export function ContextBrowserSurface({ scope, scopeId }: ContextBrowserSurfaceProps) {
  const { setSurface } = useDesk();
  const { sendMessage } = useTP();
  const [loading, setLoading] = useState(true);
  const [userMemories, setUserMemories] = useState<Memory[]>([]);
  const [scopedMemories, setScopedMemories] = useState<Memory[]>([]);
  const [deleting, setDeleting] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'personal' | 'scoped'>('personal');
  const [searchQuery, setSearchQuery] = useState('');

  // ADR-024: Project selector state
  const [projects, setProjects] = useState<Project[]>([]);
  const [loadingProjects, setLoadingProjects] = useState(false);
  const [selectedProjectId, setSelectedProjectId] = useState<string | null>(
    scope === 'project' ? (scopeId ?? null) : null
  );
  const [selectedProjectName, setSelectedProjectName] = useState<string>('Project');

  const loadedRef = useRef<string | null>(null);

  // Load user's projects for the selector
  useEffect(() => {
    async function loadProjects() {
      setLoadingProjects(true);
      try {
        const projectList = await api.projects.list();
        setProjects(projectList);

        // If we have an initial scopeId, find its name
        if (scopeId && scope === 'project') {
          const found = projectList.find((p) => p.id === scopeId);
          if (found) {
            setSelectedProjectName(found.name);
          }
        }
      } catch (err) {
        console.error('Failed to load projects:', err);
      } finally {
        setLoadingProjects(false);
      }
    }
    loadProjects();
  }, [scope, scopeId]);

  // Load memories based on scope
  const loadMemories = useCallback(async () => {
    const loadKey = `${scope}:${selectedProjectId || scopeId || 'none'}`;

    // Skip if we've already loaded this exact combination
    if (loadedRef.current === loadKey && (userMemories.length > 0 || scopedMemories.length > 0)) {
      return;
    }

    setLoading(true);
    try {
      // Always load user memories for personal context
      const userData = await api.userMemories.list();
      setUserMemories(userData);

      // Load scoped memories based on selected project
      if (selectedProjectId) {
        const projectData = await api.projectMemories.list(selectedProjectId);
        setScopedMemories(projectData);

        // Update project name
        const found = projects.find((p) => p.id === selectedProjectId);
        if (found) {
          setSelectedProjectName(found.name);
        }
      } else if (scope === 'deliverable' && scopeId) {
        // Deliverable scope: get deliverable's project
        const detail = await api.deliverables.get(scopeId);
        if (detail.deliverable?.project_id) {
          const projectData = await api.projectMemories.list(detail.deliverable.project_id);
          setScopedMemories(projectData);
          setSelectedProjectId(detail.deliverable.project_id);
          setSelectedProjectName(detail.deliverable.title || 'Deliverable');
        } else {
          setScopedMemories([]);
        }
      } else {
        setScopedMemories([]);
      }

      loadedRef.current = loadKey;
    } catch (err) {
      console.error('Failed to load memories:', err);
    } finally {
      setLoading(false);
    }
  }, [scope, scopeId, selectedProjectId, projects, userMemories.length, scopedMemories.length]);

  useEffect(() => {
    loadMemories();
  }, [loadMemories]);

  // Handle project selection change
  const handleProjectSelect = useCallback((projectId: string | null) => {
    setSelectedProjectId(projectId);
    loadedRef.current = null; // Force reload
    if (projectId) {
      setActiveTab('scoped');
    }
  }, []);

  // Filter memories by search query
  const filterMemories = useCallback(
    (memories: Memory[]) => {
      if (!searchQuery.trim()) return memories;
      const query = searchQuery.toLowerCase();
      return memories.filter(
        (m) =>
          m.content.toLowerCase().includes(query) ||
          m.tags?.some((t) => t.toLowerCase().includes(query))
      );
    },
    [searchQuery]
  );

  const filteredUserMemories = useMemo(
    () => filterMemories(userMemories),
    [filterMemories, userMemories]
  );
  const filteredScopedMemories = useMemo(
    () => filterMemories(scopedMemories),
    [filterMemories, scopedMemories]
  );

  const handleEdit = (memoryId: string) => {
    setSurface({ type: 'context-editor', memoryId });
  };

  const handleDelete = async (memoryId: string) => {
    if (!confirm('Are you sure you want to delete this memory?')) return;

    setDeleting(memoryId);
    try {
      await api.memories.delete(memoryId);
      // Remove from appropriate list
      setUserMemories((prev) => prev.filter((m) => m.id !== memoryId));
      setScopedMemories((prev) => prev.filter((m) => m.id !== memoryId));
    } catch (err) {
      console.error('Failed to delete memory:', err);
      alert('Failed to delete memory');
    } finally {
      setDeleting(null);
    }
  };

  const totalCount = userMemories.length + scopedMemories.length;
  const activeMemories = activeTab === 'personal' ? filteredUserMemories : filteredScopedMemories;

  // Determine if we show project tab (when a project is selected or we have scope context)
  const showProjectTab = selectedProjectId !== null || (scope !== 'user' && scopeId);

  return (
    <div className="h-full overflow-auto">
      <div className="max-w-3xl mx-auto px-6 py-6">
        {/* Header with search */}
        <div className="flex items-center justify-between gap-4 mb-4">
          <h1 className="text-lg font-medium shrink-0">Context</h1>
          <div className="flex items-center gap-2 flex-1 max-w-sm">
            {/* Search input */}
            <div className="relative flex-1">
              <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-muted-foreground" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search..."
                className="w-full pl-8 pr-8 py-1.5 text-sm border border-border rounded-md bg-background focus:outline-none focus:ring-1 focus:ring-primary/30"
              />
              {searchQuery && (
                <button
                  onClick={() => setSearchQuery('')}
                  className="absolute right-2 top-1/2 -translate-y-1/2 p-0.5 hover:bg-muted rounded"
                >
                  <X className="w-3 h-3 text-muted-foreground" />
                </button>
              )}
            </div>
            <button
              onClick={() => sendMessage("I'd like to add something to my memory")}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs border border-border rounded-md hover:bg-muted shrink-0"
            >
              <Plus className="w-3.5 h-3.5" />
              Add
            </button>
          </div>
        </div>

        {/* Tabs with project selector */}
        <div className="flex gap-1 mb-4 border-b border-border">
          {/* Personal tab */}
          <button
            onClick={() => setActiveTab('personal')}
            className={cn(
              'px-3 py-2 text-sm font-medium border-b-2 -mb-px transition-colors',
              activeTab === 'personal'
                ? 'border-primary text-foreground'
                : 'border-transparent text-muted-foreground hover:text-foreground'
            )}
          >
            <User className="w-3.5 h-3.5 inline mr-1.5" />
            Personal
            <span className="ml-1.5 text-xs text-muted-foreground">
              {filteredUserMemories.length}
            </span>
          </button>

          {/* Project selector dropdown (ADR-024) */}
          <ProjectSelector
            projects={projects}
            selectedProjectId={selectedProjectId}
            onSelect={handleProjectSelect}
            isLoading={loadingProjects}
          />

          {/* Show memory count when project is selected */}
          {showProjectTab && activeTab === 'scoped' && (
            <span className="self-center text-xs text-muted-foreground ml-0.5">
              {filteredScopedMemories.length}
            </span>
          )}
        </div>

        {/* Content */}
        {loading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
          </div>
        ) : activeTab === 'scoped' && !selectedProjectId ? (
          <div className="text-center py-12 border border-dashed border-border rounded-lg">
            <Folder className="w-8 h-8 mx-auto text-muted-foreground/50 mb-2" />
            <p className="text-muted-foreground mb-1">Select a project</p>
            <p className="text-sm text-muted-foreground/70">
              Choose a project from the dropdown to browse its context
            </p>
          </div>
        ) : activeMemories.length === 0 && totalCount === 0 ? (
          <div className="text-center py-12 border border-dashed border-border rounded-lg">
            <p className="text-muted-foreground mb-2">No memories yet</p>
            <p className="text-sm text-muted-foreground max-w-md mx-auto">
              Tell TP things you want it to remember — your preferences, company info,
              writing style, or any context that helps it understand you better.
            </p>
          </div>
        ) : (
          <MemoryList
            memories={activeMemories}
            emptyMessage={
              searchQuery
                ? 'No memories match your search'
                : activeTab === 'personal'
                  ? 'No personal context yet. Share things TP should always know about you.'
                  : `No context in ${selectedProjectName} yet.`
            }
            onEdit={handleEdit}
            onDelete={handleDelete}
            deletingId={deleting}
          />
        )}

        {/* Footer */}
        {!loading && totalCount > 0 && (
          <p className="mt-6 text-xs text-muted-foreground text-center">
            {totalCount} total memories • TP uses your context to personalize responses
          </p>
        )}
      </div>
    </div>
  );
}
