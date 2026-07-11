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
import { ArrowUp, Loader2, Wrench } from 'lucide-react';
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
}

interface LanePanelProps extends LaneMountSlots {
  laneId: string;
  laneName: string;
  modelLabel: string;
}

export function LanePanel({
  laneId,
  laneName,
  modelLabel,
  onArtifactWrite,
  emptyState,
  suggestions,
  composerSeed,
}: LanePanelProps) {
  const [messages, setMessages] = useState<LaneMessage[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setMessages([]);
    setError(null);
    api.lanes
      .messages(laneId)
      .then((res) => {
        if (cancelled) return;
        setMessages(
          res.messages.map((m) => ({
            id: m.id,
            role: m.role,
            content: m.content,
            created_at: m.created_at,
            tools_called: (m.metadata?.tools_called as string[]) ?? undefined,
            artifacts: toArtifacts(m.metadata?.artifacts),
          })),
        );
      })
      .catch(() => !cancelled && setError('Could not load this lane.'))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
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

  const send = useCallback(async () => {
    const content = input.trim();
    if (!content || sending) return;
    setInput('');
    setError(null);
    setSending(true);

    const userId = `local-${Date.now()}`;
    const replyId = `local-r-${Date.now()}`;
    // Optimistic user row + an empty assistant row the stream fills in place.
    setMessages((prev) => [
      ...prev,
      { id: userId, role: 'user', content },
      { id: replyId, role: 'assistant', content: '' },
    ]);

    const appendDelta = (text: string) =>
      setMessages((prev) =>
        prev.map((m) => (m.id === replyId ? { ...m, content: m.content + text } : m)),
      );

    let sawDelta = false;
    try {
      await api.lanes.sendStream(laneId, content, {
        onDelta: (text) => {
          sawDelta = true;
          appendDelta(text);
        },
        onTool: (name) =>
          setMessages((prev) =>
            prev.map((m) =>
              m.id === replyId
                ? { ...m, tools_called: [...(m.tools_called ?? []), name] }
                : m,
            ),
          ),
        // A write landed. Show the file as soon as it exists — mid-turn, before
        // the model has finished narrating it.
        onArtifact: ({ path, verb }) => {
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
        onDone: ({ tools_called, artifacts }) => {
          if (tools_called?.length) {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === replyId ? { ...m, tools_called } : m,
              ),
            );
          }
          // The terminal list is authoritative (it survives a dropped frame).
          // Union by path, keeping the streamed entries first — they carry the
          // verb, which the terminal list does not.
          const finalArtifacts = toArtifacts(artifacts);
          // The terminal list survives dropped frames — notify the mount for
          // any write the mid-turn stream may have missed (idempotent hook).
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
                m.id === replyId && !m.content
                  ? { ...m, content: '[no reply]' }
                  : m,
              ),
            );
          }
        },
        onError: (message) => {
          setError(message || 'The lane turn failed — try again.');
          // Papercut fix: preserve the user's text so it isn't lost.
          setInput((cur) => cur || content);
          // Drop the empty assistant placeholder on a hard error.
          setMessages((prev) =>
            prev.filter((m) => !(m.id === replyId && !m.content && !m.artifacts?.length)),
          );
        },
      });
    } catch {
      setError('The lane turn failed — try again.');
      setInput((cur) => cur || content);
      setMessages((prev) =>
        prev.filter((m) => !(m.id === replyId && !m.content && !m.artifacts?.length)),
      );
    } finally {
      setSending(false);
    }
  }, [input, laneId, sending, onArtifactWrite]);

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
          return (
            <div key={m.id}>
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
                    {m.content && m.tools_called && m.tools_called.length > 0 && (
                      <div className="mt-1.5 pt-1.5 border-t border-border/40 flex items-center gap-1 text-[10px] text-muted-foreground">
                        <Wrench className="w-3 h-3" />
                        {Array.from(new Set(m.tools_called)).join(' · ')}
                      </div>
                    )}
                  </div>
                </div>
              )}

              {m.role === 'assistant' && m.artifacts?.length ? (
                <div className="mt-2 space-y-2">
                  {m.artifacts.map((a) => (
                    <ArtifactCard
                      key={a.path}
                      path={a.path}
                      verb={a.verb}
                      attribution={`you via ${modelLabel}`}
                    />
                  ))}
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
        <div className="flex items-end gap-2">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                void send();
              }
            }}
            placeholder={`Message ${laneName}…`}
            rows={1}
            className="flex-1 resize-none rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-ring min-h-[38px] max-h-32"
          />
          <button
            onClick={() => void send()}
            disabled={!input.trim() || sending}
            className="p-2 rounded-md bg-primary text-primary-foreground disabled:opacity-40 shrink-0"
            aria-label="Send"
          >
            <ArrowUp className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
}
