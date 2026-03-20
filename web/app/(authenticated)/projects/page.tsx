'use client';

/**
 * Projects List Page — ADR-119 Phase 4
 *
 * Shows multi-agent collaborative projects created by Composer (ADR-120).
 * Read-only — users create projects via Orchestrator conversation.
 */

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import {
  Loader2,
  Briefcase,
  MessageSquare,
} from 'lucide-react';
import { api } from '@/lib/api/client';
import { ORCHESTRATOR_ROUTE } from '@/lib/routes';
import { getPlatformIcon } from '@/components/ui/PlatformIcons';
import { formatDistanceToNow } from 'date-fns';
import type { ProjectSummary } from '@/types';

const TYPE_LABELS: Record<string, string> = {
  slack_digest: 'Slack Recap',
  gmail_digest: 'Gmail Recap',
  notion_digest: 'Notion Recap',
  cross_platform_synthesis: 'Cross-Platform Insights',
  custom: 'Custom Project',
};

function getProjectIcon(typeKey: string | null): React.ReactNode {
  if (typeKey === 'slack_digest') return getPlatformIcon('slack', 'w-5 h-5');
  if (typeKey === 'gmail_digest') return getPlatformIcon('gmail', 'w-5 h-5');
  if (typeKey === 'notion_digest') return getPlatformIcon('notion', 'w-5 h-5');
  return <Briefcase className="w-5 h-5 text-muted-foreground" />;
}

export default function ProjectsPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [projects, setProjects] = useState<ProjectSummary[]>([]);

  useEffect(() => {
    loadProjects();
  }, []);

  const loadProjects = async () => {
    try {
      const data = await api.projects.list();
      setProjects(data.projects);
    } catch (err) {
      console.error('Failed to load projects:', err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="h-full overflow-auto">
      <div className="max-w-3xl mx-auto px-4 md:px-6 py-6">
        {/* Header */}
        <div className="mb-6">
          <h1 className="text-2xl font-bold">Projects</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Multi-agent collaborative work.{' '}
            <Link href={ORCHESTRATOR_ROUTE} className="text-primary hover:underline">
              Ask your Orchestrator
            </Link>{' '}
            to start a project.
          </p>
        </div>

        {/* Content */}
        {loading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
          </div>
        ) : projects.length === 0 ? (
          <div className="text-center py-12">
            <Briefcase className="w-8 h-8 text-muted-foreground mx-auto mb-3" />
            <p className="text-muted-foreground mb-4">No projects yet</p>
            <button
              onClick={() => router.push(ORCHESTRATOR_ROUTE)}
              className="inline-flex items-center gap-1.5 px-4 py-2 text-sm bg-primary text-primary-foreground rounded-md hover:bg-primary/90"
            >
              <MessageSquare className="w-4 h-4" />
              Ask Orchestrator to start a project
            </button>
          </div>
        ) : (
          <div className="border border-border rounded-lg divide-y divide-border overflow-hidden">
            {projects.map((project) => (
              <button
                key={project.project_slug}
                onClick={() => router.push(`/projects/${project.project_slug}`)}
                className="w-full p-4 hover:bg-muted/50 transition-colors text-left"
              >
                <div className="flex items-center gap-3">
                  <div className="shrink-0">
                    {getProjectIcon(project.type_key)}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-semibold truncate">
                        {project.title || project.project_slug.replace(/-/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}
                      </span>
                      {project.type_key && TYPE_LABELS[project.type_key] && (
                        <span className="text-xs px-1.5 py-0.5 rounded bg-muted text-muted-foreground shrink-0">
                          {TYPE_LABELS[project.type_key]}
                        </span>
                      )}
                    </div>
                    {project.purpose && (
                      <p className="text-xs text-muted-foreground mt-0.5 truncate">
                        {project.purpose}
                      </p>
                    )}
                  </div>
                  {project.updated_at && (
                    <span className="text-xs text-muted-foreground shrink-0">
                      {formatDistanceToNow(new Date(project.updated_at), { addSuffix: true })}
                    </span>
                  )}
                </div>
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
