'use client';

/**
 * Workfloor — Explorer shell with scoped TP drawer
 *
 * Finder / Windows Explorer mental model:
 * - Left: hierarchical workspace explorer (collapsible)
 * - Center: folder details view + type-aware file preview
 * - Right: TP chat drawer (collapsible)
 */

import { useState, useEffect, useCallback, useRef } from 'react';
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
  FolderOpen,
} from 'lucide-react';
import { useTP } from '@/contexts/TPContext';
import { useDesk } from '@/contexts/DeskContext';
import { useFileAttachments } from '@/hooks/useFileAttachments';
import type { Task } from '@/types';
import { cn } from '@/lib/utils';
import { api } from '@/lib/api/client';
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
} from '@/components/tp/InlineActionCard';
import { ContextSetup } from '@/components/tp/ContextSetup';

type TreeNode = import('@/types').WorkspaceTreeNode;

const EXPLORER_ROOT_PATH = '/explorer';

function asNodeArray(value: unknown): TreeNode[] {
  return Array.isArray(value) ? value as TreeNode[] : [];
}

function relabelTopLevelNodes(nodes: TreeNode[] | undefined, labelMap: Record<string, string>): TreeNode[] {
  return asNodeArray(nodes).map((node) => ({
    ...node,
    name: labelMap[node.name] || node.name,
  }));
}

function filterNodes(nodes: TreeNode[] | undefined, predicate: (node: TreeNode) => boolean): TreeNode[] {
  return asNodeArray(nodes)
    .filter(predicate)
    .map((node) => ({
      ...node,
      children: node.children ? filterNodes(node.children, predicate) : undefined,
    }));
}

function resolveNodeByPath(root: TreeNode, targetPath: string): TreeNode | null {
  if (root.path === targetPath) {
    return root;
  }

  for (const child of root.children || []) {
    const match = resolveNodeByPath(child, targetPath);
    if (match) {
      return match;
    }
  }

  return null;
}

function buildBreadcrumbs(root: TreeNode, targetPath: string): TreeNode[] {
  const trail: TreeNode[] = [];

  function walk(node: TreeNode): boolean {
    trail.push(node);
    if (node.path === targetPath) {
      return true;
    }
    for (const child of node.children || []) {
      if (walk(child)) {
        return true;
      }
    }
    trail.pop();
    return false;
  }

  walk(root);
  return trail;
}

function buildExplorerRoot(input: {
  tasksTree?: TreeNode[];
  domainTree?: TreeNode[];
  uploadTree?: TreeNode[];
  taskTitles: Record<string, string>;
  domainTitles: Record<string, string>;
  settings?: Array<{ name: string; filename: string; path: string; updated_at: string | null }>;
}): TreeNode {
  const tasksChildren = relabelTopLevelNodes(input.tasksTree, input.taskTitles);
  const domainChildren = relabelTopLevelNodes(
    filterNodes(input.domainTree, (node) => {
      const lower = node.path.toLowerCase();
      return !lower.endsWith('/_tracker.md') && !lower.startsWith('/workspace/context/signals');
    }),
    input.domainTitles
  );
  const uploadChildren = asNodeArray(input.uploadTree);
  const settingsFiles = Array.isArray(input.settings) ? input.settings : [];

  const uploadsFolder: TreeNode = {
    name: 'Uploads',
    path: `${EXPLORER_ROOT_PATH}/uploads`,
    type: 'folder',
    summary: uploadChildren.length ? `${uploadChildren.length} items` : 'No uploads yet',
    children: uploadChildren,
  };

  const settingsFolder: TreeNode = {
    name: 'Settings',
    path: `${EXPLORER_ROOT_PATH}/settings`,
    type: 'folder',
    summary: settingsFiles.length ? `${settingsFiles.length} files` : 'No settings files yet',
    children: settingsFiles.map((file) => ({
      name: file.filename,
      path: file.path,
      type: 'file' as const,
      updated_at: file.updated_at || undefined,
      summary: file.name,
    })),
  };

  return {
    name: 'yarnnn',
    path: EXPLORER_ROOT_PATH,
    type: 'folder',
    children: [
      {
        name: 'Tasks',
        path: `${EXPLORER_ROOT_PATH}/tasks`,
        type: 'folder',
        summary: tasksChildren.length ? `${tasksChildren.length} active tasks` : 'No tasks yet',
        children: tasksChildren,
      },
      {
        name: 'Domains',
        path: `${EXPLORER_ROOT_PATH}/domains`,
        type: 'folder',
        summary: domainChildren.length ? `${domainChildren.length} context domains` : 'No domains yet',
        children: domainChildren,
      },
      uploadsFolder,
      settingsFolder,
    ],
  };
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
  const [showContextSetup, setShowContextSetup] = useState(false);
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
    { id: 'create-task', label: 'Create a task', icon: ListChecks, verb: 'prompt', onSelect: () => { sendMessage('I want to create a task. What do you suggest based on my context?', { surface }); } },
    { id: 'update-info', label: 'Update my info', icon: Settings2, verb: 'prompt', onSelect: () => { setActionCard(null); setShowContextSetup(true); } },
    { id: 'web-search', label: 'Web search', icon: Globe, verb: 'prompt', onSelect: () => { setInput('Search the web for '); textareaRef.current?.focus(); } },
    { id: 'upload-file', label: 'Upload file', icon: Upload, verb: 'attach', onSelect: () => fileInputRef.current?.click() },
  ];

  return (
    <div className="flex flex-col h-full">
      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-3 py-3 space-y-2.5">
        {messages.length === 0 && !isLoading && (
          <div className="py-4 px-2">
            {taskCount === 0 ? (
              <ContextSetup
                onSubmit={(msg) => { sendMessage(msg, { surface }); }}
                showSkipOptions
                onSkipAction={(msg) => { sendMessage(msg, { surface }); }}
              />
            ) : (
              <div className="space-y-3">
                <div className="text-center">
                  <MessageCircle className="w-5 h-5 text-muted-foreground/15 mx-auto mb-1.5" />
                  <p className="text-[11px] text-muted-foreground/40">Quick actions</p>
                </div>
                <div className="flex flex-col gap-1.5">
                  <button
                    onClick={() => { sendMessage('How are my tasks doing?', { surface }); }}
                    className="text-left text-[11px] px-3 py-2 rounded-lg border border-border/50 text-muted-foreground hover:text-foreground hover:border-border hover:bg-muted/50 transition-colors"
                  >
                    How are my tasks doing?
                  </button>
                  <button
                    onClick={() => { sendMessage('I want to create a new task. What do you suggest?', { surface }); }}
                    className="text-left text-[11px] px-3 py-2 rounded-lg border border-border/50 text-muted-foreground hover:text-foreground hover:border-border hover:bg-muted/50 transition-colors"
                  >
                    Create a new task
                  </button>
                </div>
              </div>
            )}
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

        {showContextSetup && (
          <div className="mb-2">
            <ContextSetup
              compact
              onSubmit={(msg) => { setShowContextSetup(false); sendMessage(msg, { surface }); }}
              onDismiss={() => setShowContextSetup(false)}
            />
          </div>
        )}

        {actionCard && !showContextSetup && (
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
  const { loadScopedHistory } = useTP();
  const { surface } = useDesk();

  const searchParams = useSearchParams();
  const router = useRouter();

  const [tasks, setTasks] = useState<Task[]>([]);
  const [explorerRoot, setExplorerRoot] = useState<TreeNode | null>(null);
  const [selectedPath, setSelectedPath] = useState<string | null>(null);
  const [fileTreeLoading, setFileTreeLoading] = useState(false);

  const loadExplorer = useCallback(async () => {
    setFileTreeLoading(true);
    try {
      const [nav, tasksTree, domainTree, uploadTree] = await Promise.all([
        api.workspace.getNav(),
        api.workspace.getTree('/tasks'),
        api.workspace.getTree('/workspace/context'),
        api.workspace.getTree('/workspace/uploads'),
      ]);

      const navTasks = Array.isArray(nav?.tasks) ? nav.tasks : [];
      const navDomains = Array.isArray(nav?.domains) ? nav.domains : [];
      const taskTitles = Object.fromEntries(navTasks.map((task) => [task.slug, task.title]));
      const domainTitles = Object.fromEntries(navDomains.map((domain) => [domain.key, domain.display_name]));
      const nextRoot = buildExplorerRoot({
        tasksTree: asNodeArray(tasksTree),
        domainTree: asNodeArray(domainTree),
        uploadTree: asNodeArray(uploadTree),
        taskTitles,
        domainTitles,
        settings: Array.isArray(nav?.settings) ? nav.settings : [],
      });

      setExplorerRoot(nextRoot);
      setSelectedPath((prev) => (prev && resolveNodeByPath(nextRoot, prev) ? prev : nextRoot.path));
    } catch (err) {
      console.error('Failed to load explorer:', err);
    } finally {
      setFileTreeLoading(false);
    }
  }, []);

  // File-aware surface context for TP chat
  // When a file is selected, merge navigation context into the surface
  const selectedNode = explorerRoot && selectedPath ? resolveNodeByPath(explorerRoot, selectedPath) : null;
  const breadcrumbs = explorerRoot && selectedNode ? buildBreadcrumbs(explorerRoot, selectedNode.path) : [];

  const effectiveSurface = selectedNode
    ? {
        ...surface,
        type: 'workspace-explorer',
        path: selectedNode.path,
        navigation_type: selectedNode.type,
      }
    : surface;

  // Panel + room visibility
  const [panelOpen, setPanelOpen] = useState(true);
  const [chatOpen, setChatOpen] = useState(false); // Default closed — FAB to open
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
    api.tasks.list().then(setTasks).catch(() => []);
  }, []);

  useEffect(() => {
    loadExplorer();
  }, [loadExplorer]);

  useEffect(() => {
    api.tasks.list().then(setTasks).catch(() => []);
    const interval = setInterval(() => {
      refreshData();
      loadExplorer();
    }, 30000);
    const onFocus = () => {
      if (document.visibilityState === 'visible') {
        refreshData();
        loadExplorer();
      }
    };
    document.addEventListener('visibilitychange', onFocus);
    return () => { clearInterval(interval); document.removeEventListener('visibilitychange', onFocus); };
  }, [loadExplorer, refreshData]);

  useEffect(() => {
    const provider = searchParams?.get('provider');
    if (provider && searchParams?.get('status') === 'connected') {
      router.replace(HOME_ROUTE, { scroll: false });
    }
  }, [searchParams, router]);

  const activeTasks = tasks.filter(t => t.status !== 'archived');

  const handleExplorerSelect = useCallback((node: TreeNode) => {
    setSelectedPath(node.path);
  }, []);


  return (
    <div className="flex h-full overflow-hidden">
      {/* Left: Icon strip (collapsed) or Explorer panel (expanded) */}
      {panelOpen ? (
        <div className="w-[280px] shrink-0 border-r border-border flex flex-col bg-background">
          <div className="flex items-center justify-between px-3 py-2 border-b border-border shrink-0">
            <div>
              <p className="text-sm font-medium text-foreground">Explorer</p>
              <p className="text-[11px] text-muted-foreground">Workspace files and task outputs</p>
            </div>
            <button onClick={() => setPanelOpen(false)} className="p-1 text-muted-foreground/40 hover:text-muted-foreground rounded">
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
          <div className="flex-1 overflow-y-auto">
            {fileTreeLoading && !explorerRoot ? (
              <div className="flex items-center justify-center h-full text-sm text-muted-foreground">
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                Loading explorer...
              </div>
            ) : explorerRoot ? (
              <div className="p-2">
                <WorkspaceTree
                  nodes={explorerRoot.children || []}
                  selectedPath={selectedPath || undefined}
                  onSelect={handleExplorerSelect}
                />
              </div>
            ) : (
              <div className="p-3 text-sm text-muted-foreground">Failed to load explorer</div>
            )}
          </div>
        </div>
      ) : (
        <div className="w-10 shrink-0 border-r border-border flex flex-col items-center py-2 gap-2 bg-background">
          <button
            onClick={() => setPanelOpen(true)}
            className="p-2 rounded-md text-muted-foreground/50 hover:text-foreground hover:bg-muted transition-colors"
            title="Files"
          >
            <FolderOpen className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Center: Explorer content */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {selectedNode ? (
          <div className="flex-1 overflow-auto bg-background flex flex-col">
            <div className="flex items-center gap-1 px-4 py-2 border-b border-border shrink-0 overflow-x-auto">
              {breadcrumbs.map((crumb, index) => (
                <div key={crumb.path} className="flex items-center gap-1 shrink-0">
                  {index > 0 && <span className="text-xs text-muted-foreground/40">/</span>}
                  <button
                    onClick={() => setSelectedPath(crumb.path)}
                    className={cn(
                      'rounded px-1.5 py-0.5 text-xs hover:bg-muted/60',
                      crumb.path === selectedNode.path ? 'text-foreground font-medium' : 'text-muted-foreground'
                    )}
                  >
                    {crumb.name}
                  </button>
                </div>
              ))}
              <span className="ml-auto shrink-0 text-[11px] text-muted-foreground">
                {selectedNode.type === 'folder'
                  ? `${selectedNode.children?.length || 0} items`
                  : selectedNode.path.split('.').pop()?.toUpperCase() || 'FILE'}
              </span>
            </div>
            <div className="flex-1 overflow-auto">
              <ContentViewer selectedNode={selectedNode} onNavigate={handleExplorerSelect} />
            </div>
          </div>
        ) : (
          <div className="flex items-center justify-center h-full text-sm text-muted-foreground">
            Select a file or folder from the explorer
          </div>
        )}
      </div>

      {/* Right: Chat panel (slides in) or FAB (floating) */}
      {chatOpen && (
        <div className="w-[380px] shrink-0 border-l border-border flex flex-col bg-background overflow-hidden">
          {/* Chat header — always visible, never scrolls */}
          <div className="flex items-center justify-between px-3 py-2.5 border-b border-border bg-background z-10 shrink-0">
            <div className="flex items-center gap-2">
              <img src="/assets/logos/circleonly_yarnnn_1.svg" alt="" className="w-5 h-5" />
              <span className="text-xs font-medium">TP</span>
              {selectedNode && (
                <span className="text-[10px] text-muted-foreground/50 truncate max-w-[160px]">
                  · viewing {selectedNode.name}
                </span>
              )}
            </div>
            <button onClick={() => setChatOpen(false)} className="p-1.5 text-muted-foreground hover:text-foreground rounded-md hover:bg-muted transition-colors">
              <X className="w-4 h-4" />
            </button>
          </div>
          {/* Chat content — scrolls independently */}
          <div className="flex-1 min-h-0">
            <ChatPanel taskCount={activeTasks.length} pendingActionConfig={pendingActionCard} surfaceOverride={effectiveSurface} />
          </div>
        </div>
      )}

      {/* FAB — yarnnn logo, opens chat */}
      {!chatOpen && (
        <button
          onClick={() => setChatOpen(true)}
          className="fixed bottom-6 right-6 z-50 w-12 h-12 rounded-full shadow-lg hover:shadow-xl hover:scale-110 transition-all flex items-center justify-center group"
          title="Chat with TP"
        >
          <img
            src="/assets/logos/circleonly_yarnnn_1.svg"
            alt="yarnnn"
            className="w-12 h-12 transition-transform duration-500 group-hover:rotate-180"
          />
        </button>
      )}
    </div>
  );
}
