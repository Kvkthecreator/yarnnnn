'use client';

/**
 * DesktopUpdateNotice — says, in words, that the installed desktop app is too
 * old (ADR-663 D3).
 *
 * The API refuses a host below its minimum with 426 `desktop_update_required`;
 * `request()` turns that into `DESKTOP_UPDATE_EVENT` (`lib/shell/host.ts`), and
 * this notice answers it. Without it an old host would meet the refusal as a
 * screen of failed loads — a version problem reading as an outage.
 *
 * It sends the member to Settings → Desktop app, the ONE home of the download
 * links (`lib/shell/desktop-app.ts`). A browser never raises the event, so on
 * the web this renders nothing, ever.
 */

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useTranslations } from 'next-intl';
import { DESKTOP_UPDATE_EVENT } from '@/lib/shell/host';
import { Z_TOAST } from '@/lib/shell/z-tiers';

export function DesktopUpdateNotice() {
  const t = useTranslations('shell.hostUpdate');
  const router = useRouter();
  const [refused, setRefused] = useState(false);

  useEffect(() => {
    const onRefused = () => setRefused(true);
    window.addEventListener(DESKTOP_UPDATE_EVENT, onRefused);
    return () => window.removeEventListener(DESKTOP_UPDATE_EVENT, onRefused);
  }, []);

  if (!refused) return null;

  return (
    <div
      role="alert"
      // The toast tier: above the desktop and its dialogs, because nothing
      // beneath it can load until the member acts on it.
      style={{ zIndex: Z_TOAST }}
      className="fixed inset-x-0 top-0 flex flex-wrap items-center justify-center gap-3 border-b border-border bg-background px-4 py-3 text-sm text-foreground shadow-sm"
    >
      <span>{t('message')}</span>
      <button
        type="button"
        onClick={() => router.push('/settings?settings.pane=desktop')}
        className="rounded-md bg-foreground px-3 py-1.5 font-medium text-background hover:opacity-90"
      >
        {t('action')}
      </button>
    </div>
  );
}
