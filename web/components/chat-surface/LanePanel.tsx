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
 * The contract rendered here: the transcript is private to the lane; the
 * work lands in files. When a turn used tools, the reply footer names them
 * so the member sees the lane touched the commons.
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import { ArrowUp, Loader2, Wrench } from 'lucide-react';
import { api } from '@/lib/api/client';
import { cn } from '@/lib/utils';

interface LaneMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  created_at?: string;
  tools_called?: string[];
}

interface LanePanelProps {
  laneId: string;
  laneName: string;
  modelLabel: string;
}

export function LanePanel({ laneId, laneName, modelLabel }: LanePanelProps) {
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
        onDone: ({ tools_called }) => {
          if (tools_called?.length) {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === replyId ? { ...m, tools_called } : m,
              ),
            );
          }
          // A turn that streamed no text (e.g. tool-only) shows a marker.
          if (!sawDelta) {
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
            prev.filter((m) => !(m.id === replyId && !m.content)),
          );
        },
      });
    } catch {
      setError('The lane turn failed — try again.');
      setInput((cur) => cur || content);
      setMessages((prev) => prev.filter((m) => !(m.id === replyId && !m.content)));
    } finally {
      setSending(false);
    }
  }, [input, laneId, sending]);

  return (
    <div className="flex-1 min-h-0 flex flex-col">
      <div className="flex-1 min-h-0 overflow-y-auto px-3 py-3 space-y-3">
        {loading && (
          <div className="text-xs text-muted-foreground py-6 text-center">
            Loading {laneName}…
          </div>
        )}
        {!loading && messages.length === 0 && (
          <div className="text-xs text-muted-foreground py-6 px-4 text-center space-y-1">
            <p className="font-medium text-foreground/80">{laneName} · {modelLabel}</p>
            <p>
              This conversation is private to this lane. The work it produces
              lands in the shared workspace files, attributed to you via{' '}
              {modelLabel}.
            </p>
          </div>
        )}
        {messages.map((m) => (
          <div
            key={m.id}
            className={cn('flex', m.role === 'user' ? 'justify-end' : 'justify-start')}
          >
            <div
              className={cn(
                'max-w-[85%] rounded-lg px-3 py-2 text-sm whitespace-pre-wrap break-words',
                m.role === 'user'
                  ? 'bg-primary text-primary-foreground'
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
        ))}
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
