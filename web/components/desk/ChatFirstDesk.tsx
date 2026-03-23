'use client';

/**
 * ADR-037: Chat-First Surface Architecture
 * ADR-091: Workspace Layout & Navigation Architecture
 *
 * Global TP workspace — renders WorkspaceLayout with "Orchestrator" identity.
 * No agent scope. Chat is the primary interface.
 *
 * Panel tabs:
 * - Projects: compact entry cards linking to /projects/[slug]
 * - Platforms: connected platforms + document uploads (PlatformSyncStatus component)
 */

import { useState, useRef, useEffect, useCallback } from 'react';
import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import { HOME_ROUTE } from '@/lib/routes';
import {
  Command,
  CheckCircle2,
  Circle,
  Loader2,
  Send,
  X,
  ImagePlus,
  Upload,
  Search,
  Globe,
  Briefcase,
  RefreshCw,
  Bookmark,
  FileText,
} from 'lucide-react';
import { useTP } from '@/contexts/TPContext';
import { useDesk } from '@/contexts/DeskContext';
import { useFileAttachments } from '@/hooks/useFileAttachments';
import { usePlatformOnboardingState } from '@/hooks/usePlatformOnboardingState';
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
import { formatDistanceToNow } from 'date-fns';
import type { ProjectSummary } from '@/types';

// =============================================================================
// Panel: Projects (compact entry cards — ADR-122/124 project-first model)
// =============================================================================

const TYPE_LABELS: Record<string, string> = {
  slack_digest: 'Slack',
  notion_digest: 'Notion',
  cross_platform_synthesis: 'Cross-Platform',
  workspace: 'Workspace',
  bounded_deliverable: 'Deliverable',
  custom: 'Custom',
};

function getProjectIcon(typeKey: string | null): React.ReactNode {
  if (typeKey === 'slack_digest') return getPlatformIcon('slack', 'w-4 h-4');
  if (typeKey === 'notion_digest') return getPlatformIcon('notion', 'w-4 h-4');
  return <Briefcase className="w-4 h-4 text-muted-foreground" />;
}

function ProjectsPanel() {
  const { isLoading } = useTP();
  const [projects, setProjects] = useState<ProjectSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const hasLoadedOnceRef = useRef(false);
  const mountedRef = useRef(true);
  const requestSeqRef = useRef(0);

  const loadProjects = useCallback(async (silent = false) => {
    const requestSeq = ++requestSeqRef.current;

    if (!silent && !hasLoadedOnceRef.current && mountedRef.current) {
      setLoading(true);
    }

    try {
      const data = await api.projects.list();
      if (!mountedRef.current || requestSeq !== requestSeqRef.current) return;
      setProjects(data.projects);
    } catch (err) {
      console.error('Failed to load projects:', err);
    } finally {
      if (!hasLoadedOnceRef.current && mountedRef.current) {
        hasLoadedOnceRef.current = true;
        setLoading(false);
      }
    }
  }, []);

  useEffect(() => {
    mountedRef.current = true;
    void loadProjects();
    return () => { mountedRef.current = false; };
  }, [loadProjects]);

  // Refresh after each TP turn completes.
  useEffect(() => {
    if (!isLoading) { void loadProjects(true); }
  }, [isLoading, loadProjects]);

  // Poll while TP is actively working.
  useEffect(() => {
    if (!isLoading) return;
    const intervalId = window.setInterval(() => { void loadProjects(true); }, 4000);
    return () => window.clearInterval(intervalId);
  }, [isLoading, loadProjects]);

  // Refresh on focus/visibility.
  useEffect(() => {
    const onFocus = () => void loadProjects(true);
    const onVisibility = () => {
      if (document.visibilityState === 'visible') void loadProjects(true);
    };
    window.addEventListener('focus', onFocus);
    document.addEventListener('visibilitychange', onVisibility);
    return () => {
      window.removeEventListener('focus', onFocus);
      document.removeEventListener('visibilitychange', onVisibility);
    };
  }, [loadProjects]);

  if (loading) {
    return (
      <div className="flex items-center justify-center p-6">
        <Loader2 className="w-4 h-4 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (projects.length === 0) {
    return (
      <div className="p-4 text-center">
        <Briefcase className="w-8 h-8 text-muted-foreground/30 mx-auto mb-2" />
        <p className="text-sm text-muted-foreground">No projects yet</p>
        <p className="text-xs text-muted-foreground/70 mt-1">Tell yarnnn what you&apos;re working on to get started</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      <div className="divide-y divide-border flex-1 overflow-y-auto">
        {projects.map((p) => (
          <Link
            key={p.project_slug}
            href={`/projects/${p.project_slug}`}
            className="flex items-center gap-2.5 px-3 py-2.5 hover:bg-muted/50 transition-colors group"
          >
            <div className="shrink-0">
              {getProjectIcon(p.type_key)}
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-1.5">
                <span className="text-sm font-medium truncate">
                  {p.title || p.project_slug.replace(/-/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}
                </span>
                {p.type_key && TYPE_LABELS[p.type_key] && (
                  <span className="text-[10px] px-1 py-0.5 rounded bg-muted text-muted-foreground shrink-0">
                    {TYPE_LABELS[p.type_key]}
                  </span>
                )}
              </div>
              {p.purpose && (
                <span className="text-xs text-muted-foreground truncate block">{p.purpose}</span>
              )}
            </div>
            {p.updated_at && (
              <span className="text-[10px] text-muted-foreground shrink-0 hidden sm:block">
                {formatDistanceToNow(new Date(p.updated_at), { addSuffix: true })}
              </span>
            )}
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
// Starter templates — project creation + TP capabilities
// =============================================================================

/**
 * Starter prompt — single "New Project" card.
 *
 * Platform-specific projects (Slack/Notion) are created via bootstrap
 * on OAuth connection (ADR-110/113/122), not from starter cards. This eliminates
 * redundancy: bootstrap auto-scaffolds on connect, cards were just a chat detour.
 */
const NEW_PROJECT_PROMPT = 'I want to create a new project';

/** "Just chat" — single open-ended prompt for everything that isn't project creation */
const CHAT_PROMPT = 'Ask me anything — search your platforms, research the web, manage your agents, or just chat.';

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
  const [showShareForm, setShowShareForm] = useState(false);
  const [shareFilename, setShareFilename] = useState('');
  const [shareContent, setShareContent] = useState('');
  const [shareLoading, setShareLoading] = useState(false);
  const createCardsRef = useRef<HTMLDivElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Platform onboarding state — for cold-start empty state
  const { state: onboardingState } = usePlatformOnboardingState();
  const [connecting, setConnecting] = useState<string | null>(null);

  const handleConnect = useCallback(async (platform: string) => {
    setConnecting(platform);
    try {
      const result = await api.integrations.getAuthorizationUrl(platform);
      window.location.href = result.authorization_url;
    } catch (err) {
      console.error(`Failed to initiate ${platform} OAuth:`, err);
      setConnecting(null);
    }
  }, []);

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

  // Handle ?create param — pre-fill input for project creation handoff
  useEffect(() => {
    if (searchParams?.has('create')) {
      setInput('I want to set up a new project');
      textareaRef.current?.focus();
      router.replace(HOME_ROUTE, { scroll: false });
    }
  }, [searchParams, router]);

  // ADR-110/122: Detect post-OAuth redirect — ?provider=X&status=connected
  // Bootstrap now creates projects (not standalone agents), so poll projects by type_key.
  const [bootstrapProvider, setBootstrapProvider] = useState<string | null>(null);
  const [bootstrapProject, setBootstrapProject] = useState<ProjectSummary | null>(null);

  useEffect(() => {
    const provider = searchParams?.get('provider');
    const status = searchParams?.get('status');
    if (provider && status === 'connected') {
      setBootstrapProvider(provider);
      router.replace(HOME_ROUTE, { scroll: false });

      // Map OAuth provider to registry type_key
      const BOOTSTRAP_TYPE_KEYS: Record<string, string> = {
        slack: 'slack_digest',
        notion: 'notion_digest',
      };
      const expectedTypeKey = BOOTSTRAP_TYPE_KEYS[provider];
      if (!expectedTypeKey) return;

      let attempts = 0;
      const poll = setInterval(async () => {
        attempts++;
        try {
          const data = await api.projects.list();
          const found = data.projects.find(
            (p) => p.type_key === expectedTypeKey
          );
          if (found) {
            setBootstrapProject(found);
            clearInterval(poll);
          }
        } catch { /* ignore */ }
        if (attempts >= 12) clearInterval(poll); // Stop after ~60s
      }, 5000);

      return () => clearInterval(poll);
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

  const handleShareFile = async () => {
    if (!shareFilename.trim() || !shareContent.trim()) return;
    setShareLoading(true);
    try {
      await api.documents.shareFile(shareFilename.trim(), shareContent);
      setShowShareForm(false);
      setShareFilename('');
      setShareContent('');
      sendMessage(`I shared a file: ${shareFilename.trim()}`);
    } catch {
      // Form stays open on failure
    } finally {
      setShareLoading(false);
    }
  };

  // Plus menu actions — verb taxonomy (see docs/design/INLINE-PLUS-MENU.md)
  const plusMenuActions: PlusMenuAction[] = [
    {
      id: 'create-project',
      label: 'Create project',
      icon: Command,
      verb: 'show',
      onSelect: () => setShowCreateCards((prev) => !prev),
    },
    {
      id: 'share-file',
      label: 'Share a file',
      icon: FileText,
      verb: 'prompt',
      onSelect: () => setShowShareForm(true),
    },
    {
      id: 'search-platforms',
      label: 'Search platforms',
      icon: Search,
      verb: 'prompt',
      onSelect: () => {
        setInput('Search across my connected platforms for ');
        textareaRef.current?.focus();
      },
    },
    {
      id: 'web-search',
      label: 'Web search',
      icon: Globe,
      verb: 'prompt',
      onSelect: () => {
        setInput('Search the web for ');
        textareaRef.current?.focus();
      },
    },
    {
      id: 'refresh-sync',
      label: 'Refresh platforms',
      icon: RefreshCw,
      verb: 'prompt',
      onSelect: () => {
        setInput('Refresh my platform data');
        textareaRef.current?.focus();
      },
    },
    {
      id: 'save-memory',
      label: 'Save to memory',
      icon: Bookmark,
      verb: 'prompt',
      onSelect: () => {
        setInput('Remember that ');
        textareaRef.current?.focus();
      },
    },
    {
      id: 'attach-image',
      label: 'Attach image',
      icon: ImagePlus,
      verb: 'attach',
      onSelect: () => fileInputRef.current?.click(),
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

  const identityLabel = activeCommand ? formatCommandName(activeCommand) : 'Orchestrator';

  const panelTabs: WorkspacePanelTab[] = [
    {
      id: 'projects',
      label: 'Projects',
      content: <ProjectsPanel />,
    },
    {
      id: 'platforms',
      label: 'Platforms',
      content: <ContextPanel />,
    },
  ];

  return (
    <WorkspaceLayout
      identity={{
        icon: <Command className="w-5 h-5" />,
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
            {/* ADR-110/122: Bootstrap banner — shown after OAuth redirect */}
            {bootstrapProvider && (
              <div className="max-w-2xl mx-auto mb-4">
                <div className="flex items-center gap-3 p-4 rounded-lg border border-primary/20 bg-primary/5">
                  <span className="w-5 h-5 shrink-0 text-primary">
                    {getPlatformIcon(bootstrapProvider, 'w-full h-full')}
                  </span>
                  {bootstrapProject ? (
                    <div className="flex-1 flex items-center justify-between">
                      <div>
                        <p className="text-sm font-medium">
                          {bootstrapProject.title} is ready!
                        </p>
                        <p className="text-xs text-muted-foreground">
                          Your first digest will generate on schedule, or you can run it now.
                        </p>
                      </div>
                      <Link
                        href={`/projects/${bootstrapProject.project_slug}`}
                        className="text-xs font-medium text-primary hover:underline shrink-0 ml-3"
                      >
                        View project →
                      </Link>
                    </div>
                  ) : (
                    <div className="flex-1">
                      <p className="text-sm font-medium">
                        Connected {bootstrapProvider.charAt(0).toUpperCase() + bootstrapProvider.slice(1)}!
                      </p>
                      <p className="text-xs text-muted-foreground">
                        Syncing your data and setting up your project...
                      </p>
                    </div>
                  )}
                  <button
                    onClick={() => { setBootstrapProvider(null); setBootstrapProject(null); }}
                    className="text-muted-foreground hover:text-foreground shrink-0"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>
              </div>
            )}

            {messages.length === 0 && !isLoading && (
              <div className="py-8">
                <div className="text-center mb-8">
                  <Command className="w-10 h-10 text-muted-foreground/20 mx-auto mb-3" />
                  <h2 className="text-lg font-medium mb-1">
                    {onboardingState === 'no_platforms' ? 'Welcome to YARNNN' : 'What would you like to work on?'}
                  </h2>
                  <p className="text-sm text-muted-foreground max-w-sm mx-auto">
                    {onboardingState === 'no_platforms'
                      ? 'Connect a work platform to get started, or create a project from scratch.'
                      : 'Set up a project, search your platforms, or just ask anything.'}
                  </p>
                </div>
                <div className="max-w-md mx-auto space-y-3">
                  {onboardingState === 'no_platforms' && (
                    <>
                      <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Connect a platform</p>
                      <div className="grid grid-cols-2 gap-3">
                        {(['slack', 'notion'] as const).map((platform) => (
                          <button
                            key={platform}
                            onClick={() => handleConnect(platform)}
                            disabled={connecting !== null}
                            className={cn(
                              "flex items-center gap-3 p-4 rounded-lg border border-border hover:bg-muted/50 hover:border-primary/30 transition-colors text-left",
                              connecting === platform && "opacity-70",
                            )}
                          >
                            {connecting === platform
                              ? <Loader2 className="w-5 h-5 animate-spin text-muted-foreground" />
                              : getPlatformIcon(platform, 'w-5 h-5')
                            }
                            <span className="text-sm font-medium capitalize">{platform}</span>
                          </button>
                        ))}
                      </div>
                      <div className="flex items-center gap-3 py-1">
                        <div className="flex-1 border-t border-border" />
                        <span className="text-xs text-muted-foreground">or</span>
                        <div className="flex-1 border-t border-border" />
                      </div>
                    </>
                  )}
                  <button
                    onClick={() => {
                      setInput(NEW_PROJECT_PROMPT);
                      textareaRef.current?.focus();
                    }}
                    className="w-full flex items-center gap-3 p-4 rounded-lg border border-border hover:border-primary/30 hover:bg-primary/5 transition-colors text-left"
                  >
                    <span className="w-5 h-5 shrink-0 text-muted-foreground">
                      <Command className="w-full h-full" />
                    </span>
                    <div>
                      <span className="text-sm font-medium">New Project</span>
                      <span className="text-xs text-muted-foreground block">Start a custom project from scratch</span>
                    </div>
                  </button>
                  {onboardingState !== 'no_platforms' && (
                    <p className="text-xs text-muted-foreground/60 text-center px-1">{CHAT_PROMPT}</p>
                  )}
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
                <span className={cn(
                  "text-[10px] font-medium text-muted-foreground/70 tracking-wider block mb-1.5",
                  msg.role === 'user' ? 'uppercase' : 'font-brand text-[11px]'
                )}>
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

            {/* Create project cards — show verb */}
            {showCreateCards && (
              <div
                ref={createCardsRef}
                className="mb-2 p-3 rounded-xl border border-border bg-background shadow-sm animate-in fade-in slide-in-from-bottom-2 duration-150"
              >
                <div className="flex items-center justify-between mb-2">
                  <p className="text-xs font-medium text-muted-foreground">What kind of project?</p>
                  <button
                    type="button"
                    onClick={() => setShowCreateCards(false)}
                    className="text-muted-foreground hover:text-foreground transition-colors"
                  >
                    <X className="w-3.5 h-3.5" />
                  </button>
                </div>
                <button
                  onClick={() => {
                    sendMessage(NEW_PROJECT_PROMPT, { surface });
                    setShowCreateCards(false);
                  }}
                  className="w-full flex items-center gap-2 p-2.5 rounded-lg border border-border hover:border-primary/30 hover:bg-primary/5 transition-colors text-left"
                >
                  <span className="w-3.5 h-3.5 shrink-0 text-muted-foreground">
                    <Command className="w-full h-full" />
                  </span>
                  <div>
                    <span className="text-sm font-medium">New Project</span>
                    <span className="text-[11px] text-muted-foreground block">Start a custom project from scratch</span>
                  </div>
                </button>
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
                  File will be staged in user_shared/ for reference. Expires after 30 days.
                </p>
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
