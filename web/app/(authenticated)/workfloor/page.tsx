'use client';

/**
 * Workfloor — ADR-139 v3: Agent Grid + TP Chat Panel
 *
 * Left: Isometric agent room + tabbed data (Tasks | Context with nested Identity/Brand/Documents)
 * Right: TP Chat (always visible, resizable via WorkspaceLayout)
 * No drawer — chat is the right panel.
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import { HOME_ROUTE } from '@/lib/routes';
import {
  Loader2,
  X,
  ListChecks,
  LayoutGrid,
  MessageCircle,
  Send,
  Upload,
  Search,
  Globe,
  UserCircle,
  Paintbrush,
} from 'lucide-react';
import { useTP } from '@/contexts/TPContext';
import { useDesk } from '@/contexts/DeskContext';
import { useFileAttachments } from '@/hooks/useFileAttachments';
import type { Agent, Task, Document } from '@/types';
import { cn } from '@/lib/utils';
import { api } from '@/lib/api/client';
import { WorkspaceLayout, type WorkspacePanelTab } from '@/components/desk/WorkspaceLayout';
import { IsometricRoom } from '@/components/workfloor/IsometricRoom';
import { CommandPicker } from '@/components/tp/CommandPicker';
import { PlusMenu, type PlusMenuAction } from '@/components/tp/PlusMenu';
import { MessageBlocks } from '@/components/tp/InlineToolCall';
import { ToolResultList } from '@/components/tp/ToolResultCard';
import { MarkdownRenderer } from '@/components/shared/MarkdownRenderer';


// =============================================================================
// Tabs below agent room
// =============================================================================

function TasksTab({ tasks }: { tasks: Task[] }) {
  const active = tasks.filter(t => t.status !== 'archived');
  return (
    <div className="space-y-1">
      {active.length > 0 ? active.map(task => (
        <Link key={task.id} href={`/tasks/${task.slug}`} className="flex items-center justify-between px-2 py-1.5 rounded-lg hover:bg-muted/50 transition-colors text-xs">
          <div className="flex items-center gap-1.5 min-w-0">
            <span className={cn('w-1.5 h-1.5 rounded-full shrink-0', task.status === 'active' ? 'bg-green-500' : 'bg-amber-500')} />
            <span className="truncate">{task.title || task.slug}</span>
          </div>
          {task.schedule && <span className="text-muted-foreground/40 shrink-0 ml-2">{task.schedule}</span>}
        </Link>
      )) : (
        <p className="text-[10px] text-muted-foreground/30 text-center py-3">No tasks yet — set up your context first, then ask chat to create one</p>
      )}
    </div>
  );
}

function IdentityTab({ onSendMessage }: { onSendMessage: (msg: string) => void }) {
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
          <div className="text-[11px] text-muted-foreground/70 bg-muted/20 rounded-lg p-2.5 max-h-48 overflow-y-auto prose prose-xs dark:prose-invert max-w-none">
            <MarkdownRenderer content={content} compact />
          </div>
          <div className="flex items-center gap-2">
            <button onClick={() => onSendMessage('Update my identity')} className="text-[9px] text-primary hover:text-primary/80 font-medium">
              Update via chat →
            </button>
            <button onClick={() => setEditing(true)} className="text-[9px] text-muted-foreground/30 hover:text-muted-foreground/60">
              Edit manually
            </button>
          </div>
        </>
      ) : (
        <div className="py-4 px-2">
          <p className="text-[11px] text-muted-foreground/60 mb-3">Your identity helps agents understand who you are and what you care about.</p>
          <div className="space-y-1.5 text-[10px] text-muted-foreground/40">
            <p>Try telling the chat:</p>
            <p className="italic text-muted-foreground/60">&quot;Update my identity — I&apos;m [name], [role] at [company]&quot;</p>
            <p className="italic text-muted-foreground/60">&quot;Update my identity from my LinkedIn&quot;</p>
            <p className="italic text-muted-foreground/60">&quot;Update my identity from the pitch deck I uploaded&quot;</p>
          </div>
          <div className="mt-3 flex items-center gap-2">
            <button onClick={() => onSendMessage('Update my identity')} className="text-[10px] text-primary hover:underline font-medium">
              Update via chat →
            </button>
            <button onClick={() => { setDraft(''); setEditing(true); }} className="text-[9px] text-muted-foreground/30 hover:text-muted-foreground/60">
              Or edit manually
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

function BrandTab({ onSendMessage }: { onSendMessage: (msg: string) => void }) {
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
          <div className="text-[11px] text-muted-foreground/70 bg-muted/20 rounded-lg p-2.5 max-h-48 overflow-y-auto">
            <MarkdownRenderer content={content} compact />
          </div>
          <div className="flex items-center gap-2">
            <button onClick={() => onSendMessage('Update my brand')} className="text-[9px] text-primary hover:text-primary/80 font-medium">
              Update via chat →
            </button>
            <button onClick={() => setEditing(true)} className="text-[9px] text-muted-foreground/30 hover:text-muted-foreground/60">
              Edit manually
            </button>
          </div>
        </>
      ) : (
        <div className="py-4 px-2">
          <p className="text-[11px] text-muted-foreground/60 mb-3">Your brand guide shapes how agents write — tone, terminology, audience awareness.</p>
          <div className="space-y-1.5 text-[10px] text-muted-foreground/40">
            <p>Try telling the chat:</p>
            <p className="italic text-muted-foreground/60">&quot;Update my brand from our website&quot;</p>
            <p className="italic text-muted-foreground/60">&quot;Update my brand — we&apos;re technical but friendly, writing for developers&quot;</p>
            <p className="italic text-muted-foreground/60">&quot;Update my brand from the brand guidelines I uploaded&quot;</p>
          </div>
          <div className="mt-3 flex items-center gap-2">
            <button onClick={() => onSendMessage('Update my brand')} className="text-[10px] text-primary hover:underline font-medium">
              Update via chat →
            </button>
            <button onClick={() => { setDraft(''); setEditing(true); }} className="text-[9px] text-muted-foreground/30 hover:text-muted-foreground/60">
              Or edit manually
            </button>
          </div>
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
        <div key={doc.id} className="flex items-center justify-between px-2 py-1.5 rounded-lg text-xs">
          <div className="flex items-center gap-1.5 min-w-0">
            <span className={cn('w-1.5 h-1.5 rounded-full shrink-0',
              doc.processing_status === 'completed' ? 'bg-green-500' :
              doc.processing_status === 'failed' ? 'bg-red-500' :
              'bg-amber-500'
            )} />
            <span className="truncate">{doc.filename}</span>
          </div>
          <span className="text-muted-foreground/40 shrink-0 ml-2">{formatSize(doc.file_size)}</span>
        </div>
      )) : (
        <div className="py-4 px-2">
          <p className="text-[11px] text-muted-foreground/60 mb-2">Documents give agents source material to work from — pitch decks, reports, guidelines.</p>
          <p className="text-[10px] text-muted-foreground/40">Upload files via the chat input (+) or drag &amp; drop into the conversation.</p>
        </div>
      )}
    </div>
  );
}

// =============================================================================
// Chat Panel (right side — always visible)
// =============================================================================

function ChatPanel() {
  const {
    messages,
    sendMessage,
    isLoading,
    status,
    pendingClarification,
    respondToClarification,
    tokenUsage,
  } = useTP();
  const { surface } = useDesk();

  const [input, setInput] = useState('');
  const [commandPickerOpen, setCommandPickerOpen] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const {
    attachments,
    attachmentPreviews,
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

  // Workfloor-scoped actions: workspace context + task orchestration
  const plusMenuActions: PlusMenuAction[] = [
    { id: 'update-identity', label: 'Update my identity', icon: UserCircle, verb: 'prompt', onSelect: () => { setInput('Update my identity'); textareaRef.current?.focus(); } },
    { id: 'update-brand', label: 'Update my brand', icon: Paintbrush, verb: 'prompt', onSelect: () => { setInput('Update my brand'); textareaRef.current?.focus(); } },
    { id: 'create-task', label: 'Create a task', icon: ListChecks, verb: 'prompt', onSelect: () => { setInput('Create a task for '); textareaRef.current?.focus(); } },
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
              <p className="text-[11px] text-muted-foreground/40">Get started</p>
            </div>
            <div className="flex flex-col gap-1.5 px-2">
              {[
                'Tell me about myself and my work',
                'Update my brand from our website',
                'Help me set up my first task',
              ].map(chip => (
                <button
                  key={chip}
                  onClick={() => { sendMessage(chip, { surface }); }}
                  className="text-left text-[11px] px-3 py-2 rounded-lg border border-border/50 text-muted-foreground hover:text-foreground hover:border-border hover:bg-muted/50 transition-colors"
                >
                  {chip}
                </button>
              ))}
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
// Main Workfloor Page
// =============================================================================

export default function WorkfloorPage() {
  const { loadScopedHistory, sendMessage } = useTP();
  const { surface } = useDesk();

  // Send a prefilled message to TP chat (used by Update buttons in Context tabs)
  const handleContextUpdate = useCallback((msg: string) => {
    sendMessage(msg, { surface });
  }, [sendMessage, surface]);
  const searchParams = useSearchParams();
  const router = useRouter();

  const [agents, setAgents] = useState<Agent[]>([]);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [agentsLoading, setAgentsLoading] = useState(true);
  const [tasksLoading, setTasksLoading] = useState(true);
  const [bootstrapProvider, setBootstrapProvider] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'tasks' | 'context'>('tasks');
  const [contextSubTab, setContextSubTab] = useState<'identity' | 'brand' | 'documents'>('identity');

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

  // Right panel = TP Chat
  const panelTabs: WorkspacePanelTab[] = [
    { id: 'chat', label: 'Chat', content: <ChatPanel /> },
  ];

  return (
    <WorkspaceLayout
      identity={{ icon: <LayoutGrid className="w-5 h-5" />, label: 'Workfloor' }}
      panelTabs={panelTabs}
      panelDefaultOpen={true}
      panelDefaultPct={33}
    >
      <div className="flex-1 overflow-y-auto">
        {/* Bootstrap banner */}
        {bootstrapProvider && (
          <div className="flex items-center gap-3 p-3 rounded-lg border border-primary/20 bg-primary/5 mx-5 mt-5 mb-2">
            <div className="flex-1">
              <p className="text-sm font-medium">Connected {bootstrapProvider.charAt(0).toUpperCase() + bootstrapProvider.slice(1)}!</p>
              <p className="text-xs text-muted-foreground">Syncing...</p>
            </div>
            <button onClick={() => setBootstrapProvider(null)} className="text-muted-foreground hover:text-foreground"><X className="w-4 h-4" /></button>
          </div>
        )}

        {/* Agent Room — full width, isometric display */}
        <IsometricRoom agents={activeAgents} tasks={tasks} loading={agentsLoading} />

        <div className="max-w-2xl mx-auto px-5">

          {/* Tabs: Tasks | Context (nested: Identity, Brand, Documents) — ADR-144 */}
          <div>
            <div className="flex gap-1 mb-3 border-b border-border/50 pb-2">
              {(['tasks', 'context'] as const).map(tab => (
                <button
                  key={tab}
                  onClick={() => setActiveTab(tab)}
                  className={cn(
                    'px-3 py-1.5 text-xs font-medium rounded-md transition-colors capitalize',
                    activeTab === tab ? 'bg-muted text-foreground' : 'text-muted-foreground/40 hover:text-muted-foreground'
                  )}
                >
                  {tab}
                </button>
              ))}
            </div>

            {activeTab === 'tasks' && <TasksTab tasks={tasks} />}

            {activeTab === 'context' && (
              <div>
                {/* Context sub-navigation */}
                <div className="flex gap-1 mb-3 border-b border-border/30 pb-1.5">
                  {(['identity', 'brand', 'documents'] as const).map(sub => (
                    <button
                      key={sub}
                      onClick={() => setContextSubTab(sub)}
                      className={cn(
                        'px-2.5 py-1 text-[11px] font-medium rounded transition-colors capitalize',
                        contextSubTab === sub ? 'bg-primary/10 text-primary' : 'text-muted-foreground/40 hover:text-muted-foreground/70'
                      )}
                    >
                      {sub}
                    </button>
                  ))}
                </div>
                {contextSubTab === 'identity' && <IdentityTab onSendMessage={handleContextUpdate} />}
                {contextSubTab === 'brand' && <BrandTab onSendMessage={handleContextUpdate} />}
                {contextSubTab === 'documents' && <DocumentsTab />}
              </div>
            )}
          </div>
        </div>
      </div>
    </WorkspaceLayout>
  );
}
