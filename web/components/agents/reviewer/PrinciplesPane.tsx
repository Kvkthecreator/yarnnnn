'use client';

/**
 * PrinciplesPane — Dashboard archetype (ADR-198 §3).
 *
 * Renders /workspace/review/principles.md. Read-only surface; principles
 * edits route through the ambient YARNNN rail per invariant I2 (no inline
 * edit forms for foreign substrate). The "Edit principles" button seeds
 * the rail with a prompt that asks YARNNN to help revise principles.
 */

import { useEffect, useState } from 'react';
import { Loader2, Scale } from 'lucide-react';
import { api } from '@/lib/api/client';
import { MarkdownRenderer } from '@/components/shared/MarkdownRenderer';
import { EditInChatButton } from '@/components/shared/EditInChatButton';

export interface PrinciplesPaneProps {
  onOpenChatDraft: (prompt: string) => void;
}

export function PrinciplesPane({ onOpenChatDraft }: PrinciplesPaneProps) {
  const [content, setContent] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void (async () => {
      try {
        const file = await api.workspace.getFile('/workspace/review/principles.md');
        setContent(file.content ?? '');
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load principles');
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const editPrompt =
    "I'd like to revise my review principles. Show me the current principles and help me think through what to change.";

  return (
    <section className="rounded-md border border-border bg-card p-4">
      <header className="mb-3 flex items-center gap-2">
        <Scale className="h-4 w-4 text-muted-foreground" />
        <h2 className="text-sm font-semibold">Principles</h2>
        <div className="ml-auto">
          <EditInChatButton prompt={editPrompt} onOpenChatDraft={onOpenChatDraft} />
        </div>
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
              No review principles declared yet. Use Edit in chat to set them up.
            </p>
          )}
        </div>
      )}
    </section>
  );
}
