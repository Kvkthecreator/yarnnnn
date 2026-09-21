'use client';

/**
 * StudioPublish — the Blogger app's boundary act (ADR-628 phase (a)).
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
import { useTranslations } from 'next-intl';
import { Send } from 'lucide-react';
import { api, APIError } from '@/lib/api/client';
import { useFeedback } from '@/contexts/FeedbackContext';
import { useSurfacePreferences } from '@/lib/shell/useSurfacePreferences';

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
  const t = useTranslations('studio.publish');
  const [open, setOpen] = useState(false);
  const [sites, setSites] = useState<SitesState>({ kind: 'loading' });
  const [siteId, setSiteId] = useState<string>('');
  const [publishing, setPublishing] = useState(false);
  /** The receipt the member reads AFTER the act (URL + the D7 readability
   *  caveat). It stays in the panel; publishing/failed ride the canonical
   *  action-feedback layer. */
  const [receipt, setReceipt] = useState<
    { url: string; status: string; publiclyReadable?: boolean } | null
  >(null);
  const menuRef = useRef<HTMLDivElement>(null);
  const { navigateToSurface } = useSurfacePreferences();
  const { runAction } = useFeedback();

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
        setReceipt(null);
        void loadSites();
      }
      return next;
    });
  }, [loadSites]);

  // Publishing / failed ride the canonical action-feedback layer (the bespoke
  // idle|working|done|error machine here re-implemented runAction). Only the
  // receipt stays in the panel — it is read after the act, not during it.
  const run = useCallback(
    async (status: 'publish' | 'draft') => {
      if (!siteId) return;
      setPublishing(true);
      try {
        const res = await runAction(
          () =>
            api.publish.wordpress({
              path: artifactPath,
              site_id: siteId,
              status,
            }),
          {
            pending: status === 'draft' ? t('savingDraft') : t('publishing'),
            success: (r) => (r.status === 'draft' ? t('draftSaved') : t('published')),
            error: (e) =>
              e instanceof APIError
                ? (e.data as { detail?: string })?.detail || t('publishFailed')
                : t('publishFailed'),
          },
        );
        setReceipt({
          url: res.url,
          status: res.status,
          publiclyReadable: res.publicly_readable,
        });
      } catch {
        // runAction already reported it; the panel stays open to retry.
      } finally {
        setPublishing(false);
      }
    },
    [artifactPath, siteId, runAction, t],
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
        title={t('publishHint')}
        aria-label={compact ? t('publishEllipsis') : undefined}
      >
        <Send className="h-3 w-3" />
        {!compact && <span>&nbsp;{t('publishEllipsis')}</span>}
      </button>

      {open && (
        <div className={panel}>
          <p className="px-1 pb-1 pt-0.5 text-[10px] font-medium uppercase tracking-wide text-muted-foreground">
            {t('panelTitle')}
          </p>
          <div className="space-y-2 px-1 pb-1">
            {sites.kind === 'loading' && (
              <p className="text-[11px] text-muted-foreground">{t('checking')}</p>
            )}

            {sites.kind === 'unconnected' && (
              <div className="space-y-1.5">
                <p className="text-[11px] leading-snug text-muted-foreground">
                  {t('unconnected')}
                </p>
                {/* ADR-297 D19 — cross-surface navigation rides the window
                    manager, never a raw anchor. (Was a raw anchor to the
                    Connectors route since 2026-09-01 — the nav gate had been
                    red on it.) */}
                <button
                  type="button"
                  onClick={() => navigateToSurface('reach', { pane: 'connected' })}
                  className="inline-flex items-center rounded-md border border-border px-2 py-1 text-[10px] text-muted-foreground hover:bg-muted/40 hover:text-foreground"
                >
                  {t('connectWordpress')}
                </button>
              </div>
            )}

            {sites.kind === 'empty' && (
              <p className="text-[11px] leading-snug text-muted-foreground">
                {t.rich('noSite', {
                  link: (chunks) => (
                    <a
                      href="https://wordpress.com/start"
                      target="_blank"
                      rel="noreferrer"
                      className="underline hover:text-foreground"
                    >
                      {chunks}
                    </a>
                  ),
                })}
              </p>
            )}

            {sites.kind === 'error' && (
              <p className="text-[11px] text-muted-foreground">
                {t('noAnswer')}{' '}
                <button type="button" className="underline" onClick={() => void loadSites()}>
                  {t('retry')}
                </button>
              </p>
            )}

            {sites.kind === 'ready' && !receipt && (
              <>
                <label className="block text-[10px] text-muted-foreground">
                  {t('site')}
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
                    disabled={publishing || !siteId}
                    onClick={() => void run('publish')}
                    title={t('publishNowHint')}
                  >
                    {publishing ? t('publishing') : t('publish')}
                  </button>
                  <button
                    type="button"
                    className={actBtn}
                    disabled={publishing || !siteId}
                    onClick={() => void run('draft')}
                    title={t('draftHint')}
                  >
                    {t('saveAsDraft')}
                  </button>
                </div>
                <p className="text-[10px] leading-snug text-muted-foreground">
                  {t('accountNote')}
                </p>
              </>
            )}

            {receipt && (
              <div className="space-y-1">
                <p className="text-[11px] text-foreground">
                  {receipt.status === 'draft' ? t('receiptDraft') : t('receiptPublished')}
                </p>
                {receipt.url && (
                  <a
                    href={receipt.url}
                    target="_blank"
                    rel="noreferrer"
                    className="block truncate text-[10px] text-muted-foreground underline hover:text-foreground"
                  >
                    {receipt.url}
                  </a>
                )}
                {/* ADR-628 D7 — the platform accepted it, but nobody can read
                    it. Reporting plain success here is the incorrect-success
                    class pointed outward. Shown only when KNOWN false. */}
                {receipt.publiclyReadable === false && (
                  <p className="text-[10px] leading-snug text-amber-600">
                    {receipt.status === 'draft'
                      ? t('notReadableDraft')
                      : t('notReadableLive')}
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
