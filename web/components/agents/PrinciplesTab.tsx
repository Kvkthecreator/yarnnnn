'use client';

/**
 * PrinciplesTab — Thinking Partner detail Principles tab (ADR-241 D2).
 *
 * Lifted from web/components/agents/reviewer/PrinciplesPane.tsx as part
 * of the ADR-241 collapse of the Reviewer surface into TP. The substrate
 * (/workspace/review/principles.md) is unchanged — same path, same
 * operator-authored framing per ADR-194 v2 + ADR-215 R3.
 *
 * What changed is the surface: principles.md is the **judgment framework
 * TP applies to verdicts**, not a separate Reviewer-agent property. It
 * lives inside TP's detail view as one of the tabs that describe TP's
 * cognitive substrate (Identity / Principles / Tasks).
 *
 * ADR-215 R3: principles.md is operator-authored substrate — edits happen
 * on Files with `authored_by=operator` attribution via the revision chain
 * (ADR-209). This tab links out to Files for edits, it does not host an
 * inline editor.
 */

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { Loader2, Scale, FileEdit } from 'lucide-react';
import { api } from '@/lib/api/client';
import { MarkdownRenderer } from '@/components/shared/MarkdownRenderer';

const PRINCIPLES_PATH = '/workspace/review/principles.md';
const PRINCIPLES_FILES_HREF = `/context?path=${encodeURIComponent(PRINCIPLES_PATH)}`;

export function PrinciplesTab() {
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
      <p className="mb-3 text-[11px] text-muted-foreground/80">
        The judgment framework TP applies to verdicts. Operator-authored;
        edits via Files with full revision history (ADR-209).
      </p>
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
              No principles declared yet. Open Files and edit{' '}
              <code className="rounded bg-muted px-1 py-0.5 text-[11px]">principles.md</code>{' '}
              to set them up.
            </p>
          )}
        </div>
      )}
    </section>
  );
}
