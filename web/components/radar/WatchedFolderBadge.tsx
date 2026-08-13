'use client';

/**
 * WatchedFolderBadge — the Files-side indicator that a folder is under
 * Researcher's standing watch (ADR-565 D5 arc, owed since the desk shipped).
 *
 * Renders nothing unless the folder is a watched root. Files stays the
 * folder's home; the desk is where the watch is MANAGED — so the badge names
 * the fact and offers the one jump. Read-only: it never mutates, and a
 * roster-fetch failure renders as silence (the badge is an affordance, not a
 * health surface).
 *
 * The roster is fetched once per minute per session, module-cached — every
 * folder listing shares one request, not one each.
 */

import { useEffect, useState } from 'react';
import { Radar as RadarIcon } from 'lucide-react';
import { api } from '@/lib/api/client';
import { useSurfacePreferences } from '@/lib/shell/useSurfacePreferences';

const OPERATION_ROOT = '/workspace/operation';
const CACHE_TTL_MS = 60_000;

let cachedAt = 0;
let cachedTopics: string[] | null = null;
let inflight: Promise<string[]> | null = null;

async function watchedTopics(): Promise<string[]> {
  const now = Date.now();
  if (cachedTopics && now - cachedAt < CACHE_TTL_MS) return cachedTopics;
  if (!inflight) {
    inflight = api.radar
      .list()
      .then((rows) => {
        cachedTopics = rows.map((h) => h.topic);
        cachedAt = Date.now();
        return cachedTopics;
      })
      .catch(() => cachedTopics ?? [])
      .finally(() => {
        inflight = null;
      });
  }
  return inflight;
}

export function WatchedFolderBadge({ path }: { path: string }) {
  const { navigateToSurface } = useSurfacePreferences();
  const [topic, setTopic] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    if (!path.startsWith(`${OPERATION_ROOT}/`)) {
      setTopic(null);
      return;
    }
    const candidate = path.slice(OPERATION_ROOT.length + 1);
    void watchedTopics().then((topics) => {
      if (alive) setTopic(topics.includes(candidate) ? candidate : null);
    });
    return () => {
      alive = false;
    };
  }, [path]);

  if (!topic) return null;

  return (
    <div className="flex items-center justify-between gap-3 border-b bg-muted/30 px-4 py-2">
      <span className="flex items-center gap-1.5 text-xs text-muted-foreground">
        <RadarIcon className="h-3.5 w-3.5" />
        Watched by Researcher — the living report is kept in this folder.
      </span>
      <button
        type="button"
        onClick={() => navigateToSurface('radar', { topic })}
        className="shrink-0 text-xs underline-offset-2 hover:underline"
      >
        Open desk
      </button>
    </div>
  );
}
