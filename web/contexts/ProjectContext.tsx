'use client';

/**
 * ADR-013: Conversation + Surfaces
 * Context provider for managing active project state
 * Projects are conversational context, not routes
 */

import { createContext, useContext, useState, useEffect, useCallback, ReactNode } from 'react';
import { api } from '@/lib/api/client';
import type { Project } from '@/types';

// Minimal project reference for context switching
// We only need id and name for most UI operations
export interface ProjectRef {
  id: string;
  name: string;
}

interface ProjectContextValue {
  projects: Project[];
  activeProject: ProjectRef | null;
  isLoading: boolean;
  setActiveProject: (project: ProjectRef | null) => void;
  refreshProjects: () => Promise<void>;
}

const ProjectContext = createContext<ProjectContextValue | null>(null);

export function ProjectProvider({ children }: { children: ReactNode }) {
  const [projects, setProjects] = useState<Project[]>([]);
  const [activeProject, setActiveProject] = useState<ProjectRef | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const loadProjects = useCallback(async () => {
    try {
      const result = await api.projects.list();
      setProjects(result);
    } catch (error) {
      console.error('Failed to load projects:', error);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadProjects();
  }, [loadProjects]);

  // Listen for project refresh events (from TP creating projects)
  useEffect(() => {
    const handleRefresh = () => {
      loadProjects();
    };

    window.addEventListener('refreshProjects', handleRefresh);
    return () => window.removeEventListener('refreshProjects', handleRefresh);
  }, [loadProjects]);

  const handleSetActiveProject = useCallback((project: ProjectRef | null) => {
    setActiveProject(project);
    // Update URL query param for deep linking
    if (typeof window !== 'undefined') {
      const url = new URL(window.location.href);
      if (project) {
        url.searchParams.set('project', project.id);
      } else {
        url.searchParams.delete('project');
      }
      window.history.replaceState({}, '', url.toString());
    }
  }, []);

  return (
    <ProjectContext.Provider
      value={{
        projects,
        activeProject,
        isLoading,
        setActiveProject: handleSetActiveProject,
        refreshProjects: loadProjects,
      }}
    >
      {children}
    </ProjectContext.Provider>
  );
}

export function useProjectContext() {
  const context = useContext(ProjectContext);
  if (!context) {
    throw new Error('useProjectContext must be used within ProjectProvider');
  }
  return context;
}
