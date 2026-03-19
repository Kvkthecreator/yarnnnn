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
  Pencil,
  Check,
  X,
  Brain,
  ClipboardCheck,
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
  ProjectContributor,
  OutputManifest,
  ContributionFile,
  PMIntelligence,
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
  // ADR-123 Phase 3: PM intelligence events
  project_quality_assessed: {
    label: 'Quality assessed',
    icon: <ClipboardCheck className="w-4 h-4" />,
    color: 'text-purple-500',
  },
  project_contributor_steered: {
    label: 'Contributor steered',
    icon: <Brain className="w-4 h-4" />,
    color: 'text-amber-500',
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
    case 'project_quality_assessed': {
      const verdict = meta.verdict || '';
      return `PM assessed quality${verdict ? ` — ${verdict}` : ''}`;
    }
    case 'project_contributor_steered':
      return `PM steered ${meta.target_agent_slug || 'a contributor'}${meta.guidance ? ` — ${meta.guidance}` : ''}`;
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

// =============================================================================
// ADR-124 Phase 2: Meeting Room — attributed messages + @-mention input
// =============================================================================

/** Resolve display name for a message author */
function getAuthorLabel(msg: TPMessage): string {
  if (msg.role === 'user') return 'You';
  if (msg.authorName) return msg.authorName;
  if (msg.authorAgentSlug) {
    return msg.authorAgentSlug.replace(/-/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
  }
  return 'Thinking Partner';
}

/** Color accent per author role */
function getAuthorColor(msg: TPMessage): string {
  if (msg.role === 'user') return 'text-primary/70';
  switch (msg.authorRole) {
    case 'pm': return 'text-purple-600 dark:text-purple-400';
    case 'digest': return 'text-blue-600 dark:text-blue-400';
    case 'monitor': return 'text-amber-600 dark:text-amber-400';
    case 'research': return 'text-green-600 dark:text-green-400';
    default: return 'text-muted-foreground/70';
  }
}

/** Bubble background per author type */
function getBubbleBg(msg: TPMessage): string {
  if (msg.role === 'user') return 'bg-primary/10';
  switch (msg.authorRole) {
    case 'pm': return 'bg-purple-50 dark:bg-purple-950/30';
    default: return 'bg-muted';
  }
}

function MeetingRoomTab({
  activities,
  slug,
  projectTitle,
  contributors,
}: {
  activities: ProjectActivityItem[];
  slug: string;
  projectTitle: string;
  contributors: ProjectContributor[];
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
  const [targetAgent, setTargetAgent] = useState<ProjectContributor | null>(null);
  const [showMentionPicker, setShowMentionPicker] = useState(false);
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
    sendMessage(input, {
      surface,
      targetAgentId: targetAgent?.agent_id || undefined,
    });
    setInput('');
    setTargetAgent(null);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e as unknown as React.FormEvent);
    }
    // @ triggers mention picker
    if (e.key === '@') {
      setShowMentionPicker(true);
    }
  };

  const handleMentionSelect = (contributor: ProjectContributor) => {
    setTargetAgent(contributor);
    setShowMentionPicker(false);
    textareaRef.current?.focus();
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const val = e.target.value;
    setInput(val);
    // Show mention picker when @ is typed at word boundary
    if (val.endsWith('@') || val.match(/@\S{0,20}$/)) {
      setShowMentionPicker(true);
    } else if (!val.includes('@')) {
      setShowMentionPicker(false);
    }
  };

  const timeline = mergeTimeline(activities, messages);

  // Filter mention picker results
  const mentionQuery = (input.match(/@(\S*)$/) || [])[1]?.toLowerCase() || '';
  const filteredContributors = contributors.filter(c =>
    c.agent_slug.toLowerCase().includes(mentionQuery) ||
    (c.title || '').toLowerCase().includes(mentionQuery)
  );

  return (
    <div className="flex flex-col h-full">
      {/* Scrollable meeting room */}
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

          {timeline.map((item) => {
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

            // Chat message — attributed bubble (ADR-124)
            const msg = item.data;
            const authorLabel = getAuthorLabel(msg);
            const authorColor = getAuthorColor(msg);
            const bubbleBg = getBubbleBg(msg);

            return (
              <div
                key={`chat-${msg.id}`}
                className={cn(
                  'text-sm rounded-2xl px-4 py-3 max-w-[85%]',
                  bubbleBg,
                  msg.role === 'user'
                    ? 'ml-auto rounded-br-md'
                    : 'rounded-bl-md'
                )}
              >
                <span className={cn(
                  "text-[10px] font-medium tracking-wider block mb-1.5",
                  msg.role === 'user' ? 'uppercase text-primary/70' : 'font-brand text-[11px]',
                  authorColor,
                )}>
                  {authorLabel}
                  {msg.authorRole === 'pm' && msg.role !== 'user' && (
                    <span className="ml-1 opacity-60">PM</span>
                  )}
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

      {/* Chat input with @-mention support */}
      <div className="px-4 pb-4 pt-2 shrink-0 border-t border-border" style={{ paddingBottom: 'max(1rem, env(safe-area-inset-bottom))' }}>
        <div className="max-w-2xl mx-auto">
          {/* Target agent indicator */}
          {targetAgent && (
            <div className="flex items-center gap-1.5 mb-1.5 text-xs">
              <span className="text-muted-foreground">Talking to</span>
              <span className="font-medium text-purple-600 dark:text-purple-400">
                {targetAgent.title || targetAgent.agent_slug.replace(/-/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}
              </span>
              <button
                onClick={() => setTargetAgent(null)}
                className="text-muted-foreground hover:text-foreground transition-colors"
              >
                <X className="w-3 h-3" />
              </button>
            </div>
          )}

          {/* @-mention picker */}
          {showMentionPicker && filteredContributors.length > 0 && (
            <div className="mb-1.5 border border-border rounded-lg bg-background shadow-lg overflow-hidden">
              {filteredContributors.map((c) => (
                <button
                  key={c.agent_slug}
                  onClick={() => handleMentionSelect(c)}
                  className="w-full flex items-center gap-2 px-3 py-2 text-left text-sm hover:bg-muted/50 transition-colors"
                >
                  <span className={cn(
                    'w-2 h-2 rounded-full shrink-0',
                    c.role === 'pm' ? 'bg-purple-500' : 'bg-blue-500'
                  )} />
                  <span className="font-medium">
                    {c.title || c.agent_slug.replace(/-/g, ' ').replace(/\b\w/g, ch => ch.toUpperCase())}
                  </span>
                  {c.role && (
                    <span className="text-xs text-muted-foreground">{c.role}</span>
                  )}
                </button>
              ))}
            </div>
          )}

          <form onSubmit={handleSubmit}>
            <div className="flex items-end gap-2 border border-border bg-background rounded-xl shadow-sm focus-within:ring-2 focus-within:ring-primary/50 focus-within:shadow-md">
              <textarea
                ref={textareaRef}
                value={input}
                onChange={handleInputChange}
                onKeyDown={handleKeyDown}
                onBlur={() => setTimeout(() => setShowMentionPicker(false), 150)}
                disabled={isLoading}
                enterKeyHint="send"
                placeholder={targetAgent
                  ? `Message ${targetAgent.title || targetAgent.agent_slug}...`
                  : `Chat about ${projectTitle}... (@ to mention an agent)`
                }
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
  pmIntelligence,
}: {
  contributors: ProjectContributor[];
  contributions: Record<string, string[]>;
  slug: string;
  pmIntelligence?: PMIntelligence | null;
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
      {/* PM quality assessment summary */}
      {pmIntelligence?.quality_assessment && (
        <div className="px-4 py-3">
          <PMIntelligencePanel pmIntelligence={pmIntelligence} />
        </div>
      )}
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
                  {c.title || c.agent_slug.replace(/-/g, ' ').replace(/\b\w/g, ch => ch.toUpperCase())}
                </span>
                {c.role && (
                  <span className="text-[10px] text-muted-foreground ml-1.5">{c.role}</span>
                )}
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

            {/* Expanded: PM brief + contribution file contents */}
            {isExpanded && (
              <div className="mt-3 ml-6">
                {/* Per-contributor PM brief */}
                {pmIntelligence && pmIntelligence.briefs?.[c.agent_slug] && (
                  <PMIntelligencePanel pmIntelligence={pmIntelligence} agentSlug={c.agent_slug} />
                )}
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
// ADR-123 Phase 3: Editable objective section
// =============================================================================

function EditableObjective({
  slug,
  objective,
  onUpdate,
}: {
  slug: string;
  objective?: { deliverable?: string; audience?: string; format?: string; purpose?: string };
  onUpdate: (obj: { deliverable?: string; audience?: string; format?: string; purpose?: string }) => void;
}) {
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [draft, setDraft] = useState({
    deliverable: objective?.deliverable || '',
    audience: objective?.audience || '',
    format: objective?.format || '',
    purpose: objective?.purpose || '',
  });

  const handleEdit = () => {
    setDraft({
      deliverable: objective?.deliverable || '',
      audience: objective?.audience || '',
      format: objective?.format || '',
      purpose: objective?.purpose || '',
    });
    setEditing(true);
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      const cleaned = Object.fromEntries(
        Object.entries(draft).filter(([, v]) => v.trim() !== '')
      );
      await api.projects.update(slug, { objective: cleaned });
      onUpdate(cleaned);
      setEditing(false);
    } catch (err) {
      console.error('Failed to update objective:', err);
    } finally {
      setSaving(false);
    }
  };

  if (editing) {
    return (
      <div className="space-y-2 mt-1.5">
        <div className="grid grid-cols-2 gap-2">
          <input
            value={draft.deliverable}
            onChange={(e) => setDraft({ ...draft, deliverable: e.target.value })}
            placeholder="Deliverable"
            className="text-xs px-2 py-1.5 rounded border border-border bg-background focus:outline-none focus:ring-1 focus:ring-primary"
          />
          <input
            value={draft.audience}
            onChange={(e) => setDraft({ ...draft, audience: e.target.value })}
            placeholder="Audience"
            className="text-xs px-2 py-1.5 rounded border border-border bg-background focus:outline-none focus:ring-1 focus:ring-primary"
          />
          <input
            value={draft.format}
            onChange={(e) => setDraft({ ...draft, format: e.target.value })}
            placeholder="Format"
            className="text-xs px-2 py-1.5 rounded border border-border bg-background focus:outline-none focus:ring-1 focus:ring-primary"
          />
        </div>
        <input
          value={draft.purpose}
          onChange={(e) => setDraft({ ...draft, purpose: e.target.value })}
          placeholder="Purpose — why this project exists"
          className="w-full text-sm px-2 py-1.5 rounded border border-border bg-background focus:outline-none focus:ring-1 focus:ring-primary"
        />
        <div className="flex items-center gap-2">
          <button
            onClick={handleSave}
            disabled={saving}
            className="flex items-center gap-1 text-xs text-primary hover:text-primary/80 transition-colors"
          >
            {saving ? <Loader2 className="w-3 h-3 animate-spin" /> : <Check className="w-3 h-3" />}
            Save
          </button>
          <button
            onClick={() => setEditing(false)}
            className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors"
          >
            <X className="w-3 h-3" />
            Cancel
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="group/obj">
      {objective && (
        <div className="flex flex-wrap gap-2 mt-1.5">
          {objective.deliverable && (
            <span className="text-xs px-2 py-0.5 rounded bg-muted text-muted-foreground">
              {objective.deliverable}
            </span>
          )}
          {objective.audience && (
            <span className="text-xs px-2 py-0.5 rounded bg-muted text-muted-foreground">
              For {objective.audience}
            </span>
          )}
          {objective.format && (
            <span className="text-xs px-2 py-0.5 rounded bg-muted text-muted-foreground">
              {objective.format}
            </span>
          )}
          <button
            onClick={handleEdit}
            className="opacity-0 group-hover/obj:opacity-100 text-muted-foreground hover:text-foreground transition-all"
            title="Edit objective"
          >
            <Pencil className="w-3 h-3" />
          </button>
        </div>
      )}
      {objective?.purpose && (
        <p className="text-sm text-muted-foreground mt-1.5">{objective.purpose}</p>
      )}
      {!objective && (
        <button
          onClick={handleEdit}
          className="text-xs text-muted-foreground hover:text-primary transition-colors mt-1.5 flex items-center gap-1"
        >
          <Pencil className="w-3 h-3" />
          Set objective
        </button>
      )}
    </div>
  );
}

// =============================================================================
// ADR-123 Phase 3: PM Intelligence panel for Contributors tab
// =============================================================================

function PMIntelligencePanel({
  pmIntelligence,
  agentSlug,
}: {
  pmIntelligence: PMIntelligence;
  agentSlug?: string;
}) {
  // If agentSlug provided, show brief for that contributor
  if (agentSlug && pmIntelligence.briefs?.[agentSlug]) {
    return (
      <div className="border border-amber-200 dark:border-amber-800/50 rounded-lg p-3 bg-amber-50/50 dark:bg-amber-900/10 mt-2">
        <div className="flex items-center gap-1.5 mb-1.5">
          <Brain className="w-3.5 h-3.5 text-amber-600 dark:text-amber-400" />
          <span className="text-xs font-medium text-amber-700 dark:text-amber-400">PM Brief</span>
        </div>
        <div className="prose prose-sm dark:prose-invert max-w-none prose-p:my-1 text-xs">
          <ReactMarkdown>{pmIntelligence.briefs[agentSlug]}</ReactMarkdown>
        </div>
      </div>
    );
  }

  // Top-level quality assessment
  if (pmIntelligence.quality_assessment) {
    return (
      <div className="border border-purple-200 dark:border-purple-800/50 rounded-lg p-3 bg-purple-50/50 dark:bg-purple-900/10">
        <div className="flex items-center gap-1.5 mb-1.5">
          <ClipboardCheck className="w-3.5 h-3.5 text-purple-600 dark:text-purple-400" />
          <span className="text-xs font-medium text-purple-700 dark:text-purple-400">PM Quality Assessment</span>
        </div>
        <div className="prose prose-sm dark:prose-invert max-w-none prose-p:my-1 text-xs">
          <ReactMarkdown>{pmIntelligence.quality_assessment}</ReactMarkdown>
        </div>
      </div>
    );
  }

  return null;
}

// =============================================================================
// Main Component
// =============================================================================

type TabId = 'meeting-room' | 'outputs' | 'contributors';

export default function ProjectDetailPage() {
  const params = useParams<{ slug: string }>();
  const slug = params.slug;
  const router = useRouter();

  const [loading, setLoading] = useState(true);
  const [project, setProject] = useState<ProjectDetail | null>(null);
  const [activities, setActivities] = useState<ProjectActivityItem[]>([]);
  const [archiving, setArchiving] = useState(false);
  const [activeTab, setActiveTab] = useState<TabId>('meeting-room');
  const [objective, setObjective] = useState<{ deliverable?: string; audience?: string; format?: string; purpose?: string } | undefined>(undefined);

  const loadProject = useCallback(async () => {
    try {
      const [detail, activityData] = await Promise.all([
        api.projects.get(slug),
        api.projects.getActivity(slug, 30).catch(() => ({ activities: [], total: 0 })),
      ]);
      setProject(detail);
      setActivities(activityData.activities);
      setObjective(detail.project?.objective);
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

  const { project: meta, contributions, assemblies, pm_intelligence } = project;
  const title = meta.title || slug.replace(/-/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
  const contributors = meta.contributors || [];

  const tabs: { id: TabId; label: string; icon: React.ReactNode }[] = [
    { id: 'meeting-room', label: 'Meeting Room', icon: <MessageSquare className="w-4 h-4" /> },
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
            <EditableObjective
              slug={slug}
              objective={objective}
              onUpdate={(obj) => setObjective(obj)}
            />
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
        {activeTab === 'meeting-room' && (
          <MeetingRoomTab activities={activities} slug={slug} projectTitle={title} contributors={contributors} />
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
                pmIntelligence={pm_intelligence}
              />
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
