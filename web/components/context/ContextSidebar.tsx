'use client';

/**
 * Workspace sidebar — project-first file browser.
 *
 * ADR-133: Projects are the primary grouping. Each project folder
 * contains contributions, assembly, and knowledge. Workspace-level
 * files (IDENTITY.md, BRAND.md) shown separately.
 */

import { useState, useEffect } from 'react';
import { useRouter, usePathname, useSearchParams } from 'next/navigation';
import {
  FileText,
  FolderTree,
  Briefcase,
  FolderOpen,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { api } from '@/lib/api/client';
import type { ProjectSummary } from '@/types';

export function ContextSidebar() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const [projects, setProjects] = useState<ProjectSummary[]>([]);
  const [knowledgeCounts, setKnowledgeCounts] = useState<Record<string, number>>({});

  useEffect(() => {
    Promise.all([
      api.projects.list().catch(() => ({ projects: [] })),
      api.knowledge.summary().catch(() => ({ classes: [] })),
    ]).then(([projectsData, knowledge]) => {
      setProjects(projectsData.projects || []);
      const nextCounts: Record<string, number> = {};
      for (const item of knowledge.classes || []) {
        nextCounts[item.content_class] = item.count;
      }
      setKnowledgeCounts(nextCounts);
    }).catch(() => {});
  }, []);

  const isOnContextRoot = pathname === '/context';
  const activeSection = searchParams.get('section') || 'projects';
  const activeProject = searchParams.get('project');
  const totalKnowledge = Object.values(knowledgeCounts).reduce((sum, count) => sum + count, 0);

  return (
    <nav className="h-full min-h-0 border-r border-border bg-muted/50 flex flex-col">
      <div className="p-4 space-y-1 flex-1 min-h-0 overflow-y-auto">
        <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wider px-3 pt-4 pb-2">
          Workspace
        </div>

        {/* Projects — primary grouping */}
        <button
          onClick={() => router.push('/context?section=projects')}
          className={cn(
            "w-full flex items-center justify-between px-3 py-2 rounded-lg text-sm transition-colors",
            activeSection === 'projects' && !activeProject
              ? "bg-primary/10 text-primary"
              : "text-muted-foreground hover:bg-muted hover:text-foreground"
          )}
        >
          <span className="flex items-center gap-2">
            <Briefcase className="w-4 h-4" />
            Projects
          </span>
          {projects.length > 0 && (
            <span className="text-muted-foreground text-xs">{projects.length}</span>
          )}
        </button>

        {/* Per-project sub-items */}
        <div className="ml-3 space-y-0.5">
          {projects.map((p) => (
            <button
              key={p.project_slug}
              onClick={() => router.push(`/context?section=projects&project=${p.project_slug}`)}
              className={cn(
                "w-full flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs transition-colors text-left",
                activeProject === p.project_slug
                  ? "bg-primary/10 text-primary"
                  : "text-foreground hover:bg-muted"
              )}
            >
              <span className="w-1.5 h-1.5 rounded-full shrink-0 bg-green-500" />
              <span className="truncate">{p.title || p.project_slug}</span>
            </button>
          ))}
        </div>

        {/* All Files — cross-project output view */}
        <button
          onClick={() => router.push('/context?section=knowledge')}
          className={cn(
            "w-full flex items-center justify-between px-3 py-2 rounded-lg text-sm transition-colors mt-1",
            activeSection === 'knowledge'
              ? "bg-primary/10 text-primary"
              : "text-muted-foreground hover:bg-muted hover:text-foreground"
          )}
        >
          <span className="flex items-center gap-2">
            <FolderTree className="w-4 h-4" />
            All Files
          </span>
          {totalKnowledge > 0 && (
            <span className="text-muted-foreground text-xs">{totalKnowledge}</span>
          )}
        </button>

        {/* Documents */}
        <button
          onClick={() => router.push('/context?section=documents')}
          className={cn(
            "w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-colors mt-1",
            isOnContextRoot && activeSection === 'documents'
              ? "bg-primary/10 text-primary"
              : "text-muted-foreground hover:bg-muted hover:text-foreground"
          )}
        >
          <FileText className="w-4 h-4" />
          Uploads
        </button>
      </div>
    </nav>
  );
}
