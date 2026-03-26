'use client';

/**
 * Workfloor — ADR-139 v3: Agent Grid + TP Chat Panel
 *
 * Left: Agent roster (living office) + tabbed data (Tasks | Context | Platforms)
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
  Link2,
  ListChecks,
  ChevronRight,
  LayoutGrid,
  Cog,
  MessageCircle,
  Send,
  Upload,
  Search,
  Globe,
  RefreshCw,
  FlaskConical,
  FileText,
  TrendingUp,
  Users,
  BookOpen,
} from 'lucide-react';
import { useTP } from '@/contexts/TPContext';
import { useDesk } from '@/contexts/DeskContext';
import { useFileAttachments } from '@/hooks/useFileAttachments';
import type { Agent, Task } from '@/types';
import { cn } from '@/lib/utils';
import { api } from '@/lib/api/client';
import { WorkspaceLayout, type WorkspacePanelTab } from '@/components/desk/WorkspaceLayout';
import { AgentAvatar, TPAvatar } from '@/components/agents/AgentAvatar';
import { CommandPicker } from '@/components/tp/CommandPicker';
import { PlusMenu, type PlusMenuAction } from '@/components/tp/PlusMenu';
import { MessageBlocks } from '@/components/tp/InlineToolCall';
import { ToolResultList } from '@/components/tp/ToolResultCard';
import ReactMarkdown from 'react-markdown';

// =============================================================================
// Agent type config
// =============================================================================

const TYPE_CONFIG: Record<string, { hex: string; icon: typeof FlaskConical; accent: string; bgRoom: string; label: string }> = {
  research:   { hex: '#3b82f6', icon: FlaskConical,  accent: 'border-blue-400/30',   bgRoom: 'from-blue-50 to-blue-100/50 dark:from-blue-950/30 dark:to-blue-900/20',   label: 'Research' },
  content:    { hex: '#a855f7', icon: FileText,      accent: 'border-purple-400/30', bgRoom: 'from-purple-50 to-purple-100/50 dark:from-purple-950/30 dark:to-purple-900/20', label: 'Content' },
  marketing:  { hex: '#ec4899', icon: TrendingUp,    accent: 'border-pink-400/30',   bgRoom: 'from-pink-50 to-pink-100/50 dark:from-pink-950/30 dark:to-pink-900/20',   label: 'Marketing' },
  crm:        { hex: '#f97316', icon: Users,         accent: 'border-orange-400/30', bgRoom: 'from-orange-50 to-orange-100/50 dark:from-orange-950/30 dark:to-orange-900/20', label: 'CRM' },
  slack_bot:  { hex: '#14b8a6', icon: MessageCircle, accent: 'border-teal-400/30',   bgRoom: 'from-teal-50 to-teal-100/50 dark:from-teal-950/30 dark:to-teal-900/20',   label: 'Slack Bot' },
  notion_bot: { hex: '#6366f1', icon: BookOpen,      accent: 'border-indigo-400/30', bgRoom: 'from-indigo-50 to-indigo-100/50 dark:from-indigo-950/30 dark:to-indigo-900/20', label: 'Notion Bot' },
  briefer:    { hex: '#3b82f6', icon: FlaskConical,  accent: 'border-blue-400/30',   bgRoom: 'from-blue-50 to-blue-100/50 dark:from-blue-950/30 dark:to-blue-900/20',   label: 'Research' },
  researcher: { hex: '#3b82f6', icon: FlaskConical,  accent: 'border-blue-400/30',   bgRoom: 'from-blue-50 to-blue-100/50 dark:from-blue-950/30 dark:to-blue-900/20',   label: 'Research' },
  analyst:    { hex: '#3b82f6', icon: FlaskConical,  accent: 'border-blue-400/30',   bgRoom: 'from-blue-50 to-blue-100/50 dark:from-blue-950/30 dark:to-blue-900/20',   label: 'Research' },
  drafter:    { hex: '#a855f7', icon: FileText,      accent: 'border-purple-400/30', bgRoom: 'from-purple-50 to-purple-100/50 dark:from-purple-950/30 dark:to-purple-900/20', label: 'Content' },
  writer:     { hex: '#a855f7', icon: FileText,      accent: 'border-purple-400/30', bgRoom: 'from-purple-50 to-purple-100/50 dark:from-purple-950/30 dark:to-purple-900/20', label: 'Content' },
  custom:     { hex: '#6b7280', icon: Cog,           accent: 'border-gray-400/30',   bgRoom: 'from-gray-50 to-gray-100/50 dark:from-gray-950/30 dark:to-gray-900/20',   label: 'Custom' },
};

function getType(role: string) {
  return TYPE_CONFIG[role] || TYPE_CONFIG.custom;
}

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

// =============================================================================
// Agent Room Card (with avatar)
// =============================================================================

function AgentRoomCard({ agent, tasks }: { agent: Agent; tasks: Task[] }) {
  const config = getType(agent.role);
  const isRunning = agent.latest_version_status === 'generating';
  const isPaused = agent.status === 'paused';
  const hasFailed = agent.latest_version_status === 'failed';

  const agentSlug = agent.slug || agent.title.toLowerCase().replace(/\s+/g, '-');
  const assignedTasks = tasks.filter(t => t.status !== 'archived' && t.agent_slugs?.includes(agentSlug));
  const activeTask = assignedTasks[0];

  const avatarState: 'working' | 'ready' | 'paused' | 'idle' | 'error' =
    isRunning ? 'working' : isPaused ? 'paused' : hasFailed ? 'error' : activeTask ? 'ready' : 'idle';

  const Icon = config.icon;

  return (
    <Link
      href={`/agents/${agent.id}`}
      className="relative flex flex-col items-center rounded-2xl border border-border/60 bg-background p-3 pt-2 transition-all hover:shadow-md hover:-translate-y-0.5 hover:border-border"
    >
      <AgentAvatar state={avatarState} color={config.hex} size={60} icon={<Icon size={11} strokeWidth={2.5} />} />
      <span className="text-[11px] font-medium text-center mt-0.5 truncate w-full">{agent.title}</span>
      {activeTask && (
        <span className="text-[8px] text-muted-foreground/40 truncate w-full text-center">{activeTask.title}</span>
      )}
    </Link>
  );
}

// =============================================================================
// Tabs below agent grid
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
        <p className="text-[10px] text-muted-foreground/30 text-center py-3">No tasks — use chat to create one</p>
      )}
    </div>
  );
}

function IdentityTab() {
  const [profile, setProfile] = useState<{ name?: string; role?: string; company?: string; timezone?: string; summary?: string } | null>(null);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState({ name: '', role: '', company: '', timezone: '' });
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    api.profile.get().then(p => { setProfile(p); setDraft({ name: p?.name || '', role: p?.role || '', company: p?.company || '', timezone: p?.timezone || '' }); }).catch(() => {}).finally(() => setLoading(false));
  }, []);

  const handleSave = async () => {
    setSaving(true);
    try {
      const updated = await api.profile.update(draft);
      setProfile(updated);
      setEditing(false);
    } catch (e) { console.error(e); }
    setSaving(false);
  };

  if (loading) return <div className="flex items-center justify-center p-4"><Loader2 className="w-3 h-3 animate-spin text-muted-foreground" /></div>;

  const fields = [
    { key: 'name', label: 'Name' },
    { key: 'role', label: 'Role' },
    { key: 'company', label: 'Company' },
    { key: 'timezone', label: 'Timezone' },
  ] as const;

  const hasContent = profile && (profile.name || profile.role || profile.company);

  return (
    <div className="space-y-2">
      {editing ? (
        <>
          {fields.map(f => (
            <div key={f.key} className="px-2">
              <label className="text-[9px] text-muted-foreground/50 uppercase tracking-wide">{f.label}</label>
              <input
                value={draft[f.key]}
                onChange={e => setDraft(prev => ({ ...prev, [f.key]: e.target.value }))}
                className="w-full text-xs bg-muted/30 border border-border rounded px-2 py-1 mt-0.5 focus:outline-none focus:ring-1 focus:ring-primary/50"
                placeholder={f.label}
              />
            </div>
          ))}
          <div className="flex gap-1.5 px-2 pt-1">
            <button onClick={handleSave} disabled={saving} className="px-2.5 py-1 text-[10px] font-medium rounded bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50">
              {saving ? '...' : 'Save'}
            </button>
            <button onClick={() => setEditing(false)} className="px-2.5 py-1 text-[10px] font-medium rounded border border-border text-muted-foreground hover:bg-muted/50">
              Cancel
            </button>
          </div>
        </>
      ) : hasContent ? (
        <>
          {fields.map(f => {
            const val = profile?.[f.key];
            if (!val) return null;
            return (
              <div key={f.key} className="px-2 py-0.5">
                <span className="text-[9px] text-muted-foreground/40 uppercase tracking-wide">{f.label}</span>
                <p className="text-xs">{val}</p>
              </div>
            );
          })}
          {profile?.summary && (
            <div className="px-2 py-0.5">
              <span className="text-[9px] text-muted-foreground/40 uppercase tracking-wide">Summary</span>
              <p className="text-[11px] text-muted-foreground/70">{profile.summary}</p>
            </div>
          )}
          <button onClick={() => setEditing(true)} className="mx-2 mt-1 text-[9px] text-muted-foreground/40 hover:text-muted-foreground/70">
            Edit →
          </button>
        </>
      ) : (
        <div className="text-center py-4">
          <p className="text-[10px] text-muted-foreground/30 mb-2">No identity set — tell agents who you are</p>
          <button onClick={() => setEditing(true)} className="text-[10px] text-primary hover:underline">Set up identity</button>
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
          <div className="text-[11px] text-muted-foreground/70 bg-muted/20 rounded-lg p-2.5 max-h-48 overflow-y-auto">
            <ReactMarkdown>{content}</ReactMarkdown>
          </div>
          <button onClick={() => setEditing(true)} className="text-[9px] text-muted-foreground/40 hover:text-muted-foreground/70">
            Edit →
          </button>
        </>
      ) : (
        <div className="text-center py-4">
          <p className="text-[10px] text-muted-foreground/30 mb-2">No brand guide — define voice, tone, and style</p>
          <button onClick={() => { setDraft(''); setEditing(true); }} className="text-[10px] text-primary hover:underline">Add brand guide</button>
        </div>
      )}
    </div>
  );
}

function PlatformsTab() {
  const [platforms, setPlatforms] = useState<Array<{ provider: string; status: string; resource_count: number }>>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.integrations.getSummary().then(res => setPlatforms(res.platforms)).catch(() => []).finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="flex items-center justify-center p-4"><Loader2 className="w-3 h-3 animate-spin text-muted-foreground" /></div>;

  return (
    <div className="space-y-1">
      {['slack', 'notion'].map(provider => {
        const p = platforms.find(pl => pl.provider === provider);
        const connected = p && (p.status === 'active' || p.status === 'connected');
        return (
          <Link key={provider} href={connected ? `/context/${provider}` : '/settings?tab=connectors'} className="flex items-center justify-between px-2 py-1.5 rounded-lg hover:bg-muted/30 transition-colors text-xs">
            <div className="flex items-center gap-1.5">
              <span className={cn('w-1.5 h-1.5 rounded-full', connected ? 'bg-emerald-500' : 'bg-gray-300')} />
              <span className={cn('capitalize', connected ? '' : 'text-muted-foreground/30')}>{provider}</span>
            </div>
            {connected && <span className="text-[10px] text-muted-foreground/40">{p?.resource_count} sources</span>}
          </Link>
        );
      })}
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

  const plusMenuActions: PlusMenuAction[] = [
    { id: 'create-task', label: 'Create a task', icon: ListChecks, verb: 'prompt', onSelect: () => { setInput('Create a task for '); textareaRef.current?.focus(); } },
    { id: 'search-platforms', label: 'Search platforms', icon: Search, verb: 'prompt', onSelect: () => { setInput('Search across my connected platforms for '); textareaRef.current?.focus(); } },
    { id: 'web-search', label: 'Web search', icon: Globe, verb: 'prompt', onSelect: () => { setInput('Search the web for '); textareaRef.current?.focus(); } },
    { id: 'run-task', label: 'Run a task now', icon: RefreshCw, verb: 'prompt', onSelect: () => { setInput('Run my '); textareaRef.current?.focus(); } },
    { id: 'upload-file', label: 'Upload file', icon: Upload, verb: 'attach', onSelect: () => fileInputRef.current?.click() },
  ];

  return (
    <div className="flex flex-col h-full">
      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-3 py-3 space-y-2.5">
        {messages.length === 0 && !isLoading && (
          <div className="text-center py-6">
            <MessageCircle className="w-5 h-5 text-muted-foreground/15 mx-auto mb-1.5" />
            <p className="text-[11px] text-muted-foreground/40">Ask anything or type / for commands</p>
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
                  <div className="prose prose-sm dark:prose-invert max-w-none prose-p:my-0.5"><ReactMarkdown>{msg.content}</ReactMarkdown></div>
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
  const { loadScopedHistory } = useTP();
  const searchParams = useSearchParams();
  const router = useRouter();

  const [agents, setAgents] = useState<Agent[]>([]);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [agentsLoading, setAgentsLoading] = useState(true);
  const [tasksLoading, setTasksLoading] = useState(true);
  const [bootstrapProvider, setBootstrapProvider] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'tasks' | 'identity' | 'brand' | 'platforms'>('tasks');

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
      panelDefaultPct={40}
    >
      <div className="flex-1 overflow-y-auto p-5">
        <div className="max-w-2xl mx-auto">
          {/* Bootstrap banner */}
          {bootstrapProvider && (
            <div className="flex items-center gap-3 p-3 rounded-lg border border-primary/20 bg-primary/5 mb-5">
              <div className="flex-1">
                <p className="text-sm font-medium">Connected {bootstrapProvider.charAt(0).toUpperCase() + bootstrapProvider.slice(1)}!</p>
                <p className="text-xs text-muted-foreground">Syncing...</p>
              </div>
              <button onClick={() => setBootstrapProvider(null)} className="text-muted-foreground hover:text-foreground"><X className="w-4 h-4" /></button>
            </div>
          )}

          {/* TP Card */}
          <div className="mb-5">
            <div className="flex items-center gap-3 p-3 rounded-xl border border-primary/15 bg-primary/5">
              <TPAvatar size={40} />
              <div>
                <span className="text-sm font-semibold">Orchestrator</span>
                <span className="text-[10px] text-muted-foreground block">Your thinking partner — always online</span>
              </div>
              <span className="ml-auto w-2 h-2 rounded-full bg-primary animate-pulse" />
            </div>
          </div>

          {/* Agent Grid */}
          <div className="mb-5">

            {agentsLoading ? (
              <div className="flex items-center justify-center py-10"><Loader2 className="w-4 h-4 animate-spin text-muted-foreground" /></div>
            ) : activeAgents.length > 0 ? (
              <div className="grid grid-cols-3 sm:grid-cols-3 lg:grid-cols-3 gap-2.5">
                {activeAgents.map(agent => <AgentRoomCard key={agent.id} agent={agent} tasks={tasks} />)}
              </div>
            ) : (
              <div className="grid grid-cols-3 gap-2.5">
                {['Research', 'Content', 'Marketing', 'CRM', 'Slack', 'Notion'].map(name => (
                  <div key={name} className="flex flex-col items-center justify-center p-4 rounded-2xl border border-dashed border-border/30">
                    <span className="text-[10px] text-muted-foreground/20">{name}</span>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Tabs: Tasks | Context | Platforms */}
          <div className="border-t border-border pt-3">
            <div className="flex gap-1 mb-2">
              {(['tasks', 'identity', 'brand', 'platforms'] as const).map(tab => (
                <button
                  key={tab}
                  onClick={() => setActiveTab(tab)}
                  className={cn(
                    'px-2.5 py-1 text-[10px] font-medium rounded-md transition-colors capitalize',
                    activeTab === tab ? 'bg-muted text-foreground' : 'text-muted-foreground/50 hover:text-muted-foreground'
                  )}
                >
                  {tab}
                </button>
              ))}
            </div>
            {activeTab === 'tasks' && <TasksTab tasks={tasks} />}
            {activeTab === 'identity' && <IdentityTab />}
            {activeTab === 'brand' && <BrandTab />}
            {activeTab === 'platforms' && <PlatformsTab />}
          </div>
        </div>
      </div>
    </WorkspaceLayout>
  );
}
