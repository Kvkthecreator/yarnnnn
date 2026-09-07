'use client';

/**
 * SendToSlack — the Text app's boundary act (ADR-628 amendment 3).
 *
 * A header verb beside Share/Export, mounted ONLY on the Text pane (the
 * StudioPublish precedent: an app-scoped affordance is an optional mount,
 * not a fork). The member stands on a prose file and carries it across:
 *
 *   - the CHANNEL is chosen here, at the act — never stored on the
 *     connection (ADR-594 D1);
 *   - the click IS the consent (ADR-628 D2); nothing here ever sends on a
 *     schedule, and the open chat carries no send verb (D5);
 *   - the three connect states render distinctly: not connected → the
 *     Connectors door; connected with no channels; the picker (a private
 *     channel the app is not in says so — it needs the invite first);
 *   - the receipt renders after the act WITH the read-back verdict (D8):
 *     matched · differs · unreadable — never a silent "sent".
 *
 * The durable receipt is the `_publish.yaml` sidecar the server writes
 * beside the file; Reach → Crossed shows it with the rest of the boundary.
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import { Hash } from 'lucide-react';
import { api } from '@/lib/api/client';
import { useSurfacePreferences } from '@/lib/shell/useSurfacePreferences';

interface SendToSlackProps {
  /** Workspace path of the prose file (any spelling — server normalizes). */
  artifactPath: string;
  compact?: boolean;
  coarsePointer?: boolean;
}

type Channel = { id: string; name: string; is_private: boolean; is_member: boolean };

type ChannelsState =
  | { kind: 'loading' }
  | { kind: 'unconnected' }
  | { kind: 'empty' }
  | { kind: 'ready'; channels: Channel[] }
  | { kind: 'error' };

type ActState =
  | { kind: 'idle' }
  | { kind: 'working' }
  | {
      kind: 'done';
      channel: string;
      url?: string | null;
      readBack: 'matched' | 'differs' | 'unreadable';
      readBackDetail?: string;
      folded: boolean;
    }
  | { kind: 'error'; message: string };

export function SendToSlack({ artifactPath, compact = false, coarsePointer = false }: SendToSlackProps) {
  const [open, setOpen] = useState(false);
  const [channels, setChannels] = useState<ChannelsState>({ kind: 'loading' });
  const [channelId, setChannelId] = useState<string>('');
  const [act, setAct] = useState<ActState>({ kind: 'idle' });
  const menuRef = useRef<HTMLDivElement>(null);
  const { navigateToSurface } = useSurfacePreferences();

  // The ShareExport click-away grammar (outclick + Escape + in-frame press).
  useEffect(() => {
    if (!open) return;
    const close = () => setOpen(false);
    const onDown = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) close();
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') close();
    };
    const onFrame = (e: MessageEvent) => {
      if ((e.data as { type?: string } | null)?.type === 'yarnnn-canvas-press') close();
    };
    document.addEventListener('mousedown', onDown);
    document.addEventListener('keydown', onKey);
    window.addEventListener('message', onFrame);
    return () => {
      document.removeEventListener('mousedown', onDown);
      document.removeEventListener('keydown', onKey);
      window.removeEventListener('message', onFrame);
    };
  }, [open]);

  const loadChannels = useCallback(async () => {
    setChannels({ kind: 'loading' });
    try {
      const res = await api.publish.slackChannels();
      if (!res.connected) setChannels({ kind: 'unconnected' });
      else if (!res.channels.length) setChannels({ kind: 'empty' });
      else {
        const sorted = [...res.channels].sort((a, b) => a.name.localeCompare(b.name));
        setChannels({ kind: 'ready', channels: sorted });
        setChannelId((prev) => prev || (sorted.find((c) => c.is_member) ?? sorted[0]).id);
      }
    } catch {
      setChannels({ kind: 'error' });
    }
  }, []);

  const openPanel = useCallback(() => {
    setOpen((o) => {
      const next = !o;
      if (next) {
        setAct({ kind: 'idle' });
        void loadChannels();
      }
      return next;
    });
  }, [loadChannels]);

  const run = useCallback(async () => {
    if (!channelId) return;
    setAct({ kind: 'working' });
    try {
      const res = await api.publish.slack({ path: artifactPath, channel_id: channelId });
      setAct({
        kind: 'done',
        channel: res.channel,
        url: res.url,
        readBack: res.read_back,
        readBackDetail: res.read_back_detail,
        folded: res.folded,
      });
    } catch (e) {
      setAct({
        kind: 'error',
        message: e instanceof Error ? e.message : 'Send failed — try again.',
      });
    }
  }, [artifactPath, channelId]);

  const selected =
    channels.kind === 'ready' ? channels.channels.find((c) => c.id === channelId) : undefined;
  const needsInvite = !!selected && selected.is_private && !selected.is_member;

  const btn =
    'inline-flex shrink-0 items-center justify-center gap-1 whitespace-nowrap rounded-md border border-border text-[11px] text-muted-foreground transition-colors hover:bg-muted/40 hover:text-foreground ' +
    (coarsePointer ? 'min-h-[44px] ' : '') +
    (compact ? (coarsePointer ? 'w-11 px-0' : 'h-7 w-8 px-0') : 'px-2 py-1');
  const actBtn =
    'inline-flex items-center gap-1 rounded-md border border-border px-2 py-1 text-[10px] text-muted-foreground transition-colors hover:bg-muted/40 hover:text-foreground disabled:opacity-50';
  const panel =
    'absolute right-0 top-full z-30 mt-1 w-80 rounded-md border border-border bg-background p-2 shadow-md';

  return (
    <div ref={menuRef} className="relative flex shrink-0 items-center gap-1">
      <button
        type="button"
        className={btn}
        onClick={openPanel}
        title="Send this file to a Slack channel — your click, your account"
        aria-label={compact ? 'Send to Slack…' : undefined}
      >
        <Hash className="h-3 w-3" />
        {!compact && ' Send to Slack…'}
      </button>

      {open && (
        <div className={panel}>
          <p className="px-1 pb-1 pt-0.5 text-[10px] font-medium uppercase tracking-wide text-muted-foreground">
            Send to Slack
          </p>
          <div className="space-y-2 px-1 pb-1">
            {channels.kind === 'loading' && (
              <p className="text-[11px] text-muted-foreground">Checking your connection…</p>
            )}

            {channels.kind === 'unconnected' && (
              <div className="space-y-1.5">
                <p className="text-[11px] leading-snug text-muted-foreground">
                  Connect Slack once, and any prose file can go to a channel —
                  your account, your name, your click.
                </p>
                {/* ADR-297 D19 — cross-surface navigation rides the window
                    manager, never a raw href (the nav gate). */}
                <button
                  type="button"
                  onClick={() => navigateToSurface('connectors')}
                  className="inline-flex items-center rounded-md border border-border px-2 py-1 text-[10px] text-muted-foreground hover:bg-muted/40 hover:text-foreground"
                >
                  Connect Slack →
                </button>
              </div>
            )}

            {channels.kind === 'empty' && (
              <p className="text-[11px] leading-snug text-muted-foreground">
                Your Slack connection sees no channels yet. Create one in Slack, or
                invite the yarnnn app to an existing one, and try again.
              </p>
            )}

            {channels.kind === 'error' && (
              <p className="text-[11px] text-muted-foreground">
                Slack did not answer.{' '}
                <button type="button" className="underline" onClick={() => void loadChannels()}>
                  Retry
                </button>
              </p>
            )}

            {channels.kind === 'ready' && act.kind !== 'done' && (
              <>
                <label className="block text-[10px] text-muted-foreground">
                  Channel
                  <select
                    value={channelId}
                    onChange={(e) => setChannelId(e.target.value)}
                    className="mt-0.5 w-full rounded-md border border-border bg-background px-1.5 py-1 text-[11px]"
                  >
                    {channels.channels.map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.is_private ? '🔒 ' : '#'}
                        {c.name}
                        {c.is_private && !c.is_member ? ' — invite the app first' : ''}
                      </option>
                    ))}
                  </select>
                </label>
                {needsInvite && (
                  <p className="text-[10px] leading-snug text-amber-600">
                    The yarnnn app isn’t in this private channel yet. Run{' '}
                    <code className="rounded bg-muted px-1">/invite @yarnnn</code> there, then send.
                  </p>
                )}
                <div className="flex flex-wrap gap-1">
                  <button
                    type="button"
                    className={actBtn}
                    disabled={act.kind === 'working' || !channelId || needsInvite}
                    onClick={() => void run()}
                    title="Send now — the file's text is posted to the channel as one message"
                  >
                    {act.kind === 'working' ? 'Sending…' : `Send to ${selected?.name ? `#${selected.name}` : 'channel'}`}
                  </button>
                </div>
                {act.kind === 'error' && (
                  <p className="text-[10px] leading-snug text-red-500">{act.message}</p>
                )}
                <p className="text-[10px] leading-snug text-muted-foreground">
                  Sent under your own account, then read back to check it landed as
                  written. The receipt lands beside the file; nothing here ever sends
                  on a schedule.
                </p>
              </>
            )}

            {act.kind === 'done' && (
              <div className="space-y-1">
                <p className="text-[11px] text-foreground">Sent to {act.channel} ✓</p>
                {act.url && (
                  <a
                    href={act.url}
                    target="_blank"
                    rel="noreferrer"
                    className="block truncate text-[10px] text-muted-foreground underline hover:text-foreground"
                  >
                    Open in Slack
                  </a>
                )}
                {/* ADR-628 D8 — the read-back verdict. Never a silent "sent". */}
                {act.readBack === 'matched' && (
                  <p className="text-[10px] leading-snug text-muted-foreground">
                    Read back from Slack: it matches what was sent.
                  </p>
                )}
                {act.readBack === 'differs' && (
                  <p className="text-[10px] leading-snug text-amber-600">
                    Read back from Slack: stored differently than sent
                    {act.readBackDetail ? ` (${act.readBackDetail})` : ''}. Open it and check.
                  </p>
                )}
                {act.readBack === 'unreadable' && (
                  <p className="text-[10px] leading-snug text-amber-600">
                    Could not read it back from Slack{act.readBackDetail ? ` — ${act.readBackDetail}` : ''}. Open it and check.
                  </p>
                )}
                {act.folded && (
                  <p className="text-[10px] leading-snug text-muted-foreground">
                    Long — readers will see “Show more”.
                  </p>
                )}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
