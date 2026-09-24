'use client';

/**
 * UpdateNotice — the ONE place the page says a newer yarnnn exists than the one
 * the member is running (ADR-663 D3, D6, D7).
 *
 * Three states, the blocking one first:
 *
 *  - **refused** — the installed desktop app is below the API's minimum. The
 *    API answers 426 `desktop_update_required`; `request()` turns that into
 *    `DESKTOP_UPDATE_EVENT` (`lib/shell/host.ts`). Nothing beneath can load, so
 *    it is a bar across the top. If the host has already downloaded its update
 *    it offers the restart; otherwise it sends the member to Settings →
 *    Desktop app, the one home of the download links. A browser never raises it.
 *  - **host** — the desktop app's own updater downloaded and verified a new host
 *    (`src-tauri/src/update.rs`). It installs when the member quits; the card
 *    says so and offers it now.
 *  - **web** — a newer interface is live than the one this window loaded
 *    (`lib/shell/deployment.ts`). Reload picks it up. It is checked at most
 *    once a quarter hour, only while the window is in view (and on its return
 *    to view), and never again once found.
 *
 * The two cards are dismissible, because nothing is broken yet.
 */

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useTranslations } from 'next-intl';
import {
  DESKTOP_UPDATE_EVENT,
  hostUpdateReady,
  onHostUpdateReady,
  restartToUpdate,
} from '@/lib/shell/host';
import { LOADED_DEPLOYMENT, servedDeployment } from '@/lib/shell/deployment';
import { Z_TOAST } from '@/lib/shell/z-tiers';

const CHECK_EVERY_MS = 15 * 60 * 1000;

const PRIMARY = 'rounded-md bg-foreground px-3 py-1.5 font-medium text-background hover:opacity-90';

export function UpdateNotice() {
  const t = useTranslations('shell.update');
  const router = useRouter();
  const [refused, setRefused] = useState(false);
  const [hostReady, setHostReady] = useState<string | null>(null);
  const [newer, setNewer] = useState(false);
  const [dismissed, setDismissed] = useState(false);

  useEffect(() => {
    const onRefused = () => setRefused(true);
    window.addEventListener(DESKTOP_UPDATE_EVENT, onRefused);
    return () => window.removeEventListener(DESKTOP_UPDATE_EVENT, onRefused);
  }, []);

  // The host may have finished downloading before this page loaded, so ask
  // once, then listen.
  useEffect(() => {
    let unlisten: (() => void) | null = null;
    let gone = false;
    void hostUpdateReady().then((v) => v && setHostReady(v));
    void onHostUpdateReady(setHostReady).then((u) => (gone ? u() : (unlisten = u)));
    return () => {
      gone = true;
      unlisten?.();
    };
  }, []);

  useEffect(() => {
    if (!LOADED_DEPLOYMENT || newer) return;
    let last = Date.now();
    const check = async () => {
      if (document.visibilityState !== 'visible') return;
      last = Date.now();
      const served = await servedDeployment();
      if (served && served !== LOADED_DEPLOYMENT) setNewer(true);
    };
    const onVisible = () => {
      if (Date.now() - last >= CHECK_EVERY_MS) void check();
    };
    const timer = window.setInterval(check, CHECK_EVERY_MS);
    document.addEventListener('visibilitychange', onVisible);
    return () => {
      window.clearInterval(timer);
      document.removeEventListener('visibilitychange', onVisible);
    };
  }, [newer]);

  if (refused) {
    return (
      <div
        role="alert"
        // The toast tier: above the desktop and its dialogs, because nothing
        // beneath it can load until the member acts on it.
        style={{ zIndex: Z_TOAST }}
        className="fixed inset-x-0 top-0 flex flex-wrap items-center justify-center gap-3 border-b border-border bg-background px-4 py-3 text-sm text-foreground shadow-sm"
      >
        <span>{t('refused.message')}</span>
        {hostReady ? (
          <button type="button" onClick={() => void restartToUpdate()} className={PRIMARY}>
            {t('host.action')}
          </button>
        ) : (
          <button
            type="button"
            onClick={() => router.push('/settings?settings.pane=desktop')}
            className={PRIMARY}
          >
            {t('refused.action')}
          </button>
        )}
      </div>
    );
  }

  // A restart into the new host reloads the website too, so it outranks Reload.
  const card = hostReady
    ? { message: t('host.message'), action: t('host.action'), act: () => void restartToUpdate() }
    : newer
      ? { message: t('web.message'), action: t('web.action'), act: () => window.location.reload() }
      : null;
  if (!card || dismissed) return null;

  return (
    <div
      role="status"
      style={{ zIndex: Z_TOAST }}
      className="fixed bottom-4 right-4 flex max-w-[calc(100vw-2rem)] items-center gap-3 rounded-lg border border-border bg-background px-4 py-3 text-sm text-foreground shadow-lg"
    >
      <span>{card.message}</span>
      <button
        type="button"
        onClick={() => setDismissed(true)}
        className="rounded-md px-2 py-1.5 text-muted-foreground hover:text-foreground"
      >
        {t('dismiss')}
      </button>
      <button type="button" onClick={card.act} className={PRIMARY}>
        {card.action}
      </button>
    </div>
  );
}
