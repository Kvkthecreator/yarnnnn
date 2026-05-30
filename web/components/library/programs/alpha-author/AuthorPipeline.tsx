'use client';

/**
 * AuthorPipeline — alpha-author program section (order: 4 per SURFACES.yaml).
 *
 * Pipeline + cadence-health face — surfaces:
 *   - Draft pipeline state (drafts in /workspace/context/authored/ subfolders
 *     with status: draft, derived from per-piece profile.md frontmatter)
 *   - Recently published pieces (last 5 with their updated_at)
 *   - Cadence health (compares last-published timestamp against operator's
 *     declared cadence in _preferences.yaml)
 *
 * Per ADR-245 three-layer model: L3 structured affordance composed from
 * substrate reads — workspace tree under /workspace/context/authored/ +
 * per-piece profile.md frontmatter for status discovery + _preferences.yaml
 * for declared cadence + _signal.md frontmatter rolling_windows for
 * cadence_state when available.
 *
 * Approach A — substrate-read only, no new backend routes. Per-piece
 * profile.md reads are deferred to demand (we don't read every piece
 * on cockpit mount); pipeline counts come from the tree walk + per-piece
 * profile peek for the top-N candidates.
 */

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { Loader2, FileText, Clock, CheckCircle2 } from 'lucide-react';
import { api } from '@/lib/api/client';
import type { WorkspaceTreeNode } from '@/types';

const AUTHORED_ROOT = '/workspace/context/authored';
const PREFERENCES_PATH = '/workspace/context/_shared/_preferences.yaml';
const SIGNAL_PATH = '/workspace/context/authored/_signal.md';

interface PieceSummary {
  slug: string;
  path: string;
  status: 'draft' | 'published' | 'archived' | 'unknown';
  updated_at?: string;
}

interface CadenceState {
  state: 'on-cadence' | 'behind' | 'ahead' | 'unknown';
  declaredCount: number;
}

function extractStatusFromProfile(content: string): PieceSummary['status'] {
  // profile.md may have frontmatter with status field, or a body
  // "## Type & Status" section. Try frontmatter first.
  const fm = content.match(/^---\s*\n([\s\S]*?)\n---/);
  if (fm) {
    const m = fm[1].match(/^\s*status:\s*([a-z]+)/m);
    if (m) {
      const s = m[1].toLowerCase();
      if (s === 'draft' || s === 'published' || s === 'archived') return s;
    }
  }
  const body = content.replace(/^---[\s\S]*?\n---/, '');
  if (/status:\s*draft/i.test(body)) return 'draft';
  if (/status:\s*published/i.test(body)) return 'published';
  if (/status:\s*archived/i.test(body)) return 'archived';
  return 'unknown';
}

function parseCadenceFromPreferences(content: string | undefined): number {
  // Count `active: true` deliverable_preferences entries — a proxy for
  // "how many cadence commitments the operator has declared." This is
  // a soft signal; the real cadence-health computation happens in
  // outcome-reconciliation and lands in _signal.md::rolling_windows.cadence_state.
  if (!content) return 0;
  const matches = content.match(/active:\s*true/g);
  return matches?.length ?? 0;
}

function parseCadenceStateFromSignal(content: string | undefined): CadenceState['state'] {
  if (!content) return 'unknown';
  const m = content.match(/cadence_state:\s*([a-z-]+)/);
  if (!m) return 'unknown';
  const v = m[1] as CadenceState['state'];
  return ['on-cadence', 'behind', 'ahead'].includes(v) ? v : 'unknown';
}

function formatRelativeAsOf(iso: string | undefined): string {
  if (!iso) return '';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '';
  const diffSec = Math.floor((Date.now() - d.getTime()) / 1000);
  if (diffSec < 3600) return `${Math.floor(diffSec / 60)}m ago`;
  if (diffSec < 86400) return `${Math.floor(diffSec / 3600)}h ago`;
  return `${Math.floor(diffSec / 86400)}d ago`;
}

function cadenceTone(state: CadenceState['state']): string {
  if (state === 'on-cadence') return 'text-emerald-600';
  if (state === 'behind') return 'text-amber-600';
  if (state === 'ahead') return 'text-muted-foreground';
  return 'text-muted-foreground';
}

function cadenceLabel(state: CadenceState['state']): string {
  if (state === 'on-cadence') return 'on cadence';
  if (state === 'behind') return 'behind';
  if (state === 'ahead') return 'ahead';
  return 'no signal yet';
}

export function AuthorPipeline() {
  const [pieces, setPieces] = useState<PieceSummary[]>([]);
  const [cadence, setCadence] = useState<CadenceState>({ state: 'unknown', declaredCount: 0 });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const tree = await api.workspace.getTree(AUTHORED_ROOT).catch(() => null);
        if (cancelled) return;

        // Find per-piece folders: direct children of /workspace/context/authored/
        // that are folders, excluding the entities/ subfolder (entities lives
        // alongside per-piece folders but is not a piece). Files like
        // _voice.md, _editorial.md, _entities.md, _signal.md, _tracker.md are
        // filtered as well.
        const pieceFolders: WorkspaceTreeNode[] = (tree ?? []).filter(
          n => n.type === 'folder' && n.name !== 'entities' && !n.name.startsWith('_'),
        );

        // For each piece folder, peek at profile.md (best-effort; tolerate
        // missing files). Cap at 8 reads to bound cockpit load time.
        const peeks = await Promise.all(
          pieceFolders.slice(0, 8).map(async folder => {
            const profilePath = `${folder.path}/profile.md`;
            const profile = await api.workspace.getFile(profilePath).catch(() => null);
            return {
              slug: folder.name,
              path: folder.path,
              status: profile?.content ? extractStatusFromProfile(profile.content) : 'unknown' as const,
              updated_at: folder.updated_at,
            };
          }),
        );
        if (cancelled) return;
        setPieces(peeks);

        const [prefsFile, signalFile] = await Promise.all([
          api.workspace.getFile(PREFERENCES_PATH).catch(() => null),
          api.workspace.getFile(SIGNAL_PATH).catch(() => null),
        ]);
        if (cancelled) return;

        const declaredCount = parseCadenceFromPreferences(prefsFile?.content);
        const state = parseCadenceStateFromSignal(signalFile?.content);
        setCadence({ state, declaredCount });
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  if (loading) {
    return (
      <section aria-label="Pipeline" className="rounded-lg border border-border bg-card p-5">
        <div className="flex items-center justify-center py-6">
          <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
        </div>
      </section>
    );
  }

  const draftCount = pieces.filter(p => p.status === 'draft').length;
  const publishedCount = pieces.filter(p => p.status === 'published').length;
  const recentPublished = pieces
    .filter(p => p.status === 'published')
    .sort((a, b) => (b.updated_at ?? '').localeCompare(a.updated_at ?? ''))
    .slice(0, 5);

  return (
    <section aria-label="Pipeline" className="rounded-lg border border-border bg-card p-5">
      <div className="mb-4 flex items-center justify-between text-xs">
        <span className="font-medium uppercase tracking-wide text-muted-foreground/70">
          Pipeline
        </span>
        <span className={`flex items-center gap-1 ${cadenceTone(cadence.state)}`}>
          <Clock className="h-3.5 w-3.5" />
          {cadenceLabel(cadence.state)}
          {cadence.declaredCount > 0 && ` · ${cadence.declaredCount} cadence${cadence.declaredCount > 1 ? 's' : ''} declared`}
        </span>
      </div>

      {pieces.length === 0 ? (
        <div className="flex items-start gap-3 rounded-md bg-muted/40 p-4 text-sm">
          <FileText className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground" />
          <div>
            <div className="font-medium">No pieces yet</div>
            <div className="mt-1 text-muted-foreground">
              Draft pieces land under {AUTHORED_ROOT}/{'{piece-slug}'}/content.md.
              YARNNN can scaffold a first piece — open chat and ask for one.
            </div>
          </div>
        </div>
      ) : (
        <>
          <div className="grid grid-cols-3 gap-6">
            <div>
              <div className="mb-1 text-xs uppercase tracking-wide text-muted-foreground/60">
                Drafts
              </div>
              <div className="flex items-center gap-2 text-2xl font-semibold tabular-nums">
                <FileText className="h-5 w-5 text-muted-foreground" />
                {draftCount}
              </div>
              <div className="mt-1 text-sm text-muted-foreground">in progress</div>
            </div>
            <div>
              <div className="mb-1 text-xs uppercase tracking-wide text-muted-foreground/60">
                Published
              </div>
              <div className="flex items-center gap-2 text-2xl font-semibold tabular-nums">
                <CheckCircle2 className="h-5 w-5 text-emerald-600" />
                {publishedCount}
              </div>
              <div className="mt-1 text-sm text-muted-foreground">total this window</div>
            </div>
            <div>
              <div className="mb-1 text-xs uppercase tracking-wide text-muted-foreground/60">
                Total tracked
              </div>
              <div className="text-2xl font-semibold tabular-nums">
                {pieces.length}
              </div>
              <div className="mt-1 text-sm text-muted-foreground">pieces in corpus</div>
            </div>
          </div>

          {recentPublished.length > 0 && (
            <div className="mt-4 border-t border-border pt-3">
              <div className="mb-2 text-xs uppercase tracking-wide text-muted-foreground/60">
                Recently published
              </div>
              <ul className="space-y-1 text-sm">
                {recentPublished.map(p => (
                  <li key={p.path} className="flex items-baseline justify-between gap-3">
                    <Link
                      href={`/context?path=${encodeURIComponent(p.path)}`}
                      className="truncate hover:underline"
                    >
                      {p.slug}
                    </Link>
                    <span className="shrink-0 text-xs text-muted-foreground/70">
                      {formatRelativeAsOf(p.updated_at)}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </>
      )}

      <div className="mt-4 flex items-center justify-between border-t border-border pt-3 text-xs">
        <span className="text-muted-foreground/70">
          Cadence declared in _preferences.yaml
        </span>
        <Link
          href={`/context?path=${encodeURIComponent(AUTHORED_ROOT)}`}
          className="text-muted-foreground/70 hover:text-foreground hover:underline"
        >
          Open corpus →
        </Link>
      </div>
    </section>
  );
}
