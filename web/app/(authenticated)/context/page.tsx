'use client';

/**
 * Context — workspace configuration overview
 *
 * Structured UI for the yarnnn data model:
 * - Workspace: Identity + Brand (expandable content preview)
 * - Agents: Inline cards with type, status, description
 * - Tasks: Inline cards with status, schedule, objective
 * - Platforms: Connection cards with sync status
 * - Documents: Uploaded files with download
 */

import { useState, useEffect } from 'react';
import Link from 'next/link';
import {
  Loader2,
  FolderOpen,
  FileText,
  ChevronRight,
  ChevronDown,
  Users,
  ListChecks,
  Link2,
  Upload,
  RefreshCw,
  Download,
  Pause,
  Play,
} from 'lucide-react';
import { api } from '@/lib/api/client';
import { cn } from '@/lib/utils';
import { MarkdownRenderer } from '@/components/shared/MarkdownRenderer';
import { roleDisplayName, roleBadgeColor } from '@/lib/agent-identity';
import type { Agent, Task, Document } from '@/types';

// =============================================================================
// Types
// =============================================================================

type Section = 'workspace' | 'agents' | 'tasks' | 'platforms' | 'documents';

// =============================================================================
// Sidebar Tree Item
// =============================================================================

function TreeSection({
  icon: Icon,
  label,
  count,
  active,
  onClick,
}: {
  icon: typeof FolderOpen;
  label: string;
  count?: number;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={cn(
        'w-full flex items-center gap-2.5 px-3 py-2 text-sm rounded-lg transition-colors text-left',
        active
          ? 'bg-primary/10 text-primary font-medium'
          : 'text-muted-foreground hover:bg-muted/50 hover:text-foreground'
      )}
    >
      <Icon className="w-4 h-4 shrink-0" />
      <span className="flex-1 truncate">{label}</span>
      {count !== undefined && (
        <span className="text-[10px] text-muted-foreground/60">{count}</span>
      )}
    </button>
  );
}

// =============================================================================
// Content Panels
// =============================================================================

function WorkspacePanel() {
  const [identity, setIdentity] = useState<Record<string, string> | null>(null);
  const [brand, setBrand] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      api.profile.get().catch(() => null),
      api.brand.get().catch(() => ({ content: null, exists: false })),
    ]).then(([profile, brandData]) => {
      setIdentity(profile);
      if (brandData?.exists) setBrand(brandData.content);
      setLoading(false);
    });
  }, []);

  if (loading) return <LoadingState />;

  const identityContent = identity?.name
    ? [
        identity.name && `# ${identity.name}`,
        identity.role && `**Role:** ${identity.role}`,
        identity.company && `**Company:** ${identity.company}`,
        identity.timezone && `**Timezone:** ${identity.timezone}`,
        identity.summary && `\n${identity.summary}`,
      ].filter(Boolean).join('\n')
    : null;

  return (
    <div className="space-y-3">
      <p className="text-xs text-muted-foreground/50 px-1">
        Your identity and brand guidelines
      </p>
      <ExpandableCard
        title="Identity"
        preview={identity?.name ? `${identity.name}${identity.role ? ` — ${identity.role}` : ''}` : null}
        content={identityContent}
        emptyMessage="No identity configured yet"
      />
      <ExpandableCard
        title="Brand"
        preview={brand ? 'Brand guidelines configured' : null}
        content={brand}
        emptyMessage="No brand guidelines yet"
      />
    </div>
  );
}

function AgentsPanel() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.agents.list().then(setAgents).catch(() => []).finally(() => setLoading(false));
  }, []);

  if (loading) return <LoadingState />;
  if (agents.length === 0) return <EmptyState message="No agents yet" />;

  const activeAgents = agents.filter(a => a.status !== 'archived');

  return (
    <div className="space-y-3">
      <p className="text-xs text-muted-foreground/50 px-1">
        Your workforce — {activeAgents.length} agent{activeAgents.length !== 1 ? 's' : ''}
      </p>
      {activeAgents.map(agent => (
        <AgentCard key={agent.id} agent={agent} />
      ))}
    </div>
  );
}

function AgentCard({ agent }: { agent: Agent }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="border border-border rounded-lg overflow-hidden">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center gap-3 px-3 py-2.5 text-left hover:bg-muted/50 transition-colors"
      >
        {expanded
          ? <ChevronDown className="w-3.5 h-3.5 text-muted-foreground shrink-0" />
          : <ChevronRight className="w-3.5 h-3.5 text-muted-foreground shrink-0" />
        }
        <div className="min-w-0 flex-1">
          <span className="text-sm font-medium truncate block">{agent.title}</span>
          <span className={cn('inline-block mt-0.5 px-1.5 py-0.5 text-[10px] rounded font-medium', roleBadgeColor(agent.role))}>
            {roleDisplayName(agent.role)}
          </span>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          {agent.status === 'paused' && (
            <Pause className="w-3 h-3 text-amber-500" />
          )}
          <span className={cn(
            'w-2 h-2 rounded-full',
            agent.status === 'active' ? 'bg-green-500' : 'bg-amber-500'
          )} />
        </div>
      </button>

      {expanded && (
        <div className="px-3 pb-3 border-t border-border/50 space-y-2 pt-2">
          {agent.description && (
            <p className="text-xs text-muted-foreground">{agent.description}</p>
          )}

          {agent.agent_instructions && (
            <div>
              <span className="text-[10px] font-medium text-muted-foreground/60 uppercase tracking-wider">Instructions</span>
              <div className="mt-1 text-xs text-muted-foreground bg-muted/30 rounded-md px-2.5 py-2 max-h-[120px] overflow-y-auto">
                <MarkdownRenderer content={agent.agent_instructions} compact />
              </div>
            </div>
          )}

          <div className="flex items-center gap-3 text-[11px] text-muted-foreground/60 pt-1">
            {agent.version_count !== undefined && agent.version_count > 0 && (
              <span>{agent.version_count} run{agent.version_count !== 1 ? 's' : ''}</span>
            )}
            {agent.last_run_at && (
              <span>Last run {formatRelativeTime(agent.last_run_at)}</span>
            )}
            <Link
              href={`/agents/${agent.id}`}
              className="text-primary hover:underline ml-auto"
              onClick={e => e.stopPropagation()}
            >
              View details →
            </Link>
          </div>
        </div>
      )}
    </div>
  );
}

function TasksPanel() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.tasks.list().then(setTasks).catch(() => []).finally(() => setLoading(false));
  }, []);

  if (loading) return <LoadingState />;
  if (tasks.length === 0) return <EmptyState message="No tasks yet" />;

  return (
    <div className="space-y-3">
      <p className="text-xs text-muted-foreground/50 px-1">
        {tasks.length} task{tasks.length !== 1 ? 's' : ''}
      </p>
      {tasks.map(task => (
        <TaskCard key={task.id} task={task} />
      ))}
    </div>
  );
}

function TaskCard({ task }: { task: Task }) {
  return (
    <Link
      href={`/tasks/${task.slug}`}
      className="flex items-center gap-3 px-3 py-2.5 rounded-lg border border-border hover:bg-muted/50 transition-colors"
    >
      <div className="min-w-0 flex-1">
        <span className="text-sm font-medium truncate block">{task.title}</span>
        <div className="flex items-center gap-2 mt-0.5">
          {task.schedule && (
            <span className="text-[11px] text-muted-foreground">{task.schedule}</span>
          )}
          {task.objective?.deliverable && (
            <span className="text-[11px] text-muted-foreground/50 truncate">
              {task.schedule ? '·' : ''} {task.objective.deliverable}
            </span>
          )}
        </div>
      </div>
      <div className="flex items-center gap-2 shrink-0">
        {task.status === 'paused' && (
          <Pause className="w-3 h-3 text-amber-500" />
        )}
        <span className={cn(
          'w-2 h-2 rounded-full',
          task.status === 'active' ? 'bg-green-500' :
          task.status === 'paused' ? 'bg-amber-500' : 'bg-gray-400'
        )} />
      </div>
    </Link>
  );
}

function PlatformsPanel() {
  const [platforms, setPlatforms] = useState<Array<{ provider: string; status: string; workspace_name: string | null; resource_count: number }>>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.integrations.getSummary()
      .then(res => setPlatforms(res.platforms))
      .catch(() => setPlatforms([]))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <LoadingState />;

  return (
    <div className="space-y-4">
      <p className="text-xs text-muted-foreground/50 px-1">
        Connected platforms
      </p>

      {platforms.length > 0 ? (
        <div className="space-y-2">
          {platforms.map(p => (
            <Link
              key={p.provider}
              href={`/context/${p.provider}`}
              className="flex items-center justify-between p-3 rounded-lg border border-border hover:bg-muted/50 transition-colors"
            >
              <div className="flex items-center gap-3">
                <Link2 className="w-4 h-4 text-muted-foreground" />
                <div>
                  <span className="text-sm font-medium capitalize">{p.provider}</span>
                  {p.workspace_name && (
                    <span className="text-[11px] text-muted-foreground block">{p.workspace_name}</span>
                  )}
                </div>
              </div>
              <div className="flex items-center gap-2 text-xs text-muted-foreground">
                <span>{p.resource_count} sources</span>
                <span className={cn(
                  'w-2 h-2 rounded-full',
                  p.status === 'active' || p.status === 'connected' ? 'bg-green-500' : 'bg-amber-500'
                )} />
              </div>
            </Link>
          ))}
        </div>
      ) : (
        <div className="text-center py-8">
          <Link2 className="w-8 h-8 text-muted-foreground/20 mx-auto mb-2" />
          <p className="text-sm text-muted-foreground mb-1">No platforms connected</p>
          <Link href="/settings?tab=connectors" className="text-xs text-primary hover:underline">
            Connect Slack or Notion
          </Link>
        </div>
      )}

      <Link
        href="/settings?tab=connectors"
        className="flex items-center gap-2 px-3 py-2 text-xs text-muted-foreground hover:text-foreground transition-colors"
      >
        <RefreshCw className="w-3 h-3" />
        Manage integrations
      </Link>
    </div>
  );
}

function DocumentsPanel() {
  const [docs, setDocs] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.documents.list()
      .then(res => setDocs(res.documents))
      .catch(() => setDocs([]))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <LoadingState />;

  return (
    <div className="space-y-4">
      <p className="text-xs text-muted-foreground/50 px-1">
        Uploaded documents — used by agents as reference material
      </p>

      {docs.length > 0 ? (
        <div className="space-y-1">
          {docs.map(doc => (
            <DocumentRow key={doc.id} doc={doc} />
          ))}
        </div>
      ) : (
        <EmptyState message="No documents uploaded" />
      )}
    </div>
  );
}

// =============================================================================
// Shared Components
// =============================================================================

function ExpandableCard({ title, preview, content, emptyMessage }: {
  title: string;
  preview?: string | null;
  content?: string | null;
  emptyMessage: string;
}) {
  const [expanded, setExpanded] = useState(false);
  const empty = !content;

  return (
    <div className={cn(
      'rounded-lg transition-colors overflow-hidden',
      empty ? 'border border-dashed border-border/50 bg-muted/10' : 'border border-border',
    )}>
      <button
        onClick={() => !empty && setExpanded(!expanded)}
        className={cn(
          'w-full flex items-center gap-2.5 px-3 py-2.5 text-left transition-colors',
          !empty ? 'hover:bg-muted/50 cursor-pointer' : 'cursor-default',
        )}
      >
        {!empty ? (
          expanded
            ? <ChevronDown className="w-3.5 h-3.5 text-muted-foreground shrink-0" />
            : <ChevronRight className="w-3.5 h-3.5 text-muted-foreground shrink-0" />
        ) : (
          <FileText className="w-4 h-4 text-muted-foreground/30 shrink-0" />
        )}
        <div className="min-w-0 flex-1">
          <span className={cn('text-sm block', empty ? 'text-muted-foreground/40' : 'font-medium')}>{title}</span>
          {preview && !expanded ? (
            <span className="text-[11px] text-muted-foreground truncate block">{preview}</span>
          ) : empty ? (
            <span className="text-[11px] text-muted-foreground/30">{emptyMessage}</span>
          ) : null}
        </div>
      </button>
      {expanded && content && (
        <div className="px-3 pb-3 border-t border-border/50">
          <div className="mt-2 text-sm text-muted-foreground">
            <MarkdownRenderer content={content} />
          </div>
        </div>
      )}
    </div>
  );
}

function DocumentRow({ doc }: { doc: Document }) {
  const [expanded, setExpanded] = useState(false);
  const [downloading, setDownloading] = useState(false);

  const handleDownload = async (e: React.MouseEvent) => {
    e.stopPropagation();
    setDownloading(true);
    try {
      const res = await api.documents.download(doc.id);
      window.open(res.url, '_blank');
    } catch {
      // silent fail
    } finally {
      setDownloading(false);
    }
  };

  return (
    <div className="border border-border rounded-lg overflow-hidden">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center gap-2.5 px-3 py-2 text-left hover:bg-muted/50 transition-colors"
      >
        {expanded
          ? <ChevronDown className="w-3.5 h-3.5 text-muted-foreground shrink-0" />
          : <ChevronRight className="w-3.5 h-3.5 text-muted-foreground shrink-0" />
        }
        <div className="min-w-0 flex-1">
          <span className="text-sm font-medium truncate block">{doc.filename}</span>
          <span className="text-[11px] text-muted-foreground truncate block">
            {doc.file_type} · {formatFileSize(doc.file_size)}
          </span>
        </div>
        {doc.created_at && (
          <span className="text-[10px] text-muted-foreground/50 shrink-0">
            {formatRelativeTime(doc.created_at)}
          </span>
        )}
      </button>
      {expanded && (
        <div className="px-3 pb-3 border-t border-border/50">
          <div className="mt-2 flex items-center gap-3">
            <button
              onClick={handleDownload}
              disabled={downloading}
              className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-medium rounded-md border border-border hover:bg-muted/50 transition-colors disabled:opacity-50"
            >
              {downloading ? <Loader2 className="w-3 h-3 animate-spin" /> : <Download className="w-3 h-3" />}
              Download
            </button>
            <span className="text-[11px] text-muted-foreground">
              {doc.file_type} · {formatFileSize(doc.file_size)} · uploaded {doc.created_at ? formatRelativeTime(doc.created_at) : 'unknown'}
            </span>
          </div>
        </div>
      )}
    </div>
  );
}

function LoadingState() {
  return (
    <div className="flex items-center justify-center py-12">
      <Loader2 className="w-4 h-4 animate-spin text-muted-foreground" />
    </div>
  );
}

function EmptyState({ message }: { message: string }) {
  return (
    <div className="text-center py-8">
      <p className="text-xs text-muted-foreground/50">{message}</p>
    </div>
  );
}

// =============================================================================
// Helpers
// =============================================================================

function formatRelativeTime(dateStr: string): string {
  const now = Date.now();
  const then = new Date(dateStr).getTime();
  const diff = now - then;
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes}B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)}KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)}MB`;
}

// =============================================================================
// Section Config
// =============================================================================

const SECTIONS: Array<{ id: Section; label: string; icon: typeof FolderOpen }> = [
  { id: 'workspace', label: 'Workspace', icon: FolderOpen },
  { id: 'agents', label: 'Agents', icon: Users },
  { id: 'tasks', label: 'Tasks', icon: ListChecks },
  { id: 'platforms', label: 'Platforms', icon: Link2 },
  { id: 'documents', label: 'Documents', icon: Upload },
];

// =============================================================================
// Main Page
// =============================================================================

export default function ContextPage() {
  const [activeSection, setActiveSection] = useState<Section>('workspace');

  const renderPanel = () => {
    switch (activeSection) {
      case 'workspace': return <WorkspacePanel />;
      case 'agents': return <AgentsPanel />;
      case 'tasks': return <TasksPanel />;
      case 'platforms': return <PlatformsPanel />;
      case 'documents': return <DocumentsPanel />;
    }
  };

  return (
    <div className="h-full flex">
      {/* Sidebar — section navigation */}
      <div className="w-[220px] border-r border-border p-3 space-y-1 shrink-0 overflow-y-auto">
        <p className="text-[10px] font-medium text-muted-foreground/50 uppercase tracking-widest px-3 mb-2">
          Context
        </p>
        {SECTIONS.map(section => (
          <TreeSection
            key={section.id}
            icon={section.icon}
            label={section.label}
            active={activeSection === section.id}
            onClick={() => setActiveSection(section.id)}
          />
        ))}
      </div>

      {/* Content pane */}
      <div className="flex-1 overflow-y-auto p-6">
        <div className="max-w-3xl">
          {/* Breadcrumb */}
          <div className="flex items-center gap-1.5 text-xs text-muted-foreground mb-6">
            <span>Context</span>
            <ChevronRight className="w-3 h-3" />
            <span className="text-foreground font-medium">
              {SECTIONS.find(s => s.id === activeSection)?.label}
            </span>
          </div>

          {renderPanel()}
        </div>
      </div>
    </div>
  );
}
