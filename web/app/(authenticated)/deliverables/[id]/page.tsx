'use client';

/**
 * ADR-091: Deliverable Workspace
 *
 * Cowork-style layout for a single deliverable:
 * - Left: scoped TP chat (dominant, full height)
 * - Right: collapsible panel — Versions | Memory | Instructions | Sessions tabs
 * - Header: breadcrumb + deliverable identity chip + mode badge + controls
 *
 * Chat is scoped via surface_context { type: 'deliverable-detail', deliverableId }
 * which sets deliverable_id on the chat_sessions row (ADR-087).
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { useRouter, useParams } from 'next/navigation';
import Link from 'next/link';
import ReactMarkdown from 'react-markdown';
import {
  Loader2,
  Play,
  Pause,
  Settings,
  CheckCircle2,
  XCircle,
  ChevronLeft,
  MessageSquare,
  Mail,
  FileText,
  ExternalLink,
  RefreshCw,
  Sparkles,
  Copy,
  Clock,
  Database,
  Target,
  Brain,
  Bot,
  PenLine,
  History,
  Send,
  Paperclip,
  X,
} from 'lucide-react';
import { api } from '@/lib/api/client';
import { formatDistanceToNow, format } from 'date-fns';
import { cn } from '@/lib/utils';
import { DeliverableSettingsModal } from '@/components/modals/DeliverableSettingsModal';
import { WorkspaceLayout, WorkspacePanelTab } from '@/components/desk/WorkspaceLayout';
import { useTP } from '@/contexts/TPContext';
import { SkillPicker } from '@/components/tp/SkillPicker';
import { MessageBlocks } from '@/components/tp/InlineToolCall';
import { ToolResultList } from '@/components/tp/ToolResultCard';
import { TPImageAttachment } from '@/types/desk';
import { DeliverableModeBadge } from '@/components/deliverables/DeliverableModeBadge';
import type { Deliverable, DeliverableVersion, DeliverableSession, SourceSnapshot } from '@/types';

// =============================================================================
// Helpers (shared with previous page, extracted)
// =============================================================================

const PLATFORM_EMOJI: Record<string, string> = {
  slack: '\u{1F4AC}',
  gmail: '\u{1F4E7}',
  email: '\u{1F4E7}',
  notion: '\u{1F4DD}',
  calendar: '\u{1F4C5}',
  synthesis: '\u{1F4CA}',
};

const PLATFORM_ICON: Record<string, React.ComponentType<{ className?: string }>> = {
  slack: MessageSquare,
  gmail: Mail,
  email: Mail,
  notion: FileText,
};

function getPlatformEmoji(deliverable: Deliverable): string {
  const cls = deliverable.type_classification;
  if (cls?.binding === 'cross_platform' || cls?.binding === 'hybrid' || cls?.binding === 'research') {
    return '\u{1F4CA}';
  }
  const platform = cls?.primary_platform || deliverable.destination?.platform;
  return PLATFORM_EMOJI[platform || ''] || '\u{1F4CA}';
}

function formatSchedule(deliverable: Deliverable): string {
  if (deliverable.mode === 'goal') return 'Goal';
  if (deliverable.mode === 'reactive') return 'Reactive';
  if (deliverable.mode === 'proactive') return 'Proactive';
  if (deliverable.mode === 'coordinator') return 'Coordinator';
  const s = deliverable.schedule;
  if (!s) return 'No schedule';
  const time = s.time || '09:00';
  const day = s.day
    ? s.day.charAt(0).toUpperCase() + s.day.slice(1)
    : s.frequency === 'monthly' ? '1st' : '';
  switch (s.frequency) {
    case 'daily': return `Daily at ${time}`;
    case 'weekly': return `${day || 'Weekly'} at ${time}`;
    case 'biweekly': return `Every 2 weeks, ${day} at ${time}`;
    case 'monthly': return `Monthly on the ${day} at ${time}`;
    default: return s.frequency || 'Custom';
  }
}

function formatDestination(deliverable: Deliverable): string | null {
  const dest = deliverable.destination;
  if (!dest) return null;
  const target = dest.target;
  if (target?.includes('@')) return target;
  if (target?.startsWith('#')) return target;
  if (target === 'dm') return 'DM';
  return null;
}

function getStatusBadge(version: DeliverableVersion) {
  const status = version.delivery_status || version.status;
  if (status === 'delivered') {
    return (
      <span className="inline-flex items-center gap-1 text-xs text-green-600 dark:text-green-400 bg-green-50 dark:bg-green-900/30 px-2 py-0.5 rounded-full">
        <CheckCircle2 className="w-3 h-3" />
        Delivered
      </span>
    );
  }
  if (status === 'failed') {
    return (
      <span className="inline-flex items-center gap-1 text-xs text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/30 px-2 py-0.5 rounded-full">
        <XCircle className="w-3 h-3" />
        Failed
      </span>
    );
  }
  if (status === 'generating') {
    return (
      <span className="inline-flex items-center gap-1 text-xs text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-900/30 px-2 py-0.5 rounded-full">
        <Loader2 className="w-3 h-3 animate-spin" />
        Generating
      </span>
    );
  }
  return <span className="text-xs text-muted-foreground">{status}</span>;
}

function getVersionTimestamp(version: DeliverableVersion): string {
  const ts = version.delivered_at || version.created_at;
  return format(new Date(ts), 'MMM d, h:mm a');
}

function wordCount(text: string): number {
  return text.trim().split(/\s+/).filter(Boolean).length;
}

function SourcePills({ snapshots }: { snapshots: SourceSnapshot[] }) {
  if (!snapshots || snapshots.length === 0) return null;
  return (
    <span className="inline-flex items-center gap-1.5 text-xs text-muted-foreground">
      <Database className="w-3 h-3" />
      {snapshots.map((s, i) => (
        <span key={i} className="inline-flex items-center gap-0.5">
          {i > 0 && <span className="text-border">&middot;</span>}
          <span>{PLATFORM_EMOJI[s.platform] || '\u{1F4C4}'}</span>
          <span>{s.resource_name || s.resource_id}</span>
          {s.item_count != null && (
            <span className="text-muted-foreground/60">({s.item_count})</span>
          )}
        </span>
      ))}
    </span>
  );
}

// =============================================================================
// Panel tab content components
// =============================================================================

function VersionsPanel({
  versions,
  selectedIdx,
  onSelect,
  onRunNow,
  running,
  deliverable,
}: {
  versions: DeliverableVersion[];
  selectedIdx: number;
  onSelect: (idx: number) => void;
  onRunNow: () => void;
  running: boolean;
  deliverable: Deliverable;
}) {
  const isGoalMode = deliverable.mode === 'goal';
  const isPlatformBound = deliverable.type_classification?.binding === 'platform_bound';
  const hasSources = (deliverable.sources?.length ?? 0) > 0;
  const missingSourcesWarning = isPlatformBound && !hasSources;
  const selectedVersion = versions[selectedIdx] || null;

  return (
    <div className="flex flex-col h-full">
      {/* Schedule / run row */}
      <div className="px-3 py-2.5 border-b border-border shrink-0 flex items-center justify-between gap-2">
        <div className="text-xs text-muted-foreground">
          {deliverable.mode !== 'recurring' ? (
            <span className="capitalize">{deliverable.mode} mode</span>
          ) : deliverable.next_run_at ? (
            <>
              Next: <span className="font-medium text-foreground">
                {format(new Date(deliverable.next_run_at), 'EEE, MMM d')} at {format(new Date(deliverable.next_run_at), 'h:mm a')}
              </span>
              <span className="ml-1 text-muted-foreground/70">
                ({formatDistanceToNow(new Date(deliverable.next_run_at), { addSuffix: true })})
              </span>
            </>
          ) : 'No scheduled runs'}
        </div>
        <button
          onClick={onRunNow}
          disabled={running || deliverable.status === 'archived' || missingSourcesWarning}
          title={missingSourcesWarning ? 'Add sources in Settings before running' : undefined}
          className="inline-flex items-center gap-1 px-2 py-1 text-xs border border-border rounded hover:bg-muted disabled:opacity-50 disabled:cursor-not-allowed transition-colors shrink-0"
        >
          {running ? <Loader2 className="w-3 h-3 animate-spin" /> : <Play className="w-3 h-3" />}
          {isGoalMode ? 'Generate' : 'Run Now'}
        </button>
      </div>

      {missingSourcesWarning && (
        <div className="px-3 py-2 bg-amber-50 dark:bg-amber-900/20 border-b border-amber-200 dark:border-amber-800 text-xs text-amber-800 dark:text-amber-300 flex items-center gap-1.5 shrink-0">
          <span className="shrink-0">&#9888;</span>
          No sources configured — open Settings to select platform content.
        </div>
      )}

      {/* Version list */}
      {versions.length === 0 ? (
        <div className="flex-1 flex flex-col items-center justify-center p-6 text-center">
          <FileText className="w-8 h-8 text-muted-foreground/30 mb-3" />
          <p className="text-sm text-muted-foreground">No deliveries yet</p>
        </div>
      ) : (
        <div className="flex-1 overflow-y-auto">
          {/* Preview of selected version */}
          {selectedVersion && (
            <VersionPreview version={selectedVersion} />
          )}
          {/* Version list */}
          <div className="divide-y divide-border">
            {versions.slice(0, 10).map((version, idx) => (
              <button
                key={version.id}
                onClick={() => onSelect(idx)}
                className={cn(
                  'w-full px-3 py-2.5 flex items-center justify-between hover:bg-muted/50 transition-colors text-left',
                  idx === selectedIdx && 'bg-primary/5 border-l-2 border-l-primary'
                )}
              >
                <div className="flex items-center gap-2 min-w-0">
                  <span className="text-xs text-muted-foreground shrink-0">v{version.version_number}</span>
                  <span className="text-xs truncate">{getVersionTimestamp(version)}</span>
                  {getStatusBadge(version)}
                </div>
                {version.delivery_external_url && (
                  <a
                    href={version.delivery_external_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    onClick={(e) => e.stopPropagation()}
                    className="p-1 hover:bg-muted rounded transition-colors text-primary shrink-0"
                    title="View in destination"
                  >
                    <ExternalLink className="w-3.5 h-3.5" />
                  </a>
                )}
              </button>
            ))}
            {versions.length > 10 && (
              <div className="px-3 py-2 text-center">
                <span className="text-xs text-muted-foreground">Showing 10 of {versions.length}</span>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

function VersionPreview({ version }: { version: DeliverableVersion }) {
  const [expanded, setExpanded] = useState(false);
  const [copied, setCopied] = useState(false);
  const content = version.final_content || version.draft_content || '';

  const handleCopy = async () => {
    if (!content) return;
    await navigator.clipboard.writeText(content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (!content && version.status !== 'generating') return null;

  return (
    <div className="border-b border-border">
      {version.status === 'generating' ? (
        <div className="p-4 flex items-center gap-2 text-sm text-muted-foreground">
          <Loader2 className="w-4 h-4 animate-spin text-blue-500" />
          Generating content...
        </div>
      ) : (version.status === 'failed' || version.delivery_status === 'failed') ? (
        <div className="p-3 bg-red-50 dark:bg-red-900/20 flex items-center gap-2">
          <XCircle className="w-3.5 h-3.5 text-red-600 dark:text-red-400 shrink-0" />
          <span className="text-xs text-red-700 dark:text-red-400">
            {version.delivery_error || 'Delivery failed'}
          </span>
        </div>
      ) : (
        <>
          <div
            className={cn(
              'px-3 py-3 prose prose-sm dark:prose-invert max-w-none prose-headings:mt-3 prose-headings:mb-1 prose-p:my-1 prose-ul:my-1 prose-li:my-0',
              !expanded && 'max-h-48 overflow-hidden relative'
            )}
          >
            {!expanded && (
              <div className="absolute inset-x-0 bottom-0 h-12 bg-gradient-to-t from-background to-transparent pointer-events-none" />
            )}
            <ReactMarkdown>{content}</ReactMarkdown>
          </div>
          <div className="px-3 py-1.5 border-t border-border flex items-center gap-2">
            <button
              onClick={() => setExpanded(!expanded)}
              className="text-xs text-muted-foreground hover:text-foreground transition-colors"
            >
              {expanded ? 'Collapse' : 'Expand'}
            </button>
            <span className="text-border text-xs">&middot;</span>
            <button
              onClick={handleCopy}
              className="text-xs text-muted-foreground hover:text-foreground transition-colors inline-flex items-center gap-1"
            >
              {copied ? <CheckCircle2 className="w-3 h-3 text-green-600" /> : <Copy className="w-3 h-3" />}
              {copied ? 'Copied' : 'Copy'}
            </button>
            {content && (
              <>
                <span className="text-border text-xs">&middot;</span>
                <span className="text-xs text-muted-foreground">{wordCount(content).toLocaleString()} words</span>
              </>
            )}
            {version.source_snapshots && version.source_snapshots.length > 0 && (
              <>
                <span className="text-border text-xs">&middot;</span>
                <SourcePills snapshots={version.source_snapshots} />
              </>
            )}
            <div className="ml-auto flex items-center gap-2">
              <span className="text-xs text-muted-foreground">
                <Clock className="w-3 h-3 inline mr-0.5" />
                {getVersionTimestamp(version)}
              </span>
              {getStatusBadge(version)}
              {version.delivery_external_url && (
                <a
                  href={version.delivery_external_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors"
                >
                  <ExternalLink className="w-3 h-3" />
                  View
                </a>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
}

function MemoryPanel({ deliverable }: { deliverable: Deliverable }) {
  const memory = deliverable.deliverable_memory;
  const observations = memory?.observations || [];
  const goal = memory?.goal;

  if (observations.length === 0 && !goal) {
    return (
      <div className="p-4 text-center">
        <p className="text-sm text-muted-foreground py-4">
          No observations yet. The agent accumulates knowledge as it processes content for this deliverable.
        </p>
      </div>
    );
  }

  return (
    <div className="p-3 space-y-2.5">
      {goal && (
        <div className="p-3 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-md">
          <div className="flex items-center gap-1.5 mb-1">
            <Target className="w-3.5 h-3.5 text-blue-600 dark:text-blue-400" />
            <span className="text-xs font-medium text-blue-700 dark:text-blue-400">Goal</span>
          </div>
          <p className="text-sm">{goal.description}</p>
          <p className="text-xs text-muted-foreground mt-1">Status: {goal.status}</p>
          {goal.milestones && goal.milestones.length > 0 && (
            <ul className="mt-1.5 space-y-1">
              {goal.milestones.map((m, i) => (
                <li key={i} className="flex items-center gap-1.5 text-xs text-muted-foreground">
                  <span className="w-1 h-1 rounded-full bg-muted-foreground/40 shrink-0" />
                  {m}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
      {observations.map((obs, i) => (
        <div key={i} className="p-2.5 bg-muted/30 border border-border rounded-md">
          <div className="flex items-center gap-1.5 text-xs text-muted-foreground mb-1">
            <span>{obs.date}</span>
            {obs.source && (
              <>
                <span className="text-border">&middot;</span>
                <span>{obs.source}</span>
              </>
            )}
          </div>
          <p className="text-sm">{obs.note}</p>
        </div>
      ))}
    </div>
  );
}

function InstructionsPanel({
  instructions,
  onChange,
  onBlur,
  saving,
  saved,
}: {
  instructions: string;
  onChange: (v: string) => void;
  onBlur: () => void;
  saving: boolean;
  saved: boolean;
}) {
  return (
    <div className="p-3">
      <textarea
        value={instructions}
        onChange={(e) => onChange(e.target.value)}
        onBlur={onBlur}
        placeholder={
          'Add instructions for how the agent should approach this deliverable. Examples:\n\n' +
          'Use formal tone for this board report.\n' +
          'Always include an executive summary section.\n' +
          'Focus on trend analysis rather than raw numbers.\n' +
          'The audience is the executive team.'
        }
        className="w-full min-h-[160px] px-3 py-2 text-sm font-mono bg-background border border-border rounded-md focus:outline-none focus:ring-2 focus:ring-primary/20 resize-y placeholder:text-muted-foreground/60"
      />
      <div className="flex items-center justify-end mt-1.5 h-5">
        {saving && (
          <span className="text-xs text-muted-foreground flex items-center gap-1">
            <Loader2 className="w-3 h-3 animate-spin" /> Saving...
          </span>
        )}
        {saved && !saving && (
          <span className="text-xs text-green-600 flex items-center gap-1">
            <CheckCircle2 className="w-3 h-3" /> Saved
          </span>
        )}
      </div>
    </div>
  );
}

function SessionsPanel({ sessions }: { sessions: DeliverableSession[] }) {
  if (sessions.length === 0) {
    return (
      <div className="p-4 text-center">
        <p className="text-sm text-muted-foreground py-4">
          No scoped conversations yet. Chat with this deliverable open to build session history.
        </p>
      </div>
    );
  }

  return (
    <div className="p-3 space-y-2">
      {sessions.map((session) => (
        <div key={session.id} className="p-2.5 bg-muted/30 border border-border rounded-md">
          <div className="flex items-center justify-between mb-1">
            <span className="text-xs text-muted-foreground">
              {format(new Date(session.created_at), 'MMM d, h:mm a')}
            </span>
            <span className="text-xs text-muted-foreground">
              {session.message_count} message{session.message_count !== 1 ? 's' : ''}
            </span>
          </div>
          {session.summary ? (
            <p className="text-sm line-clamp-2">{session.summary}</p>
          ) : (
            <p className="text-sm text-muted-foreground italic">No summary</p>
          )}
        </div>
      ))}
    </div>
  );
}

// =============================================================================
// Scoped Chat Area (reuses TP context, scoped to this deliverable)
// =============================================================================

function DeliverableChatArea({
  deliverableId,
  deliverableTitle,
}: {
  deliverableId: string;
  deliverableTitle: string;
}) {
  const {
    messages,
    sendMessage,
    isLoading,
    status,
    pendingClarification,
    respondToClarification,
    tokenUsage,
  } = useTP();

  const [input, setInput] = useState('');
  const [attachments, setAttachments] = useState<File[]>([]);
  const [attachmentPreviews, setAttachmentPreviews] = useState<string[]>([]);
  const [skillPickerOpen, setSkillPickerOpen] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const surface = { type: 'deliverable-detail' as const, deliverableId };

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, status]);

  useEffect(() => {
    textareaRef.current?.focus();
  }, []);

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

  const skillQuery = input.startsWith('/') ? input.slice(1).split(' ')[0] : null;
  useEffect(() => {
    if (skillQuery !== null && !input.includes(' ')) {
      setSkillPickerOpen(true);
    } else {
      setSkillPickerOpen(false);
    }
  }, [skillQuery, input]);

  const fileToBase64 = (file: File): Promise<string> => {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => {
        const result = reader.result as string;
        resolve(result.split(',')[1]);
      };
      reader.onerror = reject;
      reader.readAsDataURL(file);
    });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if ((!input.trim() && attachments.length === 0) || isLoading) return;

    const images: TPImageAttachment[] = [];
    for (const file of attachments) {
      const base64 = await fileToBase64(file);
      const mediaType = file.type as TPImageAttachment['mediaType'];
      if (['image/jpeg', 'image/png', 'image/gif', 'image/webp'].includes(mediaType)) {
        images.push({ data: base64, mediaType });
      }
    }

    sendMessage(input, { surface, images: images.length > 0 ? images : undefined });
    setInput('');
    setAttachments([]);
    setAttachmentPreviews([]);
  };

  const handleSkillSelect = (command: string) => {
    setInput(command + ' ');
    setSkillPickerOpen(false);
    textareaRef.current?.focus();
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    const imageFiles = files.filter((f) => f.type.startsWith('image/'));
    if (imageFiles.length === 0) return;
    imageFiles.forEach((file) => {
      const reader = new FileReader();
      reader.onload = (e) => {
        setAttachmentPreviews((prev) => [...prev, e.target?.result as string]);
      };
      reader.readAsDataURL(file);
    });
    setAttachments((prev) => [...prev, ...imageFiles]);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const removeAttachment = (index: number) => {
    setAttachments((prev) => prev.filter((_, i) => i !== index));
    setAttachmentPreviews((prev) => prev.filter((_, i) => i !== index));
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e as unknown as React.FormEvent);
    }
  };

  return (
    <>
      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
        <div className="max-w-3xl mx-auto w-full space-y-4">
          {messages.length === 0 && !isLoading && (
            <div className="text-center py-8">
              <MessageSquare className="w-10 h-10 text-muted-foreground/20 mx-auto mb-3" />
              <p className="text-sm text-muted-foreground max-w-xs mx-auto mb-4">
                You&apos;re talking to <span className="font-medium text-foreground">{deliverableTitle}</span>.
                Ask me to generate, refine, or review.
              </p>
              <div className="flex flex-wrap justify-center gap-2">
                <button
                  onClick={() => setInput('Generate a new version')}
                  className="px-3 py-1.5 text-sm rounded-full bg-primary/10 text-primary hover:bg-primary/20 transition-colors"
                >
                  Generate a new version
                </button>
                <button
                  onClick={() => setInput('What sources are you using?')}
                  className="px-3 py-1.5 text-sm rounded-full bg-muted hover:bg-muted/80 transition-colors"
                >
                  What sources are you using?
                </button>
              </div>
            </div>
          )}

          {messages.map((msg) => (
            <div
              key={msg.id}
              className={cn(
                'text-sm rounded-lg p-3 max-w-2xl',
                msg.role === 'user' ? 'bg-primary/10 ml-auto' : 'bg-muted'
              )}
            >
              <span className="text-[10px] font-medium text-muted-foreground uppercase tracking-wide block mb-1">
                {msg.role === 'user' ? 'You' : deliverableTitle}
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
                  <p className="whitespace-pre-wrap">{msg.content}</p>
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

          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Input */}
      <div className="p-4 border-t border-border shrink-0">
        <div className="relative max-w-2xl mx-auto">
          <SkillPicker
            query={skillQuery ?? ''}
            onSelect={handleSkillSelect}
            onClose={() => setSkillPickerOpen(false)}
            isOpen={skillPickerOpen}
          />
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
                'flex items-end gap-2 border border-border bg-background transition-colors',
                attachmentPreviews.length > 0 ? 'rounded-b-lg border-t-0' : 'rounded-lg',
                'focus-within:ring-2 focus-within:ring-primary/50'
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
              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                disabled={isLoading}
                className="shrink-0 p-3 text-muted-foreground hover:text-foreground disabled:opacity-50 transition-colors"
                title="Attach images"
              >
                <Paperclip className="w-5 h-5" />
              </button>
              <textarea
                ref={textareaRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                disabled={isLoading}
                placeholder={
                  status.type === 'clarify'
                    ? 'Type your answer...'
                    : `Ask ${deliverableTitle} anything or type / for skills...`
                }
                rows={1}
                className="flex-1 py-3 pr-2 text-sm bg-transparent resize-none focus:outline-none disabled:opacity-50 max-h-[200px]"
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
              <span>Enter to send, Shift+Enter for new line</span>
              {tokenUsage && (
                <span className="font-mono tabular-nums">
                  {tokenUsage.totalTokens >= 1000
                    ? `${(tokenUsage.totalTokens / 1000).toFixed(1)}k`
                    : tokenUsage.totalTokens} tokens
                </span>
              )}
            </div>
          </form>
        </div>
      </div>
    </>
  );
}

// =============================================================================
// Main Component
// =============================================================================

export default function DeliverableWorkspacePage() {
  const params = useParams<{ id: string }>();
  const id = params.id;
  const router = useRouter();

  // Data
  const [loading, setLoading] = useState(true);
  const [deliverable, setDeliverable] = useState<Deliverable | null>(null);
  const [versions, setVersions] = useState<DeliverableVersion[]>([]);
  const [sessions, setSessions] = useState<DeliverableSession[]>([]);
  const [settingsOpen, setSettingsOpen] = useState(false);

  // UI
  const [selectedIdx, setSelectedIdx] = useState(0);
  const [running, setRunning] = useState(false);

  // Instructions editor
  const [instructions, setInstructions] = useState('');
  const [instructionsSaving, setInstructionsSaving] = useState(false);
  const [instructionsSaved, setInstructionsSaved] = useState(false);
  const saveTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const loadDeliverable = useCallback(async () => {
    try {
      const [detail, sessionData] = await Promise.all([
        api.deliverables.get(id),
        api.deliverables.listSessions(id).catch(() => []),
      ]);
      setDeliverable(detail.deliverable);
      setVersions(detail.versions);
      setInstructions(detail.deliverable.deliverable_instructions || '');
      setSessions(sessionData);
    } catch (err) {
      console.error('Failed to load deliverable:', err);
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    loadDeliverable();
  }, [loadDeliverable]);

  const handleTogglePause = async () => {
    if (!deliverable) return;
    try {
      const newStatus = deliverable.status === 'paused' ? 'active' : 'paused';
      await api.deliverables.update(id, { status: newStatus });
      setDeliverable({ ...deliverable, status: newStatus });
    } catch (err) {
      console.error('Failed to update status:', err);
    }
  };

  const handleRunNow = async () => {
    if (!deliverable) return;
    setRunning(true);
    try {
      await api.deliverables.run(id);
      await loadDeliverable();
      setSelectedIdx(0);
    } catch (err) {
      console.error('Failed to run deliverable:', err);
    } finally {
      setRunning(false);
    }
  };

  const handleInstructionsChange = (value: string) => {
    setInstructions(value);
    setInstructionsSaved(false);
    if (saveTimerRef.current) clearTimeout(saveTimerRef.current);
    saveTimerRef.current = setTimeout(() => saveInstructions(value), 2000);
  };

  const saveInstructions = async (value: string) => {
    if (!deliverable) return;
    setInstructionsSaving(true);
    try {
      await api.deliverables.update(id, { deliverable_instructions: value });
      setDeliverable({ ...deliverable, deliverable_instructions: value });
      setInstructionsSaved(true);
      setTimeout(() => setInstructionsSaved(false), 3000);
    } catch (err) {
      console.error('Failed to save instructions:', err);
    } finally {
      setInstructionsSaving(false);
    }
  };

  const handleInstructionsBlur = () => {
    if (saveTimerRef.current) clearTimeout(saveTimerRef.current);
    if (instructions !== (deliverable?.deliverable_instructions || '')) {
      saveInstructions(instructions);
    }
  };

  // ==========================================================================
  // Loading / Not found
  // ==========================================================================

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center">
        <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (!deliverable) {
    return (
      <div className="h-full flex flex-col items-center justify-center gap-4">
        <FileText className="w-8 h-8 text-muted-foreground" />
        <p className="text-muted-foreground">Deliverable not found</p>
        <button onClick={() => router.push('/deliverables')} className="text-sm text-primary hover:underline">
          Back to Deliverables
        </button>
      </div>
    );
  }

  const isGoalMode = deliverable.mode === 'goal';
  const memory = deliverable.deliverable_memory;
  const observations = memory?.observations || [];

  // ==========================================================================
  // Panel tabs
  // ==========================================================================

  const panelTabs: WorkspacePanelTab[] = [
    {
      id: 'versions',
      label: `Versions${versions.length > 0 ? ` (${versions.length})` : ''}`,
      content: (
        <VersionsPanel
          versions={versions}
          selectedIdx={selectedIdx}
          onSelect={setSelectedIdx}
          onRunNow={handleRunNow}
          running={running}
          deliverable={deliverable}
        />
      ),
    },
    {
      id: 'memory',
      label: `Memory${observations.length > 0 ? ` (${observations.length})` : ''}`,
      content: <MemoryPanel deliverable={deliverable} />,
    },
    {
      id: 'instructions',
      label: 'Instructions',
      content: (
        <InstructionsPanel
          instructions={instructions}
          onChange={handleInstructionsChange}
          onBlur={handleInstructionsBlur}
          saving={instructionsSaving}
          saved={instructionsSaved}
        />
      ),
    },
    {
      id: 'sessions',
      label: 'Sessions',
      content: <SessionsPanel sessions={sessions} />,
    },
  ];

  // ==========================================================================
  // Header pieces
  // ==========================================================================

  const modeBadge = <DeliverableModeBadge mode={deliverable.mode} />;

  const headerControls = (
    <div className="flex items-center gap-1.5">
      {deliverable.status === 'paused' ? (
        <span className="text-xs text-amber-600 bg-amber-50 dark:bg-amber-900/20 px-2 py-1 rounded-full hidden sm:flex items-center gap-1">
          <Pause className="w-3 h-3" /> Paused
        </span>
      ) : (
        <span className="text-xs text-green-600 bg-green-50 dark:bg-green-900/20 px-2 py-1 rounded-full hidden sm:flex items-center gap-1">
          <Play className="w-3 h-3" /> Active
        </span>
      )}
      <button
        onClick={handleTogglePause}
        className={cn(
          'p-1.5 border border-border rounded-md hover:bg-muted transition-colors',
          deliverable.status === 'paused' && 'text-amber-600 border-amber-300 bg-amber-50 dark:bg-amber-900/20'
        )}
        title={deliverable.status === 'paused' ? 'Resume' : 'Pause'}
      >
        {deliverable.status === 'paused' ? <Play className="w-3.5 h-3.5" /> : <Pause className="w-3.5 h-3.5" />}
      </button>
      <button
        onClick={() => setSettingsOpen(true)}
        className="p-1.5 border border-border rounded-md hover:bg-muted transition-colors"
        title="Settings"
      >
        <Settings className="w-3.5 h-3.5" />
      </button>
    </div>
  );

  const breadcrumb = (
    <Link
      href="/deliverables"
      className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground transition-colors"
    >
      <ChevronLeft className="w-4 h-4" />
      Deliverables
    </Link>
  );

  return (
    <>
      <WorkspaceLayout
        identity={{
          icon: <span className="text-base leading-none">{getPlatformEmoji(deliverable)}</span>,
          label: deliverable.title,
          badge: (
            <div className="flex items-center gap-1.5">
              {modeBadge}
              {deliverable.origin === 'coordinator_created' && (
                <span className="inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded text-[10px] font-medium bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400">
                  <Sparkles className="w-2.5 h-2.5" />
                  Coordinator
                </span>
              )}
            </div>
          ),
        }}
        breadcrumb={breadcrumb}
        headerControls={headerControls}
        panelTabs={panelTabs}
        panelDefaultOpen={true}
      >
        <DeliverableChatArea
          deliverableId={id}
          deliverableTitle={deliverable.title}
        />
      </WorkspaceLayout>

      <DeliverableSettingsModal
        deliverable={deliverable}
        open={settingsOpen}
        onClose={() => setSettingsOpen(false)}
        onSaved={(updated) => {
          setDeliverable(updated);
          setInstructions(updated.deliverable_instructions || '');
        }}
        onArchived={() => router.push('/deliverables')}
      />
    </>
  );
}
