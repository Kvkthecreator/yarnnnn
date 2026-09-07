'use client';

/**
 * ReachConnected — Reach's CONNECTED pane (ADR-642 D2).
 *
 * Every connection the member holds — platform OAuth rows and attached
 * connectors alike — with WHERE it points, what it READS and WRITES (the
 * `does` facts, derived server-side from the machinery that enacts them,
 * ADR-642 D5), how FRESH its capture is (the capture signal, the same source
 * the Connectors page reads), and WHICH standing declarations read through
 * it (derived from the standing roster's `sources[].connector`).
 *
 * Lists and doors, never acts: consent, selection and the per-tool aperture
 * stay Settings → Connectors (ADR-594 D1 — a connection is consent +
 * credential + aperture, and those are settings). Nothing here is stored
 * (DP29). No row presents an agent's record (ADR-640).
 */

import { useEffect, useState } from 'react';
import { FolderOpen, Plug, Plus } from 'lucide-react';
import { api, type StandingSummary } from '@/lib/api/client';
import { connectorMeta, FRESHNESS_PROVIDERS } from '@/lib/connectors/registry';
import { formatRelativeTime } from '@/lib/formatting';
import { useSurfacePreferences } from '@/lib/shell/useSurfacePreferences';
import { cn } from '@/lib/utils';

type Integration = Awaited<ReturnType<typeof api.integrations.list>>['integrations'][number];

interface Freshness {
  status?: string;
  observedAt: string | null;
  items?: number;
  lastError?: string;
}

const STATUS_DOT: Record<string, string> = {
  active: 'bg-emerald-500',
  error: 'bg-destructive',
  expired: 'bg-amber-500',
};

function Fact({ label, text, tone = 'muted' }: { label: string; text: string; tone?: 'muted' | 'warn' }) {
  return (
    <div className="flex gap-2">
      <dt className="w-16 shrink-0 text-muted-foreground/60">{label}</dt>
      <dd className={cn('min-w-0 flex-1 leading-snug', tone === 'warn' ? 'text-amber-600' : 'text-muted-foreground')}>
        {text}
      </dd>
    </div>
  );
}

export function ReachConnected() {
  const { navigateToSurface } = useSurfacePreferences();
  const [rows, setRows] = useState<Integration[] | null>(null);
  const [standing, setStanding] = useState<StandingSummary[]>([]);
  const [freshness, setFreshness] = useState<Record<string, Freshness>>({});
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [ints, decls] = await Promise.all([
          api.integrations.list(),
          api.standing.list().catch(() => [] as StandingSummary[]),
        ]);
        if (cancelled) return;
        const list = ints.integrations ?? [];
        setRows(list);
        setStanding(decls);
        // The capture-signal fan-out (ADR-401 D6 — freshness is DERIVED from
        // the signal, never the stored status column). Each call guarded so
        // one platform's failure never blanks the others.
        const providers = FRESHNESS_PROVIDERS.filter(
          (p): p is 'slack' | 'notion' | 'github' =>
            list.some((i) => i.provider === p && i.status === 'active'),
        );
        const results = await Promise.all(
          providers.map(async (provider) => {
            try {
              const s = await api.integrations.getCaptureSignal(provider);
              const block = s.observed?.[`capture-${provider}`];
              const fresh: Freshness = {
                status: block?.status,
                observedAt: block?.observed_at ?? null,
                items: block?.items,
                lastError: block?.last_error,
              };
              return [provider, fresh] as const;
            } catch {
              return null;
            }
          }),
        );
        if (cancelled) return;
        const map: Record<string, Freshness> = {};
        results.forEach((r) => {
          if (r) map[r[0]] = r[1];
        });
        setFreshness(map);
      } catch (e) {
        if (!cancelled) {
          setError(e instanceof Error ? e.message : String(e));
          setRows([]);
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  if (rows === null) {
    return <div className="h-24 rounded-md bg-muted/30 animate-pulse" />;
  }

  if (rows.length === 0) {
    return (
      <div className="rounded-lg border border-dashed border-border/60 px-6 py-10 text-center">
        <Plug className="mx-auto mb-3 h-6 w-6 text-muted-foreground/40" />
        <p className="text-sm font-medium text-foreground/80">Nothing is connected yet</p>
        <p className="mt-1 text-xs text-muted-foreground/70">
          Connect a platform once, and this page shows what it reads, what it writes, and who reads through it.
        </p>
        {error && <p className="mt-2 text-[11px] text-destructive">{error}</p>}
        <button
          type="button"
          onClick={() => navigateToSurface('connectors')}
          className="mt-4 inline-flex items-center gap-1.5 rounded-md border border-border px-3 py-1.5 text-xs text-muted-foreground hover:bg-muted/40 hover:text-foreground"
        >
          <Plus className="h-3.5 w-3.5" />
          Connect a platform
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <ul className="space-y-3">
        {rows.map((i) => {
          const attached = i.kind === 'attached';
          const meta = attached ? undefined : connectorMeta(i.provider);
          const name = attached
            ? (i.title ?? i.provider.replace(/^mcp:/, ''))
            : (meta?.displayName ?? i.provider);
          const fresh = freshness[i.provider];
          const readers = standing.filter((d) => d.sources.some((s) => s.connector === i.provider));
          return (
            <li key={i.id} className="rounded-lg border border-border/60 p-4">
              <div className="flex items-start gap-3">
                <div
                  className={cn(
                    'flex h-9 w-9 shrink-0 items-center justify-center rounded-lg',
                    meta ? meta.brand.chipClass : 'bg-muted',
                  )}
                >
                  {meta ? meta.brand.icon : <Plug className="h-4 w-4 text-muted-foreground" />}
                </div>
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-x-2 gap-y-0.5">
                    <span className="text-sm font-medium text-foreground">{name}</span>
                    {i.target && <span className="truncate text-xs text-muted-foreground">{i.target}</span>}
                    <span
                      className={cn('h-1.5 w-1.5 rounded-full', STATUS_DOT[i.status] ?? 'bg-muted-foreground/40')}
                      title={i.status}
                      aria-label={i.status}
                    />
                    {attached && (
                      <span className="rounded-full border border-border px-1.5 py-0.5 text-[10px] text-muted-foreground">
                        attached
                      </span>
                    )}
                  </div>
                  <dl className="mt-2 space-y-1 text-[11px]">
                    {i.does?.reads && <Fact label="Reads" text={i.does.reads} />}
                    {i.does?.writes && <Fact label="Writes" text={i.does.writes} />}
                    {attached && (
                      <Fact
                        label="Exposes"
                        text={`${i.tools_exposed ?? 0} tool${i.tools_exposed === 1 ? '' : 's'} to your turns${i.category ? ` · ${i.category}` : ''}`}
                      />
                    )}
                    {fresh && (
                      <Fact
                        label="Last read"
                        text={
                          fresh.observedAt
                            ? `${formatRelativeTime(fresh.observedAt)}${fresh.items ? ` · ${fresh.items} items` : ''}`
                            : 'not reading yet'
                        }
                        tone={fresh.lastError ? 'warn' : 'muted'}
                      />
                    )}
                    {readers.length > 0 && (
                      <div className="flex gap-2">
                        <dt className="w-16 shrink-0 text-muted-foreground/60">Read by</dt>
                        <dd className="flex flex-wrap gap-1">
                          {readers.map((d) => (
                            <button
                              key={d.topic}
                              type="button"
                              onClick={() =>
                                navigateToSurface('files', { path: d.target_path ?? d.declaration_path })
                              }
                              className="inline-flex items-center gap-1 rounded-full border border-border px-2 py-0.5 text-[10px] text-muted-foreground hover:text-foreground"
                              title="A standing declaration reads this connection — open the file it keeps"
                            >
                              <FolderOpen className="h-3 w-3" />
                              {d.topic}
                            </button>
                          ))}
                        </dd>
                      </div>
                    )}
                  </dl>
                </div>
              </div>
            </li>
          );
        })}
      </ul>
      <p className="text-[11px] leading-snug text-muted-foreground/70">
        Consent, what each connection may read, and what each attached tool may do live in Settings → Connectors.
        This page shows what is connected and what moves through it.
      </p>
    </div>
  );
}
