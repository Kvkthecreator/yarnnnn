'use client';

/**
 * Workfloor — ADR-139: Home Surface
 *
 * Left: Agent cards grid + TP chat (workspace-scoped)
 * Right: [Tasks] [Workspace] tabs
 *
 * Replaces /orchestrator as the landing page.
 */

import { useState, useEffect, useRef, useCallback } from 'react';
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
  Upload,
  Search,
  Globe,
  RefreshCw,
  Bookmark,
  ChevronRight,
  FlaskConical,
  FileText,
  TrendingUp,
  Users,
  MessageCircle,
  BookOpen,
  Clock,
  AlertCircle,
} from 'lucide-react';
import { useTP } from '@/contexts/TPContext';
import { useDesk } from '@/contexts/DeskContext';
import { useFileAttachments } from '@/hooks/useFileAttachments';
import { Todo } from '@/types/desk';
import type { Agent, Task } from '@/types';
import ReactMarkdown from 'react-markdown';
import { cn } from '@/lib/utils';
import { CommandPicker } from '@/components/tp/CommandPicker';
import { PlusMenu, type PlusMenuAction } from '@/components/tp/PlusMenu';
import { ToolResultList } from '@/components/tp/ToolResultCard';
import { MessageBlocks } from '@/components/tp/InlineToolCall';
import { WorkspaceLayout, WorkspacePanelTab } from '@/components/desk/WorkspaceLayout';
import { api } from '@/lib/api/client';

// =============================================================================
// Archetype visuals (ADR-130/138)
// =============================================================================

const ARCHETYPE_CONFIG: Record<string, { icon: typeof FlaskConical; color: string; label: string }> = {
  // Primary ADR-140 types
  research:   { icon: FlaskConical,   color: 'text-blue-500',   label: 'Research Agent' },
  content:    { icon: FileText,       color: 'text-purple-500', label: 'Content Agent' },
  marketing:  { icon: TrendingUp,     color: 'text-pink-500',   label: 'Marketing Agent' },
  crm:        { icon: Users,          color: 'text-orange-500', label: 'CRM Agent' },
  slack_bot:  { icon: MessageCircle,  color: 'text-teal-500',   label: 'Slack Bot' },
  notion_bot: { icon: BookOpen,       color: 'text-indigo-500', label: 'Notion Bot' },
  // Legacy role mappings
  briefer:    { icon: FlaskConical,   color: 'text-blue-500',   label: 'Research Agent' },
  monitor:    { icon: FlaskConical,   color: 'text-blue-500',   label: 'Research Agent' },
  scout:      { icon: FlaskConical,   color: 'text-blue-500',   label: 'Research Agent' },
  digest:     { icon: FlaskConical,   color: 'text-blue-500',   label: 'Research Agent' },
  researcher: { icon: FlaskConical,   color: 'text-blue-500',   label: 'Research Agent' },
  analyst:    { icon: FlaskConical,   color: 'text-blue-500',   label: 'Research Agent' },
  synthesize: { icon: FlaskConical,   color: 'text-blue-500',   label: 'Research Agent' },
  custom:     { icon: FlaskConical,   color: 'text-blue-500',   label: 'Research Agent' },
  drafter:    { icon: FileText,       color: 'text-purple-500', label: 'Content Agent' },
  writer:     { icon: FileText,       color: 'text-purple-500', label: 'Content Agent' },
  planner:    { icon: FileText,       color: 'text-purple-500', label: 'Content Agent' },
  prepare:    { icon: FileText,       color: 'text-purple-500', label: 'Content Agent' },
};

function getArchetype(role: string) {
  return ARCHETYPE_CONFIG[role] || ARCHETYPE_CONFIG.research;
}

// =============================================================================
// Agent Card — OpenClaw-inspired status display
// =============================================================================

// Type accent colors for card borders and backgrounds
const ARCHETYPE_ACCENTS: Record<string, { border: string; bg: string; glow: string }> = {
  // Keyed by resolved label (lowercase) for lookup from getArchetype
  'research agent':  { border: 'border-blue-500/30',   bg: 'bg-blue-500/5',   glow: 'hover:shadow-blue-500/10' },
  'content agent':   { border: 'border-purple-500/30', bg: 'bg-purple-500/5', glow: 'hover:shadow-purple-500/10' },
  'marketing agent': { border: 'border-pink-500/30',   bg: 'bg-pink-500/5',   glow: 'hover:shadow-pink-500/10' },
  'crm agent':       { border: 'border-orange-500/30', bg: 'bg-orange-500/5', glow: 'hover:shadow-orange-500/10' },
  'slack bot':       { border: 'border-teal-500/30',   bg: 'bg-teal-500/5',   glow: 'hover:shadow-teal-500/10' },
  'notion bot':      { border: 'border-indigo-500/30', bg: 'bg-indigo-500/5', glow: 'hover:shadow-indigo-500/10' },
};

const DEFAULT_ACCENT = { border: 'border-border', bg: 'bg-muted/30', glow: '' };

function getAccent(role: string) {
  const archetype = getArchetype(role);
  return ARCHETYPE_ACCENTS[archetype.label.toLowerCase()] || DEFAULT_ACCENT;
}

function AgentCard({ agent }: { agent: Agent }) {
  const archetype = getArchetype(agent.role);
  const accent = getAccent(agent.role);
  const Icon = archetype.icon;

  // Status derivation — OpenClaw-inspired prominent status
  const isRunning = agent.latest_version_status === 'generating';
  const hasFailed = agent.latest_version_status === 'failed';
  const isPaused = agent.status === 'paused';

  const statusLabel = isRunning ? 'WORKING' : isPaused ? 'PAUSED' : hasFailed ? 'ERROR' : 'READY';
  const statusColor = isRunning ? 'text-blue-500' : isPaused ? 'text-amber-500' : hasFailed ? 'text-red-500' : 'text-green-500';
  const statusDot = isRunning ? 'bg-blue-500 animate-pulse' : isPaused ? 'bg-amber-500' : hasFailed ? 'bg-red-500' : 'bg-green-500';

  const lastRunLabel = agent.last_run_at
    ? formatRelativeTime(agent.last_run_at)
    : 'Awaiting first run';

  return (
    <Link
      href={`/agents/${agent.id}`}
      className={cn(
        'group flex flex-col rounded-xl border p-4 transition-all hover:shadow-md',
        accent.border,
        accent.bg,
        accent.glow,
      )}
    >
      {/* Status bar — prominent, OpenClaw-style */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-1.5">
          <span className={cn('w-2 h-2 rounded-full shrink-0', statusDot)} />
          <span className={cn('text-[10px] font-semibold uppercase tracking-widest', statusColor)}>
            {statusLabel}
          </span>
        </div>
        <span className="text-[10px] text-muted-foreground/50">{lastRunLabel}</span>
      </div>

      {/* Agent identity — icon + name prominent */}
      <div className="flex items-center gap-3 mb-2">
        <div className={cn(
          'w-9 h-9 rounded-lg flex items-center justify-center border',
          accent.border,
          'bg-background',
        )}>
          <Icon className={cn('w-5 h-5', archetype.color)} />
        </div>
        <div className="min-w-0 flex-1">
          <div className="text-sm font-medium truncate">{agent.title}</div>
          <div className="text-[11px] text-muted-foreground">{archetype.label}</div>
        </div>
      </div>

      {/* Description / tagline from agent instructions (first line) */}
      {agent.description && (
        <p className="text-[11px] text-muted-foreground/70 line-clamp-2 mt-1">
          {agent.description}
        </p>
      )}
    </Link>
  );
}

// =============================================================================
// Tasks Panel
// =============================================================================

function TasksPanel() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.tasks.list().then(setTasks).catch(() => setTasks([])).finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center p-6">
        <Loader2 className="w-4 h-4 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (tasks.length === 0) {
    return (
      <div className="p-4 text-center">
        <p className="text-sm text-muted-foreground">No tasks yet.</p>
        <p className="text-xs text-muted-foreground/60 mt-1">
          Tell the orchestrator what work you need done.
        </p>
      </div>
    );
  }

  return (
    <div className="divide-y divide-border">
      {tasks.map((task) => (
        <Link
          key={task.id}
          href={`/tasks/${task.slug}`}
          className="flex items-center justify-between p-3 hover:bg-muted/50 transition-colors group"
        >
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2">
              <span className={cn(
                'w-2 h-2 rounded-full shrink-0',
                task.status === 'active' ? 'bg-green-500' :
                task.status === 'paused' ? 'bg-amber-500' :
                task.status === 'completed' ? 'bg-blue-500' : 'bg-gray-400'
              )} />
              <span className="text-sm font-medium truncate">{task.title}</span>
            </div>
            <div className="flex items-center gap-3 mt-0.5 text-[11px] text-muted-foreground">
              {task.schedule && <span>{task.schedule}</span>}
              {task.last_run_at && <span>{formatRelativeTime(task.last_run_at)}</span>}
              {task.agent_slugs?.[0] && <span>{task.agent_slugs[0]}</span>}
            </div>
          </div>
          <ChevronRight className="w-4 h-4 text-muted-foreground/50 group-hover:text-foreground transition-colors shrink-0" />
        </Link>
      ))}
    </div>
  );
}

// =============================================================================
// Workspace Panel (identity + brand + platforms)
// =============================================================================

function WorkspacePanel() {
  const [identity, setIdentity] = useState<{ name?: string; role?: string; company?: string; summary?: string } | null>(null);
  const [brandContent, setBrandContent] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      api.profile.get().catch(() => null),
      api.brand.get().catch(() => ({ content: null, exists: false })),
    ]).then(([profile, brand]) => {
      if (profile) setIdentity(profile);
      if (brand.exists) setBrandContent(brand.content);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center p-6">
        <Loader2 className="w-4 h-4 animate-spin text-muted-foreground" />
      </div>
    );
  }

  // Workspace file slots — always show structure, even when empty
  const fileSlots = [
    { label: 'IDENTITY.md', path: '/workspace/IDENTITY.md', content: identity?.name ? `${identity.name}${identity.role ? ` — ${identity.role}` : ''}${identity.company ? ` at ${identity.company}` : ''}` : null },
    { label: 'BRAND.md', path: '/workspace/BRAND.md', content: brandContent },
    { label: 'preferences.md', path: '/memory/preferences.md', content: null },
    { label: 'notes.md', path: '/memory/notes.md', content: null },
  ];

  return (
    <div className="p-3 space-y-4">
      {/* Workspace files — always show all slots */}
      <div>
        <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-2">Workspace Files</p>
        <div className="space-y-1.5">
          {fileSlots.map(slot => (
            <div
              key={slot.label}
              className={cn(
                'flex items-center justify-between px-3 py-2 rounded-lg border text-xs',
                slot.content
                  ? 'border-border bg-background'
                  : 'border-dashed border-border/50 bg-muted/20'
              )}
            >
              <div className="min-w-0 flex-1">
                <span className="font-medium text-foreground/80">{slot.label}</span>
                {slot.content ? (
                  <p className="text-muted-foreground truncate mt-0.5">{slot.content}</p>
                ) : (
                  <p className="text-muted-foreground/40 mt-0.5">Empty</p>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Knowledge base */}
      <div>
        <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-2">Knowledge Base</p>
        <div className="px-3 py-2 rounded-lg border border-dashed border-border/50 bg-muted/20 text-xs text-muted-foreground/40">
          /knowledge/ — accumulates from platform sync + agent outputs
        </div>
      </div>

      {/* Platform status */}
      <div>
        <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-2">Platforms</p>
        <div className="flex gap-2">
          <Link href="/integrations" className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-border text-xs hover:bg-muted/50 transition-colors">
            Slack
          </Link>
          <Link href="/integrations" className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-border text-xs hover:bg-muted/50 transition-colors">
            Notion
          </Link>
        </div>
      </div>
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

function formatTokenCount(tokens: number): string {
  if (tokens >= 1000) return `${(tokens / 1000).toFixed(1)}k`;
  return tokens.toString();
}

// =============================================================================
// Main Workfloor Page
// =============================================================================

export default function WorkfloorPage() {
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

  // Load global (unscoped) history
  useEffect(() => {
    loadScopedHistory();
  }, [loadScopedHistory]);

  const searchParams = useSearchParams();
  const router = useRouter();

  const [input, setInput] = useState('');
  const [commandPickerOpen, setCommandPickerOpen] = useState(false);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [agentsLoading, setAgentsLoading] = useState(true);
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

  // Load agents
  useEffect(() => {
    api.agents.list().then(setAgents).catch(() => setAgents([])).finally(() => setAgentsLoading(false));
  }, []);

  // Handle ?create param
  useEffect(() => {
    if (searchParams?.has('create')) {
      setInput('I want to set up new agents');
      textareaRef.current?.focus();
      router.replace(HOME_ROUTE, { scroll: false });
    }
  }, [searchParams, router]);

  // Handle post-OAuth redirect
  const [bootstrapProvider, setBootstrapProvider] = useState<string | null>(null);
  useEffect(() => {
    const provider = searchParams?.get('provider');
    const connStatus = searchParams?.get('status');
    if (provider && connStatus === 'connected') {
      setBootstrapProvider(provider);
      router.replace(HOME_ROUTE, { scroll: false });
    }
  }, [searchParams, router]);

  // Auto-scroll
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, status]);

  // Focus on mount
  useEffect(() => {
    textareaRef.current?.focus();
  }, []);

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

  // Command picker
  const commandQuery = input.startsWith('/') ? input.slice(1).split(' ')[0] : null;
  useEffect(() => {
    setCommandPickerOpen(commandQuery !== null && !input.includes(' '));
  }, [commandQuery, input]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if ((!input.trim() && attachments.length === 0) || isLoading) return;
    const images = await getImagesForAPI();
    sendMessage(input, { surface, images: images.length > 0 ? images : undefined });
    setInput('');
    clearAttachments();
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

  // Plus menu actions
  const plusMenuActions: PlusMenuAction[] = [
    { id: 'upload-file', label: 'Upload file', icon: Upload, verb: 'attach', onSelect: () => fileInputRef.current?.click() },
    { id: 'search-platforms', label: 'Search platforms', icon: Search, verb: 'prompt', onSelect: () => { setInput('Search across my connected platforms for '); textareaRef.current?.focus(); } },
    { id: 'web-search', label: 'Web search', icon: Globe, verb: 'prompt', onSelect: () => { setInput('Search the web for '); textareaRef.current?.focus(); } },
    { id: 'refresh-sync', label: 'Refresh platforms', icon: RefreshCw, verb: 'prompt', onSelect: () => { setInput('Refresh my platform data'); textareaRef.current?.focus(); } },
    { id: 'save-memory', label: 'Save to memory', icon: Bookmark, verb: 'prompt', onSelect: () => { setInput('Remember that '); textareaRef.current?.focus(); } },
  ];

  const identityLabel = activeCommand
    ? activeCommand.split('-').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ')
    : 'Workfloor';

  const panelTabs: WorkspacePanelTab[] = [
    { id: 'tasks', label: 'Tasks', content: <TasksPanel /> },
    { id: 'workspace', label: 'Workspace', content: <WorkspacePanel /> },
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
      panelDefaultPct={35}
    >
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

        {fileError && (
          <div className="absolute top-4 left-1/2 -translate-x-1/2 z-50 px-3 py-1.5 rounded-lg bg-destructive text-destructive-foreground text-xs font-medium shadow-lg animate-in fade-in slide-in-from-top-2 duration-200">
            {fileError}
          </div>
        )}

        {/* Todos progress */}
        {todos.length > 0 && todos.some(t => t.status === 'in_progress') && (
          <div className="px-4 py-3 border-b border-border bg-muted/20 shrink-0">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-medium text-muted-foreground">Progress</span>
              <span className="text-xs text-muted-foreground">
                {todos.filter(t => t.status === 'completed').length}/{todos.length}
              </span>
            </div>
            <div className="space-y-1.5 max-h-28 overflow-y-auto">
              {todos.map((todo, i) => <TodoItem key={i} todo={todo} />)}
            </div>
          </div>
        )}

        {/* Main scrollable area: agents grid + chat messages */}
        <div className="flex-1 overflow-y-auto px-5 sm:px-6 py-4 space-y-4">
          <div className="max-w-3xl mx-auto w-full space-y-4">

            {/* Bootstrap banner */}
            {bootstrapProvider && (
              <div className="flex items-center gap-3 p-4 rounded-lg border border-primary/20 bg-primary/5">
                <div className="flex-1">
                  <p className="text-sm font-medium">
                    Connected {bootstrapProvider.charAt(0).toUpperCase() + bootstrapProvider.slice(1)}!
                  </p>
                  <p className="text-xs text-muted-foreground">Syncing your data...</p>
                </div>
                <button onClick={() => setBootstrapProvider(null)} className="text-muted-foreground hover:text-foreground shrink-0">
                  <X className="w-4 h-4" />
                </button>
              </div>
            )}

            {/* Agent office — always visible, OpenClaw-inspired */}
            {!agentsLoading && (() => {
              const active = agents.filter(a => a.status !== 'archived');
              const working = active.filter(a => a.latest_version_status === 'generating');
              const ready = active.filter(a => a.status === 'active' && a.latest_version_status !== 'generating');
              const paused = active.filter(a => a.status === 'paused');

              return (
                <div>
                  <div className="flex items-center justify-between mb-3">
                    <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
                      Your Team {active.length > 0 && <span className="opacity-50">({active.length})</span>}
                    </p>
                    {active.length > 0 && (
                      <div className="flex items-center gap-3 text-[10px]">
                        {working.length > 0 && (
                          <span className="flex items-center gap-1 text-blue-500">
                            <span className="w-1.5 h-1.5 rounded-full bg-blue-500 animate-pulse" />
                            {working.length} working
                          </span>
                        )}
                        <span className="flex items-center gap-1 text-green-500">
                          <span className="w-1.5 h-1.5 rounded-full bg-green-500" />
                          {ready.length} ready
                        </span>
                        {paused.length > 0 && (
                          <span className="flex items-center gap-1 text-amber-500">
                            <span className="w-1.5 h-1.5 rounded-full bg-amber-500" />
                            {paused.length} paused
                          </span>
                        )}
                      </div>
                    )}
                  </div>

                  {active.length > 0 ? (
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                      {active.map(agent => (
                        <AgentCard key={agent.id} agent={agent} />
                      ))}
                    </div>
                  ) : (
                    /* Empty office — placeholder desks */
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                      {[
                        { label: 'Monitor', desc: 'Watches your domain', color: 'border-green-500/20 bg-green-500/5' },
                        { label: 'Researcher', desc: 'Investigates with depth', color: 'border-blue-500/20 bg-blue-500/5' },
                      ].map(slot => (
                        <div
                          key={slot.label}
                          className={cn(
                            'flex flex-col items-center justify-center p-6 rounded-xl border border-dashed transition-colors',
                            slot.color,
                            'opacity-40',
                          )}
                        >
                          <p className="text-xs font-medium text-muted-foreground">{slot.label}</p>
                          <p className="text-[10px] text-muted-foreground/60 mt-0.5">{slot.desc}</p>
                        </div>
                      ))}
                    </div>
                  )}

                  {active.length === 0 && (
                    <p className="text-xs text-muted-foreground/50 text-center mt-3">
                      Describe your work below — agents will appear here.
                    </p>
                  )}
                </div>
              );
            })()}

            {/* Starter cards — shown when no messages yet */}
            {messages.length === 0 && !isLoading && (
              <div className="max-w-md mx-auto space-y-3 mt-4">
                <Link
                  href="/onboarding"
                  className="w-full flex items-center gap-3 p-4 rounded-lg border border-border hover:border-primary/30 hover:bg-primary/5 transition-colors text-left"
                >
                  <Upload className="w-5 h-5 shrink-0 text-muted-foreground" />
                  <div>
                    <span className="text-sm font-medium">Set up your team</span>
                    <span className="text-xs text-muted-foreground block">Upload files or describe your work</span>
                  </div>
                </Link>
                <button
                  onClick={() => { setInput('I need help with '); textareaRef.current?.focus(); }}
                  className="w-full flex items-center gap-3 p-4 rounded-lg border border-border hover:border-primary/30 hover:bg-primary/5 transition-colors text-left"
                >
                  <Command className="w-5 h-5 shrink-0 text-muted-foreground" />
                  <div>
                    <span className="text-sm font-medium">Or just tell me</span>
                    <span className="text-xs text-muted-foreground block">Describe what you need and I&apos;ll set it up</span>
                  </div>
                </button>
              </div>
            )}

            {/* Chat messages */}
            {messages.map(msg => (
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
                      <img key={i} src={`data:${img.mediaType};base64,${img.data}`} alt={`Attachment ${i + 1}`} className="max-w-[200px] max-h-[150px] object-contain rounded border border-border" />
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
                      <button key={i} onClick={() => respondToClarification(option)} className="px-4 py-2 text-sm rounded-lg border border-primary/30 bg-primary/5 text-primary hover:bg-primary/15 hover:border-primary/50 transition-all font-medium shadow-sm">
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

        {/* Input */}
        <div className="px-4 pb-4 pt-2 shrink-0" style={{ paddingBottom: 'max(1rem, env(safe-area-inset-bottom))' }}>
          <div className="relative max-w-2xl mx-auto">
            <CommandPicker
              query={commandQuery ?? ''}
              onSelect={handleCommandSelect}
              onClose={() => setCommandPickerOpen(false)}
              isOpen={commandPickerOpen}
            />

            <form onSubmit={handleSubmit}>
              {attachmentPreviews.length > 0 && (
                <div className="flex flex-wrap gap-2 mb-2 p-2 rounded-t-lg border border-b-0 border-border bg-muted/30">
                  {attachmentPreviews.map((preview, index) => (
                    <div key={index} className="relative group">
                      <img src={preview} alt={`Attachment ${index + 1}`} className="h-16 w-16 object-cover rounded-md border border-border" />
                      <button type="button" onClick={() => removeAttachment(index)} className="absolute -top-1.5 -right-1.5 w-5 h-5 bg-background border border-border rounded-full flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity hover:bg-destructive hover:text-destructive-foreground">
                        <X className="w-3 h-3" />
                      </button>
                    </div>
                  ))}
                </div>
              )}

              <div className={cn(
                'flex items-end gap-2 border border-border bg-background shadow-sm transition-colors',
                attachmentPreviews.length > 0 ? 'rounded-b-xl border-t-0' : 'rounded-xl',
                'focus-within:ring-2 focus-within:ring-primary/50 focus-within:shadow-md'
              )}>
                <input ref={fileInputRef} type="file" accept="image/*,.pdf,.docx,.txt,.md" multiple onChange={handleFileSelect} className="hidden" />
                <PlusMenu actions={plusMenuActions} disabled={isLoading} />
                <textarea
                  ref={textareaRef}
                  value={input}
                  onChange={e => setInput(e.target.value)}
                  onKeyDown={handleKeyDown}
                  onPaste={handlePaste}
                  disabled={isLoading}
                  enterKeyHint="send"
                  placeholder={status.type === 'clarify' ? 'Type your answer...' : 'Ask anything or type / for skills...'}
                  rows={1}
                  className="flex-1 py-3 pr-2 text-base sm:text-sm bg-transparent resize-none focus:outline-none disabled:opacity-50 max-h-[200px]"
                />
                <button type="submit" disabled={isLoading || (!input.trim() && attachments.length === 0)} className="shrink-0 p-3 text-primary hover:text-primary/80 disabled:text-muted-foreground disabled:opacity-50 transition-colors" aria-label="Send">
                  <Send className="w-5 h-5" />
                </button>
              </div>

              <div className="mt-1.5 flex items-center justify-between text-[10px] text-muted-foreground/60">
                <span className="hidden sm:inline">Enter to send, Shift+Enter for new line</span>
                <span className="sm:hidden">Tap send</span>
                {tokenUsage && (
                  <span className="font-mono tabular-nums">{formatTokenCount(tokenUsage.totalTokens)} tokens</span>
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
      <span className={cn(
        'text-xs',
        todo.status === 'completed' && 'text-muted-foreground line-through',
        todo.status === 'in_progress' && 'text-foreground font-medium'
      )}>
        {todo.status === 'in_progress' ? todo.activeForm || todo.content : todo.content}
      </span>
    </div>
  );
}
