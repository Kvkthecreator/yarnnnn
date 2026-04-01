'use client';

/**
 * Workfloor — ADR-139 v4: Habbo-style overlay layout
 *
 * Isometric room fills viewport as ambient backdrop.
 * Floating panels overlay the room:
 * - Left: Tasks/Context panel (collapsible, tabbed)
 * - Right: TP Chat panel (collapsible)
 * - Bottom: Action bar (New Task, Update Context) + suggestion chips
 *
 * No vertical stacking — everything visible in one screen.
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import { HOME_ROUTE } from '@/lib/routes';
import {
  Loader2,
  X,
  MessageCircle,
  Send,
  Upload,
  Globe,
  Settings2,
  ListChecks,
  ChevronDown,
  ChevronUp,
  Plus,
} from 'lucide-react';
import { useTP } from '@/contexts/TPContext';
import { useDesk } from '@/contexts/DeskContext';
import { useFileAttachments } from '@/hooks/useFileAttachments';
import type { Agent, Task, Document } from '@/types';
import { cn } from '@/lib/utils';
import { api } from '@/lib/api/client';
import { WorkspaceDashboard } from '@/components/workspace/WorkspaceDashboard';
import { IsometricRoom } from '@/components/workfloor/IsometricRoom';
import { WorkspaceTree } from '@/components/workspace/WorkspaceTree';
import { ContentViewer } from '@/components/workspace/ContentViewer';
import { CommandPicker } from '@/components/tp/CommandPicker';
import { PlusMenu, type PlusMenuAction } from '@/components/tp/PlusMenu';
import { MessageBlocks } from '@/components/tp/InlineToolCall';
import { ToolResultList } from '@/components/tp/ToolResultCard';
import { MarkdownRenderer } from '@/components/shared/MarkdownRenderer';
import {
  InlineActionCard,
  type ActionCardConfig,
  contextUpdateCard,
  NEW_TASK_CARD,
  IDENTITY_SETUP_CARD,
  BRAND_SETUP_CARD,
} from '@/components/tp/InlineActionCard';


// =============================================================================
// Tabs — Tasks & Context content
// =============================================================================

function TasksTab({ tasks }: { tasks: Task[] }) {
  const active = tasks.filter(t => t.status !== 'archived');

  if (active.length === 0) {
    return (
      <div className="py-6 px-2 text-center">
        <p className="text-[13px] text-muted-foreground/50">No tasks yet</p>
        <p className="text-[11px] text-muted-foreground/30 mt-1">Use + New Task to create one via chat</p>
      </div>
    );
  }

  return (
    <div className="space-y-0.5">
      {active.map(task => (
        <Link key={task.id} href={`/tasks/${task.slug}`} className="flex items-center justify-between px-2 py-1.5 rounded hover:bg-muted/50 transition-colors text-[13px]">
          <div className="flex items-center gap-1.5 min-w-0">
            <span className={cn('w-1.5 h-1.5 rounded-full shrink-0', task.status === 'active' ? 'bg-green-500' : 'bg-amber-500')} />
            <span className="truncate">{task.title || task.slug}</span>
          </div>
          {task.schedule && <span className="text-muted-foreground/30 shrink-0 ml-2 text-[11px]">{task.schedule}</span>}
        </Link>
      ))}
    </div>
  );
}

function IdentityTab() {
  const [content, setContent] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState('');
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    api.identity.get().then(res => { if (res?.exists && res.content) { setContent(res.content); setDraft(res.content); } }).catch(() => {}).finally(() => setLoading(false));
  }, []);

  const handleSave = async () => {
    setSaving(true);
    try {
      await api.identity.save(draft);
      setContent(draft);
      setEditing(false);
    } catch (e) { console.error(e); }
    setSaving(false);
  };

  if (loading) return <div className="flex items-center justify-center p-4"><Loader2 className="w-3 h-3 animate-spin text-muted-foreground" /></div>;

  return (
    <div className="space-y-2">
      {editing ? (
        <>
          <textarea
            value={draft}
            onChange={e => setDraft(e.target.value)}
            rows={8}
            placeholder="# Identity\n\n## Who\nName, Role at Company..."
            className="w-full text-xs bg-muted/30 border border-border rounded px-2.5 py-2 focus:outline-none focus:ring-1 focus:ring-primary/50 resize-y font-mono"
          />
          <div className="flex gap-1.5 pt-0.5">
            <button onClick={handleSave} disabled={saving} className="px-2.5 py-1 text-[10px] font-medium rounded bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50">
              {saving ? '...' : 'Save'}
            </button>
            <button onClick={() => { setDraft(content || ''); setEditing(false); }} className="px-2.5 py-1 text-[10px] font-medium rounded border border-border text-muted-foreground hover:bg-muted/50">
              Cancel
            </button>
          </div>
        </>
      ) : content ? (
        <>
          <div className="text-[13px] text-muted-foreground/70 bg-muted/20 rounded-lg p-3 prose prose-sm dark:prose-invert max-w-none">
            <MarkdownRenderer content={content} compact />
          </div>
          <button onClick={() => setEditing(true)} className="text-[11px] text-muted-foreground/40 hover:text-muted-foreground/60 mt-1">
            Edit
          </button>
        </>
      ) : (
        <div className="py-4 px-2">
          <p className="text-[13px] text-muted-foreground/60 mb-3">Your identity helps agents understand who you are and what you care about.</p>
          <p className="text-[11px] text-muted-foreground/40 mb-3">Use the <span className="font-medium text-muted-foreground/60">Update</span> button above to tell the chat, or write directly:</p>
          <button onClick={() => { setDraft(''); setEditing(true); }} className="text-[11px] text-primary hover:underline font-medium">
            Write identity
          </button>
        </div>
      )}
    </div>
  );
}

function BrandTab() {
  const [content, setContent] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState('');
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    api.brand.get().then(res => { if (res?.exists && res.content) { setContent(res.content); setDraft(res.content); } }).catch(() => {}).finally(() => setLoading(false));
  }, []);

  const handleSave = async () => {
    setSaving(true);
    try {
      await api.brand.save(draft);
      setContent(draft);
      setEditing(false);
    } catch (e) { console.error(e); }
    setSaving(false);
  };

  if (loading) return <div className="flex items-center justify-center p-4"><Loader2 className="w-3 h-3 animate-spin text-muted-foreground" /></div>;

  return (
    <div className="space-y-2">
      {editing ? (
        <>
          <textarea
            value={draft}
            onChange={e => setDraft(e.target.value)}
            rows={8}
            placeholder="Brand voice, tone, terminology, style guidelines..."
            className="w-full text-xs bg-muted/30 border border-border rounded px-2.5 py-2 mx-0 focus:outline-none focus:ring-1 focus:ring-primary/50 resize-y"
          />
          <div className="flex gap-1.5 px-0 pt-0.5">
            <button onClick={handleSave} disabled={saving} className="px-2.5 py-1 text-[10px] font-medium rounded bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50">
              {saving ? '...' : 'Save'}
            </button>
            <button onClick={() => { setDraft(content || ''); setEditing(false); }} className="px-2.5 py-1 text-[10px] font-medium rounded border border-border text-muted-foreground hover:bg-muted/50">
              Cancel
            </button>
          </div>
        </>
      ) : content ? (
        <>
          <div className="text-[13px] text-muted-foreground/70 bg-muted/20 rounded-lg p-3 prose prose-sm dark:prose-invert max-w-none">
            <MarkdownRenderer content={content} compact />
          </div>
          <button onClick={() => setEditing(true)} className="text-[11px] text-muted-foreground/40 hover:text-muted-foreground/60 mt-1">
            Edit
          </button>
        </>
      ) : (
        <div className="py-4 px-2">
          <p className="text-[13px] text-muted-foreground/60 mb-3">Your brand guide shapes how agents write — tone, terminology, audience awareness.</p>
          <p className="text-[11px] text-muted-foreground/40 mb-3">Use the <span className="font-medium text-muted-foreground/60">Update</span> button above to tell the chat, or write directly:</p>
          <button onClick={() => { setDraft(''); setEditing(true); }} className="text-[11px] text-primary hover:underline font-medium">
            Write brand guide
          </button>
        </div>
      )}
    </div>
  );
}

function DocumentsTab() {
  const [docs, setDocs] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.documents.list()
      .then(res => setDocs(res.documents || []))
      .catch(() => [])
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="flex items-center justify-center p-4"><Loader2 className="w-3 h-3 animate-spin text-muted-foreground" /></div>;

  function formatSize(bytes: number): string {
    if (bytes < 1024) return `${bytes}B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)}KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)}MB`;
  }

  return (
    <div className="space-y-1">
      {docs.length > 0 ? docs.map(doc => (
        <div key={doc.id} className="flex items-center justify-between px-2 py-1.5 rounded-lg text-[13px]">
          <div className="flex items-center gap-1.5 min-w-0">
            <span className={cn('w-1.5 h-1.5 rounded-full shrink-0',
              doc.processing_status === 'completed' ? 'bg-green-500' :
              doc.processing_status === 'failed' ? 'bg-red-500' :
              'bg-amber-500'
            )} />
            <span className="truncate">{doc.filename}</span>
          </div>
          <span className="text-muted-foreground/40 shrink-0 ml-2 text-[11px]">{formatSize(doc.file_size)}</span>
        </div>
      )) : (
        <div className="py-4 px-2">
          <p className="text-[13px] text-muted-foreground/60 mb-2">Documents give agents source material to work from — pitch decks, reports, guidelines.</p>
          <p className="text-[11px] text-muted-foreground/40">Upload files via the chat input (+) or drag &amp; drop into the conversation.</p>
        </div>
      )}
    </div>
  );
}

// =============================================================================
// Floating Chat Panel
// =============================================================================

function ChatPanel({ taskCount, pendingActionConfig, surfaceOverride }: { taskCount: number; pendingActionConfig?: ActionCardConfig | null; surfaceOverride?: any }) {
  const {
    messages,
    sendMessage,
    isLoading,
    status,
    pendingClarification,
    respondToClarification,
    tokenUsage,
  } = useTP();
  const { surface: deskSurface } = useDesk();
  const surface = surfaceOverride || deskSurface; // File selection overrides desk surface

  const [input, setInput] = useState('');
  const [commandPickerOpen, setCommandPickerOpen] = useState(false);
  const [actionCard, setActionCard] = useState<ActionCardConfig | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Accept action card from parent (panel header buttons)
  useEffect(() => {
    if (pendingActionConfig) {
      setActionCard(pendingActionConfig);
    }
  }, [pendingActionConfig]);

  const handleActionSelect = (message: string) => {
    // If message ends with a space, it's a prefill — don't send yet
    if (message.endsWith(' ')) {
      setInput(message);
      setActionCard(null);
      textareaRef.current?.focus();
    } else {
      sendMessage(message, { surface });
      setActionCard(null);
    }
  };

  const {
    attachments,
    attachmentPreviews,
    error: fileError,
    uploadedDocs,
    handleFileSelect,
    handlePaste,
    removeAttachment,
    clearAttachments,
    getImagesForAPI,
    fileInputRef,
  } = useFileAttachments();

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, status]);

  const adjustHeight = useCallback(() => {
    const ta = textareaRef.current;
    if (ta) { ta.style.height = 'auto'; ta.style.height = `${Math.min(ta.scrollHeight, 150)}px`; }
  }, []);
  useEffect(() => { adjustHeight(); }, [input, adjustHeight]);

  const commandQuery = input.startsWith('/') ? input.slice(1).split(' ')[0] : null;
  useEffect(() => { setCommandPickerOpen(commandQuery !== null && !input.includes(' ')); }, [commandQuery, input]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if ((!input.trim() && attachments.length === 0) || isLoading) return;
    const images = await getImagesForAPI();
    sendMessage(input, { surface, images: images.length > 0 ? images : undefined });
    setInput('');
    clearAttachments();
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSubmit(e as unknown as React.FormEvent); }
  };

  // PlusMenu: structured action cards for create/update, direct prefill for simple actions
  const plusMenuActions: PlusMenuAction[] = [
    { id: 'create-task', label: 'Create a task', icon: ListChecks, verb: 'prompt', onSelect: () => setActionCard(NEW_TASK_CARD) },
    { id: 'update-identity', label: 'Update identity', icon: Settings2, verb: 'prompt', onSelect: () => setActionCard(IDENTITY_SETUP_CARD) },
    { id: 'web-search', label: 'Web search', icon: Globe, verb: 'prompt', onSelect: () => { setInput('Search the web for '); textareaRef.current?.focus(); } },
    { id: 'upload-file', label: 'Upload file', icon: Upload, verb: 'attach', onSelect: () => fileInputRef.current?.click() },
  ];

  return (
    <div className="flex flex-col h-full">
      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-3 py-3 space-y-2.5">
        {messages.length === 0 && !isLoading && (
          <div className="py-6 space-y-3">
            <div className="text-center">
              <MessageCircle className="w-5 h-5 text-muted-foreground/15 mx-auto mb-1.5" />
              <p className="text-[11px] text-muted-foreground/40">
                {taskCount === 0 ? 'Get started' : 'Quick actions'}
              </p>
            </div>
            <div className="flex flex-col gap-1.5 px-2">
              {taskCount === 0 ? (
                <>
                  <button
                    onClick={() => setActionCard(IDENTITY_SETUP_CARD)}
                    className="text-left text-[11px] px-3 py-2 rounded-lg border border-border/50 text-muted-foreground hover:text-foreground hover:border-border hover:bg-muted/50 transition-colors"
                  >
                    Tell me about myself and my work
                  </button>
                  <button
                    onClick={() => setActionCard(NEW_TASK_CARD)}
                    className="text-left text-[11px] px-3 py-2 rounded-lg border border-border/50 text-muted-foreground hover:text-foreground hover:border-border hover:bg-muted/50 transition-colors"
                  >
                    What can you track for me?
                  </button>
                  <button
                    onClick={() => { sendMessage('Help me get set up', { surface }); }}
                    className="text-left text-[11px] px-3 py-2 rounded-lg border border-border/50 text-muted-foreground hover:text-foreground hover:border-border hover:bg-muted/50 transition-colors"
                  >
                    Help me get set up
                  </button>
                </>
              ) : (
                <>
                  <button
                    onClick={() => { sendMessage('How are my tasks doing?', { surface }); }}
                    className="text-left text-[11px] px-3 py-2 rounded-lg border border-border/50 text-muted-foreground hover:text-foreground hover:border-border hover:bg-muted/50 transition-colors"
                  >
                    How are my tasks doing?
                  </button>
                  <button
                    onClick={() => setActionCard(NEW_TASK_CARD)}
                    className="text-left text-[11px] px-3 py-2 rounded-lg border border-border/50 text-muted-foreground hover:text-foreground hover:border-border hover:bg-muted/50 transition-colors"
                  >
                    Create a new task
                  </button>
                </>
              )}
            </div>
          </div>
        )}

        {messages.map(msg => (
          <div key={msg.id} className={cn('text-[13px] rounded-2xl px-3 py-2 max-w-[92%]', msg.role === 'user' ? 'bg-primary/10 ml-auto rounded-br-md' : 'bg-muted rounded-bl-md')}>
            <span className={cn("text-[9px] font-medium text-muted-foreground/50 tracking-wider block mb-1", msg.role === 'user' ? 'uppercase' : 'font-brand text-[10px]')}>
              {msg.role === 'user' ? 'You' : 'yarnnn'}
            </span>
            {msg.blocks && msg.blocks.length > 0 ? (
              <MessageBlocks blocks={msg.blocks} />
            ) : msg.role === 'assistant' && !msg.content && isLoading ? (
              <div className="flex items-center gap-1.5 text-muted-foreground text-xs"><Loader2 className="w-3 h-3 animate-spin" />Thinking...</div>
            ) : (
              <>
                {msg.role === 'assistant' ? (
                  <MarkdownRenderer content={msg.content} compact />
                ) : (
                  <p className="whitespace-pre-wrap">{msg.content}</p>
                )}
                {msg.toolResults && msg.toolResults.length > 0 && <ToolResultList results={msg.toolResults} compact />}
              </>
            )}
          </div>
        ))}

        {status.type === 'thinking' && messages[messages.length - 1]?.role === 'user' && (
          <div className="flex items-center gap-1.5 text-muted-foreground text-xs"><Loader2 className="w-3 h-3 animate-spin" />Thinking...</div>
        )}

        {status.type === 'clarify' && pendingClarification && (
          <div className="space-y-2 bg-muted/50 rounded-lg p-3 border border-border">
            <p className="text-xs font-medium">{pendingClarification.question}</p>
            {pendingClarification.options?.length ? (
              <div className="flex flex-wrap gap-1.5">
                {pendingClarification.options.map((opt, i) => (
                  <button key={i} onClick={() => respondToClarification(opt)} className="px-2.5 py-1 text-[11px] rounded-lg border border-primary/30 bg-primary/5 text-primary hover:bg-primary/15 font-medium">{opt}</button>
                ))}
              </div>
            ) : <p className="text-[10px] text-muted-foreground">Type your response below</p>}
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="px-3 pb-3 pt-1 border-t border-border shrink-0">
        <CommandPicker query={commandQuery ?? ''} onSelect={(cmd) => { setInput(cmd + ' '); setCommandPickerOpen(false); textareaRef.current?.focus(); }} onClose={() => setCommandPickerOpen(false)} isOpen={commandPickerOpen} />

        {fileError && (
          <div className="mb-2 p-2 rounded-lg border border-destructive/30 bg-destructive/5 text-xs text-destructive">
            {fileError}
          </div>
        )}

        {uploadedDocs.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mb-2 p-1.5 rounded-lg border border-border bg-muted/30">
            {uploadedDocs.map((doc, i) => (
              <div key={i} className="flex items-center gap-1.5 text-xs px-2 py-1 rounded bg-background border border-border">
                <span className="truncate max-w-[120px]">{doc.name}</span>
                <span className={doc.status === 'done' ? 'text-green-600' : doc.status === 'error' ? 'text-destructive' : 'text-muted-foreground'}>
                  {doc.status === 'uploading' ? '...' : doc.status === 'done' ? '✓' : '✗'}
                </span>
              </div>
            ))}
          </div>
        )}

        {attachmentPreviews.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mb-2 p-1.5 rounded-lg border border-border bg-muted/30">
            {attachmentPreviews.map((preview, i) => (
              <div key={i} className="relative group">
                <img src={preview} alt="" className="h-10 w-10 object-cover rounded border border-border" />
                <button onClick={() => removeAttachment(i)} className="absolute -top-1 -right-1 w-3.5 h-3.5 bg-background border border-border rounded-full flex items-center justify-center opacity-0 group-hover:opacity-100"><X className="w-2 h-2" /></button>
              </div>
            ))}
          </div>
        )}

        {actionCard && (
          <div className="mb-2">
            <InlineActionCard
              config={actionCard}
              onSelect={handleActionSelect}
              onDismiss={() => setActionCard(null)}
            />
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <div className="flex items-end gap-1.5 border border-border bg-background rounded-xl focus-within:ring-2 focus-within:ring-primary/50">
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
              placeholder="Ask anything or type / ..."
              rows={1}
              className="flex-1 py-2.5 pr-1 text-sm bg-transparent resize-none focus:outline-none disabled:opacity-50 max-h-[150px]"
            />
            <button type="submit" disabled={isLoading || (!input.trim() && attachments.length === 0)} className="shrink-0 p-2.5 text-primary disabled:text-muted-foreground disabled:opacity-50 transition-colors"><Send className="w-4 h-4" /></button>
          </div>
          <div className="mt-1 flex items-center justify-between text-[9px] text-muted-foreground/40">
            <span>Enter to send, Shift+Enter for new line</span>
            {tokenUsage && <span className="font-mono">{tokenUsage.totalTokens >= 1000 ? `${(tokenUsage.totalTokens / 1000).toFixed(1)}k` : tokenUsage.totalTokens} tokens</span>}
          </div>
        </form>
      </div>
    </div>
  );
}

// =============================================================================
// Main Workfloor Page — Overlay Layout
// =============================================================================

export default function WorkfloorPage() {
  const { loadScopedHistory, sendMessage } = useTP();
  const { surface } = useDesk();

  const searchParams = useSearchParams();
  const router = useRouter();

  const [agents, setAgents] = useState<Agent[]>([]);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [agentsLoading, setAgentsLoading] = useState(true);
  const [tasksLoading, setTasksLoading] = useState(true);
  const [bootstrapProvider, setBootstrapProvider] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'tasks' | 'files'>('files');
  const [fileTree, setFileTree] = useState<import('@/types').WorkspaceTreeNode[]>([]);
  const [selectedFile, setSelectedFile] = useState<import('@/types').WorkspaceTreeNode | null>(null);
  const [fileTreeLoading, setFileTreeLoading] = useState(false);

  // Load file tree when Files tab is activated
  useEffect(() => {
    if (activeTab !== 'files' || fileTree.length > 0) return;
    setFileTreeLoading(true);
    // Only show /workspace in file tree — agents have the room, tasks have the Tasks tab
    api.workspace.getTree('/workspace').then((workspace) => {
      setFileTree(workspace);
    }).catch(err => {
      console.error('Failed to load file tree:', err);
    }).finally(() => setFileTreeLoading(false));
  }, [activeTab, fileTree.length]);
  // showCatalog removed — catalog only shows for zero-tasks empty state

  // File-aware surface context for TP chat
  // When a file is selected, merge navigation context into the surface
  const effectiveSurface = selectedFile && activeTab === 'files'
    ? {
        ...surface,
        type: 'workspace-explorer',
        path: selectedFile.path,
        navigation_type: selectedFile.type,
      }
    : surface;

  // Panel + room visibility
  const [panelOpen, setPanelOpen] = useState(true);
  const [chatOpen, setChatOpen] = useState(true);
  // roomCollapsed removed — isometric room replaced by dashboard

  // Action card — set by panel buttons, rendered in ChatPanel
  const [pendingActionCard, setPendingActionCard] = useState<ActionCardConfig | null>(null);
  const showActionCard = useCallback((config: ActionCardConfig) => {
    setPendingActionCard(config);
    setChatOpen(true);
    setTimeout(() => setPendingActionCard(null), 200);
  }, []);

  useEffect(() => { loadScopedHistory(); }, [loadScopedHistory]);

  const refreshData = useCallback(() => {
    api.agents.list().then(setAgents).catch(() => []);
    api.tasks.list().then(setTasks).catch(() => []);
  }, []);

  useEffect(() => {
    api.agents.list().then(setAgents).catch(() => []).finally(() => setAgentsLoading(false));
    api.tasks.list().then(setTasks).catch(() => []).finally(() => setTasksLoading(false));
    const interval = setInterval(refreshData, 30000);
    const onFocus = () => { if (document.visibilityState === 'visible') refreshData(); };
    document.addEventListener('visibilitychange', onFocus);
    return () => { clearInterval(interval); document.removeEventListener('visibilitychange', onFocus); };
  }, [refreshData]);

  useEffect(() => {
    const provider = searchParams?.get('provider');
    if (provider && searchParams?.get('status') === 'connected') {
      setBootstrapProvider(provider);
      router.replace(HOME_ROUTE, { scroll: false });
    }
  }, [searchParams, router]);

  const activeAgents = agents.filter(a => a.status !== 'archived');
  const activeTasks = tasks.filter(t => t.status !== 'archived');


  return (
    <div className="relative h-full overflow-hidden">
      {/* Layer 1: Activity feed + compact room, respects panel widths */}
      <div className={cn(
        "absolute top-0 bottom-0 overflow-hidden flex flex-col",
        panelOpen ? "left-[400px]" : "left-0",
        chatOpen ? "right-[400px]" : "right-0",
      )}>
        <WorkspaceDashboard
          tasks={tasks}
          agents={agents}
          isometricRoom={
            <IsometricRoom
              agents={activeAgents}
              tasks={tasks}
              loading={agentsLoading}
              collapsed={false}
              onTPClick={() => setChatOpen(true)}
              onAction={(msg) => { sendMessage(msg, { surface }); setChatOpen(true); }}
            />
          }
        />
      </div>

      {/* Layer 1b: Content viewer — shows when file selected from Files tab */}
      {/* Positioned between left panel (w-[380px] + left-4) and right chat (w-[380px] + right-4) */}
      {selectedFile && activeTab === 'files' && (
        <div className={cn(
          "absolute top-4 bottom-4 z-10 bg-background/95 backdrop-blur-sm rounded-lg border border-border/50 overflow-auto shadow-sm",
          panelOpen ? "left-[400px]" : "left-4",
          chatOpen ? "right-[400px]" : "right-4",
        )}>
          <ContentViewer selectedNode={selectedFile} onNavigate={(node) => setSelectedFile(node)} />
        </div>
      )}

      {/* Layer 2: Bootstrap banner */}
      {bootstrapProvider && (
        <div className="absolute top-3 left-1/2 -translate-x-1/2 z-30">
          <div className="flex items-center gap-3 p-3 rounded-lg border border-primary/20 bg-primary/5 backdrop-blur-sm">
            <div>
              <p className="text-sm font-medium">Connected {bootstrapProvider.charAt(0).toUpperCase() + bootstrapProvider.slice(1)}!</p>
              <p className="text-xs text-muted-foreground">Syncing...</p>
            </div>
            <button onClick={() => setBootstrapProvider(null)} className="text-muted-foreground hover:text-foreground"><X className="w-4 h-4" /></button>
          </div>
        </div>
      )}

      {/* Layer 3: Floating left panel — Tasks/Context */}
      <div className={cn(
        'absolute left-4 top-4 bottom-4 z-20 w-[380px] flex flex-col transition-all duration-200',
        panelOpen ? 'opacity-100' : 'opacity-0 pointer-events-none -translate-x-4'
      )}>
        <div className="flex flex-col flex-1 min-h-0 bg-background/90 backdrop-blur-md border border-border/50 rounded-xl shadow-lg overflow-hidden">
          {/* Panel header: tabs + actions */}
          <div className="flex items-center justify-between px-3 py-2 border-b border-border/50 shrink-0">
            <div className="flex gap-1">
              {(['tasks', 'files'] as const).map(tab => (
                <button
                  key={tab}
                  onClick={() => setActiveTab(tab)}
                  className={cn(
                    'px-2.5 py-1 text-xs font-medium rounded-md transition-colors capitalize',
                    activeTab === tab ? 'bg-muted text-foreground' : 'text-muted-foreground/40 hover:text-muted-foreground'
                  )}
                >
                  {tab}
                </button>
              ))}
            </div>
            <div className="flex items-center gap-1">
              {activeTab === 'tasks' && (
                <button
                  onClick={() => showActionCard(NEW_TASK_CARD)}
                  className="flex items-center gap-1 px-2 py-1 text-[10px] font-medium rounded-md border border-primary/30 text-primary hover:bg-primary/10 transition-colors"
                >
                  <Plus className="w-3 h-3" /> New Task
                </button>
              )}
              {activeTab === 'files' && selectedFile && (
                <button
                  onClick={() => setSelectedFile(null)}
                  className="text-[10px] text-muted-foreground/60 hover:text-foreground px-1.5 py-0.5 rounded hover:bg-muted"
                >
                  Close file
                </button>
              )}
              <button onClick={() => setPanelOpen(false)} className="p-1 text-muted-foreground/40 hover:text-muted-foreground rounded">
                <X className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>

          {/* Panel content */}
          <div className="flex-1 overflow-y-auto p-3">
            {activeTab === 'tasks' && <TasksTab tasks={tasks} />}

            {activeTab === 'files' && (
              <div className="flex flex-col h-full -mx-3 -mt-1">
                {fileTreeLoading ? (
                  <div className="flex items-center justify-center py-8">
                    <Loader2 className="w-4 h-4 animate-spin text-muted-foreground" />
                  </div>
                ) : (
                  <WorkspaceTree
                    nodes={fileTree}
                    selectedPath={selectedFile?.path}
                    onSelect={(node) => setSelectedFile(node)}
                  />
                )}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Layer 4: Floating right panel — Chat */}
      <div className={cn(
        'absolute right-4 top-4 bottom-4 z-20 w-[380px] flex flex-col transition-all duration-200',
        chatOpen ? 'opacity-100' : 'opacity-0 pointer-events-none translate-x-4'
      )}>
        <div className="flex flex-col flex-1 min-h-0 bg-background/90 backdrop-blur-md border border-border/50 rounded-xl shadow-lg overflow-hidden">
          {/* Chat header — shows TP context awareness */}
          <div className="flex items-center justify-between px-3 py-2 border-b border-border/50 shrink-0">
            <div className="flex items-center gap-2">
              <span className="text-xs font-medium">TP</span>
              {selectedFile && activeTab === 'files' && (
                <span className="text-[10px] text-muted-foreground/50 truncate max-w-[180px]">
                  viewing {selectedFile.name}
                </span>
              )}
            </div>
            <button onClick={() => setChatOpen(false)} className="p-1 text-muted-foreground/40 hover:text-muted-foreground rounded">
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
          <ChatPanel taskCount={activeTasks.length} pendingActionConfig={pendingActionCard} surfaceOverride={effectiveSurface} />
        </div>
      </div>

      {/* Layer 5: Top-center control bar — panel toggles + room hide */}
      <div className="absolute top-2 left-1/2 -translate-x-1/2 z-30 flex items-center gap-1 bg-background/80 backdrop-blur-md rounded-lg border border-border/30 px-1 py-0.5">
        <button
          onClick={() => setPanelOpen(v => !v)}
          className={cn(
            'flex items-center gap-1.5 px-2.5 py-1.5 text-[10px] font-medium rounded-md transition-colors',
            panelOpen ? 'text-foreground bg-muted/50' : 'text-muted-foreground/40 hover:text-muted-foreground'
          )}
        >
          <ListChecks className="w-3 h-3" /> Tasks
        </button>
        <button
          onClick={() => setChatOpen(v => !v)}
          className={cn(
            'flex items-center gap-1.5 px-2.5 py-1.5 text-[10px] font-medium rounded-md transition-colors',
            chatOpen ? 'text-foreground bg-muted/50' : 'text-muted-foreground/40 hover:text-muted-foreground'
          )}
        >
          <MessageCircle className="w-3 h-3" /> Chat
        </button>
        {/* Hide workfloor toggle removed — dashboard replaces isometric room */}
      </div>
    </div>
  );
}
