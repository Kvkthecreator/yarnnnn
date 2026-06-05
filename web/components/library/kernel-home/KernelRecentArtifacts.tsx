'use client';

/**
 * KernelRecentArtifacts — Home slot #5 (ADR-312).
 *
 * Kernel-universal: renders for EVERY workspace from kernel substrate
 * (delivered task outputs in `workspace_files` under
 * /workspace/operation/reports/{slug}/{date}/output.md), independent of the active
 * program. Programs do NOT declare this slot.
 *
 * Compact: the few most-recent delivered outputs as rows linking to the
 * recurrence detail (where the output renders). Self-hides when the
 * workspace has produced nothing yet — the cold-start Home stays honest.
 */

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { FileText, ArrowRight } from 'lucide-react';
import { api } from '@/lib/api/client';
import { formatRelativeTime } from '@/lib/formatting';

const COMPACT_LIMIT = 5;

interface Artifact {
  slug: string;
  date: string;
  path: string;
  summary: string | null;
  updated_at: string | null;
}

export function KernelRecentArtifacts() {
  const [artifacts, setArtifacts] = useState<Artifact[] | null>(null);

  useEffect(() => {
    let cancelled = false;
    api.workspace
      .recentArtifacts(COMPACT_LIMIT)
      .then((r) => {
        if (!cancelled) setArtifacts(r.artifacts);
      })
      .catch(() => {
        if (!cancelled) setArtifacts([]);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  if (!artifacts || artifacts.length === 0) return null;

  return (
    <section
      aria-label="Recent artifacts"
      className="rounded-lg border border-border/60 bg-card/50"
    >
      <header className="flex items-center justify-between px-4 py-2.5 border-b border-border/40">
        <div className="flex items-center gap-2">
          <FileText className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
          <h2 className="text-sm font-medium text-foreground">Recently delivered</h2>
        </div>
        <Link
          href="/files?path=/workspace/reports"
          className="inline-flex items-center gap-1 text-[11px] text-muted-foreground/70 hover:text-foreground transition-colors"
        >
          All <ArrowRight className="h-3 w-3" />
        </Link>
      </header>
      <ul className="divide-y divide-border/30">
        {artifacts.map((a) => (
          <li key={a.path}>
            <Link
              href={`/recurrence?task=${encodeURIComponent(a.slug)}`}
              className="flex items-center gap-3 px-4 py-2.5 hover:bg-muted/40 transition-colors"
            >
              {/* Backend returns a clean human title (path/machine prefixes
                  stripped); render it as the single line. */}
              <span className="flex-1 min-w-0 text-sm text-foreground truncate">
                {a.summary?.trim() || a.slug}
              </span>
              {a.updated_at && (
                <span className="text-[11px] text-muted-foreground/50 shrink-0 tabular-nums">
                  {formatRelativeTime(a.updated_at)}
                </span>
              )}
            </Link>
          </li>
        ))}
      </ul>
    </section>
  );
}
