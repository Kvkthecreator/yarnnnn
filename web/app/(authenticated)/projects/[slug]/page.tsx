'use client';

/**
 * Project Detail Page — ADR-119 Phase 4b
 *
 * Tab layout: Timeline | Outputs | Contributors
 * Timeline: interleaved activity events + project-scoped TP chat.
 * Outputs: assembly cards with inline markdown preview.
 * Contributors: expandable list with contribution files + agent links.
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { useRouter, useParams } from 'next/navigation';
import Link from 'next/link';
import ReactMarkdown from 'react-markdown';
import {
  Loader2,
  ChevronLeft,
  FolderKanban,
  Users,
  Package,
  FileText,
  HeartPulse,
  AlertTriangle,
  FastForward,
  TrendingUp,
  Archive,
  Send,
  MessageSquare,
  ChevronDown,
  ChevronRight,
  ExternalLink,
} from 'lucide-react';
import { api } from '@/lib/api/client';
import { formatDistanceToNow, format, isToday, isYesterday, startOfDay } from 'date-fns';
import { cn } from '@/lib/utils';
import { useTP } from '@/contexts/TPContext';
import { MessageBlocks } from '@/components/tp/InlineToolCall';
import { ToolResultList } from '@/components/tp/ToolResultCard';
import type {
  ProjectDetail,
  ProjectActivityItem,
  OutputManifest,
  ContributionFile,
} from '@/types';
import type { TPMessage } from '@/types/desk';

// =============================================================================
// Activity event rendering — personified language
// =============================================================================

const ACTIVITY_EVENT_CONFIG: Record<string, {
  label: string;
  icon: React.ReactNode;
  color: string;
}> = {
  project_heartbeat: {
    label: 'Check-in',
    icon: <HeartPulse className="w-4 h-4" />,
    color: 'text-purple-500',
  },
  project_assembled: {
    label: 'Assembly',
    icon: <Package className="w-4 h-4" />,
    color: 'text-green-500',
  },
  project_escalated: {
    label: 'Needs attention',
    icon: <AlertTriangle className="w-4 h-4" />,
    color: 'text-amber-500',
  },
  project_contributor_advanced: {
    label: 'Early run',
    icon: <FastForward className="w-4 h-4" />,
    color: 'text-blue-500',
  },
  duty_promoted: {
    label: 'Promotion',
    icon: <TrendingUp className="w-4 h-4" />,
    color: 'text-green-500',
  },
};

function formatActivitySummary(item: ProjectActivityItem): string {
  const meta = item.metadata || {};
  switch (item.event_type) {
    case 'project_heartbeat': {
      const fresh = meta.contributors_fresh ?? '?';
      const stale = Number(meta.contributors_stale) || 0;
      return stale > 0
        ? `PM checked on contributors — ${fresh} fresh, ${stale} overdue`
        : `PM checked on contributors — all ${fresh} fresh`;
    }
    case 'project_assembled':
      return item.summary || 'Assembled outputs and delivered';
    case 'project_escalated':
      return `PM flagged an issue${meta.reason ? ` — ${meta.reason}` : ''}`;
    case 'project_contributor_advanced':
      return `PM asked ${meta.target_agent_slug || 'a contributor'} to run early${meta.reason ? ` — ${meta.reason}` : ''}`;
    case 'duty_promoted':
      return item.summary || 'Agent earned a new duty';
    default:
      return item.summary || item.event_type;
  }
}

// =============================================================================
// Unified timeline item — activity events + chat messages merged by timestamp
// =============================================================================

type TimelineItem =
  | { kind: 'activity'; data: ProjectActivityItem }
  | { kind: 'chat'; data: TPMessage };

function mergeTimeline(activities: ProjectActivityItem[], messages: TPMessage[]): TimelineItem[] {
  const items: TimelineItem[] = [
    ...activities.map((a) => ({ kind: 'activity' as const, data: a })),
    ...messages.map((m) => ({ kind: 'chat' as const, data: m })),
  ];
  items.sort((a, b) => {
    const aTime = a.kind === 'activity' ? new Date(a.data.created_at).getTime() : a.data.timestamp.getTime();
    const bTime = b.kind === 'activity' ? new Date(b.data.created_at).getTime() : b.data.timestamp.getTime();
    return aTime - bTime;
  });
  return items;
}

// =============================================================================
// Tab components
// =============================================================================

function TimelineTab({
  activities,
  slug,
  projectTitle,
}: {
  activities: ProjectActivityItem[];
  slug: string;
  projectTitle: string;
}) {
  const {
    messages,
    sendMessage,
    isLoading,
    status,
    pendingClarification,
    respondToClarification,
    loadScopedHistory,
  } = useTP();

  const [input, setInput] = useState('');
  const bottomRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Load project-scoped history on mount
  useEffect(() => {
    loadScopedHistory(undefined, slug);
  }, [slug, loadScopedHistory]);

  // Auto-scroll on new items
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, activities, status]);

  const adjustTextareaHeight = useCallback(() => {
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = 'auto';
      textarea.style.height = `${Math.min(textarea.scrollHeight, 200)}px`;
    }
  }, []);

  useEffect(() => {
    adjustTextareaHeight();
  }, [input, adjustTextareaHeight]);

  const surface = { type: 'project-detail' as const, projectSlug: slug };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;
    sendMessage(input, { surface });
    setInput('');
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e as unknown as React.FormEvent);
    }
  };

  const timeline = mergeTimeline(activities, messages);

  return (
    <div className="flex flex-col h-full">
      {/* Scrollable timeline */}
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-2">
        <div className="max-w-2xl mx-auto w-full space-y-2">
          {timeline.length === 0 && !isLoading && (
            <div className="text-center py-8">
              <MessageSquare className="w-10 h-10 text-muted-foreground/20 mx-auto mb-3" />
              <p className="text-sm text-muted-foreground max-w-xs mx-auto">
                No activity yet. The PM will start checking in soon, or you can chat about this project below.
              </p>
            </div>
          )}

          {timeline.map((item, i) => {
            if (item.kind === 'activity') {
              const a = item.data;
              const config = ACTIVITY_EVENT_CONFIG[a.event_type] || {
                label: a.event_type,
                icon: <FileText className="w-4 h-4" />,
                color: 'text-muted-foreground',
              };
              return (
                <div key={`activity-${a.id}`} className="flex items-start gap-2 py-1.5">
                  <span className={cn('mt-0.5 shrink-0', config.color)}>
                    {config.icon}
                  </span>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm">{formatActivitySummary(a)}</p>
                    <p className="text-xs text-muted-foreground">
                      {format(new Date(a.created_at), 'MMM d, h:mm a')}
                    </p>
                  </div>
                </div>
              );
            }

            // Chat message
            const msg = item.data;
            return (
              <div
                key={`chat-${msg.id}`}
                className={cn(
                  'text-sm rounded-2xl px-4 py-3 max-w-[85%]',
                  msg.role === 'user'
                    ? 'bg-primary/10 ml-auto rounded-br-md'
                    : 'bg-muted rounded-bl-md'
                )}
              >
                <span className={cn(
                  "text-[10px] font-medium text-muted-foreground/70 tracking-wider block mb-1.5",
                  msg.role === 'user' ? 'uppercase' : 'font-brand text-[11px]'
                )}>
                  {msg.role === 'user' ? 'You' : 'Thinking Partner'}
                </span>
                {msg.blocks && msg.blocks.length > 0 ? (
                  <MessageBlocks blocks={msg.blocks} />
                ) : msg.role === 'assistant' && !msg.content && isLoading ? (
                  <div className="flex items-center gap-2 text-muted-foreground">
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span>Thinking...</span>
                  </div>
                ) : (
                  <>
                    {msg.role === 'assistant' ? (
                      <div className="prose prose-sm dark:prose-invert max-w-none prose-p:my-1 prose-headings:mt-3 prose-headings:mb-1 prose-ul:my-1 prose-ol:my-1 prose-li:my-0">
                        <ReactMarkdown>{msg.content}</ReactMarkdown>
                      </div>
                    ) : (
                      <p className="whitespace-pre-wrap">{msg.content}</p>
                    )}
                    {msg.toolResults && msg.toolResults.length > 0 && (
                      <ToolResultList results={msg.toolResults} compact />
                    )}
                  </>
                )}
              </div>
            );
          })}

          {status.type === 'thinking' && messages[messages.length - 1]?.role === 'user' && (
            <div className="flex items-center gap-2 text-muted-foreground text-sm">
              <Loader2 className="w-4 h-4 animate-spin" />
              <span>Thinking...</span>
            </div>
          )}

          {status.type === 'clarify' && pendingClarification && (
            <div className="space-y-3 bg-muted/50 rounded-lg p-4 max-w-2xl border border-border">
              <p className="text-sm font-medium">{pendingClarification.question}</p>
              {pendingClarification.options && pendingClarification.options.length > 0 ? (
                <div className="flex flex-wrap gap-2">
                  {pendingClarification.options.map((option, idx) => (
                    <button
                      key={idx}
                      onClick={() => respondToClarification(option)}
                      className="px-4 py-2 text-sm rounded-lg border border-primary/30 bg-primary/5 text-primary hover:bg-primary/15 hover:border-primary/50 transition-all font-medium shadow-sm"
                    >
                      {option}
                    </button>
                  ))}
                </div>
              ) : (
                <p className="text-xs text-muted-foreground">Type your response below</p>
              )}
            </div>
          )}

          <div ref={bottomRef} />
        </div>
      </div>

      {/* Chat input */}
      <div className="px-4 pb-4 pt-2 shrink-0 border-t border-border" style={{ paddingBottom: 'max(1rem, env(safe-area-inset-bottom))' }}>
        <form onSubmit={handleSubmit} className="max-w-2xl mx-auto">
          <div className="flex items-end gap-2 border border-border bg-background rounded-xl shadow-sm focus-within:ring-2 focus-within:ring-primary/50 focus-within:shadow-md">
            <textarea
              ref={textareaRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={isLoading}
              enterKeyHint="send"
              placeholder={`Chat about ${projectTitle}...`}
              rows={1}
              className="flex-1 py-3 pl-4 pr-2 text-base sm:text-sm bg-transparent resize-none focus:outline-none disabled:opacity-50 max-h-[200px]"
            />
            <button
              type="submit"
              disabled={isLoading || !input.trim()}
              className="shrink-0 p-3 text-primary hover:text-primary/80 disabled:text-muted-foreground disabled:opacity-50 transition-colors"
              aria-label="Send"
            >
              <Send className="w-5 h-5" />
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function OutputsTab({ slug }: { slug: string }) {
  const [outputs, setOutputs] = useState<OutputManifest[]>([]);
  const [loading, setLoading] = useState(true);
  const [expandedFolder, setExpandedFolder] = useState<string | null>(null);
  const [previewContent, setPreviewContent] = useState<string | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);

  useEffect(() => {
    api.projects.getOutputs(slug).then((res) => {
      setOutputs(res.outputs);
    }).catch(() => {}).finally(() => setLoading(false));
  }, [slug]);

  const handleExpand = async (folder: string) => {
    if (expandedFolder === folder) {
      setExpandedFolder(null);
      setPreviewContent(null);
      return;
    }
    setExpandedFolder(folder);
    setPreviewLoading(true);
    try {
      const detail = await api.projects.getOutput(slug, folder);
      setPreviewContent(detail.content);
    } catch {
      setPreviewContent('Failed to load preview.');
    } finally {
      setPreviewLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="w-5 h-5 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (outputs.length === 0) {
    return (
      <div className="text-center py-12">
        <Package className="w-8 h-8 text-muted-foreground/20 mx-auto mb-3" />
        <p className="text-sm text-muted-foreground">No assemblies yet — the PM will trigger one when contributions are ready.</p>
      </div>
    );
  }

  return (
    <div className="divide-y divide-border">
      {outputs.map((o) => (
        <div key={o.folder} className="px-4 py-3">
          <button
            onClick={() => handleExpand(o.folder)}
            className="w-full flex items-center gap-2 text-left group"
          >
            {expandedFolder === o.folder ? (
              <ChevronDown className="w-4 h-4 text-muted-foreground shrink-0" />
            ) : (
              <ChevronRight className="w-4 h-4 text-muted-foreground shrink-0" />
            )}
            <div className="flex-1 min-w-0">
              <span className="text-sm font-medium group-hover:text-primary transition-colors">
                v{o.version}
              </span>
              {o.created_at && (
                <span className="text-xs text-muted-foreground ml-2">
                  {format(new Date(o.created_at), 'MMM d, yyyy h:mm a')}
                </span>
              )}
            </div>
            <span className={cn(
              'text-xs px-2 py-0.5 rounded',
              o.status === 'delivered' ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400' :
              o.status === 'active' ? 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400' :
              'bg-muted text-muted-foreground'
            )}>
              {o.status}
            </span>
          </button>

          {/* Expanded: file list + preview */}
          {expandedFolder === o.folder && (
            <div className="mt-3 ml-6 space-y-3">
              {/* File list */}
              {o.files.length > 0 && (
                <div className="space-y-1">
                  {o.files.map((f, fi) => (
                    <div key={fi} className="flex items-center gap-2 text-xs text-muted-foreground">
                      <FileText className="w-3 h-3 shrink-0" />
                      <span className="truncate">{f.path}</span>
                      {f.content_url && (
                        <a
                          href={f.content_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-primary hover:underline shrink-0"
                        >
                          <ExternalLink className="w-3 h-3" />
                        </a>
                      )}
                    </div>
                  ))}
                </div>
              )}

              {/* Sources */}
              {o.sources.length > 0 && (
                <p className="text-xs text-muted-foreground">
                  Sources: {o.sources.join(', ')}
                </p>
              )}

              {/* Inline markdown preview */}
              {previewLoading ? (
                <div className="flex items-center gap-2 text-muted-foreground text-xs py-2">
                  <Loader2 className="w-3 h-3 animate-spin" />
                  Loading preview...
                </div>
              ) : previewContent ? (
                <div className="border border-border rounded-lg p-3 bg-muted/30 max-h-80 overflow-y-auto">
                  <div className="prose prose-sm dark:prose-invert max-w-none prose-p:my-1">
                    <ReactMarkdown>{previewContent}</ReactMarkdown>
                  </div>
                </div>
              ) : null}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

function ContributorsTab({
  contributors,
  contributions,
  slug,
}: {
  contributors: { agent_slug: string; agent_id?: string; expected_contribution?: string }[];
  contributions: Record<string, string[]>;
  slug: string;
}) {
  const [expanded, setExpanded] = useState<string | null>(null);
  const [files, setFiles] = useState<ContributionFile[]>([]);
  const [filesLoading, setFilesLoading] = useState(false);

  const handleExpand = async (agentSlug: string) => {
    if (expanded === agentSlug) {
      setExpanded(null);
      setFiles([]);
      return;
    }
    setExpanded(agentSlug);
    setFilesLoading(true);
    try {
      const res = await api.projects.getContributions(slug, agentSlug);
      setFiles(res.files);
    } catch {
      setFiles([]);
    } finally {
      setFilesLoading(false);
    }
  };

  if (contributors.length === 0) {
    return (
      <div className="text-center py-12">
        <Users className="w-8 h-8 text-muted-foreground/20 mx-auto mb-3" />
        <p className="text-sm text-muted-foreground">No contributors assigned yet.</p>
      </div>
    );
  }

  return (
    <div className="divide-y divide-border">
      {contributors.map((c) => {
        const contribPaths = contributions[c.agent_slug] || [];
        const isExpanded = expanded === c.agent_slug;
        return (
          <div key={c.agent_slug} className="px-4 py-3">
            <button
              onClick={() => handleExpand(c.agent_slug)}
              className="w-full flex items-center gap-2 text-left group"
            >
              {isExpanded ? (
                <ChevronDown className="w-4 h-4 text-muted-foreground shrink-0" />
              ) : (
                <ChevronRight className="w-4 h-4 text-muted-foreground shrink-0" />
              )}
              <div className="flex-1 min-w-0">
                <span className="text-sm font-medium group-hover:text-primary transition-colors">
                  {c.agent_slug.replace(/-/g, ' ').replace(/\b\w/g, ch => ch.toUpperCase())}
                </span>
                {c.expected_contribution && (
                  <p className="text-xs text-muted-foreground mt-0.5">{c.expected_contribution}</p>
                )}
              </div>
              <div className="flex items-center gap-2 shrink-0">
                {contribPaths.length > 0 && (
                  <span className="text-xs text-muted-foreground flex items-center gap-1">
                    <FileText className="w-3 h-3" />
                    {contribPaths.length}
                  </span>
                )}
                {c.agent_id && (
                  <Link
                    href={`/agents/${c.agent_id}`}
                    onClick={(e) => e.stopPropagation()}
                    className="text-xs text-primary hover:underline"
                  >
                    View agent
                  </Link>
                )}
              </div>
            </button>

            {/* Expanded: contribution file contents */}
            {isExpanded && (
              <div className="mt-3 ml-6">
                {filesLoading ? (
                  <div className="flex items-center gap-2 text-muted-foreground text-xs py-2">
                    <Loader2 className="w-3 h-3 animate-spin" />
                    Loading contributions...
                  </div>
                ) : files.length === 0 ? (
                  <p className="text-xs text-muted-foreground">No contribution files yet.</p>
                ) : (
                  <div className="space-y-3">
                    {files.map((f) => (
                      <div key={f.path} className="border border-border rounded-lg overflow-hidden">
                        <div className="px-3 py-1.5 bg-muted/50 text-xs text-muted-foreground flex items-center gap-1.5">
                          <FileText className="w-3 h-3" />
                          {f.path.split('/').pop()}
                          {f.updated_at && (
                            <span className="ml-auto">{formatDistanceToNow(new Date(f.updated_at), { addSuffix: true })}</span>
                          )}
                        </div>
                        <div className="p-3 max-h-60 overflow-y-auto">
                          <div className="prose prose-sm dark:prose-invert max-w-none prose-p:my-1">
                            <ReactMarkdown>{f.content}</ReactMarkdown>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

// =============================================================================
// Main Component
// =============================================================================

type TabId = 'timeline' | 'outputs' | 'contributors';

export default function ProjectDetailPage() {
  const params = useParams<{ slug: string }>();
  const slug = params.slug;
  const router = useRouter();

  const [loading, setLoading] = useState(true);
  const [project, setProject] = useState<ProjectDetail | null>(null);
  const [activities, setActivities] = useState<ProjectActivityItem[]>([]);
  const [archiving, setArchiving] = useState(false);
  const [activeTab, setActiveTab] = useState<TabId>('timeline');

  const loadProject = useCallback(async () => {
    try {
      const [detail, activityData] = await Promise.all([
        api.projects.get(slug),
        api.projects.getActivity(slug, 30).catch(() => ({ activities: [], total: 0 })),
      ]);
      setProject(detail);
      setActivities(activityData.activities);
    } catch (err) {
      console.error('Failed to load project:', err);
    } finally {
      setLoading(false);
    }
  }, [slug]);

  useEffect(() => {
    loadProject();
  }, [loadProject]);

  const handleArchive = async () => {
    if (!confirm('Archive this project? This will hide it from the active list.')) return;
    setArchiving(true);
    try {
      await api.projects.archive(slug);
      router.push('/projects');
    } catch (err) {
      console.error('Failed to archive project:', err);
      setArchiving(false);
    }
  };

  // Loading
  if (loading) {
    return (
      <div className="h-full flex items-center justify-center">
        <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  // Not found
  if (!project) {
    return (
      <div className="h-full flex flex-col items-center justify-center gap-4">
        <FolderKanban className="w-8 h-8 text-muted-foreground" />
        <p className="text-muted-foreground">Project not found</p>
        <button onClick={() => router.push('/projects')} className="text-sm text-primary hover:underline">
          Back to Projects
        </button>
      </div>
    );
  }

  const { project: meta, contributions, assemblies } = project;
  const title = meta.title || slug.replace(/-/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
  const intent = meta.intent;
  const contributors = meta.contributors || [];

  const tabs: { id: TabId; label: string; icon: React.ReactNode }[] = [
    { id: 'timeline', label: 'Timeline', icon: <HeartPulse className="w-4 h-4" /> },
    { id: 'outputs', label: `Outputs${assemblies.length > 0 ? ` (${assemblies.length})` : ''}`, icon: <Package className="w-4 h-4" /> },
    { id: 'contributors', label: `Contributors${contributors.length > 0 ? ` (${contributors.length})` : ''}`, icon: <Users className="w-4 h-4" /> },
  ];

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="shrink-0 px-4 md:px-6 py-4 border-b border-border">
        <Link
          href="/projects"
          className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground transition-colors mb-3"
        >
          <ChevronLeft className="w-4 h-4" />
          Projects
        </Link>

        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-xl font-bold">{title}</h1>
            {intent && (
              <div className="flex flex-wrap gap-2 mt-1.5">
                {intent.deliverable && (
                  <span className="text-xs px-2 py-0.5 rounded bg-muted text-muted-foreground">
                    {intent.deliverable}
                  </span>
                )}
                {intent.audience && (
                  <span className="text-xs px-2 py-0.5 rounded bg-muted text-muted-foreground">
                    For {intent.audience}
                  </span>
                )}
                {intent.format && (
                  <span className="text-xs px-2 py-0.5 rounded bg-muted text-muted-foreground">
                    {intent.format}
                  </span>
                )}
              </div>
            )}
            {intent?.purpose && (
              <p className="text-sm text-muted-foreground mt-1.5">{intent.purpose}</p>
            )}
          </div>
          <button
            onClick={handleArchive}
            disabled={archiving}
            className="text-xs text-muted-foreground hover:text-destructive transition-colors flex items-center gap-1 shrink-0"
            title="Archive project"
          >
            {archiving ? <Loader2 className="w-3 h-3 animate-spin" /> : <Archive className="w-3 h-3" />}
            Archive
          </button>
        </div>

        {/* Tabs */}
        <div className="flex gap-1 mt-4 -mb-4 overflow-x-auto">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={cn(
                'flex items-center gap-1.5 px-3 py-2 text-sm font-medium border-b-2 transition-colors whitespace-nowrap',
                activeTab === tab.id
                  ? 'border-primary text-foreground'
                  : 'border-transparent text-muted-foreground hover:text-foreground'
              )}
            >
              {tab.icon}
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Tab content */}
      <div className="flex-1 min-h-0 overflow-hidden">
        {activeTab === 'timeline' && (
          <TimelineTab activities={activities} slug={slug} projectTitle={title} />
        )}
        {activeTab === 'outputs' && (
          <div className="h-full overflow-y-auto">
            <div className="max-w-3xl mx-auto">
              <OutputsTab slug={slug} />
            </div>
          </div>
        )}
        {activeTab === 'contributors' && (
          <div className="h-full overflow-y-auto">
            <div className="max-w-3xl mx-auto">
              <ContributorsTab
                contributors={contributors}
                contributions={contributions}
                slug={slug}
              />
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
