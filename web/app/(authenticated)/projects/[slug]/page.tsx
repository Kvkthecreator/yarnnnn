'use client';

/**
 * Project Detail Page — ADR-134 (evolves ADR-124)
 *
 * Single-surface workfloor: agents as characters, output as hero, chat as drawer.
 * No tabs — one continuous scene. Agents are your team, visible and alive.
 * Click agent → chat drawer. Gear icon → settings modal.
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { useRouter, useParams } from 'next/navigation';
import Link from 'next/link';
import ReactMarkdown from 'react-markdown';
import {
  Loader2,
  ChevronLeft,
  FolderKanban,
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
  FolderOpen,
  Folder,
  File,
  AtSign,
  BarChart3,
  Combine,
  Activity,
  Users,
  Play,
  ThumbsUp,
  ThumbsDown,
  CalendarClock,
  FileOutput,
  Settings,
} from 'lucide-react';
import { api } from '@/lib/api/client';
import { formatDistanceToNow, format } from 'date-fns';
import { cn } from '@/lib/utils';
import {
  agentDisplayName,
  roleBadgeColor,
  roleDisplayName,
  roleShortLabel,
  statusIndicator,
  authorColor as getAuthorColorFromRole,
} from '@/lib/agent-identity';
import { AgentAvatar } from '@/components/agents/AgentAvatar';
import { useTP } from '@/contexts/TPContext';
import { MessageBlocks } from '@/components/tp/InlineToolCall';
import { ToolResultList } from '@/components/tp/ToolResultCard';
import { PlusMenu, type PlusMenuAction } from '@/components/tp/PlusMenu';
import { WorkspaceLayout, type WorkspacePanelTab } from '@/components/desk/WorkspaceLayout';
import type {
  ProjectDetail,
  ProjectActivityItem,
  ProjectMember,
  OutputManifest,
  PMIntelligence,
  PMCognitiveState,
  CognitiveAssessment,
  ProjectWorkspaceFile,
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
  // ADR-126: Agent Pulse events
  agent_pulsed: {
    label: 'Pulse',
    icon: <HeartPulse className="w-4 h-4" />,
    color: 'text-cyan-500',
  },
  pm_pulsed: {
    label: 'PM Pulse',
    icon: <HeartPulse className="w-4 h-4" />,
    color: 'text-purple-500',
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
  // ADR-127: File triage events
  project_file_triaged: {
    label: 'File triaged',
    icon: <FileText className="w-4 h-4" />,
    color: 'text-blue-500',
  },
  // ADR-129: Agent lifecycle events now project-scoped
  agent_run: {
    label: 'Output',
    icon: <Play className="w-4 h-4" />,
    color: 'text-blue-500',
  },
  agent_scheduled: {
    label: 'Scheduled',
    icon: <CalendarClock className="w-4 h-4" />,
    color: 'text-blue-400',
  },
  agent_generated: {
    label: 'Generated',
    icon: <FileOutput className="w-4 h-4" />,
    color: 'text-emerald-500',
  },
  agent_approved: {
    label: 'Approved',
    icon: <ThumbsUp className="w-4 h-4" />,
    color: 'text-green-500',
  },
  agent_rejected: {
    label: 'Rejected',
    icon: <ThumbsDown className="w-4 h-4" />,
    color: 'text-red-500',
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
    case 'agent_pulsed': {
      const action = meta.action || 'sensed';
      return `Agent pulsed — ${action}${meta.reason ? `: ${meta.reason}` : ''}`;
    }
    case 'pm_pulsed': {
      const pmAction = meta.action || 'sensed';
      return `PM pulsed — ${pmAction}${meta.reason ? `: ${meta.reason}` : ''}`;
    }
    // ADR-129: Agent lifecycle events in project timeline
    case 'agent_run':
      return item.summary || 'Agent produced output';
    case 'agent_scheduled':
      return item.summary || 'Agent queued for execution';
    case 'agent_generated':
      return item.summary || 'Agent generated content';
    case 'agent_approved':
      return item.summary || 'Output approved';
    case 'agent_rejected':
      return item.summary || 'Output rejected';
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

/** Resolve display name for a message author.
 *  ADR-124: TP is implicit infrastructure in meeting rooms — never label as "Thinking Partner".
 *  Fallback to "Project Manager" since PM is the default interlocutor.
 */
function getAuthorLabel(msg: TPMessage): string {
  if (msg.role === 'user') return 'You';
  if (msg.authorName) return msg.authorName;
  if (msg.authorAgentSlug) {
    return msg.authorAgentSlug.replace(/-/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
  }
  return 'Project Manager';
}

/** Color accent per author role */
function getAuthorColor(msg: TPMessage): string {
  if (msg.role === 'user') return 'text-primary/70';
  return getAuthorColorFromRole(msg.authorRole);
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
  contributors: ProjectMember[];
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
  const [targetAgent, setTargetAgent] = useState<ProjectMember | null>(null);
  const [showMentionPicker, setShowMentionPicker] = useState(false);
  const [showShareForm, setShowShareForm] = useState(false);
  const [shareFilename, setShareFilename] = useState('');
  const [shareContent, setShareContent] = useState('');
  const [shareLoading, setShareLoading] = useState(false);
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

  const handleShareFile = async () => {
    if (!shareFilename.trim() || !shareContent.trim()) return;
    setShareLoading(true);
    try {
      await api.projects.shareFile(slug, shareFilename.trim(), shareContent);
      setShowShareForm(false);
      setShareFilename('');
      setShareContent('');
      // Notify in chat that file was shared
      sendMessage(`I shared a file: ${shareFilename.trim()}`, { surface });
    } catch {
      // Silently fail — user will see the form still open
    } finally {
      setShareLoading(false);
    }
  };

  const plusMenuActions: PlusMenuAction[] = [
    {
      id: 'mention-agent',
      label: 'Mention an agent',
      icon: AtSign,
      verb: 'prompt',
      onSelect: () => {
        setInput((prev) => prev + '@');
        setShowMentionPicker(true);
        textareaRef.current?.focus();
      },
    },
    {
      id: 'share-file',
      label: 'Share a file',
      icon: FileText,
      verb: 'prompt',
      onSelect: () => {
        setShowShareForm(true);
      },
    },
    {
      id: 'request-status',
      label: 'Request status',
      icon: BarChart3,
      verb: 'prompt',
      onSelect: () => {
        sendMessage('/status', { surface });
      },
    },
    {
      id: 'assemble',
      label: 'Assemble output',
      icon: Combine,
      verb: 'prompt',
      onSelect: () => {
        sendMessage('/assemble', { surface });
      },
    },
  ];

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

  const handleMentionSelect = (contributor: ProjectMember) => {
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
      <div className="flex-1 overflow-y-auto px-4 md:px-6 py-4 space-y-2">
        <div className="max-w-3xl mx-auto w-full space-y-2">
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
      <div className="px-4 pb-4 pt-2 shrink-0" style={{ paddingBottom: 'max(1rem, env(safe-area-inset-bottom))' }}>
        <div className="relative max-w-2xl mx-auto">
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
                  <AgentAvatar name={agentDisplayName(c.title, c.agent_slug)} role={c.role} avatarUrl={c.avatar_url} size="sm" />
                  <span className="font-medium">
                    {agentDisplayName(c.title, c.agent_slug)}
                  </span>
                  {c.role && (
                    <span className="text-xs text-muted-foreground">{roleDisplayName(c.role)}</span>
                  )}
                </button>
              ))}
            </div>
          )}

          {showShareForm && (
            <div className="mb-3 p-4 border border-border rounded-xl bg-muted/30 space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">Share a file</span>
                <button
                  type="button"
                  onClick={() => { setShowShareForm(false); setShareFilename(''); setShareContent(''); }}
                  className="text-muted-foreground hover:text-foreground"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
              <input
                type="text"
                value={shareFilename}
                onChange={(e) => setShareFilename(e.target.value)}
                placeholder="Filename (e.g., meeting-notes.md)"
                className="w-full px-3 py-2 text-sm border border-border rounded-lg bg-background focus:outline-none focus:ring-2 focus:ring-primary/50"
              />
              <textarea
                value={shareContent}
                onChange={(e) => setShareContent(e.target.value)}
                placeholder="Paste or type file content..."
                rows={5}
                className="w-full px-3 py-2 text-sm border border-border rounded-lg bg-background resize-none focus:outline-none focus:ring-2 focus:ring-primary/50"
              />
              <div className="flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => { setShowShareForm(false); setShareFilename(''); setShareContent(''); }}
                  className="px-3 py-1.5 text-sm text-muted-foreground hover:text-foreground"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={handleShareFile}
                  disabled={shareLoading || !shareFilename.trim() || !shareContent.trim()}
                  className="px-3 py-1.5 text-sm bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 disabled:opacity-50"
                >
                  {shareLoading ? 'Sharing...' : 'Share'}
                </button>
              </div>
              <p className="text-[11px] text-muted-foreground">
                File will be staged in user_shared/ for PM to triage. Expires after 30 days if not promoted.
              </p>
            </div>
          )}

          <form onSubmit={handleSubmit}>
            <div className="flex items-end gap-2 border border-border bg-background rounded-xl shadow-sm focus-within:ring-2 focus-within:ring-primary/50 focus-within:shadow-md">
              <PlusMenu actions={plusMenuActions} disabled={isLoading} />
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
                className="flex-1 py-3 pr-2 text-base sm:text-sm bg-transparent resize-none focus:outline-none disabled:opacity-50 max-h-[200px]"
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

          <div className="mt-1.5 flex items-center justify-between text-[10px] text-muted-foreground/60">
            <span className="hidden sm:inline">Enter to send, Shift+Enter for new line</span>
            <span className="sm:hidden">Tap send or use keyboard Send</span>
          </div>
        </div>
      </div>
    </div>
  );
}

// =============================================================================
// ADR-124 Phase 4: Context Tab — Workspace File Browser
// =============================================================================

/** Build a tree structure from flat file paths */
interface TreeNode {
  name: string;
  path: string;
  isFolder: boolean;
  children: TreeNode[];
  file?: ProjectWorkspaceFile;
}

function buildFileTree(files: ProjectWorkspaceFile[]): TreeNode[] {
  const root: TreeNode[] = [];

  for (const f of files) {
    const parts = f.relative_path.split('/').filter(Boolean);
    let current = root;

    for (let i = 0; i < parts.length; i++) {
      const part = parts[i];
      const isLast = i === parts.length - 1;
      let existing = current.find(n => n.name === part);

      if (!existing) {
        existing = {
          name: part,
          path: parts.slice(0, i + 1).join('/'),
          isFolder: !isLast,
          children: [],
          file: isLast ? f : undefined,
        };
        current.push(existing);
      }

      if (!isLast) {
        existing.isFolder = true;
        current = existing.children;
      }
    }
  }

  // Sort: folders first, then alphabetical
  const sortNodes = (nodes: TreeNode[]) => {
    nodes.sort((a, b) => {
      if (a.isFolder !== b.isFolder) return a.isFolder ? -1 : 1;
      return a.name.localeCompare(b.name);
    });
    nodes.forEach(n => sortNodes(n.children));
  };
  sortNodes(root);

  return root;
}

function FileTreeNode({
  node,
  depth,
  selectedPath,
  onSelect,
}: {
  node: TreeNode;
  depth: number;
  selectedPath: string | null;
  onSelect: (path: string) => void;
}) {
  const [expanded, setExpanded] = useState(depth < 2);

  if (node.isFolder) {
    return (
      <div>
        <button
          onClick={() => setExpanded(!expanded)}
          className="w-full flex items-center gap-1.5 py-1 px-2 text-left text-sm hover:bg-muted/50 rounded transition-colors"
          style={{ paddingLeft: `${depth * 16 + 8}px` }}
        >
          {expanded ? (
            <ChevronDown className="w-3 h-3 text-muted-foreground shrink-0" />
          ) : (
            <ChevronRight className="w-3 h-3 text-muted-foreground shrink-0" />
          )}
          {expanded ? (
            <FolderOpen className="w-3.5 h-3.5 text-amber-500 shrink-0" />
          ) : (
            <Folder className="w-3.5 h-3.5 text-amber-500 shrink-0" />
          )}
          <span className="font-medium truncate">{node.name}</span>
        </button>
        {expanded && node.children.map((child) => (
          <FileTreeNode
            key={child.path}
            node={child}
            depth={depth + 1}
            selectedPath={selectedPath}
            onSelect={onSelect}
          />
        ))}
      </div>
    );
  }

  return (
    <button
      onClick={() => onSelect(node.file?.relative_path || node.path)}
      className={cn(
        'w-full flex items-center gap-1.5 py-1 px-2 text-left text-sm rounded transition-colors',
        selectedPath === (node.file?.relative_path || node.path)
          ? 'bg-primary/10 text-primary'
          : 'hover:bg-muted/50'
      )}
      style={{ paddingLeft: `${depth * 16 + 8}px` }}
    >
      <File className="w-3.5 h-3.5 text-muted-foreground shrink-0" />
      <span className="truncate">{node.name}</span>
      {node.file?.updated_at && (
        <span className="ml-auto text-[10px] text-muted-foreground shrink-0">
          {formatDistanceToNow(new Date(node.file.updated_at), { addSuffix: true })}
        </span>
      )}
    </button>
  );
}

function ContextTab({ slug }: { slug: string }) {
  const [files, setFiles] = useState<ProjectWorkspaceFile[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedPath, setSelectedPath] = useState<string | null>(null);
  const [fileContent, setFileContent] = useState<string | null>(null);
  const [contentLoading, setContentLoading] = useState(false);

  useEffect(() => {
    api.projects.getFiles(slug).then((res) => {
      setFiles(res.files);
    }).catch(() => {}).finally(() => setLoading(false));
  }, [slug]);

  const handleSelect = async (path: string) => {
    if (selectedPath === path) {
      setSelectedPath(null);
      setFileContent(null);
      return;
    }
    setSelectedPath(path);
    setContentLoading(true);
    try {
      const res = await api.projects.getFileContent(slug, path);
      setFileContent(res.content);
    } catch {
      setFileContent('Failed to load file content.');
    } finally {
      setContentLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="w-5 h-5 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (files.length === 0) {
    return (
      <div className="text-center py-12">
        <FolderOpen className="w-8 h-8 text-muted-foreground/20 mx-auto mb-3" />
        <p className="text-sm text-muted-foreground">No workspace files yet — files will appear here as agents contribute.</p>
      </div>
    );
  }

  const tree = buildFileTree(files);

  return (
    <div className="flex h-full">
      {/* File tree sidebar */}
      <div className={cn(
        'border-r border-border overflow-y-auto py-2',
        selectedPath ? 'w-64 shrink-0' : 'w-full max-w-md mx-auto'
      )}>
        <div className="px-3 pb-2 mb-1 border-b border-border">
          <p className="text-xs text-muted-foreground">
            {files.length} file{files.length !== 1 ? 's' : ''} in /projects/{slug}/
          </p>
        </div>
        {tree.map((node) => (
          <FileTreeNode
            key={node.path}
            node={node}
            depth={0}
            selectedPath={selectedPath}
            onSelect={handleSelect}
          />
        ))}
      </div>

      {/* File content preview */}
      {selectedPath && (
        <div className="flex-1 min-w-0 overflow-y-auto">
          <div className="px-4 py-2 border-b border-border bg-muted/30 flex items-center gap-2">
            <FileText className="w-3.5 h-3.5 text-muted-foreground shrink-0" />
            <span className="text-xs font-mono text-muted-foreground truncate">{selectedPath}</span>
            <button
              onClick={() => { setSelectedPath(null); setFileContent(null); }}
              className="ml-auto text-muted-foreground hover:text-foreground transition-colors shrink-0"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
          {contentLoading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="w-4 h-4 animate-spin text-muted-foreground" />
            </div>
          ) : fileContent ? (
            <div className="p-4">
              <div className="prose prose-sm dark:prose-invert max-w-none prose-p:my-1 prose-headings:mt-3 prose-headings:mb-1">
                <ReactMarkdown>{fileContent}</ReactMarkdown>
              </div>
            </div>
          ) : null}
        </div>
      )}
    </div>
  );
}

function OutputsTab({ slug }: { slug: string }) {
  const [outputs, setOutputs] = useState<OutputManifest[]>([]);
  const [loading, setLoading] = useState(true);
  const [expandedFolder, setExpandedFolder] = useState<string | null>(null);
  const [previewContent, setPreviewContent] = useState<string | null>(null);
  const [composedHtml, setComposedHtml] = useState<string | null>(null);
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
    setComposedHtml(null);
    try {
      const detail = await api.projects.getOutput(slug, folder);
      setPreviewContent(detail.content);
      // ADR-130 Phase 2: Prefer composed HTML when available
      if (detail.composed_html) {
        setComposedHtml(detail.composed_html);
      }
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

              {/* Output preview — composed HTML (ADR-130) or markdown fallback */}
              {previewLoading ? (
                <div className="flex items-center gap-2 text-muted-foreground text-xs py-2">
                  <Loader2 className="w-3 h-3 animate-spin" />
                  Loading preview...
                </div>
              ) : composedHtml ? (
                <div className="border border-border rounded-lg overflow-hidden max-h-[32rem] overflow-y-auto">
                  <iframe
                    srcDoc={composedHtml}
                    className="w-full min-h-[20rem]"
                    style={{ border: 'none', height: '100%' }}
                    sandbox="allow-same-origin"
                    title="Composed output"
                  />
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

// =============================================================================
// Participants Sidebar — compact list for Meeting Room panel
// =============================================================================

function ParticipantsSidebar({
  members,
  contributionCounts,
  slug,
  pmIntelligence,
}: {
  members: ProjectMember[];
  contributionCounts: Record<string, number>;
  slug: string;
  pmIntelligence?: PMIntelligence | null;
}) {
  const [selectedMember, setSelectedMember] = useState<ProjectMember | null>(null);

  // Sort: PM first, then by role
  const sorted = [...members].sort((a, b) => {
    if (a.role === 'pm' && b.role !== 'pm') return -1;
    if (b.role === 'pm' && a.role !== 'pm') return 1;
    return 0;
  });

  return (
    <div className="flex flex-col h-full">
      {/* Participant list */}
      <div className={cn(
        'overflow-y-auto',
        selectedMember ? 'shrink-0 max-h-[40%]' : 'flex-1',
      )}>
        <div className="px-3 py-2">
          <div className="space-y-0.5">
            {sorted.map((m) => {
              const name = agentDisplayName(m.title, m.agent_slug);
              const isSelected = selectedMember?.agent_slug === m.agent_slug;

              return (
                <button
                  key={m.agent_slug}
                  onClick={() => setSelectedMember(isSelected ? null : m)}
                  className={cn(
                    'w-full flex items-center gap-3 px-2 py-2 rounded-lg transition-colors text-left',
                    isSelected ? 'bg-muted' : 'hover:bg-muted/50',
                  )}
                >
                  <AgentAvatar
                    name={name}
                    role={m.role}
                    avatarUrl={m.avatar_url}
                    size="md"
                    status={m.status}
                  />
                  <div className="flex-1 min-w-0">
                    <span className="text-sm font-medium truncate block">{name}</span>
                  </div>
                  {m.role && (
                    <span className={cn('text-[9px] font-medium px-1 py-0.5 rounded-full shrink-0', roleBadgeColor(m.role))}>
                      {roleShortLabel(m.role)}
                    </span>
                  )}
                </button>
              );
            })}
          </div>
        </div>
      </div>

      {/* Inline profile card — shown below list when a member is selected */}
      {selectedMember && (
        <div className="flex-1 min-h-0 overflow-y-auto border-t border-border">
          <InlineProfileCard
            member={selectedMember}
            contributionCount={contributionCounts[selectedMember.agent_slug] || 0}
            slug={slug}
            pmIntelligence={pmIntelligence}
            onClose={() => setSelectedMember(null)}
          />
        </div>
      )}
    </div>
  );
}

/** Inline profile card — identity-first agent display */
function InlineProfileCard({
  member,
  contributionCount,
  slug,
  pmIntelligence,
  onClose,
}: {
  member: ProjectMember;
  contributionCount: number;
  slug: string;
  pmIntelligence?: PMIntelligence | null;
  onClose: () => void;
}) {
  const name = agentDisplayName(member.title, member.agent_slug);
  const si = statusIndicator(member.status);

  return (
    <div className="px-3 py-3 space-y-3">
      {/* Identity header */}
      <div className="flex items-start gap-3">
        <AgentAvatar
          name={name}
          role={member.role}
          avatarUrl={member.avatar_url}
          size="lg"
          status={member.status}
        />
        <div className="flex-1 min-w-0">
          <h3 className="text-sm font-semibold truncate">{name}</h3>
          <div className="flex items-center gap-1.5 mt-0.5 flex-wrap">
            {member.role && (
              <span className={cn('text-[9px] font-medium px-1.5 py-0.5 rounded-full', roleBadgeColor(member.role))}>
                {roleDisplayName(member.role)}
              </span>
            )}
            <span className="flex items-center gap-1 text-[10px] text-muted-foreground">
              <span className={cn('w-1.5 h-1.5 rounded-full', si.color)} />
              {si.label}
            </span>
          </div>
        </div>
        <button onClick={onClose} className="text-muted-foreground hover:text-foreground transition-colors shrink-0">
          <X className="w-3.5 h-3.5" />
        </button>
      </div>

      {/* Bio — what this agent is (from AGENT.md) */}
      {member.bio && (
        <p className="text-[11px] text-foreground/80 leading-relaxed">{member.bio}</p>
      )}

      {/* Track record */}
      {member.total_runs != null && member.total_runs > 0 && (
        <div className="flex items-center gap-3 text-[11px]">
          <span className="text-muted-foreground">
            {member.total_runs} run{member.total_runs !== 1 ? 's' : ''}
          </span>
          {member.approval_rate != null && (
            <span className="text-muted-foreground">
              {member.approval_rate}% approved
            </span>
          )}
        </div>
      )}

      {/* ADR-128 Phase 6: Cognitive state — self-assessment + trajectory */}
      {member.role !== 'pm' && member.cognitive_state && (
        <div className="bg-muted/40 rounded-lg px-2.5 py-2 space-y-2">
          <p className="text-[10px] font-medium text-muted-foreground">Self-assessment (latest)</p>
          <div className="space-y-1">
            {member.cognitive_state.mandate && (
              <div className="flex items-center gap-2 text-[10px]">
                <span className="w-[50px] text-muted-foreground text-right">Mandate</span>
                <span className={cn('font-medium', LEVEL_CONFIG[member.cognitive_state.mandate.level].text)}>
                  {member.cognitive_state.mandate.level}
                </span>
                {member.cognitive_state.mandate.reason && member.cognitive_state.mandate.level !== 'high' && (
                  <span className="text-muted-foreground truncate">— {member.cognitive_state.mandate.reason}</span>
                )}
              </div>
            )}
            {member.cognitive_state.fitness && (
              <div className="flex items-center gap-2 text-[10px]">
                <span className="w-[50px] text-muted-foreground text-right">Fitness</span>
                <span className={cn('font-medium', LEVEL_CONFIG[member.cognitive_state.fitness.level].text)}>
                  {member.cognitive_state.fitness.level}
                </span>
                {member.cognitive_state.fitness.reason && member.cognitive_state.fitness.level !== 'high' && (
                  <span className="text-muted-foreground truncate">— {member.cognitive_state.fitness.reason}</span>
                )}
              </div>
            )}
            {member.cognitive_state.currency && (
              <div className="flex items-center gap-2 text-[10px]">
                <span className="w-[50px] text-muted-foreground text-right">Context</span>
                <span className={cn('font-medium', LEVEL_CONFIG[member.cognitive_state.currency.level].text)}>
                  {member.cognitive_state.currency.level}
                </span>
                {member.cognitive_state.currency.reason && member.cognitive_state.currency.level !== 'high' && (
                  <span className="text-muted-foreground truncate">— {member.cognitive_state.currency.reason}</span>
                )}
              </div>
            )}
            {member.cognitive_state.confidence && (
              <div className="flex items-center gap-2 text-[10px]">
                <span className="w-[50px] text-muted-foreground text-right">Output</span>
                <span className={cn('font-medium', LEVEL_CONFIG[member.cognitive_state.confidence.level].text)}>
                  {member.cognitive_state.confidence.level}
                </span>
                {member.cognitive_state.confidence.reason && member.cognitive_state.confidence.level !== 'high' && (
                  <span className="text-muted-foreground truncate">— {member.cognitive_state.confidence.reason}</span>
                )}
              </div>
            )}
          </div>
          {/* Confidence trajectory sparkline — last 5 runs */}
          {member.cognitive_state.confidence_trajectory && member.cognitive_state.confidence_trajectory.length > 1 && (
            <div className="flex items-center gap-1.5 pt-0.5">
              <span className="text-[9px] text-muted-foreground">Trend</span>
              <div className="flex items-center gap-0.5">
                {member.cognitive_state.confidence_trajectory.map((level, i) => (
                  <span
                    key={i}
                    className={cn(
                      'w-2 h-2 rounded-sm',
                      level === 'high' && 'bg-green-500/70',
                      level === 'medium' && 'bg-amber-500/60',
                      level === 'low' && 'bg-red-500/50',
                    )}
                  />
                ))}
              </div>
              <span className="text-[9px] text-muted-foreground">({member.cognitive_state.confidence_trajectory.length} runs)</span>
            </div>
          )}
        </div>
      )}

      {/* Current thesis — what the agent currently thinks */}
      {member.thesis_snippet && (
        <div className="bg-muted/40 rounded-lg px-2.5 py-2">
          <p className="text-[10px] font-medium text-muted-foreground mb-0.5">Current thesis</p>
          <p className="text-[11px] text-foreground/70 italic leading-relaxed">{member.thesis_snippet}</p>
        </div>
      )}

      {/* Last active */}
      {member.last_run_at && (
        <p className="text-[10px] text-muted-foreground">
          Last active {formatDistanceToNow(new Date(member.last_run_at), { addSuffix: true })}
        </p>
      )}

      {/* PM brief — what the PM wants from this agent */}
      {pmIntelligence?.briefs?.[member.agent_slug] && (
        <PMIntelligencePanel pmIntelligence={pmIntelligence} agentSlug={member.agent_slug} />
      )}

      {/* Contributions — compact count, not full file list */}
      {contributionCount > 0 && (
        <div className="flex items-center gap-1.5 text-[11px] text-muted-foreground">
          <FileText className="w-3 h-3" />
          <span>{contributionCount} contribution{contributionCount !== 1 ? 's' : ''}</span>
        </div>
      )}

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
// ADR-124 Phase 5: Settings Tab — consolidated project configuration
// =============================================================================

function SettingsTab({
  slug,
  project,
  objective,
  onUpdateObjective,
  onArchive,
  archiving,
}: {
  slug: string;
  project: ProjectDetail['project'];
  objective?: { deliverable?: string; audience?: string; format?: string; purpose?: string };
  onUpdateObjective: (obj: { deliverable?: string; audience?: string; format?: string; purpose?: string }) => void;
  onArchive: () => void;
  archiving: boolean;
}) {
  return (
    <div className="max-w-5xl mx-auto px-4 md:px-6 py-6 space-y-8">
      {/* Objective */}
      <section>
        <h3 className="text-sm font-semibold mb-2">Objective</h3>
        <EditableObjective
          slug={slug}
          objective={objective}
          onUpdate={onUpdateObjective}
        />
      </section>

      {/* Assembly Spec */}
      <section>
        <h3 className="text-sm font-semibold mb-2">Assembly Configuration</h3>
        {project.assembly_spec ? (
          <div className="text-sm bg-muted/30 rounded-lg p-3 border border-border">
            <div className="prose prose-sm dark:prose-invert max-w-none prose-p:my-1">
              <ReactMarkdown>{project.assembly_spec}</ReactMarkdown>
            </div>
          </div>
        ) : (
          <p className="text-sm text-muted-foreground">No assembly configuration set. The PM will define how outputs are combined.</p>
        )}
      </section>

      {/* Delivery */}
      <section>
        <h3 className="text-sm font-semibold mb-2">Delivery</h3>
        {project.delivery && Object.keys(project.delivery).length > 0 ? (
          <div className="text-sm space-y-1">
            {Object.entries(project.delivery).map(([key, value]) => {
              const labels: Record<string, string> = {
                channel: 'Channel',
                target: 'Recipient',
                cadence: 'Delivery cadence',
                format: 'Format',
              };
              return (
                <div key={key} className="flex items-center gap-2">
                  <span className="text-muted-foreground">{labels[key] || key}:</span>
                  <span>{String(value)}</span>
                </div>
              );
            })}
          </div>
        ) : (
          <p className="text-sm text-muted-foreground">No delivery preferences configured.</p>
        )}
        <p className="text-xs text-muted-foreground mt-2">
          Agents produce outputs. The project delivers to you on the configured cadence.
        </p>
      </section>

      {/* Danger Zone */}
      <section className="border-t border-border pt-6">
        <h3 className="text-sm font-semibold text-destructive mb-2">Danger Zone</h3>
        <button
          onClick={onArchive}
          disabled={archiving}
          className="flex items-center gap-1.5 text-sm text-destructive hover:text-destructive/80 transition-colors border border-destructive/30 rounded-lg px-3 py-2 hover:bg-destructive/5"
        >
          {archiving ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Archive className="w-3.5 h-3.5" />}
          Archive this project
        </button>
        <p className="text-xs text-muted-foreground mt-1.5">
          Archiving hides the project from the active list. Files are preserved.
        </p>
      </section>
    </div>
  );
}

// =============================================================================
// ADR-126: Workfloor — Agent Pulse Visualization
// =============================================================================

type PulseDecision = 'generate' | 'observe' | 'wait' | 'escalate';

const PULSE_DECISION_CONFIG: Record<PulseDecision, { label: string; color: string; bgColor: string }> = {
  generate: { label: 'Generating', color: 'text-green-600 dark:text-green-400', bgColor: 'bg-green-500' },
  observe: { label: 'Observing', color: 'text-blue-600 dark:text-blue-400', bgColor: 'bg-blue-500' },
  wait: { label: 'Waiting', color: 'text-muted-foreground', bgColor: 'bg-gray-400' },
  escalate: { label: 'Needs attention', color: 'text-amber-600 dark:text-amber-400', bgColor: 'bg-amber-500' },
};

// ADR-128 Phase 6: Cognitive assessment bar for contributor cards
const LEVEL_CONFIG = {
  high: { width: 'w-[80%]', color: 'bg-green-500/60', text: 'text-green-600 dark:text-green-400' },
  medium: { width: 'w-[55%]', color: 'bg-amber-500/60', text: 'text-amber-600 dark:text-amber-400' },
  low: { width: 'w-[30%]', color: 'bg-red-500/50', text: 'text-red-600 dark:text-red-400' },
};

function CognitiveBar({ label, level, reason }: { label: string; level: 'high' | 'medium' | 'low'; reason?: string }) {
  const config = LEVEL_CONFIG[level];
  return (
    <div className="flex items-center gap-2 text-[10px]">
      <span className="w-[52px] text-muted-foreground shrink-0 text-right">{label}</span>
      <div className="flex-1 h-1.5 bg-muted rounded-full overflow-hidden">
        <div className={cn('h-full rounded-full transition-all', config.width, config.color)} />
      </div>
      <span className={cn('shrink-0', config.text)}>{level}</span>
      {reason && level !== 'high' && (
        <span className="text-muted-foreground truncate max-w-[140px]">— {reason}</span>
      )}
    </div>
  );
}

// ADR-128 Phase 6: PM 5-layer constraint indicator
const LAYER_LABELS = ['Commitment', 'Structure', 'Context', 'Quality', 'Readiness'] as const;
const LAYER_KEYS = ['commitment', 'structure', 'context', 'quality', 'readiness'] as const;

function PMLayers({ state }: { state: PMCognitiveState }) {
  return (
    <div className="mt-1.5 space-y-1">
      <div className="flex items-center gap-1 flex-wrap">
        {LAYER_KEYS.map((key, i) => {
          const status = state.layers[key];
          return (
            <span
              key={key}
              className={cn(
                'text-[9px] font-medium px-1 py-0.5 rounded',
                status === 'satisfied' && 'text-green-600 dark:text-green-400',
                status === 'broken' && 'text-red-600 dark:text-red-400 bg-red-500/10',
                status === 'unknown' && 'text-muted-foreground/40',
              )}
            >
              {status === 'satisfied' ? '✓' : status === 'broken' ? '✗' : '·'} {LAYER_LABELS[i]}
            </span>
          );
        })}
      </div>
      {state.constraint_summary && (
        <p className="text-[10px] text-muted-foreground italic leading-relaxed truncate">
          {state.constraint_summary}
        </p>
      )}
    </div>
  );
}

function CognitiveCards({ cognitive }: { cognitive: CognitiveAssessment }) {
  // If all 4 dimensions are high, show compressed state
  const allHealthy = (
    cognitive.mandate?.level === 'high' &&
    cognitive.fitness?.level === 'high' &&
    cognitive.currency?.level === 'high' &&
    cognitive.confidence?.level === 'high'
  );

  if (allHealthy) {
    return (
      <div className="mt-1.5 flex items-center gap-1 text-[10px] text-green-600 dark:text-green-400">
        <Check className="w-3 h-3" />
        <span>All dimensions healthy</span>
      </div>
    );
  }

  return (
    <div className="mt-1.5 space-y-0.5">
      {cognitive.mandate && <CognitiveBar label="Mandate" level={cognitive.mandate.level} reason={cognitive.mandate.reason} />}
      {cognitive.fitness && <CognitiveBar label="Fitness" level={cognitive.fitness.level} reason={cognitive.fitness.reason} />}
      {cognitive.currency && <CognitiveBar label="Context" level={cognitive.currency.level} reason={cognitive.currency.reason} />}
      {cognitive.confidence && <CognitiveBar label="Output" level={cognitive.confidence.level} reason={cognitive.confidence.reason} />}
    </div>
  );
}

function WorkfloorView({
  members,
  activities,
  slug,
  pmCognitiveState,
  onAgentClick,
}: {
  members: ProjectMember[];
  activities: ProjectActivityItem[];
  slug: string;
  pmCognitiveState?: PMCognitiveState | null;
  onAgentClick?: (agentSlug: string) => void;
}) {
  // Derive latest pulse state per agent from activity events
  const agentPulseState = useCallback(() => {
    const states: Record<string, { decision: PulseDecision; reason?: string; timestamp: string }> = {};
    for (const a of activities) {
      if (a.event_type === 'agent_pulsed' || a.event_type === 'pm_pulsed') {
        const agentSlug = a.metadata?.agent_slug as string | undefined;
        const decision = (a.metadata?.action as string || 'observe') as PulseDecision;
        if (agentSlug) {
          states[agentSlug] = {
            decision,
            reason: a.metadata?.reason as string | undefined,
            timestamp: a.created_at,
          };
        }
      }
    }
    return states;
  }, [activities]);

  const pulseStates = agentPulseState();

  // Sort: PM first, then by role
  const sorted = [...members].sort((a, b) => {
    if (a.role === 'pm' && b.role !== 'pm') return -1;
    if (b.role === 'pm' && a.role !== 'pm') return 1;
    return 0;
  });

  // Build a "thought" for each agent — what they're currently doing/thinking
  const getAgentThought = (m: ProjectMember, pulse: { decision: PulseDecision; reason?: string; timestamp: string } | undefined) => {
    const isPM = m.role === 'pm';

    // Active pulse state — use reason as the thought
    if (pulse?.reason) {
      return pulse.reason;
    }
    if (pulse?.decision === 'generate') {
      return isPM ? 'Coordinating assembly...' : 'Working on the next output...';
    }
    if (pulse?.decision === 'observe') {
      return isPM ? 'Monitoring contributor state...' : 'Watching for new signals...';
    }
    if (pulse?.decision === 'wait') {
      return 'Waiting for the right moment...';
    }
    if (pulse?.decision === 'escalate') {
      return 'Something needs attention.';
    }

    // No pulse — use last activity
    if (m.last_run_at) {
      return `Last active ${formatDistanceToNow(new Date(m.last_run_at), { addSuffix: true })}`;
    }
    return 'Getting ready...';
  };

  // PM has actionable layers?
  const pmHasAssessment = pmCognitiveState &&
    !Object.values(pmCognitiveState.layers).every(v => v === 'unknown');

  return (
    <div className="flex flex-col h-full">
      <div className="flex-1 overflow-y-auto p-4 md:p-6">
        <div className="max-w-4xl mx-auto">
          {sorted.length === 0 ? (
            <div className="text-center py-16">
              <Activity className="w-12 h-12 text-muted-foreground/15 mx-auto mb-4" />
              <p className="text-sm text-muted-foreground">No agents on the workfloor yet.</p>
            </div>
          ) : (
            <>
              {/* Agent cards — avatar-centered, Sims-inspired */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {sorted.map((m) => {
                  const name = agentDisplayName(m.title, m.agent_slug);
                  const pulse = pulseStates[m.agent_slug];
                  const decisionConfig = pulse
                    ? PULSE_DECISION_CONFIG[pulse.decision] || PULSE_DECISION_CONFIG.wait
                    : null;
                  const isPM = m.role === 'pm';
                  const thought = getAgentThought(m, pulse);

                  return (
                    <div
                      key={m.agent_slug}
                      onClick={() => onAgentClick?.(m.agent_slug)}
                      className="group relative flex flex-col items-center p-5 rounded-2xl border border-border bg-background hover:bg-muted/20 transition-all cursor-pointer"
                    >
                      {/* Pulse indicator — top-right corner */}
                      {decisionConfig && (
                        <div className="absolute top-3 right-3 flex items-center gap-1">
                          <span className={cn('w-2 h-2 rounded-full', decisionConfig.bgColor)} />
                          <span className={cn('text-[10px] font-medium', decisionConfig.color)}>
                            {decisionConfig.label}
                          </span>
                        </div>
                      )}

                      {/* Avatar — centered, large, with pulse ring */}
                      <div className="relative mb-3">
                        <AgentAvatar
                          name={name}
                          role={m.role}
                          avatarUrl={m.avatar_url}
                          size="lg"
                          status={m.status}
                        />
                        {/* Pulse ring for generating */}
                        {pulse?.decision === 'generate' && (
                          <span className="absolute inset-0 rounded-full border-2 border-green-500/30 animate-ping" />
                        )}
                        {/* Subtle breathing for observing */}
                        {pulse?.decision === 'observe' && (
                          <span className="absolute inset-0 rounded-full border-2 border-blue-500/20 animate-pulse" />
                        )}
                      </div>

                      {/* Name + role */}
                      <div className="flex items-center gap-1.5 mb-1">
                        <span className="text-sm font-semibold">{name}</span>
                        {m.role && (
                          <span className={cn('text-[9px] font-medium px-1.5 py-0.5 rounded-full', roleBadgeColor(m.role))}>
                            {roleShortLabel(m.role)}
                          </span>
                        )}
                      </div>

                      {/* Thought bubble — what the agent is thinking/doing */}
                      <p className="text-[11px] text-muted-foreground text-center leading-relaxed max-w-[200px] mb-2 italic">
                        &ldquo;{thought}&rdquo;
                      </p>

                      {/* Cognitive state — contributors get bars, PM gets layers */}
                      {isPM && pmHasAssessment && pmCognitiveState && (
                        <div className="w-full mt-1">
                          <PMLayers state={pmCognitiveState} />
                        </div>
                      )}
                      {!isPM && m.cognitive_state && (
                        <div className="w-full mt-1">
                          <CognitiveCards cognitive={m.cognitive_state} />
                        </div>
                      )}

                      {/* Timestamp — subtle bottom */}
                      {pulse?.timestamp && (
                        <span className="text-[9px] text-muted-foreground/50 mt-2">
                          {format(new Date(pulse.timestamp), 'h:mm a')}
                        </span>
                      )}
                    </div>
                  );
                })}
              </div>

              {/* Recent activity timeline */}
              {activities.filter(a => a.event_type === 'agent_pulsed' || a.event_type === 'pm_pulsed').length > 0 && (
                <div className="mt-8 border-t border-border pt-4">
                  <p className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground/60 mb-3">Recent Activity</p>
                  <div className="space-y-1.5">
                    {activities
                      .filter(a => a.event_type === 'agent_pulsed' || a.event_type === 'pm_pulsed')
                      .slice(-8)
                      .reverse()
                      .map((a) => {
                        const config = ACTIVITY_EVENT_CONFIG[a.event_type];
                        return (
                          <div key={a.id} className="flex items-start gap-2 py-1">
                            <span className={cn('mt-0.5 shrink-0', config?.color || 'text-muted-foreground')}>
                              {config?.icon || <HeartPulse className="w-3.5 h-3.5" />}
                            </span>
                            <div className="flex-1 min-w-0">
                              <p className="text-xs">{formatActivitySummary(a)}</p>
                            </div>
                            <span className="text-[10px] text-muted-foreground shrink-0">
                              {format(new Date(a.created_at), 'h:mm a')}
                            </span>
                          </div>
                        );
                      })}
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}

// =============================================================================
// =============================================================================
// Main Component — ADR-134: Single-surface workfloor with chat drawer
// =============================================================================

export default function ProjectDetailPage() {
  const params = useParams<{ slug: string }>();
  const slug = params.slug;
  const router = useRouter();

  const [loading, setLoading] = useState(true);
  const [project, setProject] = useState<ProjectDetail | null>(null);
  const [activities, setActivities] = useState<ProjectActivityItem[]>([]);
  const [archiving, setArchiving] = useState(false);
  const [objective, setObjective] = useState<{ deliverable?: string; audience?: string; format?: string; purpose?: string } | undefined>(undefined);
  // ADR-134: Chat drawer state — one conversation, @-mention routes to agent
  const [chatOpen, setChatOpen] = useState(false);
  const [mentionAgent, setMentionAgent] = useState<string | null>(null); // pre-fill @-mention
  // ADR-134: Settings modal state
  const [settingsOpen, setSettingsOpen] = useState(false);

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

  const { project: meta, contribution_counts, assembly_count, pm_intelligence, project_cognitive_state } = project;
  const title = meta.title || slug.replace(/-/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
  const members = meta.contributors || [];

  // ADR-134: Phase state + work plan from API
  const phaseState = (project as any).phase_state as { current_phase?: string; phases?: Record<string, { status: string }> } | null;
  const workPlan = (project as any).work_plan as string | null;
  const latestOutput = (project as any).latest_output as { folder: string; content: string; composed_html?: string } | null;
  const phases = phaseState?.phases || {};
  const phaseNames = Object.keys(phases);
  const currentPhase = phaseState?.current_phase || '';

  return (
    <div className="h-full flex flex-col bg-background">
      {/* ── PROJECT HEADER ── */}
      <div className="border-b border-border px-4 py-2.5 shrink-0">
        <div className="flex items-center gap-3">
          <Link href="/projects" className="text-muted-foreground hover:text-foreground transition-colors">
            <ChevronLeft className="w-4 h-4" />
          </Link>
          <h1 className="text-sm font-semibold truncate">{title}</h1>
          {/* Phase stepper */}
          {phaseNames.length > 0 && (
            <div className="hidden md:flex items-center gap-1 text-[10px] ml-2">
              {phaseNames.map((name, i) => {
                const status = phases[name]?.status || 'pending';
                const isCurrent = name === currentPhase;
                return (
                  <span key={name} className="flex items-center gap-0.5">
                    {i > 0 && <span className="text-muted-foreground mx-0.5">→</span>}
                    <span className={cn(
                      'px-1.5 py-0.5 rounded',
                      status === 'complete' ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400' :
                      isCurrent ? 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400 font-medium' :
                      'bg-muted text-muted-foreground'
                    )}>
                      {name.replace(/^Phase \d+:\s*/, '')}
                    </span>
                  </span>
                );
              })}
            </div>
          )}
          <button
            onClick={() => setSettingsOpen(true)}
            className="p-1.5 rounded-md text-muted-foreground hover:text-foreground hover:bg-muted transition-colors ml-auto"
          >
            <Settings className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* ── MAIN: Chat (left) + Context Panel (right) ── */}
      <div className="flex-1 flex overflow-hidden">

        {/* LEFT: Chat / Meeting Room (primary surface) */}
        <div className="flex-1 flex flex-col min-w-0">
          <MeetingRoomTab
            activities={activities}
            slug={slug}
            projectTitle={title}
            contributors={members}
          />
        </div>

        {/* RIGHT: Context Panel — objective → output → team → files */}
        <div className="w-[340px] lg:w-[380px] border-l border-border overflow-y-auto shrink-0 hidden md:block">

          {/* 1. Objective */}
          <div className="px-3 py-3 border-b border-border">
            <p className="text-[10px] font-medium text-muted-foreground uppercase tracking-wider mb-1.5">Objective</p>
            {objective?.deliverable ? (
              <div className="space-y-1 text-xs">
                <p className="text-foreground font-medium">{objective.deliverable}</p>
                {objective.audience && <p className="text-muted-foreground">For: {objective.audience}</p>}
                {objective.purpose && <p className="text-muted-foreground">{objective.purpose}</p>}
              </div>
            ) : (
              <p className="text-xs text-muted-foreground italic">No objective set — refine in settings</p>
            )}
          </div>

          {/* 2. Latest Output */}
          <div className="px-3 py-3 border-b border-border">
            <p className="text-[10px] font-medium text-muted-foreground uppercase tracking-wider mb-1.5">Latest Output</p>
            {latestOutput?.composed_html ? (
              <div className="border border-border rounded-lg overflow-hidden">
                <iframe
                  srcDoc={latestOutput.composed_html}
                  className="w-full"
                  style={{ border: 'none', minHeight: '200px', height: '30vh' }}
                  sandbox="allow-same-origin"
                  title="Latest output"
                />
              </div>
            ) : latestOutput?.content ? (
              <div className="border border-border rounded-lg p-2.5 bg-muted/20 max-h-48 overflow-y-auto">
                <div className="prose prose-xs dark:prose-invert max-w-none">
                  <ReactMarkdown>{latestOutput.content}</ReactMarkdown>
                </div>
              </div>
            ) : (
              <p className="text-xs text-muted-foreground italic">No outputs yet</p>
            )}
            {assembly_count > 1 && (
              <button className="text-[10px] text-primary hover:underline mt-1.5">
                View {assembly_count} previous outputs
              </button>
            )}
          </div>

          {/* 3. Team — compact workfloor cards */}
          <div className="px-3 py-3 border-b border-border">
            <p className="text-[10px] font-medium text-muted-foreground uppercase tracking-wider mb-2">Team ({members.length})</p>
            <div className="space-y-2">
              {members.map((m) => {
                const name = agentDisplayName(m.title, m.agent_slug);
                const isPM = m.role === 'pm';
                return (
                  <div key={m.agent_slug} className="flex items-center gap-2.5 group">
                    <AgentAvatar
                      name={name}
                      role={m.role}
                      avatarUrl={m.avatar_url}
                      size="sm"
                      status={m.status}
                    />
                    <div className="flex-1 min-w-0">
                      <p className="text-xs font-medium truncate">{name}</p>
                      <p className="text-[10px] text-muted-foreground">{roleDisplayName(m.role)}</p>
                    </div>
                    {m.total_runs != null && m.total_runs > 0 && (
                      <span className="text-[10px] text-muted-foreground shrink-0">{m.total_runs} runs</span>
                    )}
                  </div>
                );
              })}
            </div>
          </div>

          {/* 4. Work Plan (if exists) */}
          {workPlan && (
            <div className="px-3 py-3 border-b border-border">
              <p className="text-[10px] font-medium text-muted-foreground uppercase tracking-wider mb-1.5">Work Plan</p>
              <div className="prose prose-xs dark:prose-invert max-w-none text-[11px] leading-relaxed max-h-40 overflow-y-auto">
                <ReactMarkdown>{workPlan.slice(0, 500)}</ReactMarkdown>
              </div>
            </div>
          )}

          {/* 5. PM Coordination (latest pulse) */}
          {(() => {
            const pmPulse = activities.find(a => a.event_type === 'pm_pulsed');
            return pmPulse ? (
              <div className="px-3 py-3 border-b border-border">
                <p className="text-[10px] font-medium text-muted-foreground uppercase tracking-wider mb-1.5">PM Status</p>
                <p className="text-[11px] text-foreground/80">{pmPulse.summary || String(pmPulse.metadata?.reason || 'Monitoring')}</p>
              </div>
            ) : null;
          })()}

        </div>
      </div>

      {/* ── SETTINGS MODAL ── */}
      {settingsOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40" onClick={() => setSettingsOpen(false)}>
          <div
            className="bg-background rounded-xl border border-border shadow-xl w-full max-w-lg max-h-[80vh] overflow-y-auto"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between px-4 py-3 border-b border-border">
              <h2 className="text-sm font-semibold">Project Settings</h2>
              <button
                onClick={() => setSettingsOpen(false)}
                className="p-1 rounded text-muted-foreground hover:text-foreground"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
            <SettingsTab
              slug={slug}
              project={meta}
              objective={objective}
              onUpdateObjective={(obj) => setObjective(obj)}
              onArchive={handleArchive}
              archiving={archiving}
            />
          </div>
        </div>
      )}
    </div>
  );
}
