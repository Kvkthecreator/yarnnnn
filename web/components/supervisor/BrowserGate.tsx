'use client';

/**
 * BrowserGate — the browser is the Supervisor's prerequisite for SETTING UP and
 * RUNNING work, never for seeing it (ADR-667 D4).
 *
 * The page asks for its browser hands (`browserHands()`, ADR-662 D15). With
 * them on, the gate renders its children — the Supervisor's conversation.
 * Without them it is the install step: what the extension is for, *Add to
 * Chrome* when the store listing exists, *Switch it on* when it is installed
 * but off, and a quieter *continue without it* for work that reads and acts
 * on nothing (the unattended kind, which needs no browser).
 *
 * ⚠️ THE SWITCH IS `storeUrl`, not the app stage. Until ADR-662 is Accepted,
 * ADR-661's tripwire holds `CHROME_EXTENSION.storeUrl` null, and the step
 * names the extension without offering a link it cannot honestly offer.
 *
 * "Continue without it" is a per-viewer convenience, remembered in this
 * browser only; storage that throws (private window) just forgets it.
 */

import { useCallback, useEffect, useState, type ReactNode } from 'react';
import { useTranslations } from 'next-intl';
import { Globe } from 'lucide-react';
import { CHROME_EXTENSION, browserHands, setBrowserHands, type BrowserHands } from '@/lib/shell/hands';
import { Working } from '@/components/shared/Working';

const SKIP_KEY = 'yarnnn.supervisor.without-browser';

function readSkip(): boolean {
  try { return window.localStorage.getItem(SKIP_KEY) === '1'; } catch { return false; }
}
function writeSkip(on: boolean) {
  try {
    if (on) window.localStorage.setItem(SKIP_KEY, '1');
    else window.localStorage.removeItem(SKIP_KEY);
  } catch { /* forgotten — the gate simply asks again */ }
}

export function BrowserGate({ children }: { children: ReactNode }) {
  const t = useTranslations('supervisor.gate');
  const [hands, setHands] = useState<BrowserHands | null>(null);
  const [skipped, setSkipped] = useState(false);
  const [switching, setSwitching] = useState(false);

  const check = useCallback(() => {
    void browserHands().then(setHands);
  }, []);

  useEffect(() => {
    setSkipped(readSkip());
    check();
    // A member who went to install it comes back to this tab: ask again.
    window.addEventListener('focus', check);
    return () => window.removeEventListener('focus', check);
  }, [check]);

  if (hands === null) return <Working label={t('checking')} />;
  if (hands.on || skipped) return <>{children}</>;

  // Installed and answering, but switched off (the desktop app's host may
  // answer with no extension behind it — that is not installed).
  const installedOff = hands.executor !== null && hands.connected && !hands.on;
  const hostTooOld = hands.executor === null && hands.hostTooOld === true;

  return (
    <div className="rounded-lg border border-border/70 px-5 py-6">
      <span className="flex h-9 w-9 items-center justify-center rounded-md border border-border/60">
        <Globe className="h-4 w-4 text-muted-foreground" aria-hidden />
      </span>
      <h2 className="mt-3 text-[15px] font-semibold text-foreground">{t('title')}</h2>
      <p className="mt-1 text-[13px] text-muted-foreground">{t('body')}</p>
      <div className="mt-4 flex flex-wrap items-center gap-2">
        {installedOff ? (
          <button
            type="button"
            disabled={switching}
            onClick={async () => {
              setSwitching(true);
              await setBrowserHands(true);
              setSwitching(false);
              check();
            }}
            className="rounded-md bg-foreground px-3 py-1.5 text-xs font-medium text-background transition-opacity hover:opacity-90 disabled:opacity-50"
          >
            {t('switchOn')}
          </button>
        ) : hostTooOld ? (
          <span className="text-xs text-muted-foreground">{t('updateApp')}</span>
        ) : CHROME_EXTENSION.storeUrl ? (
          <a
            href={CHROME_EXTENSION.storeUrl}
            target="_blank"
            rel="noreferrer"
            className="rounded-md bg-foreground px-3 py-1.5 text-xs font-medium text-background transition-opacity hover:opacity-90"
          >
            {t('add')}
          </a>
        ) : (
          <span className="text-xs text-muted-foreground">{t('comingSoon')}</span>
        )}
        <button
          type="button"
          onClick={() => { writeSkip(true); setSkipped(true); }}
          className="rounded-md px-2.5 py-1.5 text-xs text-muted-foreground underline-offset-2 hover:text-foreground hover:underline"
        >
          {t('without')}
        </button>
      </div>
    </div>
  );
}
