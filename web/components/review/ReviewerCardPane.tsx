'use client';

/**
 * ReviewerCardPane — Dashboard archetype (ADR-198 §3).
 *
 * Renders /workspace/review/IDENTITY.md. Static surface; the Reviewer's
 * identity is declarative and changes rarely. Not a write surface.
 */

import { useEffect, useState } from 'react';
import { Loader2, ShieldCheck } from 'lucide-react';
import { api } from '@/lib/api/client';
import { MarkdownRenderer } from '@/components/shared/MarkdownRenderer';

export function ReviewerCardPane() {
  const [content, setContent] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void (async () => {
      try {
        const file = await api.workspace.getFile('/workspace/review/IDENTITY.md');
        setContent(file.content ?? '');
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load Reviewer identity');
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  return (
    <section className="rounded-md border border-border bg-card p-4">
      <header className="mb-3 flex items-center gap-2">
        <ShieldCheck className="h-4 w-4 text-muted-foreground" />
        <h2 className="text-sm font-semibold">Reviewer</h2>
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
              Reviewer identity not yet scaffolded for this workspace.
            </p>
          )}
        </div>
      )}
    </section>
  );
}
