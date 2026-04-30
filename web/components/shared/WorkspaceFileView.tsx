'use client';

/**
 * WorkspaceFileView — universal kernel component for rendering a workspace
 * file inline anywhere in the surface.
 *
 * Replaces per-surface file-fetch logic (SnapshotModal's MandateTab,
 * ReviewStandardTab, SubstrateTab on /agents, etc.). One component, one
 * contract:
 *
 *   - Loads the file at `path`
 *   - Shows a loading state, then either:
 *       · Markdown content + authored-by attribution + Edit-in-chat CTA
 *       · Empty state with a prompt to author in chat
 *   - Handles 404 as empty state (not error chrome) per ADR-198 §3
 *
 * Zero LLM calls. Pure substrate read.
 *
 * Can render inside: modal overlay, side drawer, agents page tab,
 * work-page detail panel, chat composer area. Container is neutral —
 * callers wrap it as needed.
 */

import { useEffect, useState } from 'react';
import { Loader2, type LucideIcon } from 'lucide-react';
import { api, APIError } from '@/lib/api/client';
import { MarkdownRenderer } from '@/components/shared/MarkdownRenderer';
import { EditInChatButton } from '@/components/shared/EditInChatButton';

export interface WorkspaceFileViewProps {
  /** Absolute workspace path, e.g. /workspace/context/_shared/MANDATE.md */
  path: string;

  /** Optional heading shown above the content. */
  title?: string;

  /** Optional icon component displayed next to the title. */
  icon?: LucideIcon;

  /** Short tagline below the title. */
  tagline?: string;

  /**
   * Prompt seeded into chat when operator clicks Edit in chat.
   * If omitted, no Edit button is shown.
   */
  editPrompt?: string;

  /**
   * Callback invoked with the editPrompt when operator clicks Edit.
   * Required when editPrompt is provided.
   */
  onEdit?: (prompt: string) => void;

  /**
   * Custom empty-state body rendered when the file is absent or whitespace.
   * If omitted, a generic "No content yet" empty state is shown.
   */
  emptyBody?: React.ReactNode;

  /**
   * Max content lines before clamping. Undefined = show full file.
   * Useful for snippet views (e.g. awareness.md tail).
   */
  maxLines?: number;

  /** Additional className on the root element. */
  className?: string;
}

function tailMarkdown(content: string, maxLines: number): string {
  const lines = content.split('\n');
  if (lines.length <= maxLines) return content;
  return lines.slice(-maxLines).join('\n');
}

export function WorkspaceFileView({
  path,
  title,
  icon: Icon,
  tagline,
  editPrompt,
  onEdit,
  emptyBody,
  maxLines,
  className,
}: WorkspaceFileViewProps) {
  const [content, setContent] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [authoredBy, setAuthoredBy] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const file = await api.workspace.getFile(path);
        if (cancelled) return;
        setContent(file?.content ?? '');

        // Surface head-revision authorship (ADR-209 enrichment).
        // Non-fatal — if revision fetch fails, attribution just stays hidden.
        try {
          const revs = await api.workspace.listRevisions(path, 1);
          if (!cancelled && revs?.revisions?.[0]?.authored_by) {
            const raw = revs.revisions[0].authored_by;
            const label =
              raw === 'operator' ? 'You' :
              raw.startsWith('yarnnn:') ? 'YARNNN' :
              raw.startsWith('agent:') ? `Agent (${raw.slice(6)})` :
              raw.startsWith('specialist:') ? 'Specialist' :
              raw.startsWith('reviewer:') ? 'Reviewer' :
              raw.startsWith('system:') ? 'System' : null;
            if (!cancelled) setAuthoredBy(label);
          }
        } catch { /* non-fatal */ }
      } catch (err) {
        if (cancelled) return;
        // 404 = empty state, not error chrome (ADR-198 §3 Briefing invariant).
        setContent('');
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, [path]);

  const isEmpty = !content || !content.trim();
  const displayContent = content && maxLines ? tailMarkdown(content.trim(), maxLines) : content?.trim() ?? '';

  return (
    <div className={className}>
      {/* Header: title + authored-by + edit CTA */}
      {(title || editPrompt) && (
        <div className="flex items-start justify-between gap-3 mb-3">
          <div className="min-w-0 flex-1">
            {title && (
              <div className="flex items-center gap-1.5">
                {Icon && <Icon className="h-3.5 w-3.5 text-muted-foreground shrink-0" />}
                <h3 className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
                  {title}
                </h3>
              </div>
            )}
            {tagline && (
              <p className="mt-0.5 text-[11px] text-muted-foreground/70">{tagline}</p>
            )}
            {authoredBy && (
              <p className="mt-0.5 text-[10px] text-muted-foreground/50">
                Last edited by {authoredBy}
              </p>
            )}
          </div>
          {editPrompt && onEdit && (
            <EditInChatButton
              prompt={editPrompt}
              onOpenChatDraft={onEdit}
              variant="compact"
            />
          )}
        </div>
      )}

      {/* Content */}
      {loading ? (
        <div className="flex items-center justify-center py-6">
          <Loader2 className="h-4 w-4 animate-spin text-muted-foreground/40" />
        </div>
      ) : isEmpty ? (
        <div className="rounded-md border border-dashed border-border/60 bg-muted/10 px-4 py-5 text-sm text-muted-foreground">
          {emptyBody ?? (
            <p className="text-center text-xs">
              No content yet.{' '}
              {editPrompt && onEdit && (
                <button
                  type="button"
                  onClick={() => onEdit(editPrompt)}
                  className="font-medium underline underline-offset-4 hover:no-underline"
                >
                  Author in chat
                </button>
              )}
            </p>
          )}
        </div>
      ) : (
        <div className="text-sm text-foreground/90">
          <MarkdownRenderer content={displayContent} compact />
          {maxLines && content && content.split('\n').length > maxLines && (
            <p className="mt-1 text-[10px] text-muted-foreground/50 italic">
              Showing last {maxLines} lines —{' '}
              <a href={`/context?path=${encodeURIComponent(path)}`} className="underline underline-offset-4">
                open full file
              </a>
            </p>
          )}
        </div>
      )}
    </div>
  );
}
