'use client';

/**
 * MaterialNarrativeStrip — Cockpit pane #4 in the six-question cockpit
 * framing (2026-04-28 reshape). The pane that answers "what did the team
 * do since I last looked?"
 *
 * Universal across program bundles. Reads the workspace narrative
 * (ADR-219) filtered to material-weight entries only — trades fired,
 * proposals reviewed, principles updated, calibration shifts. Housekeeping
 * pulses (back-office sweeps, narrative_digest cards, idle pings) do not
 * appear here. Routine entries appear in collapsed form only when the
 * pane is empty of material.
 *
 * Source: `/api/narrative/by-task` (ADR-219 Commit 4) — slices keyed by
 * task slug, each carrying `last_material`. We flatten + sort by
 * `created_at` desc and render the most recent N.
 *
 * Empty state: "Quiet day — nothing material since last look."
 */

import { useEffect, useState } from 'react';
import { Sparkles } from 'lucide-react';
import Link from 'next/link';
import { api } from '@/lib/api/client';
import type { NarrativeMaterialEntry } from '@/types';

const SHOW_LIMIT = 5;

interface MaterialEntry extends NarrativeMaterialEntry {
  task_slug: string;
}

export function MaterialNarrativeStrip() {
  const [entries, setEntries] = useState<MaterialEntry[] | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const resp = await api.narrative.byTask(24);
        const flat: MaterialEntry[] = [];
        for (const slice of resp.tasks) {
          if (slice.last_material) {
            flat.push({ ...slice.last_material, task_slug: slice.task_slug });
          }
        }
        flat.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
        if (!cancelled) setEntries(flat);
      } catch {
        if (!cancelled) setEntries([]);
      }
    })();
  }, []);

  if (entries === null) return null;

  return (
    <section className="rounded-lg border border-border bg-card p-4">
      <div className="mb-2 flex items-center justify-between text-xs">
        <h3 className="font-medium uppercase tracking-wide text-muted-foreground/70">
          Since last look · past 24h
        </h3>
        <Link
          href="/chat?weight=material"
          className="text-muted-foreground/60 underline-offset-4 hover:text-foreground hover:underline"
        >
          Full narrative →
        </Link>
      </div>
      {entries.length === 0 ? (
        <p className="rounded-md border border-dashed border-border px-4 py-4 text-center text-sm text-muted-foreground">
          Quiet day — nothing material since last look.
        </p>
      ) : (
        <ul className="space-y-1.5">
          {entries.slice(0, SHOW_LIMIT).map((entry, idx) => (
            <li key={`${entry.task_slug}-${idx}`} className="flex items-start gap-2 text-sm">
              <Sparkles className="mt-0.5 h-3 w-3 shrink-0 text-muted-foreground/40" />
              <div className="flex-1 min-w-0">
                <Link
                  href={`/work?task=${encodeURIComponent(entry.task_slug)}`}
                  className="text-foreground hover:underline"
                >
                  <span className="line-clamp-1">{entry.summary}</span>
                </Link>
                <span className="text-[11px] text-muted-foreground/60">
                  {entry.task_slug} · {formatRelative(entry.created_at)}
                </span>
              </div>
            </li>
          ))}
          {entries.length > SHOW_LIMIT && (
            <li className="pt-1 text-center">
              <Link
                href="/chat?weight=material"
                className="text-xs font-medium text-muted-foreground underline-offset-4 hover:text-foreground hover:underline"
              >
                See {entries.length - SHOW_LIMIT} more material entries
              </Link>
            </li>
          )}
        </ul>
      )}
    </section>
  );
}

function formatRelative(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60_000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}
