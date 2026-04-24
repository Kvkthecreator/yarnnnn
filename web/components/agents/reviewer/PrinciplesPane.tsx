'use client';

/**
 * PrinciplesPane — Dashboard archetype (ADR-198 §3).
 *
 * Renders /workspace/review/principles.md as a read surface on the Agents
 * tab's Reviewer detail view. ADR-215 R3: principles.md is operator-authored
 * substrate — edits happen on Files with `authored_by=operator` attribution
 * via the revision chain (ADR-209). This pane links out to Files for edits,
 * it does not host an inline editor (that lives on Files where every
 * `_shared/`-class substrate file gets the same treatment).
 *
 * Phase 3 change (ADR-215): the prior "Edit via YARNNN" chat seed is
 * retired. principles.md joined SHARED_EDITABLE_PATHS alongside the four
 * `_shared/` rules, so the edit surface is the same substrate editor every
 * other authored rule uses.
 */

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { Loader2, Scale, FileEdit } from 'lucide-react';
import { api } from '@/lib/api/client';
import { MarkdownRenderer } from '@/components/shared/MarkdownRenderer';

const PRINCIPLES_PATH = '/workspace/review/principles.md';
const PRINCIPLES_FILES_HREF = `/context?path=${encodeURIComponent(PRINCIPLES_PATH)}`;

export function PrinciplesPane() {
  const [content, setContent] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void (async () => {
      try {
        const file = await api.workspace.getFile(PRINCIPLES_PATH);
        setContent(file.content ?? '');
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load principles');
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  return (
    <section className="rounded-md border border-border bg-card p-4">
      <header className="mb-3 flex items-center gap-2">
        <Scale className="h-4 w-4 text-muted-foreground" />
        <h2 className="text-sm font-semibold">Principles</h2>
        <Link
          href={PRINCIPLES_FILES_HREF}
          className="ml-auto inline-flex items-center gap-1 rounded-md border border-border px-2 py-0.5 text-[11px] text-muted-foreground hover:bg-muted hover:text-foreground"
        >
          <FileEdit className="h-3 w-3" />
          Edit on Files
        </Link>
      </header>
      {loading && (
        <div className="flex items-center justify-center py-4">
          <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
        </div>
      )}
      {error && (
        <p className="text-sm text-muted-foreground">{error}</p>
      )}
      {!loading && !error && (
        <div className="text-sm text-foreground/90">
          {content ? (
            <MarkdownRenderer content={content} compact />
          ) : (
            <p className="text-muted-foreground">
              No review principles declared yet. Open Files and edit{' '}
              <code className="rounded bg-muted px-1 py-0.5 text-[11px]">principles.md</code>{' '}
              to set them up.
            </p>
          )}
        </div>
      )}
    </section>
  );
}
