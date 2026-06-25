'use client';

/**
 * EmissionsView — the Out lens of the Context boundary surface (ADR-370).
 *
 * Read-only legibility over what the operation emitted to the outside world:
 * operator-addressing dispatches (email / Slack / Notion sends) — what
 * shipped, to whom, when, and whether it landed. Reads GET /api/emissions
 * (a union over destination_delivery_log + notifications; no new table).
 *
 * This is NEVER a send affordance — operator-addressing writes are system
 * infrastructure (ADR-299/304). The lens shows what already happened.
 */

import { useEffect, useState } from 'react';
import { ArrowUpFromLine, ExternalLink, Loader2 } from 'lucide-react';
import { api } from '@/lib/api/client';

type Emission = Awaited<ReturnType<typeof api.emissions>>[number];

function StatusPill({ status }: { status: string }) {
  const s = status.toLowerCase();
  const landed = s === 'delivered' || s === 'sent';
  const failed = s === 'failed';
  const cls = landed
    ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
    : failed
      ? 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400'
      : 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400';
  return (
    <span className={`px-2 py-0.5 rounded text-xs font-medium ${cls}`}>{status}</span>
  );
}

function ChannelLabel({ channel }: { channel: string }) {
  return (
    <span className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
      {channel}
    </span>
  );
}

function formatWhen(iso: string): string {
  // Best-effort, locale-aware; the API returns ISO strings.
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  });
}

export function EmissionsView() {
  const [emissions, setEmissions] = useState<Emission[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    api
      .emissions()
      .then((rows) => {
        if (!cancelled) setEmissions(rows);
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof Error ? err.message : 'Failed to load emissions');
      });
    return () => {
      cancelled = true;
    };
  }, []);

  if (error) {
    return (
      <div className="rounded-md border border-destructive/30 bg-destructive/5 px-4 py-3 text-sm text-destructive">
        {error}
      </div>
    );
  }

  if (!emissions) {
    return (
      <div className="flex items-center justify-center py-10">
        <Loader2 className="w-5 h-5 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (emissions.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-center">
        <ArrowUpFromLine className="w-6 h-6 text-muted-foreground/50 mb-3" />
        <p className="text-sm font-medium text-foreground">Nothing emitted yet</p>
        <p className="text-xs text-muted-foreground mt-1 max-w-xs">
          When the operation sends an email, Slack message, or Notion update on your
          behalf, it lands here — what shipped, to whom, and when.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {emissions.map((e) => (
        <div
          key={`${e.source}:${e.id}`}
          className="flex items-start gap-3 rounded-md border border-border/60 px-3 py-2.5"
        >
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <ChannelLabel channel={e.channel} />
              <StatusPill status={e.status} />
              {e.external_url && (
                <a
                  href={e.external_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 text-xs text-primary hover:underline"
                >
                  <ExternalLink className="w-3 h-3" />
                  view
                </a>
              )}
            </div>
            {e.destination && (
              <p className="text-sm text-foreground mt-0.5 truncate" title={e.destination}>
                {e.destination}
              </p>
            )}
            {e.error_message && (
              <p className="text-xs text-destructive mt-0.5">{e.error_message}</p>
            )}
          </div>
          <div className="shrink-0 text-xs text-muted-foreground whitespace-nowrap pt-0.5">
            {formatWhen(e.completed_at || e.created_at)}
          </div>
        </div>
      ))}
    </div>
  );
}
