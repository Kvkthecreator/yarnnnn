'use client';

/**
 * Context — yarnnn's Finder
 *
 * File explorer for the entire yarnnn data model:
 * - Workspace (IDENTITY.md, BRAND.md, CONTEXT.md)
 * - Agents (/agents/{slug}/ → AGENT.md, memory/)
 * - Tasks (/tasks/{slug}/ → TASK.md, outputs/)
 * - Knowledge (/knowledge/ → digests, analyses, research, insights)
 * - Platforms (Slack, Notion — connections + sync status)
 * - Documents (uploaded files)
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
  Brain,
  Link2,
  Upload,
  RefreshCw,
} from 'lucide-react';
import { api } from '@/lib/api/client';
import { cn } from '@/lib/utils';
import ReactMarkdown from 'react-markdown';
import type { Agent, Task, KnowledgeFile, Document } from '@/types';

// =============================================================================
// Types
// =============================================================================

type Section = 'workspace' | 'agents' | 'tasks' | 'knowledge' | 'platforms' | 'documents';

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

  const files = [
    { name: 'IDENTITY.md', path: '/workspace/IDENTITY.md', content: identity?.name ? `${identity.name}${identity.role ? ` — ${identity.role}` : ''}${identity.company ? ` at ${identity.company}` : ''}` : null, summary: identity?.summary },
    { name: 'BRAND.md', path: '/workspace/BRAND.md', content: brand },
    { name: 'CONTEXT.md', path: '/workspace/CONTEXT.md', content: null },
    { name: 'preferences.md', path: '/memory/preferences.md', content: null },
    { name: 'notes.md', path: '/memory/notes.md', content: null },
  ];

  return (
    <div className="space-y-1">
      <p className="text-xs text-muted-foreground/50 px-1 mb-3">
        /workspace/ — your identity and preferences
      </p>
      {files.map(f => (
        <FileRow key={f.name} name={f.name} path={f.path} preview={f.content} empty={!f.content} />
      ))}
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

  return (
    <div className="space-y-1">
      <p className="text-xs text-muted-foreground/50 px-1 mb-3">
        /agents/ — persistent domain experts
      </p>
      {agents.filter(a => a.status !== 'archived').map(agent => (
        <div key={agent.id} className="border border-border rounded-lg overflow-hidden mb-2">
          <Link
            href={`/agents/${agent.id}`}
            className="flex items-center gap-2.5 px-3 py-2.5 hover:bg-muted/50 transition-colors"
          >
            <FolderOpen className="w-4 h-4 text-muted-foreground shrink-0" />
            <div className="min-w-0 flex-1">
              <span className="text-sm font-medium truncate block">{agent.title}</span>
              <span className="text-[11px] text-muted-foreground">/agents/{agent.slug || agent.id}/</span>
            </div>
            <span className={cn(
              'w-2 h-2 rounded-full shrink-0',
              agent.status === 'active' ? 'bg-green-500' : 'bg-amber-500'
            )} />
          </Link>
          <div className="px-3 pb-2 flex gap-1.5 flex-wrap">
            <FileChip name="AGENT.md" />
            <FileChip name="memory/" />
            {agent.agent_instructions && <FileChip name="instructions" filled />}
          </div>
        </div>
      ))}
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
    <div className="space-y-1">
      <p className="text-xs text-muted-foreground/50 px-1 mb-3">
        /tasks/ — defined work units
      </p>
      {tasks.map(task => (
        <div key={task.id} className="border border-border rounded-lg overflow-hidden mb-2">
          <Link
            href={`/tasks/${task.slug}`}
            className="flex items-center gap-2.5 px-3 py-2.5 hover:bg-muted/50 transition-colors"
          >
            <FolderOpen className="w-4 h-4 text-muted-foreground shrink-0" />
            <div className="min-w-0 flex-1">
              <span className="text-sm font-medium truncate block">{task.title}</span>
              <span className="text-[11px] text-muted-foreground">/tasks/{task.slug}/</span>
            </div>
            <span className={cn(
              'w-2 h-2 rounded-full shrink-0',
              task.status === 'active' ? 'bg-green-500' :
              task.status === 'paused' ? 'bg-amber-500' : 'bg-gray-400'
            )} />
          </Link>
          <div className="px-3 pb-2 flex gap-1.5 flex-wrap">
            <FileChip name="TASK.md" />
            <FileChip name="outputs/" />
            <FileChip name="memory/" />
          </div>
        </div>
      ))}
    </div>
  );
}

function KnowledgePanel() {
  const [summary, setSummary] = useState<{ total: number; classes: Array<{ content_class: string; count: number }> } | null>(null);
  const [files, setFiles] = useState<KnowledgeFile[]>([]);
  const [selectedClass, setSelectedClass] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.knowledge.summary().then(setSummary).catch(() => null).finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (selectedClass) {
      api.knowledge.listFiles({ content_class: selectedClass as any, limit: 20 })
        .then(res => setFiles(res.files))
        .catch(() => setFiles([]));
    } else {
      api.knowledge.listFiles({ limit: 20 })
        .then(res => setFiles(res.files))
        .catch(() => setFiles([]));
    }
  }, [selectedClass]);

  if (loading) return <LoadingState />;

  return (
    <div className="space-y-4">
      <p className="text-xs text-muted-foreground/50 px-1">
        /knowledge/ — accumulated from platform sync + agent outputs
      </p>

      {/* Class chips */}
      {summary && summary.classes.length > 0 && (
        <div className="flex gap-1.5 flex-wrap px-1">
          <button
            onClick={() => setSelectedClass(null)}
            className={cn(
              'px-2.5 py-1 text-[11px] font-medium rounded-full border transition-colors',
              !selectedClass ? 'border-primary bg-primary/10 text-primary' : 'border-border text-muted-foreground hover:text-foreground'
            )}
          >
            All ({summary.total})
          </button>
          {summary.classes.map(c => (
            <button
              key={c.content_class}
              onClick={() => setSelectedClass(c.content_class)}
              className={cn(
                'px-2.5 py-1 text-[11px] font-medium rounded-full border transition-colors',
                selectedClass === c.content_class ? 'border-primary bg-primary/10 text-primary' : 'border-border text-muted-foreground hover:text-foreground'
              )}
            >
              {c.content_class} ({c.count})
            </button>
          ))}
        </div>
      )}

      {/* File list */}
      {files.length > 0 ? (
        <div className="space-y-1">
          {files.map(f => (
            <FileRow
              key={f.path}
              name={f.name}
              path={f.path}
              preview={f.summary}
              timestamp={f.updated_at}
            />
          ))}
        </div>
      ) : (
        <EmptyState message="No knowledge files yet — they accumulate from platform sync and agent outputs" />
      )}
    </div>
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
        Platform connections — where external data comes from
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
          <Link href="/integrations" className="text-xs text-primary hover:underline">
            Connect Slack or Notion
          </Link>
        </div>
      )}

      <Link
        href="/integrations"
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
        Uploaded documents — used for onboarding context and agent reference
      </p>

      {docs.length > 0 ? (
        <div className="space-y-1">
          {docs.map(doc => (
            <FileRow
              key={doc.id}
              name={doc.filename}
              path={`/documents/${doc.id}`}
              preview={`${doc.file_type} · ${formatFileSize(doc.file_size)}`}
              timestamp={doc.created_at}
            />
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

function FileRow({ name, path, preview, empty, timestamp }: {
  name: string;
  path: string;
  preview?: string | null;
  empty?: boolean;
  timestamp?: string | null;
}) {
  return (
    <div className={cn(
      'flex items-center gap-2.5 px-3 py-2 rounded-lg transition-colors',
      empty ? 'border border-dashed border-border/50 bg-muted/10' : 'border border-border hover:bg-muted/50',
    )}>
      <FileText className={cn('w-4 h-4 shrink-0', empty ? 'text-muted-foreground/30' : 'text-muted-foreground')} />
      <div className="min-w-0 flex-1">
        <span className={cn('text-sm truncate block', empty ? 'text-muted-foreground/40' : 'font-medium')}>{name}</span>
        {preview ? (
          <span className="text-[11px] text-muted-foreground truncate block">{preview}</span>
        ) : empty ? (
          <span className="text-[11px] text-muted-foreground/30">Empty</span>
        ) : null}
      </div>
      {timestamp && (
        <span className="text-[10px] text-muted-foreground/50 shrink-0">
          {formatRelativeTime(timestamp)}
        </span>
      )}
    </div>
  );
}

function FileChip({ name, filled }: { name: string; filled?: boolean }) {
  return (
    <span className={cn(
      'px-1.5 py-0.5 text-[10px] rounded border',
      filled ? 'border-primary/20 bg-primary/5 text-primary/70' : 'border-border/50 text-muted-foreground/50'
    )}>
      {name}
    </span>
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

const SECTIONS: Array<{ id: Section; label: string; icon: typeof FolderOpen; path: string }> = [
  { id: 'workspace', label: 'Workspace', icon: FolderOpen, path: '/workspace/' },
  { id: 'agents', label: 'Agents', icon: Users, path: '/agents/' },
  { id: 'tasks', label: 'Tasks', icon: ListChecks, path: '/tasks/' },
  { id: 'knowledge', label: 'Knowledge', icon: Brain, path: '/knowledge/' },
  { id: 'platforms', label: 'Platforms', icon: Link2, path: '' },
  { id: 'documents', label: 'Documents', icon: Upload, path: '' },
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
      case 'knowledge': return <KnowledgePanel />;
      case 'platforms': return <PlatformsPanel />;
      case 'documents': return <DocumentsPanel />;
    }
  };

  return (
    <div className="h-full flex">
      {/* Sidebar — tree navigation */}
      <div className="w-[220px] border-r border-border p-3 space-y-1 shrink-0 overflow-y-auto">
        <p className="text-[10px] font-medium text-muted-foreground/50 uppercase tracking-widest px-3 mb-2">
          Explorer
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
            <FolderOpen className="w-3.5 h-3.5" />
            <span>Context</span>
            <ChevronRight className="w-3 h-3" />
            <span className="text-foreground font-medium">
              {SECTIONS.find(s => s.id === activeSection)?.label}
            </span>
            {SECTIONS.find(s => s.id === activeSection)?.path && (
              <span className="text-muted-foreground/40 ml-1">
                {SECTIONS.find(s => s.id === activeSection)?.path}
              </span>
            )}
          </div>

          {renderPanel()}
        </div>
      </div>
    </div>
  );
}
