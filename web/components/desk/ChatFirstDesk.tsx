'use client';

/**
 * ADR-037: Chat-First Surface Architecture
 * ADR-091: Workspace Layout & Navigation Architecture
 *
 * Global TP workspace — renders WorkspaceLayout with "Agent" identity.
 * No agent scope. Chat is the primary interface.
 *
 * Panel tabs:
 * - Agents: compact entry cards linking to /agents/[id]
 * - Context: platform sync status (existing PlatformSyncStatus component)
 */

import { useState, useRef, useEffect, useCallback } from 'react';
import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import {
  Sparkles,
  CheckCircle2,
  Circle,
  Loader2,
  Send,
  X,
  ImagePlus,
  FileText,
  ArrowRight,
  Upload,
  Search,
  Globe,
  Layers,
  Brain,
} from 'lucide-react';
import { useTP } from '@/contexts/TPContext';
import { useDesk } from '@/contexts/DeskContext';
import { useFileAttachments } from '@/hooks/useFileAttachments';
import { Todo } from '@/types/desk';
import ReactMarkdown from 'react-markdown';
import { cn } from '@/lib/utils';
import { CommandPicker } from '@/components/tp/CommandPicker';
import { PlusMenu, type PlusMenuAction } from '@/components/tp/PlusMenu';
import { ToolResultList } from '@/components/tp/ToolResultCard';
import { MessageBlocks } from '@/components/tp/InlineToolCall';
import { getPlatformIcon } from '@/components/ui/PlatformIcons';
import { PlatformSyncStatus } from './PlatformSyncStatus';
import { WorkspaceLayout, WorkspacePanelTab } from './WorkspaceLayout';
import { api } from '@/lib/api/client';
import type { Agent } from '@/types';

// =============================================================================
// Helpers: platform icon derivation (AGENT-PRESENTATION-PRINCIPLES.md)
// =============================================================================

/** Derive platform providers from agent sources for visual display */
function getAgentPlatformProviders(agent: Agent): string[] {
  const providers: Record<string, true> = {};
  for (const s of agent.sources ?? []) {
    const p = s.provider as string | undefined;
    if (p) {
      // Normalize "google" → "gmail" or "calendar" based on resource_id
      if (p === 'google') {
        const rid = s.resource_id;
        const gmailLabels = ['INBOX', 'SENT', 'IMPORTANT', 'STARRED'];
        if (rid && (gmailLabels.includes(rid.toUpperCase()) || rid.startsWith('label:'))) {
          providers['gmail'] = true;
        } else {
          providers['calendar'] = true;
        }
      } else {
        providers[p] = true;
      }
    }
  }
  return Object.keys(providers);
}

/** Render platform icon(s) for an agent — source-first visual anchor */
function AgentSourceIcons({ agent, className = 'w-4 h-4' }: { agent: Agent; className?: string }) {
  const providers = getAgentPlatformProviders(agent);

  if (providers.length === 0) {
    // Research/knowledge agents — use skill-derived icon
    if (agent.skill === 'research') return <Globe className={className} />;
    return <Brain className={className} />;
  }

  if (providers.length === 1) {
    return <>{getPlatformIcon(providers[0], className)}</>;
  }

  // Multi-platform: show stacked icons (max 2 visible + overflow)
  return (
    <div className="flex items-center -space-x-1">
      {providers.slice(0, 2).map((p) => (
        <span key={p} className="inline-block">{getPlatformIcon(p, className)}</span>
      ))}
      {providers.length > 2 && (
        <span className="text-[9px] text-muted-foreground font-medium ml-0.5">+{providers.length - 2}</span>
      )}
    </div>
  );
}

// =============================================================================
// Panel: Agents (compact entry cards)
// =============================================================================

function AgentsPanel() {
  const { isLoading } = useTP();
  const [agents, setAgents] = useState<Agent[]>([]);
  const [loading, setLoading] = useState(true);
  const hasLoadedOnceRef = useRef(false);
  const mountedRef = useRef(true);
  const requestSeqRef = useRef(0);

  const loadAgents = useCallback(async (silent = false) => {
    const requestSeq = ++requestSeqRef.current;

    // Show blocking spinner only on first load.
    if (!silent && !hasLoadedOnceRef.current && mountedRef.current) {
      setLoading(true);
    }

    try {
      const data = await api.agents.list();
      if (!mountedRef.current || requestSeq !== requestSeqRef.current) return;
      setAgents(data);
    } catch (err) {
      console.error('Failed to load agents:', err);
    } finally {
      if (!hasLoadedOnceRef.current && mountedRef.current) {
        hasLoadedOnceRef.current = true;
        setLoading(false);
      }
    }
  }, []);

  // Initial load + unmount guard.
  useEffect(() => {
    mountedRef.current = true;
    void loadAgents();
    return () => {
      mountedRef.current = false;
    };
  }, [loadAgents]);

  // Refresh after each TP turn completes.
  useEffect(() => {
    if (!isLoading) {
      void loadAgents(true);
    }
  }, [isLoading, loadAgents]);

  // Poll while TP is actively working so status transitions show up during execution.
  useEffect(() => {
    if (!isLoading) return;
    const intervalId = window.setInterval(() => {
      void loadAgents(true);
    }, 4000);
    return () => window.clearInterval(intervalId);
  }, [isLoading, loadAgents]);

  // Refresh when tab regains focus/visibility.
  useEffect(() => {
    const onFocus = () => void loadAgents(true);
    const onVisibility = () => {
      if (document.visibilityState === 'visible') {
        void loadAgents(true);
      }
    };

    window.addEventListener('focus', onFocus);
    document.addEventListener('visibilitychange', onVisibility);
    return () => {
      window.removeEventListener('focus', onFocus);
      document.removeEventListener('visibilitychange', onVisibility);
    };
  }, [loadAgents]);

  const getRunStatusLabel = (agent: Agent): string => {
    const status = agent.latest_version_status;
    if (status === 'delivered') return 'Delivered';
    if (status === 'failed') return 'Failed';
    if (status === 'generating') return 'Generating...';
    if (status === 'staged') return 'Ready for review';
    if (status === 'reviewing') return 'Pending approval';
    if (status === 'approved') return 'Approved';
    if (status === 'rejected') return 'Needs revision';

    if (agent.version_count) {
      return `${agent.version_count} version${agent.version_count !== 1 ? 's' : ''}`;
    }
    return 'No deliveries yet';
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center p-6">
        <Loader2 className="w-4 h-4 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (agents.length === 0) {
    return (
      <div className="p-4 text-center">
        <FileText className="w-8 h-8 text-muted-foreground/30 mx-auto mb-2" />
        <p className="text-sm text-muted-foreground">No agents yet</p>
        <p className="text-xs text-muted-foreground/70 mt-1">Ask yarnnn in chat to create one</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      <div className="divide-y divide-border flex-1 overflow-y-auto">
        {agents.map((d) => (
          <Link
            key={d.id}
            href={`/agents/${d.id}`}
            className="flex items-center justify-between px-3 py-2.5 hover:bg-muted/50 transition-colors group"
          >
            <div className="flex items-center gap-2 min-w-0">
              {/* Source-first: platform icon as primary visual anchor */}
              <span className="shrink-0 text-muted-foreground relative">
                <AgentSourceIcons agent={d} className="w-4 h-4" />
                {/* Status dot */}
                <span className={cn(
                  'absolute -bottom-0.5 -right-0.5 w-2 h-2 rounded-full border border-background',
                  d.status === 'paused' ? 'bg-amber-400' : 'bg-green-500'
                )} />
              </span>
              <div className="min-w-0">
                <span className="text-sm font-medium truncate block">{d.title}</span>
                <span className="text-xs text-muted-foreground">
                  {getRunStatusLabel(d)}
                </span>
              </div>
            </div>
            <ArrowRight className="w-3.5 h-3.5 text-muted-foreground shrink-0 opacity-0 group-hover:opacity-100 transition-opacity ml-2" />
          </Link>
        ))}
      </div>
    </div>
  );
}

// =============================================================================
// Panel: Context (platform sync status)
// =============================================================================

function ContextPanel() {
  return (
    <div className="overflow-y-auto min-h-0">
      <PlatformSyncStatus />
    </div>
  );
}

// =============================================================================
// Helpers
// =============================================================================

/**
 * Format token count with K suffix for thousands (like Claude Code)
 */
function formatTokenCount(tokens: number): string {
  if (tokens >= 1000) {
    return `${(tokens / 1000).toFixed(1)}k`;
  }
  return tokens.toString();
}

// =============================================================================
// Agent creation templates — source-first, per AGENT-PRESENTATION-PRINCIPLES.md
// =============================================================================

const STARTER_TEMPLATES = [
  {
    id: 'slack-recap',
    label: 'Slack Recap',
    description: 'Daily or weekly summary of your Slack channels',
    prompt: 'Set up a recurring Slack recap for me',
    icon: 'slack' as const,
  },
  {
    id: 'meeting-prep',
    label: 'Meeting Prep',
    description: 'Reads your calendar and preps you for the day\'s meetings',
    prompt: 'Set up daily meeting prep from my calendar and Slack',
    icon: 'calendar' as const,
  },
  {
    id: 'work-summary',
    label: 'Work Summary',
    description: 'Weekly synthesis across all your connected platforms',
    prompt: 'Set up a weekly work summary across my platforms',
    icon: 'cross-platform' as const,
  },
  {
    id: 'proactive-insights',
    label: 'Proactive Insights',
    description: 'Spots emerging themes and researches them for you',
    prompt: 'Set up proactive insights that research trends across my platforms',
    icon: 'globe' as const,
  },
];

type TemplateIcon = typeof STARTER_TEMPLATES[number]['icon'];

/** Map template icon keys to React nodes — platform icons + lucide fallbacks */
function getTemplateIcon(icon: TemplateIcon): React.ReactNode {
  switch (icon) {
    case 'slack':
      return getPlatformIcon('slack', 'w-full h-full');
    case 'calendar':
      return getPlatformIcon('calendar', 'w-full h-full');
    case 'cross-platform':
      return <Layers className="w-full h-full" />;
    case 'globe':
      return <Globe className="w-full h-full" />;
    default:
      return <Brain className="w-full h-full" />;
  }
}

// =============================================================================
// Main component
// =============================================================================

export function ChatFirstDesk() {
  const {
    todos,
    messages,
    activeCommand,
    sendMessage,
    isLoading,
    status,
    pendingClarification,
    respondToClarification,
    tokenUsage,
    loadScopedHistory,
  } = useTP();
  const { surface } = useDesk();

  // ADR-087 Phase 3: Load global (unscoped) history when dashboard mounts
  // This ensures navigating back from an agent reloads the global thread
  useEffect(() => {
    loadScopedHistory();
  }, [loadScopedHistory]);

  const searchParams = useSearchParams();
  const router = useRouter();

  const [input, setInput] = useState('');
  const [commandPickerOpen, setCommandPickerOpen] = useState(false);
  const [showCreateCards, setShowCreateCards] = useState(false);
  const createCardsRef = useRef<HTMLDivElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const {
    attachments,
    attachmentPreviews,
    isDragging,
    error: fileError,
    dropZoneProps,
    handleFileSelect,
    handlePaste,
    removeAttachment,
    clearAttachments,
    getImagesForAPI,
    fileInputRef,
  } = useFileAttachments();

  // Handle ?create param — pre-fill input for agent creation handoff
  useEffect(() => {
    if (searchParams?.has('create')) {
      setInput('I want to create a new agent');
      textareaRef.current?.focus();
      router.replace('/dashboard', { scroll: false });
    }
  }, [searchParams, router]);

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, status]);

  // Focus textarea on mount
  useEffect(() => {
    textareaRef.current?.focus();
  }, []);

  // Dismiss create cards on click outside
  useEffect(() => {
    if (!showCreateCards) return;
    function handleClick(e: MouseEvent) {
      if (createCardsRef.current && !createCardsRef.current.contains(e.target as Node)) {
        setShowCreateCards(false);
      }
    }
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, [showCreateCards]);

  // Auto-resize textarea
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

  // Detect command picker trigger
  const commandQuery = input.startsWith('/') ? input.slice(1).split(' ')[0] : null;

  useEffect(() => {
    if (commandQuery !== null && !input.includes(' ')) {
      setCommandPickerOpen(true);
    } else {
      setCommandPickerOpen(false);
    }
  }, [commandQuery, input]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if ((!input.trim() && attachments.length === 0) || isLoading) return;

    const images = await getImagesForAPI();
    sendMessage(input, { surface, images: images.length > 0 ? images : undefined });
    setInput('');
    clearAttachments();
    setShowCreateCards(false);
  };

  const handleCommandSelect = (command: string) => {
    setInput(command + ' ');
    setCommandPickerOpen(false);
    textareaRef.current?.focus();
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e as unknown as React.FormEvent);
    }
  };

  // Plus menu actions — verb taxonomy (see docs/design/INLINE-PLUS-MENU.md)
  const plusMenuActions: PlusMenuAction[] = [
    {
      id: 'attach-image',
      label: 'Attach image',
      icon: ImagePlus,
      verb: 'attach',
      onSelect: () => fileInputRef.current?.click(),
    },
    {
      id: 'create-agent',
      label: 'Create work-agent',
      icon: Sparkles,
      verb: 'show',
      onSelect: () => setShowCreateCards((prev) => !prev),
    },
    {
      id: 'search-platforms',
      label: 'Search my platforms',
      icon: Search,
      verb: 'prompt',
      onSelect: () => {
        setInput('Search across my connected platforms for ');
        textareaRef.current?.focus();
      },
    },
  ];

  const handleOptionClick = (option: string) => {
    respondToClarification(option);
  };

  const formatCommandName = (skill: string) => {
    return skill
      .split('-')
      .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ');
  };

  const identityLabel = activeCommand ? formatCommandName(activeCommand) : 'Agent';

  const panelTabs: WorkspacePanelTab[] = [
    {
      id: 'agents',
      label: 'Agents',
      content: <AgentsPanel />,
    },
    {
      id: 'context',
      label: 'Context',
      content: <ContextPanel />,
    },
  ];

  return (
    <WorkspaceLayout
      identity={{
        icon: <Sparkles className="w-5 h-5" />,
        label: identityLabel,
        badge: isLoading ? <Loader2 className="w-4 h-4 animate-spin text-primary" /> : undefined,
      }}
      panelTabs={panelTabs}
      panelDefaultOpen={true}
      panelDefaultPct={25}
    >
      {/* Drop zone container — wraps messages + input */}
      <div className="relative flex flex-col flex-1 min-h-0" {...dropZoneProps}>
        {/* Drop zone overlay */}
        {isDragging && (
          <div className="absolute inset-0 z-50 bg-primary/5 backdrop-blur-[1px] flex items-center justify-center">
            <div className="border-2 border-dashed border-primary/40 rounded-xl p-8 flex flex-col items-center gap-2">
              <Upload className="w-8 h-8 text-primary/60" />
              <span className="text-sm font-medium text-primary/80">Drop images here</span>
            </div>
          </div>
        )}

        {/* File error toast */}
        {fileError && (
          <div className="absolute top-4 left-1/2 -translate-x-1/2 z-50 px-3 py-1.5 rounded-lg bg-destructive text-destructive-foreground text-xs font-medium shadow-lg animate-in fade-in slide-in-from-top-2 duration-200">
            {fileError}
          </div>
        )}

        {/* Todos — only show when there's active work */}
        {todos.length > 0 && todos.some((t) => t.status === 'in_progress') && (
          <div className="px-4 py-3 border-b border-border bg-muted/20 shrink-0">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-medium text-muted-foreground">Progress</span>
              <span className="text-xs text-muted-foreground">
                {todos.filter((t) => t.status === 'completed').length}/{todos.length}
              </span>
            </div>
            <div className="space-y-1.5 max-h-28 overflow-y-auto">
              {todos.map((todo, i) => (
                <TodoItem key={i} todo={todo} />
              ))}
            </div>
          </div>
        )}

        {/* Messages — centered with max-width */}
        <div className="flex-1 overflow-y-auto px-5 sm:px-6 py-4 space-y-4">
          <div className="max-w-3xl mx-auto w-full space-y-3">
            {messages.length === 0 && !isLoading && (
              <div className="py-8">
                <div className="text-center mb-8">
                  <Sparkles className="w-10 h-10 text-muted-foreground/20 mx-auto mb-3" />
                  <h2 className="text-lg font-medium mb-1">What would you like to work on?</h2>
                  <p className="text-sm text-muted-foreground max-w-sm mx-auto">
                    Pick a starting point, or just type anything below.
                  </p>
                </div>
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 max-w-2xl mx-auto">
                  {STARTER_TEMPLATES.map((tpl) => (
                    <button
                      key={tpl.id}
                      onClick={() => {
                        setInput(tpl.prompt);
                        textareaRef.current?.focus();
                      }}
                      className="flex flex-col items-start gap-1 p-3 rounded-lg border border-border hover:border-primary/30 hover:bg-primary/5 transition-colors text-left"
                    >
                      <div className="flex items-center gap-1.5 mb-0.5">
                        <span className="w-4 h-4 shrink-0 text-muted-foreground">
                          {getTemplateIcon(tpl.icon)}
                        </span>
                        <span className="text-sm font-medium">{tpl.label}</span>
                      </div>
                      <span className="text-xs text-muted-foreground leading-snug">{tpl.description}</span>
                    </button>
                  ))}
                  <button
                    onClick={() => {
                      setInput('What can you help me with?');
                      textareaRef.current?.focus();
                    }}
                    className="flex flex-col items-start gap-1 p-3 rounded-lg border border-dashed border-border hover:border-primary/30 hover:bg-muted/50 transition-colors text-left"
                  >
                    <span className="text-sm font-medium">Just chat</span>
                    <span className="text-xs text-muted-foreground leading-snug">Ask me anything about your work</span>
                  </button>
                </div>
              </div>
            )}

            {messages.map((msg) => (
              <div
                key={msg.id}
                className={cn(
                  'text-sm rounded-2xl px-4 py-3 max-w-[85%] sm:max-w-2xl',
                  msg.role === 'user'
                    ? 'bg-primary/10 ml-auto rounded-br-md'
                    : 'bg-muted rounded-bl-md'
                )}
              >
                <span className="text-[10px] font-medium text-muted-foreground/70 uppercase tracking-wider block mb-1.5">
                  {msg.role === 'user' ? 'You' : 'yarnnn'}
                </span>
                {msg.images && msg.images.length > 0 && (
                  <div className="flex flex-wrap gap-2 mb-2">
                    {msg.images.map((img, i) => (
                      <img
                        key={i}
                        src={`data:${img.mediaType};base64,${img.data}`}
                        alt={`Attachment ${i + 1}`}
                        className="max-w-[200px] max-h-[150px] object-contain rounded border border-border"
                      />
                    ))}
                  </div>
                )}
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
            ))}

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
                    {pendingClarification.options.map((option, i) => (
                      <button
                        key={i}
                        onClick={() => handleOptionClick(option)}
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

            <div ref={messagesEndRef} />
          </div>
        </div>

        {/* Input — floating */}
        <div className="px-4 pb-4 pt-2 shrink-0" style={{ paddingBottom: 'max(1rem, env(safe-area-inset-bottom))' }}>
          <div className="relative max-w-2xl mx-auto">
            <CommandPicker
              query={commandQuery ?? ''}
              onSelect={handleCommandSelect}
              onClose={() => setCommandPickerOpen(false)}
              isOpen={commandPickerOpen}
            />

            {/* Create agent cards — show verb */}
            {showCreateCards && (
              <div
                ref={createCardsRef}
                className="mb-2 p-3 rounded-xl border border-border bg-background shadow-sm animate-in fade-in slide-in-from-bottom-2 duration-150"
              >
                <div className="flex items-center justify-between mb-2">
                  <p className="text-xs font-medium text-muted-foreground">What should your agent do?</p>
                  <button
                    type="button"
                    onClick={() => setShowCreateCards(false)}
                    className="text-muted-foreground hover:text-foreground transition-colors"
                  >
                    <X className="w-3.5 h-3.5" />
                  </button>
                </div>
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-1.5">
                  {STARTER_TEMPLATES.map((tpl) => (
                    <button
                      key={tpl.id}
                      onClick={() => {
                        sendMessage(tpl.prompt, { surface });
                        setShowCreateCards(false);
                      }}
                      className="flex flex-col items-start gap-0.5 p-2.5 rounded-lg border border-border hover:border-primary/30 hover:bg-primary/5 transition-colors text-left"
                    >
                      <div className="flex items-center gap-1.5 mb-0.5">
                        <span className="w-3.5 h-3.5 shrink-0 text-muted-foreground">
                          {getTemplateIcon(tpl.icon)}
                        </span>
                        <span className="text-sm font-medium">{tpl.label}</span>
                      </div>
                      <span className="text-[11px] text-muted-foreground leading-snug">{tpl.description}</span>
                    </button>
                  ))}
                </div>
              </div>
            )}

            <form onSubmit={handleSubmit}>
              {attachmentPreviews.length > 0 && (
                <div className="flex flex-wrap gap-2 mb-2 p-2 rounded-t-lg border border-b-0 border-border bg-muted/30">
                  {attachmentPreviews.map((preview, index) => (
                    <div key={index} className="relative group">
                      <img
                        src={preview}
                        alt={`Attachment ${index + 1}`}
                        className="h-16 w-16 object-cover rounded-md border border-border"
                      />
                      <button
                        type="button"
                        onClick={() => removeAttachment(index)}
                        className="absolute -top-1.5 -right-1.5 w-5 h-5 bg-background border border-border rounded-full flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity hover:bg-destructive hover:text-destructive-foreground"
                      >
                        <X className="w-3 h-3" />
                      </button>
                    </div>
                  ))}
                </div>
              )}

              <div
                className={cn(
                  'flex items-end gap-2 border border-border bg-background shadow-sm transition-colors',
                  attachmentPreviews.length > 0 ? 'rounded-b-xl border-t-0' : 'rounded-xl',
                  'focus-within:ring-2 focus-within:ring-primary/50 focus-within:shadow-md'
                )}
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="image/*"
                  multiple
                  onChange={handleFileSelect}
                  className="hidden"
                />
                <PlusMenu actions={plusMenuActions} disabled={isLoading} />

                <textarea
                  ref={textareaRef}
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={handleKeyDown}
                  onPaste={handlePaste}
                  disabled={isLoading}
                  enterKeyHint="send"
                  placeholder={
                    status.type === 'clarify'
                      ? 'Type your answer...'
                      : 'Ask anything or type / for skills...'
                  }
                  rows={1}
                  className="flex-1 py-3 pr-2 text-base sm:text-sm bg-transparent resize-none focus:outline-none disabled:opacity-50 max-h-[200px]"
                />

                <button
                  type="submit"
                  disabled={isLoading || (!input.trim() && attachments.length === 0)}
                  className="shrink-0 p-3 text-primary hover:text-primary/80 disabled:text-muted-foreground disabled:opacity-50 transition-colors"
                  aria-label="Send"
                >
                  <Send className="w-5 h-5" />
                </button>
              </div>

              <div className="mt-1.5 flex items-center justify-between text-[10px] text-muted-foreground/60">
                <span className="hidden sm:inline">Enter to send, Shift+Enter for new line</span>
                <span className="sm:hidden">Tap send or use keyboard Send</span>
                {tokenUsage && (
                  <span className="font-mono tabular-nums">
                    {formatTokenCount(tokenUsage.totalTokens)} tokens
                  </span>
                )}
              </div>
            </form>
          </div>
        </div>
      </div>
    </WorkspaceLayout>
  );
}

function TodoItem({ todo }: { todo: Todo }) {
  return (
    <div className="flex items-center gap-2">
      {todo.status === 'completed' ? (
        <CheckCircle2 className="w-3.5 h-3.5 text-green-600 shrink-0" />
      ) : todo.status === 'in_progress' ? (
        <Loader2 className="w-3.5 h-3.5 text-primary animate-spin shrink-0" />
      ) : (
        <Circle className="w-3.5 h-3.5 text-muted-foreground shrink-0" />
      )}
      <span
        className={cn(
          'text-xs',
          todo.status === 'completed' && 'text-muted-foreground line-through',
          todo.status === 'in_progress' && 'text-foreground font-medium'
        )}
      >
        {todo.status === 'in_progress' ? todo.activeForm || todo.content : todo.content}
      </span>
    </div>
  );
}
