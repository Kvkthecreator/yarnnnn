'use client';

/**
 * ReachBrowser — the member's own browser, on Reach (ADR-664).
 *
 * The browser is reach like a connection: the agent acts on any website
 * through it (ADR-662 D15, the yarnnn Chrome extension). What it DOES is served
 * by the one reach structure (`reach_status.browser_does`, on
 * `GET /api/integrations` as `browser`) — no reach sentence is written here
 * (ADR-644). What only this page can know is whether the extension answers it:
 * that is the state line (`browserHands`).
 */

import { useEffect, useState } from 'react';
import { useTranslations } from 'next-intl';
import { Globe } from 'lucide-react';
import { browserHands, type BrowserHands } from '@/lib/shell/hands';
import { AddToChrome } from '@/components/shared/AddToChrome';
import { cn } from '@/lib/utils';

export type BrowserDoes = { name: string; reads: string; writes: string; chat?: string; agents: string };

export function ReachBrowser({
  does,
  Fact,
}: {
  does: BrowserDoes;
  Fact: (p: { label: string; text: string }) => JSX.Element;
}) {
  const t = useTranslations('reach');
  const [hands, setHands] = useState<BrowserHands | null>(null);

  useEffect(() => {
    let live = true;
    browserHands().then((h) => live && setHands(h));
    return () => {
      live = false;
    };
  }, []);

  const connected = !!hands && hands.executor !== null && hands.on;
  const version = hands && 'version' in hands ? hands.version : undefined;
  const state = connected ? t('browser.connected', { version: version ?? '' }) : t('browser.missing');

  return (
    <li className="rounded-lg border border-border/60 p-4">
      <div className="flex items-start gap-3">
        <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md border border-border/60">
          <Globe className="h-4 w-4 text-muted-foreground" aria-hidden />
        </span>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-x-2 gap-y-0.5">
            <span className="text-sm font-medium text-foreground">{does.name}</span>
            {hands && (
              <>
                <span className="truncate text-xs text-muted-foreground">{state}</span>
                <span
                  className={cn('h-1.5 w-1.5 rounded-full', connected ? 'bg-emerald-500' : 'bg-muted-foreground/40')}
                  aria-hidden
                />
              </>
            )}
            {hands && !connected && (
              <AddToChrome className="ml-auto shrink-0 text-[11px] text-muted-foreground underline underline-offset-2 hover:text-foreground" />
            )}
          </div>
          <dl className="mt-2 space-y-1 text-[11px]">
            <Fact label={t('facts.reads')} text={does.reads} />
            <Fact label={t('facts.writes')} text={does.writes} />
            <Fact label={t('facts.agents')} text={does.agents} />
          </dl>
        </div>
      </div>
    </li>
  );
}
