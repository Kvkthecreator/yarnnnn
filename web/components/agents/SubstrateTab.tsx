'use client';

/**
 * SubstrateTab — uniform tab content for substrate-file rendering on the
 * Thinking Partner detail view (ADR-241 + ADR-236 Round 5+ extension).
 *
 * Authored by ADR-236 Round 5+ (2026-04-30). Replaces the per-tab
 * inconsistency the operator flagged ("streamline look and feel of
 * all tabs to have a singular look and feel").
 *
 * Single shape:
 *   - Section header (icon + label + tagline + optional Edit-in-chat
 *     pinned to the right of the title)
 *   - Loading state (shared)
 *   - Empty state (shared, with chat-mediated authoring CTA)
 *   - Markdown render of the file content
 *
 * One tab = one substrate file = one rendering. PrinciplesTab is the
 * predecessor; this generalizes its pattern so Mandate / Autonomy /
 * Memory tabs share visual rhythm.
 *
 * Mutation surface: chat. Per ADR-236 Cluster A and the ADR-241 +
 * EditInChatButton R3-supersession, every substrate edit flows through
 * chat. The tab's "Edit in chat" affordance seeds a substrate-specific
 * prompt rather than navigating to Files.
 */

import { useEffect, useState } from 'react';
import { Loader2, type LucideIcon } from 'lucide-react';
import { api, APIError } from '@/lib/api/client';
import { MarkdownRenderer } from '@/components/shared/MarkdownRenderer';
import { EditInChatButton } from '@/components/shared/EditInChatButton';
import { useTP } from '@/contexts/TPContext';

export interface SubstrateTabProps {
  /** Tab heading rendered next to the icon. */
  title: string;
  /** Lucide icon for the heading. */
  icon: LucideIcon;
  /** One-line operator-facing tagline below the heading. */
  tagline: string;
  /** Workspace path of the substrate file (e.g. /workspace/context/_shared/MANDATE.md). */
  path: string;
  /** Prompt seeded into chat when the operator clicks Edit in chat. */
  editPrompt: string;
  /**
   * Empty-state copy when the file is absent or whitespace-only.
   * Should explain what the file is for in operator language.
   */
  emptyStateBody: React.ReactNode;
}

export function SubstrateTab({
  title,
  icon: Icon,
  tagline,
  path,
  editPrompt,
  emptyStateBody,
}: SubstrateTabProps) {
  const { sendMessage } = useTP();
  const [content, setContent] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const file = await api.workspace.getFile(path);
        if (!cancelled) setContent(file?.content ?? '');
      } catch (err) {
        if (cancelled) return;
        // 404 is empty state, not error chrome (ADR-198 §3 Briefing
        // invariant — applied here at a general substrate-render shape).
        if (err instanceof APIError && err.status === 404) setContent('');
        else setContent('');
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [path]);

  const isEmpty = !content || !content.trim();

  return (
    <section className="rounded-md border border-border bg-card p-4">
      {/* Header — title + tagline on the left, Edit-in-chat pinned right. */}
      <header className="mb-3 flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <Icon className="h-4 w-4 text-muted-foreground" />
            <h2 className="text-sm font-semibold">{title}</h2>
          </div>
          <p className="mt-1 text-[11px] text-muted-foreground/80">{tagline}</p>
        </div>
        <EditInChatButton
          prompt={editPrompt}
          onOpenChatDraft={(prompt) => sendMessage(prompt)}
        />
      </header>

      {loading ? (
        <div className="flex items-center justify-center py-4">
          <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
        </div>
      ) : isEmpty ? (
        <div className="rounded-md border border-dashed border-border/60 bg-muted/10 px-4 py-5 text-sm text-muted-foreground">
          {emptyStateBody}
        </div>
      ) : (
        <div className="text-sm text-foreground/90">
          <MarkdownRenderer content={content!} compact />
        </div>
      )}
    </section>
  );
}
