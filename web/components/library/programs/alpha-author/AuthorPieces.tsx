'use client';

/**
 * AuthorPieces — alpha-author's live-entities list (Home slot #4, "what's
 * in play").
 *
 * Six-slot contract (ADR-312 D2 + the 2026-06-04 amendment): a program
 * declares exactly ONE entity list (slot #4), program-labeled. For an
 * author the entities are **Pieces** (essays / posts / deck narratives /
 * IR memos). Reshaped from the former AuthorPipeline, which was a 3-metric
 * grid (Drafts / Published / Total) — that's a dashboard, not a list of
 * what's in play. This is a labeled list: each piece is a row with its
 * state, newest first.
 *
 * Substrate (unchanged): walk /workspace/operation/authored/ for piece
 * folders, peek profile.md for draft/published state.
 */

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { Loader2, PenLine, ArrowRight, CircleDot, CheckCircle2 } from 'lucide-react';
import { api } from '@/lib/api/client';
import { useHome } from '../../HomeContext';
import type { WorkspaceTreeNode } from '@/types';

const AUTHORED_ROOT = '/workspace/operation/authored';

interface Piece {
  slug: string;
  path: string;
  status: 'draft' | 'published' | 'archived' | 'unknown';
  updated_at?: string;
}

function statusFromProfile(content: string): Piece['status'] {
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

function titleize(slug: string): string {
  return slug.replace(/[-_]/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}

function relTime(iso: string | undefined): string {
  if (!iso) return '';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '';
  const sec = Math.floor((Date.now() - d.getTime()) / 1000);
  if (sec < 3600) return `${Math.floor(sec / 60)}m ago`;
  if (sec < 86400) return `${Math.floor(sec / 3600)}h ago`;
  return `${Math.floor(sec / 86400)}d ago`;
}

const STATUS_ORDER: Record<Piece['status'], number> = {
  draft: 0,
  published: 1,
  unknown: 2,
  archived: 3,
};

export function AuthorPieces() {
  const { onOpenChatDraft } = useHome();
  const [pieces, setPieces] = useState<Piece[] | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const tree = await api.workspace.getTree(AUTHORED_ROOT).catch(() => null);
        if (cancelled) return;
        const folders: WorkspaceTreeNode[] = (tree ?? []).filter(
          (n) => n.type === 'folder' && n.name !== 'entities' && !n.name.startsWith('_'),
        );
        const peeked = await Promise.all(
          folders.slice(0, 12).map(async (folder) => {
            const profile = await api.workspace
              .getFile(`${folder.path}/profile.md`)
              .catch(() => null);
            return {
              slug: folder.name,
              path: folder.path,
              status: profile?.content
                ? statusFromProfile(profile.content)
                : ('unknown' as const),
              updated_at: folder.updated_at,
            };
          }),
        );
        if (!cancelled) setPieces(peeked);
      } catch {
        if (!cancelled) setPieces([]);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  if (pieces === null) {
    return (
      <section aria-label="Pieces" className="rounded-lg border border-border/60 bg-card/50 p-5">
        <div className="flex items-center justify-center py-6">
          <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
        </div>
      </section>
    );
  }

  const draftCount = pieces.filter((p) => p.status === 'draft').length;
  const publishedCount = pieces.filter((p) => p.status === 'published').length;

  const sorted = [...pieces].sort((a, b) => {
    const s = STATUS_ORDER[a.status] - STATUS_ORDER[b.status];
    if (s !== 0) return s;
    return (b.updated_at ?? '').localeCompare(a.updated_at ?? '');
  });
  const shown = sorted.slice(0, 6);
  const overflow = sorted.length - shown.length;

  return (
    <section aria-label="Pieces" className="rounded-lg border border-border/60 bg-card/50">
      <header className="flex items-center justify-between px-4 py-2.5 border-b border-border/40">
        <div className="flex items-center gap-2">
          <PenLine className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
          <h2 className="text-sm font-medium text-foreground">Pieces</h2>
          {pieces.length > 0 && (
            <span className="text-[11px] text-muted-foreground/60">
              {publishedCount} published · {draftCount} in progress
            </span>
          )}
        </div>
        <Link
          href={`/files?path=${encodeURIComponent(AUTHORED_ROOT)}`}
          className="inline-flex items-center gap-1 text-[11px] text-muted-foreground/70 hover:text-foreground transition-colors"
        >
          All pieces <ArrowRight className="h-3 w-3" />
        </Link>
      </header>

      {pieces.length === 0 ? (
        <div className="px-4 py-6 text-center">
          <p className="text-sm text-foreground mb-1">No pieces yet</p>
          <button
            type="button"
            onClick={() =>
              onOpenChatDraft('Help me start a new piece — set up a draft I can write into.')
            }
            className="text-sm text-primary hover:underline"
          >
            Start your first piece →
          </button>
        </div>
      ) : (
        <ul className="divide-y divide-border/30">
          {shown.map((p) => (
            <li key={p.path}>
              <Link
                href={`/files?path=${encodeURIComponent(p.path)}`}
                className="flex items-center gap-3 px-4 py-2.5 hover:bg-muted/40 transition-colors"
              >
                {p.status === 'published' ? (
                  <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600 shrink-0" />
                ) : (
                  <CircleDot className="h-3.5 w-3.5 text-amber-500 shrink-0" />
                )}
                <span className="flex-1 min-w-0 text-sm text-foreground truncate">
                  {titleize(p.slug)}
                </span>
                <span className="text-[11px] text-muted-foreground/50 shrink-0">
                  {p.status === 'published'
                    ? 'published'
                    : p.status === 'draft'
                    ? 'in progress'
                    : ''}
                </span>
                {p.updated_at && (
                  <span className="text-[11px] text-muted-foreground/40 shrink-0 tabular-nums">
                    {relTime(p.updated_at)}
                  </span>
                )}
              </Link>
            </li>
          ))}
        </ul>
      )}
      {overflow > 0 && (
        <Link
          href={`/files?path=${encodeURIComponent(AUTHORED_ROOT)}`}
          className="block px-4 py-2 text-[11px] text-muted-foreground/60 hover:text-foreground hover:bg-muted/30 transition-colors border-t border-border/30"
        >
          +{overflow} more pieces →
        </Link>
      )}
    </section>
  );
}
