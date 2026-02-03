'use client';

/**
 * ADR-023: Supervisor Desk Architecture
 * ProjectDetailSurface - View project details (legacy, lower priority)
 */

import { useState, useEffect } from 'react';
import { Loader2, ArrowLeft, Settings, Folder } from 'lucide-react';
import { api } from '@/lib/api/client';
import { useDesk } from '@/contexts/DeskContext';
import { format } from 'date-fns';
import type { Project, ProjectWithCounts } from '@/types';

interface ProjectDetailSurfaceProps {
  projectId: string;
}

export function ProjectDetailSurface({ projectId }: ProjectDetailSurfaceProps) {
  const { setSurface } = useDesk();
  const [loading, setLoading] = useState(true);
  const [project, setProject] = useState<ProjectWithCounts | null>(null);

  useEffect(() => {
    loadProject();
  }, [projectId]);

  const loadProject = async () => {
    setLoading(true);
    try {
      const data = await api.projects.get(projectId);
      setProject(data);
    } catch (err) {
      console.error('Failed to load project:', err);
    } finally {
      setLoading(false);
    }
  };

  const goBack = () => {
    setSurface({ type: 'project-list' });
  };

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center">
        <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (!project) {
    return (
      <div className="h-full flex items-center justify-center text-muted-foreground">
        Project not found
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="shrink-0 h-14 border-b border-border flex items-center justify-between px-4">
        <div className="flex items-center gap-3">
          <button onClick={goBack} className="p-1.5 hover:bg-muted rounded">
            <ArrowLeft className="w-4 h-4" />
          </button>
          <div>
            <h1 className="font-medium">{project.name}</h1>
            <p className="text-xs text-muted-foreground">
              Created {format(new Date(project.created_at), 'MMMM d, yyyy')}
            </p>
          </div>
        </div>

        <button className="p-1.5 border border-border rounded-md hover:bg-muted">
          <Settings className="w-3.5 h-3.5" />
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-auto">
        <div className="max-w-4xl mx-auto px-6 py-6">
          <div className="p-8 border border-border rounded-lg bg-muted/30 text-center">
            <Folder className="w-12 h-12 mx-auto mb-4 text-muted-foreground" />
            <h2 className="text-lg font-medium mb-2">{project.name}</h2>
            {project.description && (
              <p className="text-sm text-muted-foreground mb-4">{project.description}</p>
            )}

            <div className="inline-flex items-center gap-6 text-sm text-muted-foreground">
              <span>{project.memory_count || 0} memories</span>
              <span>{project.ticket_count || 0} work items</span>
            </div>
          </div>

          <div className="mt-6 space-y-3">
            <button
              onClick={() =>
                setSurface({ type: 'context-browser', scope: 'project', scopeId: projectId })
              }
              className="w-full p-4 border border-border rounded-lg hover:bg-muted text-left"
            >
              <span className="text-sm font-medium">View Project Context</span>
              <p className="text-xs text-muted-foreground">
                {project.memory_count || 0} memories stored
              </p>
            </button>

            <button
              onClick={() => setSurface({ type: 'document-list', projectId })}
              className="w-full p-4 border border-border rounded-lg hover:bg-muted text-left"
            >
              <span className="text-sm font-medium">View Documents</span>
              <p className="text-xs text-muted-foreground">Documents uploaded to this project</p>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
