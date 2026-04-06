'use client';

/**
 * AgentDashboard — Composed view assembled from workspace domain files.
 *
 * SURFACE-ARCHITECTURE.md v6: Each agent type has a fixed template.
 * The dashboard reads existing workspace files via API and renders
 * them as structured sections. No LLM cost — pure frontend rendering.
 *
 * Sections:
 * - What's New (from signals/ or recent file updates)
 * - Synthesis (from _landscape.md, _overview.md, etc.)
 * - Entities (from entity subfolders as cards)
 * - Footer links (Browse files, View latest report)
 */

import { useState, useEffect } from 'react';
import {
  Loader2,
  FileText,
  FolderOpen,
  ExternalLink,
  TrendingUp,
  Users as UsersIcon,
  Briefcase,
  BookOpen,
  BarChart3,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { api } from '@/lib/api/client';
import { MarkdownRenderer } from '@/components/shared/MarkdownRenderer';
import type { Agent, Task } from '@/types';

interface AgentDashboardProps {
  agent: Agent;
  tasks: Task[];
  onBrowseFiles: () => void;
}

// Domain → icon mapping
const DOMAIN_ICONS: Record<string, React.ElementType> = {
  competitors: BarChart3,
  market: TrendingUp,
  relationships: UsersIcon,
  projects: Briefcase,
  content_research: BookOpen,
};

// Entity type → display label
const ENTITY_LABELS: Record<string, string> = {
  company: 'Competitors',
  segment: 'Market Segments',
  contact: 'Contacts',
  project: 'Projects',
  topic: 'Research Topics',
};

function formatShort(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime();
  const hours = Math.floor(diff / 3600000);
  if (hours < 1) return 'just now';
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  if (days < 7) return `${days}d ago`;
  return `${Math.floor(days / 7)}w ago`;
}

export function AgentDashboard({ agent, tasks, onBrowseFiles }: AgentDashboardProps) {
  const domain = agent.context_domain;
  const cls = agent.agent_class || 'domain-steward';

  const [loading, setLoading] = useState(true);
  const [domainData, setDomainData] = useState<{
    entities: Array<{ slug: string; name: string; last_updated: string | null; preview: string | null; files: Array<{ name: string; path: string; updated_at: string | null }> }>;
    synthesis_files: Array<{ name: string; filename: string; path: string; updated_at: string | null; preview: string | null }>;
    entity_count: number;
  } | null>(null);
  const [synthesisContent, setSynthesisContent] = useState<string | null>(null);

  useEffect(() => {
    if (!domain) { setLoading(false); return; }

    setLoading(true);
    api.workspace.getDomainEntities(domain)
      .then(async (data) => {
        setDomainData(data);

        // Load the first synthesis file content for inline rendering
        const primarySynth = data.synthesis_files?.[0];
        if (primarySynth?.path) {
          try {
            const file = await api.workspace.getFile(primarySynth.path);
            if (file?.content) setSynthesisContent(file.content);
          } catch { /* best effort */ }
        }
      })
      .catch(() => setDomainData(null))
      .finally(() => setLoading(false));
  }, [domain]);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-16">
        <Loader2 className="w-5 h-5 animate-spin text-muted-foreground" />
      </div>
    );
  }

  // Synthesizer/bot agents without owned domains — show different view
  if (!domain || cls === 'synthesizer') {
    return <SynthesizerDashboard agent={agent} tasks={tasks} onBrowseFiles={onBrowseFiles} />;
  }

  const entities = domainData?.entities || [];
  const entityCount = domainData?.entity_count || 0;
  const synthFiles = domainData?.synthesis_files || [];
  const Icon = DOMAIN_ICONS[domain] || FolderOpen;
  const entityLabel = ENTITY_LABELS[domainData?.entity_count ? 'company' : 'entity'] || 'Entities';

  // Find recently updated entities (within last 24h)
  const recentEntities = entities.filter(e =>
    e.last_updated && (Date.now() - new Date(e.last_updated).getTime()) < 86400000
  );

  return (
    <div className="h-full overflow-auto">
      {/* What's New section */}
      {recentEntities.length > 0 && (
        <div className="px-5 py-4 border-b border-border">
          <h3 className="text-xs font-medium uppercase tracking-wide text-muted-foreground/50 mb-2">
            What's New
          </h3>
          <div className="space-y-1.5">
            {recentEntities.slice(0, 5).map(entity => (
              <div key={entity.slug} className="flex items-center gap-2 text-sm">
                <span className="w-1.5 h-1.5 rounded-full bg-green-500 shrink-0" />
                <span className="font-medium">{entity.name}</span>
                <span className="text-muted-foreground/50 text-xs">
                  updated {entity.last_updated ? formatShort(entity.last_updated) : ''}
                </span>
                {entity.preview && (
                  <span className="text-xs text-muted-foreground truncate ml-auto max-w-[200px]">
                    {entity.preview}
                  </span>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Synthesis / Overview */}
      {synthesisContent && (
        <div className="px-5 py-4 border-b border-border">
          <h3 className="text-xs font-medium uppercase tracking-wide text-muted-foreground/50 mb-2">
            {synthFiles[0]?.name?.replace('.md', '').replace('_', ' ') || 'Overview'}
          </h3>
          <div className="prose prose-sm max-w-none dark:prose-invert text-sm">
            <MarkdownRenderer content={synthesisContent.slice(0, 2000)} />
          </div>
        </div>
      )}

      {/* Entity cards */}
      {entities.length > 0 && (
        <div className="px-5 py-4 border-b border-border">
          <h3 className="text-xs font-medium uppercase tracking-wide text-muted-foreground/50 mb-3">
            {ENTITY_LABELS[domainData?.entity_count ? '' : ''] || domain} ({entityCount})
          </h3>
          <div className="grid grid-cols-2 gap-2">
            {entities.slice(0, 8).map(entity => {
              const isRecent = entity.last_updated && (Date.now() - new Date(entity.last_updated).getTime()) < 86400000;
              return (
                <div
                  key={entity.slug}
                  className={cn(
                    'rounded-lg border p-3 text-sm',
                    isRecent ? 'border-green-500/20 bg-green-500/5' : 'border-border'
                  )}
                >
                  <div className="flex items-center gap-1.5 mb-1">
                    <Icon className="w-3.5 h-3.5 text-muted-foreground/50" />
                    <span className="font-medium truncate">{entity.name}</span>
                  </div>
                  {entity.preview && (
                    <p className="text-xs text-muted-foreground line-clamp-2">{entity.preview}</p>
                  )}
                  <div className="flex items-center gap-2 mt-1.5 text-[10px] text-muted-foreground/40">
                    <span>{entity.files?.length || 0} files</span>
                    {entity.last_updated && (
                      <span>{formatShort(entity.last_updated)}</span>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
          {entities.length > 8 && (
            <p className="text-xs text-muted-foreground/40 mt-2">
              +{entities.length - 8} more
            </p>
          )}
        </div>
      )}

      {/* Empty state */}
      {entities.length === 0 && !synthesisContent && (
        <div className="px-5 py-12 text-center">
          <FolderOpen className="w-10 h-10 text-muted-foreground/15 mx-auto mb-3" />
          <p className="text-sm text-muted-foreground">No data yet</p>
          <p className="text-xs text-muted-foreground/50 mt-1">
            This dashboard populates as the agent works.
          </p>
        </div>
      )}

      {/* Footer links */}
      <div className="px-5 py-3 flex items-center gap-3">
        <button
          onClick={onBrowseFiles}
          className="text-xs text-muted-foreground hover:text-foreground flex items-center gap-1 transition-colors"
        >
          <FolderOpen className="w-3 h-3" />
          Browse files
        </button>
      </div>
    </div>
  );
}

/** Synthesizer/Reporting agent — shows latest output instead of domain entities */
function SynthesizerDashboard({
  agent,
  tasks,
  onBrowseFiles,
}: {
  agent: Agent;
  tasks: Task[];
  onBrowseFiles: () => void;
}) {
  const [latestOutput, setLatestOutput] = useState<{ html?: string; md?: string; date?: string } | null>(null);
  const [loading, setLoading] = useState(true);

  const synthesisTasks = tasks.filter(t => t.task_class === 'synthesis');

  useEffect(() => {
    if (synthesisTasks.length === 0) { setLoading(false); return; }
    const primary = synthesisTasks[0];
    api.tasks.getLatestOutput(primary.slug)
      .then(output => {
        if (output) {
          setLatestOutput({
            html: output.html_content,
            md: output.content || output.md_content,
            date: output.date,
          });
        }
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [synthesisTasks.map(t => t.slug).join(',')]); // eslint-disable-line react-hooks/exhaustive-deps

  if (loading) {
    return <div className="flex items-center justify-center py-16"><Loader2 className="w-5 h-5 animate-spin text-muted-foreground" /></div>;
  }

  if (!latestOutput) {
    return (
      <div className="px-5 py-12 text-center">
        <FileText className="w-10 h-10 text-muted-foreground/15 mx-auto mb-3" />
        <p className="text-sm text-muted-foreground">No reports yet</p>
        <p className="text-xs text-muted-foreground/50 mt-1">
          Reports will appear here once the agent produces its first output.
        </p>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col">
      {latestOutput.date && (
        <div className="px-5 py-2 text-[11px] text-muted-foreground/50 border-b border-border/40">
          Latest report: {latestOutput.date}
        </div>
      )}
      <div className="flex-1 min-h-0 overflow-auto">
        {latestOutput.html ? (
          <iframe
            srcDoc={latestOutput.html}
            className="h-full min-h-[500px] w-full border-0 bg-white"
            sandbox="allow-same-origin allow-scripts"
            title="Latest report"
          />
        ) : latestOutput.md ? (
          <div className="p-5">
            <div className="prose prose-sm max-w-none dark:prose-invert">
              <MarkdownRenderer content={latestOutput.md} />
            </div>
          </div>
        ) : null}
      </div>
    </div>
  );
}
