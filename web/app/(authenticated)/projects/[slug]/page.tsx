'use client';

/**
 * Project Detail Page — ADR-124
 *
 * Tab layout: Meeting Room | Members | Context | Outputs | Settings
 * Meeting Room: interleaved activity events + project-scoped chat with @-mentions.
 * Members: personified agent participant list with profile cards.
 * Context: workspace file browser.
 * Outputs: assembly cards with inline markdown preview.
 * Settings: objective, assembly config, delivery, archive.
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
  FolderOpen,
  Folder,
  File,
  Settings,
} from 'lucide-react';
import { api } from '@/lib/api/client';
import { formatDistanceToNow, format } from 'date-fns';
import { cn } from '@/lib/utils';
import { useTP } from '@/contexts/TPContext';
import { MessageBlocks } from '@/components/tp/InlineToolCall';
import { ToolResultList } from '@/components/tp/ToolResultCard';
import type {
  ProjectDetail,
  ProjectActivityItem,
  ProjectMember,
  OutputManifest,
  ContributionFile,
  PMIntelligence,
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
      <div className="px-4 md:px-6 pb-4 pt-2 shrink-0 border-t border-border" style={{ paddingBottom: 'max(1rem, env(safe-area-inset-bottom))' }}>
        <div className="max-w-3xl mx-auto">
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
                    <span className="text-xs text-muted-foreground">{roleDisplayName(c.role)}</span>
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

// =============================================================================
// Shared helpers for member display
// =============================================================================

/** Display name for a member — title or humanized slug */
function memberName(m: ProjectMember): string {
  return m.title || m.agent_slug.replace(/-/g, ' ').replace(/\b\w/g, ch => ch.toUpperCase());
}

/** Role → user-facing display name */
function roleDisplayName(role?: string): string {
  switch (role) {
    case 'pm': return 'Project Manager';
    case 'digest': return 'Recap';
    case 'monitor': return 'Monitor';
    case 'research': return 'Researcher';
    case 'synthesize': return 'Synthesizer';
    case 'prepare': return 'Prep';
    case 'act': return 'Operator';
    case 'custom': return 'Custom';
    default: return role || '';
  }
}

/** Scope → user-facing display name */
function scopeDisplayName(scope?: string): string {
  switch (scope) {
    case 'platform': return 'Single platform';
    case 'cross_platform': return 'Cross-platform';
    case 'knowledge': return 'Knowledge';
    case 'research': return 'Research';
    case 'autonomous': return 'Autonomous';
    default: return scope?.replace(/_/g, ' ') || '';
  }
}

/** Mode → user-facing display name */
function modeDisplayName(mode?: string): string {
  switch (mode) {
    case 'recurring': return 'Scheduled';
    case 'goal': return 'Goal-driven';
    case 'reactive': return 'On event';
    case 'proactive': return 'Self-initiated';
    case 'coordinator': return 'Coordinator';
    default: return mode?.replace(/_/g, ' ') || '';
  }
}

/** Role badge color */
function roleBadgeColor(role?: string): string {
  switch (role) {
    case 'pm': return 'bg-purple-100 text-purple-700 dark:bg-purple-900/40 dark:text-purple-300';
    case 'digest': return 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300';
    case 'monitor': return 'bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300';
    case 'research': return 'bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300';
    case 'synthesize': return 'bg-teal-100 text-teal-700 dark:bg-teal-900/40 dark:text-teal-300';
    case 'prepare': return 'bg-indigo-100 text-indigo-700 dark:bg-indigo-900/40 dark:text-indigo-300';
    default: return 'bg-muted text-muted-foreground';
  }
}

/** Avatar color based on role */
function avatarColor(role?: string): string {
  switch (role) {
    case 'pm': return 'bg-purple-500';
    case 'digest': return 'bg-blue-500';
    case 'monitor': return 'bg-amber-500';
    case 'research': return 'bg-green-500';
    case 'synthesize': return 'bg-teal-500';
    case 'prepare': return 'bg-indigo-500';
    default: return 'bg-gray-500';
  }
}

/** Status indicator */
function statusIndicator(status?: string): { color: string; label: string } {
  switch (status) {
    case 'active': return { color: 'bg-green-500', label: 'Active' };
    case 'paused': return { color: 'bg-amber-500', label: 'Paused' };
    case 'archived': return { color: 'bg-gray-400', label: 'Archived' };
    default: return { color: 'bg-green-500', label: 'Active' };
  }
}

// =============================================================================
// Agent Profile Card — slide-out panel
// =============================================================================

function AgentProfileCard({
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
  const [files, setFiles] = useState<ContributionFile[]>([]);
  const [filesLoading, setFilesLoading] = useState(true);

  useEffect(() => {
    api.projects.getContributions(slug, member.agent_slug)
      .then((res) => setFiles(res.files))
      .catch(() => setFiles([]))
      .finally(() => setFilesLoading(false));
  }, [slug, member.agent_slug]);

  const name = memberName(member);
  const initials = name.split(' ').map(w => w[0]).join('').slice(0, 2).toUpperCase();
  const si = statusIndicator(member.status);

  return (
    <div className="fixed inset-0 z-50 flex justify-end" onClick={onClose}>
      <div className="absolute inset-0 bg-black/20 backdrop-blur-[1px]" />
      <div
        className="relative w-full max-w-md bg-background border-l border-border h-full overflow-y-auto animate-in slide-in-from-right-5 duration-200"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="sticky top-0 bg-background/95 backdrop-blur-sm border-b border-border px-5 py-4 flex items-start gap-4">
          <div className={cn('w-14 h-14 rounded-full flex items-center justify-center text-white text-lg font-semibold shrink-0', avatarColor(member.role))}>
            {initials}
          </div>
          <div className="flex-1 min-w-0">
            <h2 className="text-lg font-semibold truncate">{name}</h2>
            <div className="flex items-center gap-2 mt-1">
              {member.role && (
                <span className={cn('text-[10px] font-medium px-1.5 py-0.5 rounded-full', roleBadgeColor(member.role))}>
                  {roleDisplayName(member.role)}
                </span>
              )}
              <span className="flex items-center gap-1 text-xs text-muted-foreground">
                <span className={cn('w-1.5 h-1.5 rounded-full', si.color)} />
                {si.label}
              </span>
            </div>
            {member.expected_contribution && (
              <p className="text-xs text-muted-foreground mt-1.5">{member.expected_contribution}</p>
            )}
          </div>
          <button onClick={onClose} className="text-muted-foreground hover:text-foreground transition-colors shrink-0 mt-1">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Details */}
        <div className="px-5 py-4 space-y-5">
          {/* Info grid */}
          <div className="grid grid-cols-2 gap-3">
            {member.scope && (
              <div>
                <p className="text-[10px] text-muted-foreground/70 uppercase tracking-wider mb-0.5">Scope</p>
                <p className="text-sm">{scopeDisplayName(member.scope)}</p>
              </div>
            )}
            {member.mode && (
              <div>
                <p className="text-[10px] text-muted-foreground/70 uppercase tracking-wider mb-0.5">Trigger</p>
                <p className="text-sm">{modeDisplayName(member.mode)}</p>
              </div>
            )}
            {member.schedule && (member.schedule as Record<string, string>).frequency && (
              <div>
                <p className="text-[10px] text-muted-foreground/70 uppercase tracking-wider mb-0.5">Schedule</p>
                <p className="text-sm">{(member.schedule as Record<string, string>).frequency}</p>
              </div>
            )}
            {member.origin && (
              <div>
                <p className="text-[10px] text-muted-foreground/70 uppercase tracking-wider mb-0.5">Origin</p>
                <p className="text-sm">{member.origin.replace(/_/g, ' ')}</p>
              </div>
            )}
            {member.last_run_at && (
              <div>
                <p className="text-[10px] text-muted-foreground/70 uppercase tracking-wider mb-0.5">Last active</p>
                <p className="text-sm">{formatDistanceToNow(new Date(member.last_run_at), { addSuffix: true })}</p>
              </div>
            )}
            {member.created_at && (
              <div>
                <p className="text-[10px] text-muted-foreground/70 uppercase tracking-wider mb-0.5">Joined</p>
                <p className="text-sm">{format(new Date(member.created_at), 'MMM d, yyyy')}</p>
              </div>
            )}
          </div>

          {/* PM brief for this member */}
          {pmIntelligence?.briefs?.[member.agent_slug] && (
            <div>
              <PMIntelligencePanel pmIntelligence={pmIntelligence} agentSlug={member.agent_slug} />
            </div>
          )}

          {/* Contributions */}
          <div>
            <h3 className="text-xs font-semibold text-muted-foreground mb-2 uppercase tracking-wider">
              Contributions ({contributionCount})
            </h3>
            {filesLoading ? (
              <div className="flex items-center gap-2 text-muted-foreground text-xs py-3">
                <Loader2 className="w-3 h-3 animate-spin" />
                Loading...
              </div>
            ) : files.length === 0 ? (
              <p className="text-xs text-muted-foreground py-2">No contribution files yet.</p>
            ) : (
              <div className="space-y-2">
                {files.map((f) => (
                  <div key={f.path} className="border border-border rounded-lg overflow-hidden">
                    <div className="px-3 py-1.5 bg-muted/50 text-xs text-muted-foreground flex items-center gap-1.5">
                      <FileText className="w-3 h-3" />
                      {f.path.split('/').pop()}
                      {f.updated_at && (
                        <span className="ml-auto">{formatDistanceToNow(new Date(f.updated_at), { addSuffix: true })}</span>
                      )}
                    </div>
                    <div className="p-3 max-h-48 overflow-y-auto">
                      <div className="prose prose-sm dark:prose-invert max-w-none prose-p:my-1">
                        <ReactMarkdown>{f.content}</ReactMarkdown>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Link to full agent page */}
          {member.agent_id && (
            <Link
              href={`/agents/${member.agent_id}`}
              className="flex items-center justify-center gap-1.5 text-sm font-medium text-primary hover:text-primary/80 border border-primary/30 rounded-lg py-2 px-4 hover:bg-primary/5 transition-colors"
            >
              <ExternalLink className="w-3.5 h-3.5" />
              Open full agent page
            </Link>
          )}
        </div>
      </div>
    </div>
  );
}

// =============================================================================
// Members Tab — personified participant list (KakaoTalk-style)
// =============================================================================

function MembersTab({
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

  if (members.length === 0) {
    return (
      <div className="text-center py-12">
        <Users className="w-8 h-8 text-muted-foreground/20 mx-auto mb-3" />
        <p className="text-sm text-muted-foreground">No members yet.</p>
      </div>
    );
  }

  // Sort: PM first, then by role
  const sorted = [...members].sort((a, b) => {
    if (a.role === 'pm' && b.role !== 'pm') return -1;
    if (b.role === 'pm' && a.role !== 'pm') return 1;
    return 0;
  });

  return (
    <>
      <div className="max-w-2xl mx-auto px-4 md:px-6 py-4">
        {/* PM quality assessment at top */}
        {pmIntelligence?.quality_assessment && (
          <div className="mb-4">
            <PMIntelligencePanel pmIntelligence={pmIntelligence} />
          </div>
        )}

        {/* Member count header */}
        <p className="text-xs text-muted-foreground mb-3 px-1">
          {members.length} member{members.length !== 1 ? 's' : ''}
        </p>

        {/* Member list */}
        <div className="space-y-1">
          {sorted.map((m) => {
            const name = memberName(m);
            const initials = name.split(' ').map(w => w[0]).join('').slice(0, 2).toUpperCase();
            const si = statusIndicator(m.status);
            const contribCount = contributionCounts[m.agent_slug] || 0;

            return (
              <button
                key={m.agent_slug}
                onClick={() => setSelectedMember(m)}
                className="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl hover:bg-muted/50 transition-colors text-left group"
              >
                {/* Avatar */}
                <div className="relative shrink-0">
                  <div className={cn('w-10 h-10 rounded-full flex items-center justify-center text-white text-sm font-semibold', avatarColor(m.role))}>
                    {initials}
                  </div>
                  {/* Status dot */}
                  <span className={cn(
                    'absolute -bottom-0.5 -right-0.5 w-3 h-3 rounded-full border-2 border-background',
                    si.color,
                  )} />
                </div>

                {/* Name + meta */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium truncate">{name}</span>
                    {m.role && (
                      <span className={cn('text-[10px] font-medium px-1.5 py-0.5 rounded-full shrink-0', roleBadgeColor(m.role))}>
                        {roleDisplayName(m.role)}
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-muted-foreground truncate mt-0.5">
                    {m.expected_contribution || (m.last_run_at
                      ? `Active ${formatDistanceToNow(new Date(m.last_run_at), { addSuffix: true })}`
                      : 'No activity yet'
                    )}
                  </p>
                </div>

                {/* Right side: contribution count */}
                {contribCount > 0 && (
                  <span className="text-xs text-muted-foreground flex items-center gap-1 shrink-0">
                    <FileText className="w-3 h-3" />
                    {contribCount}
                  </span>
                )}

                <ChevronRight className="w-4 h-4 text-muted-foreground/50 shrink-0 opacity-0 group-hover:opacity-100 transition-opacity" />
              </button>
            );
          })}
        </div>
      </div>

      {/* Profile card slide-out */}
      {selectedMember && (
        <AgentProfileCard
          member={selectedMember}
          contributionCount={contributionCounts[selectedMember.agent_slug] || 0}
          slug={slug}
          pmIntelligence={pmIntelligence}
          onClose={() => setSelectedMember(null)}
        />
      )}
    </>
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
  members,
  onUpdateObjective,
  onArchive,
  archiving,
}: {
  slug: string;
  project: ProjectDetail['project'];
  objective?: { deliverable?: string; audience?: string; format?: string; purpose?: string };
  members: ProjectMember[];
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

      {/* Members */}
      <section>
        <h3 className="text-sm font-semibold mb-2">Members</h3>
        {members.length > 0 ? (
          <div className="space-y-2">
            {members.map((m) => (
              <div key={m.agent_slug} className="flex items-center gap-2 text-sm">
                <span className={cn('w-2 h-2 rounded-full shrink-0', avatarColor(m.role))} />
                <span className="font-medium">{memberName(m)}</span>
                {m.role && (
                  <span className={cn('text-[10px] font-medium px-1.5 py-0.5 rounded-full', roleBadgeColor(m.role))}>
                    {roleDisplayName(m.role)}
                  </span>
                )}
                {m.expected_contribution && (
                  <span className="text-xs text-muted-foreground ml-auto">{m.expected_contribution}</span>
                )}
              </div>
            ))}
          </div>
        ) : (
          <p className="text-sm text-muted-foreground">No members assigned.</p>
        )}
        <p className="text-xs text-muted-foreground mt-2">
          Members are managed via the meeting room. Ask the PM to add or reassign members.
        </p>
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
            {Object.entries(project.delivery).map(([key, value]) => (
              <div key={key} className="flex items-center gap-2">
                <span className="text-muted-foreground">{key}:</span>
                <span>{String(value)}</span>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-sm text-muted-foreground">No delivery preferences configured.</p>
        )}
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
// Main Component
// =============================================================================

type TabId = 'meeting-room' | 'members' | 'context' | 'outputs' | 'settings';

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

  const { project: meta, contribution_counts, assembly_count, pm_intelligence } = project;
  const title = meta.title || slug.replace(/-/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
  const members = meta.contributors || [];

  const tabs: { id: TabId; label: string; icon: React.ReactNode }[] = [
    { id: 'meeting-room', label: 'Meeting Room', icon: <MessageSquare className="w-4 h-4" /> },
    { id: 'members', label: `Members${members.length > 0 ? ` (${members.length})` : ''}`, icon: <Users className="w-4 h-4" /> },
    { id: 'context', label: 'Context', icon: <FolderOpen className="w-4 h-4" /> },
    { id: 'outputs', label: `Outputs${assembly_count > 0 ? ` (${assembly_count})` : ''}`, icon: <Package className="w-4 h-4" /> },
    { id: 'settings', label: 'Settings', icon: <Settings className="w-4 h-4" /> },
  ];

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="shrink-0 border-b border-border">
        <div className="max-w-5xl mx-auto px-4 md:px-6 py-4">
          <Link
            href="/projects"
            className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground transition-colors mb-3"
          >
            <ChevronLeft className="w-4 h-4" />
            Projects
          </Link>

          <div>
            <h1 className="text-xl font-bold">{title}</h1>
            {objective?.deliverable && (
              <p className="text-sm text-muted-foreground mt-0.5">
                {objective.deliverable}
                {objective.audience && ` for ${objective.audience}`}
                {objective.format && ` — ${objective.format}`}
              </p>
            )}
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
      </div>

      {/* Tab content */}
      <div className="flex-1 min-h-0 overflow-hidden">
        {activeTab === 'meeting-room' && (
          <MeetingRoomTab activities={activities} slug={slug} projectTitle={title} contributors={members} />
        )}
        {activeTab === 'members' && (
          <div className="h-full overflow-y-auto">
            <MembersTab
              members={members}
              contributionCounts={contribution_counts}
              slug={slug}
              pmIntelligence={pm_intelligence}
            />
          </div>
        )}
        {activeTab === 'context' && (
          <ContextTab slug={slug} />
        )}
        {activeTab === 'outputs' && (
          <div className="h-full overflow-y-auto">
            <div className="max-w-5xl mx-auto px-4 md:px-6">
              <OutputsTab slug={slug} />
            </div>
          </div>
        )}
        {activeTab === 'settings' && (
          <div className="h-full overflow-y-auto">
            <SettingsTab
              slug={slug}
              project={meta}
              objective={objective}
              members={members}
              onUpdateObjective={(obj) => setObjective(obj)}
              onArchive={handleArchive}
              archiving={archiving}
            />
          </div>
        )}
      </div>
    </div>
  );
}
