'use client';

/**
 * StudioPublish — the Blogger desk's boundary act (ADR-628 phase (a)).
 *
 * A third header verb beside Share/Export, mounted ONLY on the blogger app
 * (the exportPng precedent: an app-scoped affordance is an optional mount,
 * not a fork). It is the ONE member-facing door to the outbound seam:
 *
 *   - the SITE is chosen here, at the act — never stored on the connection
 *     (ADR-594 D1: a connection is consent + credential + aperture);
 *   - Publish and Draft are both offered; the default is Publish — the act
 *     is member-clicked by design, so the click IS the consent (ADR-628 D2);
 *   - the three connect states render distinctly (ADR-628 amendment):
 *     not connected → the Connectors door; connected with no sites → the
 *     free-site guidance (a wordpress.com blog is ~2 clicks, once);
 *     connected with sites → the picker.
 *
 * The receipt (URL + status) renders in the panel after the act; the durable
 * receipt is the `_publish.yaml` sidecar the server writes beside the post.
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import { Send } from 'lucide-react';
import { api } from '@/lib/api/client';

interface StudioPublishProps {
  /** Workspace path of the post artifact (any spelling — server normalizes). */
  artifactPath: string;
  compact?: boolean;
  coarsePointer?: boolean;
}

type SitesState =
  | { kind: 'loading' }
  | { kind: 'unconnected' }
  | { kind: 'empty' }
  | { kind: 'ready'; sites: Array<{ id: string; name: string; url: string }> }
  | { kind: 'error' };

export function StudioPublish({
  artifactPath,
  compact = false,
  coarsePointer = false,
}: StudioPublishProps) {
  const [open, setOpen] = useState(false);
  const [sites, setSites] = useState<SitesState>({ kind: 'loading' });
  const [siteId, setSiteId] = useState<string>('');
  const [act, setAct] = useState<
    | { kind: 'idle' }
    | { kind: 'working' }
    | { kind: 'done'; url: string; status: string }
    | { kind: 'error'; message: string }
  >({ kind: 'idle' });
  const menuRef = useRef<HTMLDivElement>(null);

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

  const loadSites = useCallback(async () => {
    setSites({ kind: 'loading' });
    try {
      const res = await api.publish.wordpressSites();
      if (!res.connected) setSites({ kind: 'unconnected' });
      else if (!res.sites.length) setSites({ kind: 'empty' });
      else {
        setSites({ kind: 'ready', sites: res.sites });
        setSiteId((prev) => prev || res.sites[0].id);
      }
    } catch {
      setSites({ kind: 'error' });
    }
  }, []);

  const openPanel = useCallback(() => {
    setOpen((o) => {
      const next = !o;
      if (next) {
        setAct({ kind: 'idle' });
        void loadSites();
      }
      return next;
    });
  }, [loadSites]);

  const run = useCallback(
    async (status: 'publish' | 'draft') => {
      if (!siteId) return;
      setAct({ kind: 'working' });
      try {
        const res = await api.publish.wordpress({
          path: artifactPath,
          site_id: siteId,
          status,
        });
        setAct({ kind: 'done', url: res.url, status: res.status });
      } catch (e) {
        setAct({
          kind: 'error',
          message: e instanceof Error ? e.message : 'Publish failed — try again.',
        });
      }
    },
    [artifactPath, siteId],
  );

  const btn =
    'inline-flex shrink-0 items-center justify-center gap-1 whitespace-nowrap rounded-md border border-border text-[11px] text-muted-foreground transition-colors hover:bg-muted/40 hover:text-foreground disabled:opacity-40 ' +
    (coarsePointer ? 'min-h-[44px] ' : '') +
    (compact ? (coarsePointer ? 'w-11 px-0' : 'h-7 w-8 px-0') : 'px-2 py-1');
  const actBtn =
    'inline-flex items-center gap-1 rounded-md border border-border px-2 py-1 text-[10px] text-muted-foreground transition-colors hover:bg-muted/40 hover:text-foreground disabled:opacity-40';
  const panel =
    'absolute right-0 top-full z-30 mt-1 w-80 rounded-md border border-border bg-background p-2 shadow-md';

  return (
    <div ref={menuRef} className="relative flex shrink-0 items-center gap-1">
      <button
        type="button"
        className={btn}
        onClick={openPanel}
        title="Publish this post to your blog — your click, your account"
        aria-label={compact ? 'Publish…' : undefined}
      >
        <Send className="h-3 w-3" />
        {!compact && ' Publish…'}
      </button>

      {open && (
        <div className={panel}>
          <p className="px-1 pb-1 pt-0.5 text-[10px] font-medium uppercase tracking-wide text-muted-foreground">
            Publish to WordPress
          </p>
          <div className="space-y-2 px-1 pb-1">
            {sites.kind === 'loading' && (
              <p className="text-[11px] text-muted-foreground">Checking your connection…</p>
            )}

            {sites.kind === 'unconnected' && (
              <div className="space-y-1.5">
                <p className="text-[11px] leading-snug text-muted-foreground">
                  Connect WordPress once, and every post can publish to your own
                  blog — your account, your name, your click.
                </p>
                <a
                  href="/connectors"
                  className="inline-flex items-center rounded-md border border-border px-2 py-1 text-[10px] text-muted-foreground hover:bg-muted/40 hover:text-foreground"
                >
                  Connect WordPress →
                </a>
              </div>
            )}

            {sites.kind === 'empty' && (
              <p className="text-[11px] leading-snug text-muted-foreground">
                Your WordPress account has no site yet. A free blog
                (yourname.wordpress.com) takes about a minute at{' '}
                <a
                  href="https://wordpress.com/start"
                  target="_blank"
                  rel="noreferrer"
                  className="underline hover:text-foreground"
                >
                  wordpress.com/start
                </a>
                {' '}— after that, publishing from here is one click.
              </p>
            )}

            {sites.kind === 'error' && (
              <p className="text-[11px] text-muted-foreground">
                WordPress did not answer.{' '}
                <button type="button" className="underline" onClick={() => void loadSites()}>
                  Retry
                </button>
              </p>
            )}

            {sites.kind === 'ready' && act.kind !== 'done' && (
              <>
                <label className="block text-[10px] text-muted-foreground">
                  Site
                  <select
                    value={siteId}
                    onChange={(e) => setSiteId(e.target.value)}
                    className="mt-0.5 w-full rounded-md border border-border bg-background px-1.5 py-1 text-[11px]"
                  >
                    {sites.sites.map((s) => (
                      <option key={s.id} value={s.id}>
                        {s.name}
                      </option>
                    ))}
                  </select>
                </label>
                <div className="flex flex-wrap gap-1">
                  <button
                    type="button"
                    className={actBtn}
                    disabled={act.kind === 'working' || !siteId}
                    onClick={() => void run('publish')}
                    title="Publish live, now — the post goes public on your site"
                  >
                    {act.kind === 'working' ? 'Publishing…' : 'Publish'}
                  </button>
                  <button
                    type="button"
                    className={actBtn}
                    disabled={act.kind === 'working' || !siteId}
                    onClick={() => void run('draft')}
                    title="Send as a draft — it lands on your site unpublished, for a final look there"
                  >
                    Save as draft there
                  </button>
                </div>
                {act.kind === 'error' && (
                  <p className="text-[10px] leading-snug text-red-500">{act.message}</p>
                )}
                <p className="text-[10px] leading-snug text-muted-foreground">
                  Published under your own account. The receipt lands beside the
                  post; nothing here ever publishes on a schedule.
                </p>
              </>
            )}

            {act.kind === 'done' && (
              <div className="space-y-1">
                <p className="text-[11px] text-foreground">
                  {act.status === 'draft' ? 'Draft saved on your site ✓' : 'Published ✓'}
                </p>
                {act.url && (
                  <a
                    href={act.url}
                    target="_blank"
                    rel="noreferrer"
                    className="block truncate text-[10px] text-muted-foreground underline hover:text-foreground"
                  >
                    {act.url}
                  </a>
                )}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
