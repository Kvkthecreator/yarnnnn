'use client';

/**
 * LanePanel — one chat lane's conversation body (ADR-411, implements
 * ADR-408 D6).
 *
 * A lane is a model-pinned helper thread: an isolated conversation whose
 * model works the SHARED workspace through the file-verb tool surface.
 * This panel is deliberately simpler than the steward's ConversationPanel:
 * non-streaming turns (POST → JSON reply), no command picker, no surface
 * override — a lane is a working thread, not the OS terminal.
 *
 * ADR-412 D2/D3 (2026-07-06): relocated from the chat-drawer chrome
 * (shell/chrome/) to the Chat surface body — the drawer purified to the
 * steward (Altitude 1); lanes live in their windowed workbench
 * (Altitude 2). Mechanics unchanged.
 *
 * ADR-441 D2 (2026-07-11): THE lane-thread renderer — one per Altitude 2,
 * frame-agnostic, mounted N times (the /chat workbench, the Studio's left
 * pane) behind the named `LaneMountSlots` contract below. Deliberately NOT
 * merged with the steward's ConversationPanel: the A1/A2 split is a
 * wire-protocol split (ADR-441 D1), not a styling preference.
 *
 * The contract rendered here: the transcript is private to the lane; the
 * work lands in files. When a turn used tools, the reply footer names them
 * so the member sees the lane touched the commons.
 *
 * 2026-07-09 — THE ARTIFACT CARD. Naming the verb was not enough: a lane that
 * wrote a report rendered as `gemini-2.5-pro · WriteFile…` and the member never
 * saw what it made. The stream now carries the PATH of every landed
 * WriteFile/EditFile (`lane_runner.artifact_path_from`), and each one mounts
 * `ArtifactCard` → `FileBody` — the same viewer the Files surface uses. The
 * card renders and opens; it never edits (ADR-236: chat is the mutation
 * surface). Assistant text renders as markdown, as it always should have.
 */

import { useCallback, useEffect, useRef, useState, type ReactNode } from 'react';
import { useAutoResize, COMPOSER_MAX_PX } from '@/hooks/useAutoResize';
import {
  ArrowUp,
  Check,
  Copy,
  FileText,
  ImageIcon,
  Loader2,
  Paperclip,
  Pencil,
  RefreshCw,
  Square,
  Wrench,
  X,
} from 'lucide-react';
import { api } from '@/lib/api/client';
import { formatTimestamp } from '@/lib/formatting';
import { cn } from '@/lib/utils';
import { MarkdownRenderer } from '@/components/shared/MarkdownRenderer';
import { ArtifactCard } from './ArtifactCard';

/** Day label for a message's separator (local date). '' when no timestamp. */
function dayKey(ts?: string): string {
  if (!ts) return '';
  const d = new Date(ts);
  return Number.isNaN(d.getTime()) ? '' : d.toDateString();
}

/** A file this turn wrote or revised — the pointer the lane contract promises. */
interface LaneArtifact {
  path: string;
  verb?: string;
}

interface LaneMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  created_at?: string;
  tools_called?: string[];
  /** Persisted on the assistant row's metadata, so a reloaded lane keeps its cards. */
  artifacts?: LaneArtifact[];
  /** Phase-A attachments: what this user turn carried (metadata, chips). */
  attachments?: Array<{ path: string; kind: 'image' | 'file'; name?: string }>;
}

/** A composer attachment mid-flight: uploading → uploaded (path set) | failed. */
interface PendingAttachment {
  key: string;
  name: string;
  kind: 'image' | 'file';
  path?: string;
  uploading: boolean;
  error?: boolean;
}

/** Metadata `artifacts` is a bare path list on the wire; the verb rides the
 *  live stream only. Normalize both shapes to one. */
function toArtifacts(raw: unknown): LaneArtifact[] | undefined {
  if (!Array.isArray(raw) || raw.length === 0) return undefined;
  const out: LaneArtifact[] = [];
  for (const item of raw) {
    if (typeof item === 'string') out.push({ path: item });
    else if (item && typeof item === 'object' && typeof (item as LaneArtifact).path === 'string') {
      out.push(item as LaneArtifact);
    }
  }
  return out.length ? out : undefined;
}

/**
 * The lane mount-slots contract (ADR-441 D2) — how an embedding surface
 * configures THE lane-thread renderer. One renderer, N mounts (the /chat
 * workbench, the Studio's left pane); the mount owns its frame and declares
 * slots — it never reaches into the thread's messages or transport. A new
 * mount need is a new named slot here, never a surface-specific branch
 * inside LanePanel.
 */
export interface LaneMountSlots {
  /** Fires when a write LANDS mid-turn (and again from the terminal list), so
   *  the mount can refresh its view of a file this lane just authored — the
   *  Studio canvas reload (ADR-440). */
  onArtifactWrite?: (path: string) => void;
  /** Replace the default (lane-contract) empty state — teach the mount's act
   *  in the mount's own words. Absent → the /chat default renders (ADR-440). */
  emptyState?: ReactNode;
  /** Starter prompts, rendered as clickable chips while the transcript is
   *  empty; clicking one fills the composer (ADR-440). */
  suggestions?: string[];
  /** Composer seed: when `nonce` changes, `text` is set into (or appended to)
   *  the composer. Drives pointing + the insert menu (ADR-440 v1.1). */
  composerSeed?: { text: string; nonce: number } | null;
  /** How this mount renders an assistant turn's artifact writes (ADR-443):
   *   - `'card'` (default): the full ArtifactCard preview — the mount has no
   *     other view of the artifact (/chat).
   *   - `'link'`: a compact "wrote {file} →" citation line — the mount
   *     references the artifact but doesn't render it inline.
   *   - `'none'`: suppress entirely — the mount fully OWNS the artifact view,
   *     so an inline render would be a duplicate (Studio: the canvas IS the
   *     artifact view; the transcript stays pure conversation).
   *  The card-vs-suppress decision is a MOUNT concern (declared here), never a
   *  branch inside the renderer (ADR-441 D2). */
  artifactWrite?: 'card' | 'link' | 'none';
}

interface LanePanelProps extends LaneMountSlots {
  laneId: string;
  laneName: string;
  modelLabel: string;
  /** Phase-A hygiene: the turn auto-named a default-named lane (server truth
   *  rides the done frame) — the mount updates its list/header. */
  onLaneRenamed?: (name: string) => void;
  /** Phase-A attachments: may this lane's model receive images? (LANE_MODELS
   *  vision flag — the server guards regardless; this gates the affordance.) */
  visionCapable?: boolean;
}

export function LanePanel({
  laneId,
  laneName,
  modelLabel,
  onArtifactWrite,
  emptyState,
  suggestions,
  composerSeed,
  artifactWrite = 'card',
  onLaneRenamed,
  visionCapable = true,
}: LanePanelProps) {
  const [messages, setMessages] = useState<LaneMessage[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // Phase-A turn controls: the in-flight stream's abort handle (stop), the
  // user message being edited (edit-and-resend), copy feedback.
  const abortRef = useRef<AbortController | null>(null);
  const [editing, setEditing] = useState<{ id: string; original: string } | null>(null);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  // Phase-A attachments: composer chips (upload → send as turn refs).
  const [attachments, setAttachments] = useState<PendingAttachment[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  // The composer grows with what you're writing, then holds and scrolls — the
  // CLI gesture. `rows={1}` alone pins it at one line forever (a CSS max-h is
  // only a ceiling; nothing pushes the box up to it), so the height is written
  // from scrollHeight. Shared with the shell drawer's composer — one rule.
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  useAutoResize(textareaRef, input);

  /** Upload files into the raw lane (ADR-395) and track them as chips. */
  const addFiles = useCallback(
    (files: File[]) => {
      for (const file of files) {
        const kind: 'image' | 'file' = file.type.startsWith('image/') ? 'image' : 'file';
        if (kind === 'image' && !visionCapable) {
          setError(`${modelLabel} cannot see images — attach documents instead.`);
          continue;
        }
        const key = `att-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
        setAttachments((prev) => [
          ...prev,
          { key, name: file.name, kind, uploading: true },
        ]);
        api.documents
          .upload(file)
          .then((res) => {
            const item = res.results?.[0];
            setAttachments((prev) =>
              prev.map((a) =>
                a.key === key
                  ? item?.success && item.workspace_path
                    ? { ...a, uploading: false, path: item.workspace_path }
                    : { ...a, uploading: false, error: true }
                  : a,
              ),
            );
          })
          .catch(() =>
            setAttachments((prev) =>
              prev.map((a) => (a.key === key ? { ...a, uploading: false, error: true } : a)),
            ),
          );
      }
    },
    [modelLabel, visionCapable],
  );

  const mapMessages = (
    rows: Array<{
      id: string;
      role: 'user' | 'assistant';
      content: string;
      created_at: string;
      metadata: Record<string, unknown>;
    }>,
  ): LaneMessage[] =>
    rows.map((m) => ({
      id: m.id,
      role: m.role,
      content: m.content,
      created_at: m.created_at,
      tools_called: (m.metadata?.tools_called as string[]) ?? undefined,
      artifacts: toArtifacts(m.metadata?.artifacts),
      attachments:
        (m.metadata?.attachments as LaneMessage['attachments']) ?? undefined,
    }));

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setMessages([]);
    setError(null);
    api.lanes
      .messages(laneId)
      .then((res) => {
        if (cancelled) return;
        setMessages(mapMessages(res.messages));
      })
      .catch(() => !cancelled && setError('Could not load this lane.'))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [laneId]);

  /** Silent transcript resync — swaps optimistic local ids for DB ids (edit/
   *  regenerate need them) and picks up a server-persisted partial after a
   *  stop. The mount stays put (`key={laneId}` remounts on lane switch). */
  const resyncMessages = useCallback(async () => {
    try {
      const res = await api.lanes.messages(laneId);
      setMessages(mapMessages(res.messages));
    } catch {
      /* non-fatal — the optimistic view stands */
    }
  }, [laneId]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, sending]);

  // ADR-440 v1.1 — composer seeding (pointing + insert menu). Appends when
  // the member already typed something; replaces when the composer is empty.
  useEffect(() => {
    if (!composerSeed?.text) return;
    setInput((cur) => (cur.trim() ? `${cur.replace(/\s*$/, ' ')}${composerSeed.text}` : composerSeed.text));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [composerSeed?.nonce]);

  /** The one streaming-turn runner — send, edit-and-resend, and regenerate
   *  share it (Phase-A turn controls). Optimistic transcript surgery up
   *  front, the shared handler set during, a silent resync after. */
  const runStream = useCallback(
    async (
      kind: 'send' | 'regenerate',
      opts: {
        content?: string;
        replaceFromMessageId?: string;
        attachments?: Array<{ path: string; kind: 'image' | 'file'; name?: string }>;
      } = {},
    ) => {
      if (sending) return;
      setError(null);
      setSending(true);
      const controller = new AbortController();
      abortRef.current = controller;

      const replyId = `local-r-${Date.now()}`;
      if (kind === 'send') {
        const userId = `local-${Date.now()}`;
        // Optimistic: (on edit) truncate from the edited row, then the user
        // row + an empty assistant row the stream fills in place.
        setMessages((prev) => {
          let base = prev;
          if (opts.replaceFromMessageId) {
            const idx = base.findIndex((m) => m.id === opts.replaceFromMessageId);
            if (idx >= 0) base = base.slice(0, idx);
          }
          return [
            ...base,
            {
              id: userId,
              role: 'user',
              content: opts.content ?? '',
              attachments: opts.attachments,
            },
            { id: replyId, role: 'assistant', content: '' },
          ];
        });
      } else {
        // Regenerate: drop the tail after the last user row, add the placeholder.
        setMessages((prev) => {
          let lastUser = -1;
          for (let i = prev.length - 1; i >= 0; i--) {
            if (prev[i].role === 'user') {
              lastUser = i;
              break;
            }
          }
          if (lastUser < 0) return prev;
          return [...prev.slice(0, lastUser + 1), { id: replyId, role: 'assistant', content: '' }];
        });
      }

      const appendDelta = (text: string) =>
        setMessages((prev) =>
          prev.map((m) => (m.id === replyId ? { ...m, content: m.content + text } : m)),
        );

      let sawDelta = false;
      const dropEmptyPlaceholder = () =>
        setMessages((prev) =>
          prev.filter((m) => !(m.id === replyId && !m.content && !m.artifacts?.length)),
        );
      const handlers = {
        onDelta: (text: string) => {
          sawDelta = true;
          appendDelta(text);
        },
        onTool: (name: string) =>
          setMessages((prev) =>
            prev.map((m) =>
              m.id === replyId
                ? { ...m, tools_called: [...(m.tools_called ?? []), name] }
                : m,
            ),
          ),
        // A write landed. Show the file as soon as it exists — mid-turn, before
        // the model has finished narrating it.
        onArtifact: ({ path, verb }: { path: string; verb: string }) => {
          onArtifactWrite?.(path);
          setMessages((prev) =>
            prev.map((m) => {
              if (m.id !== replyId) return m;
              const existing = m.artifacts ?? [];
              if (existing.some((a) => a.path === path)) return m;
              return { ...m, artifacts: [...existing, { path, verb }] };
            }),
          );
        },
        onDone: ({
          tools_called,
          artifacts,
          lane_name,
        }: {
          rounds: number;
          tools_called: string[];
          artifacts: string[];
          lane_name?: string;
        }) => {
          // Phase-A hygiene: the server auto-named this lane on first turn.
          if (lane_name) onLaneRenamed?.(lane_name);
          if (tools_called?.length) {
            setMessages((prev) =>
              prev.map((m) => (m.id === replyId ? { ...m, tools_called } : m)),
            );
          }
          // The terminal list is authoritative (it survives a dropped frame).
          // Union by path, keeping the streamed entries first — they carry the
          // verb, which the terminal list does not.
          const finalArtifacts = toArtifacts(artifacts);
          finalArtifacts?.forEach((a) => onArtifactWrite?.(a.path));
          if (finalArtifacts) {
            setMessages((prev) =>
              prev.map((m) => {
                if (m.id !== replyId) return m;
                const seen = m.artifacts ?? [];
                const merged = [
                  ...seen,
                  ...finalArtifacts.filter((a) => !seen.some((s) => s.path === a.path)),
                ];
                return { ...m, artifacts: merged };
              }),
            );
          }
          // A turn that streamed no text shows a marker — UNLESS it produced an
          // artifact, in which case the card is the reply and a "[no reply]"
          // bubble above it would be a lie.
          if (!sawDelta && !finalArtifacts) {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === replyId && !m.content ? { ...m, content: '[no reply]' } : m,
              ),
            );
          }
        },
        onError: (message: string) => {
          setError(message || 'The lane turn failed — try again.');
          // Papercut fix: preserve the user's text so it isn't lost.
          if (kind === 'send' && opts.content) setInput((cur) => cur || opts.content!);
          dropEmptyPlaceholder();
        },
      };

      try {
        if (kind === 'send') {
          await api.lanes.sendStream(laneId, opts.content ?? '', handlers, {
            signal: controller.signal,
            replaceFromMessageId: opts.replaceFromMessageId,
            attachments: opts.attachments,
          });
        } else {
          await api.lanes.regenerateStream(laneId, handlers, {
            signal: controller.signal,
          });
        }
      } catch {
        setError('The lane turn failed — try again.');
        if (kind === 'send' && opts.content) setInput((cur) => cur || opts.content!);
        dropEmptyPlaceholder();
      } finally {
        const stopped = controller.signal.aborted;
        abortRef.current = null;
        setSending(false);
        if (stopped) {
          // Stopped: drop a text-less placeholder, then resync once the server
          // has persisted the partial (it does so on disconnect — give it a beat).
          dropEmptyPlaceholder();
          setTimeout(() => void resyncMessages(), 600);
        } else {
          void resyncMessages();
        }
      }
    },
    [laneId, sending, onArtifactWrite, onLaneRenamed, resyncMessages],
  );

  const send = useCallback(async () => {
    const content = input.trim();
    if (!content || sending) return;
    // Attachments still uploading hold the send (a ref without a path would
    // silently drop); failed ones are skipped.
    if (attachments.some((a) => a.uploading)) return;
    const ready = attachments
      .filter((a) => a.path && !a.error)
      .map((a) => ({ path: a.path!, kind: a.kind, name: a.name }));
    setInput('');
    setAttachments([]);
    const replaceFromMessageId = editing?.id;
    setEditing(null);
    await runStream('send', {
      content,
      replaceFromMessageId,
      attachments: ready.length ? ready : undefined,
    });
  }, [input, sending, editing, attachments, runStream]);

  /** Phase-A turn controls: stop — abort the stream; the server persists the
   *  partial reply (any writes that landed stand — the no-rewind rule). */
  const stop = useCallback(() => {
    abortRef.current?.abort();
  }, []);

  const startEdit = useCallback((m: LaneMessage) => {
    setEditing({ id: m.id, original: m.content });
    setInput(m.content);
  }, []);

  const cancelEdit = useCallback(() => {
    setEditing(null);
    setInput('');
  }, []);

  const copyMessage = useCallback((m: LaneMessage) => {
    void navigator.clipboard?.writeText(m.content).then(() => {
      setCopiedId(m.id);
      setTimeout(() => setCopiedId((cur) => (cur === m.id ? null : cur)), 1500);
    });
  }, []);

  return (
    <div className="flex-1 min-h-0 flex flex-col">
      <div className="flex-1 min-h-0 overflow-y-auto px-3 py-3 space-y-3">
        {loading && (
          <div className="text-xs text-muted-foreground py-6 text-center">
            Loading {laneName}…
          </div>
        )}
        {!loading && messages.length === 0 && (
          <div className="py-6 px-4 space-y-3">
            {emptyState ?? (
              <div className="text-xs text-muted-foreground text-center space-y-1">
                <p className="font-medium text-foreground/80">{laneName} · {modelLabel}</p>
                <p>
                  This conversation is private to this lane. The work it produces
                  lands in the shared workspace files, attributed to you via{' '}
                  {modelLabel}.
                </p>
              </div>
            )}
            {suggestions && suggestions.length > 0 && (
              <div className="flex flex-col items-stretch gap-1.5">
                {suggestions.map((s) => (
                  <button
                    key={s}
                    type="button"
                    onClick={() => setInput(s)}
                    className="rounded-lg border border-border px-3 py-2 text-left text-xs text-muted-foreground transition-colors hover:bg-muted/40 hover:text-foreground"
                  >
                    {s}
                  </button>
                ))}
              </div>
            )}
          </div>
        )}
        {messages.map((m, i) => {
          // Session legibility: a day-separator when the calendar day changes
          // (ADR-412 D2). Reloaded lanes read across sessions, not as one blob.
          const prevDay = i > 0 ? dayKey(messages[i - 1].created_at) : '';
          const thisDay = dayKey(m.created_at);
          const showDay = thisDay !== '' && thisDay !== prevDay;
          const isLast = i === messages.length - 1;
          return (
            <div key={m.id} className="group">
              {showDay && (
                <div className="flex items-center gap-2 my-3">
                  <div className="flex-1 h-px bg-border" />
                  <span className="text-[10px] text-muted-foreground/70 uppercase tracking-wide">
                    {formatTimestamp(m.created_at)}
                  </span>
                  <div className="flex-1 h-px bg-border" />
                </div>
              )}
              {/* The bubble is speech. An artifact is not speech — it renders
                  below, at row width, outside the bubble (ADR-236: render +
                  open, never edit). A tool-only turn shows only the card. */}
              {(m.content || m.role === 'user' || !m.artifacts?.length) && (
                <div className={cn('flex', m.role === 'user' ? 'justify-end' : 'justify-start')}>
                  <div
                    className={cn(
                      'max-w-[85%] rounded-lg px-3 py-2 text-sm break-words',
                      m.role === 'user'
                        ? 'bg-primary text-primary-foreground whitespace-pre-wrap'
                        : 'bg-muted text-foreground',
                    )}
                  >
                    {/* Streaming: an empty assistant bubble shows a live indicator
                        until the first delta lands, then fills token-by-token. */}
                    {m.role === 'assistant' && !m.content ? (
                      <span className="flex items-center gap-2 text-muted-foreground">
                        <Loader2 className="w-3.5 h-3.5 animate-spin" />
                        {(m.tools_called && m.tools_called.length > 0)
                          ? `${modelLabel} · ${Array.from(new Set(m.tools_called)).join(' · ')}…`
                          : `${modelLabel} is working…`}
                      </span>
                    ) : m.role === 'assistant' ? (
                      // 2026-07-09: the lane's reply is markdown, like every
                      // other model reply in the product. It rendered as raw
                      // text for no reason other than that LanePanel was a
                      // reimplementation.
                      <div className="prose prose-sm max-w-none dark:prose-invert prose-p:my-1.5 prose-pre:my-2">
                        <MarkdownRenderer content={m.content} />
                      </div>
                    ) : (
                      m.content
                    )}
                    {/* Phase-A attachments: what this user turn carried. */}
                    {m.role === 'user' && m.attachments && m.attachments.length > 0 && (
                      <div className="mt-1.5 pt-1.5 border-t border-primary-foreground/20 flex flex-wrap gap-1">
                        {m.attachments.map((a) => (
                          <span
                            key={a.path}
                            className="inline-flex items-center gap-1 rounded bg-primary-foreground/15 px-1.5 py-0.5 text-[10px]"
                          >
                            {a.kind === 'image' ? (
                              <ImageIcon className="w-3 h-3" />
                            ) : (
                              <FileText className="w-3 h-3" />
                            )}
                            <span className="truncate max-w-[140px]">
                              {a.name || a.path.split('/').pop()}
                            </span>
                          </span>
                        ))}
                      </div>
                    )}
                    {m.content && m.tools_called && m.tools_called.length > 0 && (
                      <div className="mt-1.5 pt-1.5 border-t border-border/40 flex items-center gap-1 text-[10px] text-muted-foreground">
                        <Wrench className="w-3 h-3" />
                        {Array.from(new Set(m.tools_called)).join(' · ')}
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Phase-A turn controls: hover actions under the bubble — copy
                  everywhere; edit-and-resend on persisted user rows; regenerate
                  on the trailing assistant row. Hidden mid-stream. */}
              {!sending && m.content && (
                <div
                  className={cn(
                    'flex gap-0.5 mt-0.5 opacity-0 group-hover:opacity-100 transition-opacity',
                    m.role === 'user' ? 'justify-end' : 'justify-start',
                  )}
                >
                  <button
                    type="button"
                    onClick={() => copyMessage(m)}
                    className="p-1 rounded text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
                    aria-label="Copy message"
                    title="Copy"
                  >
                    {copiedId === m.id ? (
                      <Check className="w-3 h-3" />
                    ) : (
                      <Copy className="w-3 h-3" />
                    )}
                  </button>
                  {m.role === 'user' && !m.id.startsWith('local-') && (
                    <button
                      type="button"
                      onClick={() => startEdit(m)}
                      className="p-1 rounded text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
                      aria-label="Edit and resend"
                      title="Edit & resend"
                    >
                      <Pencil className="w-3 h-3" />
                    </button>
                  )}
                  {m.role === 'assistant' && isLast && (
                    <button
                      type="button"
                      onClick={() => void runStream('regenerate')}
                      className="p-1 rounded text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
                      aria-label="Regenerate reply"
                      title="Regenerate"
                    >
                      <RefreshCw className="w-3 h-3" />
                    </button>
                  )}
                </div>
              )}

              {/* ADR-443: how artifact writes render is a MOUNT concern the
                  mount declares via the `artifactWrite` slot. 'card' (default,
                  /chat) = full preview; 'link' = a compact citation line; 'none'
                  (Studio) = suppressed, because the mount already owns the view
                  (the canvas), so a transcript render would duplicate it. */}
              {m.role === 'assistant' && m.artifacts?.length && artifactWrite !== 'none' ? (
                <div className="mt-2 space-y-2">
                  {m.artifacts.map((a) =>
                    artifactWrite === 'link' ? (
                      <div
                        key={a.path}
                        className="flex items-center gap-1.5 text-xs text-muted-foreground"
                      >
                        <FileText className="h-3.5 w-3.5 shrink-0" />
                        <span className="text-foreground/80">{a.verb}</span>
                        <span className="truncate font-medium">{a.path.split('/').pop() || a.path}</span>
                      </div>
                    ) : (
                      <ArtifactCard
                        key={a.path}
                        path={a.path}
                        verb={a.verb}
                        attribution={`you via ${modelLabel}`}
                      />
                    ),
                  )}
                </div>
              ) : null}
            </div>
          );
        })}
        {error && (
          <div className="text-xs text-destructive text-center">{error}</div>
        )}
        <div ref={bottomRef} />
      </div>

      <div className="border-t border-border p-2 shrink-0">
        {/* Phase-A edit-and-resend: the banner names the mode; Esc cancels.
            Sending replaces the tail from the edited message (transcript
            only — the ledger keeps what already landed). */}
        {editing && (
          <div className="flex items-center justify-between px-2 pb-1.5 text-[11px] text-muted-foreground">
            <span className="flex items-center gap-1">
              <Pencil className="w-3 h-3" />
              Editing — sending replaces this message and everything after it
            </span>
            <button
              type="button"
              onClick={cancelEdit}
              className="px-1.5 py-0.5 rounded hover:bg-muted hover:text-foreground transition-colors"
            >
              Cancel
            </button>
          </div>
        )}
        {/* Phase-A attachments: composer chips (uploading → ready | failed). */}
        {attachments.length > 0 && (
          <div className="flex flex-wrap gap-1 px-1 pb-1.5">
            {attachments.map((a) => (
              <span
                key={a.key}
                className={cn(
                  'inline-flex items-center gap-1 rounded border px-1.5 py-0.5 text-[11px]',
                  a.error
                    ? 'border-destructive/50 text-destructive'
                    : 'border-border text-muted-foreground',
                )}
              >
                {a.uploading ? (
                  <Loader2 className="w-3 h-3 animate-spin" />
                ) : a.kind === 'image' ? (
                  <ImageIcon className="w-3 h-3" />
                ) : (
                  <FileText className="w-3 h-3" />
                )}
                <span className="truncate max-w-[140px]">{a.name}</span>
                {a.error && <span>failed</span>}
                <button
                  type="button"
                  onClick={() =>
                    setAttachments((prev) => prev.filter((p) => p.key !== a.key))
                  }
                  className="p-0.5 rounded hover:text-foreground"
                  aria-label={`Remove ${a.name}`}
                >
                  <X className="w-3 h-3" />
                </button>
              </span>
            ))}
          </div>
        )}
        <div className="flex items-end gap-2">
          <input
            ref={fileInputRef}
            type="file"
            multiple
            accept={
              visionCapable
                ? 'image/png,image/jpeg,image/webp,image/gif,.pdf,.docx,.txt,.md'
                : '.pdf,.docx,.txt,.md'
            }
            className="hidden"
            onChange={(e) => {
              const files = Array.from(e.target.files ?? []);
              if (files.length) addFiles(files);
              e.target.value = '';
            }}
          />
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            disabled={sending}
            className="p-2 rounded-md text-muted-foreground hover:text-foreground hover:bg-muted disabled:opacity-40 shrink-0 transition-colors"
            aria-label="Attach a file"
            title="Attach"
          >
            <Paperclip className="w-4 h-4" />
          </button>
          <textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                void send();
              }
              if (e.key === 'Escape' && editing) {
                e.preventDefault();
                cancelEdit();
              }
            }}
            onPaste={(e) => {
              // Pasted images (screenshots) become attachments.
              const files = Array.from(e.clipboardData?.files ?? []).filter((f) =>
                f.type.startsWith('image/'),
              );
              if (files.length) {
                e.preventDefault();
                addFiles(files);
              }
            }}
            placeholder={editing ? 'Edit your message…' : `Message ${laneName}…`}
            rows={1}
            style={{ maxHeight: COMPOSER_MAX_PX }}
            className="flex-1 resize-none overflow-y-auto rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-ring min-h-[38px]"
          />
          {sending ? (
            <button
              onClick={stop}
              className="p-2 rounded-md border border-border text-foreground hover:bg-muted shrink-0 transition-colors"
              aria-label="Stop generating"
              title="Stop"
            >
              <Square className="w-4 h-4" />
            </button>
          ) : (
            <button
              onClick={() => void send()}
              disabled={!input.trim() || attachments.some((a) => a.uploading)}
              className="p-2 rounded-md bg-primary text-primary-foreground disabled:opacity-40 shrink-0"
              aria-label="Send"
            >
              <ArrowUp className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
