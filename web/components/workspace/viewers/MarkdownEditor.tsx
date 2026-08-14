'use client';

/**
 * MarkdownEditor — the editor app for the prose currency (ADR-570).
 *
 * Textarea-grade, deliberately: plain text, monospace, no block model, no
 * Studio machinery (D7). It is the SECOND reference app (ADR-427 §10) — its
 * whole job is to exercise the public contract: revision write + CAS + 409 +
 * attribution through the ONE member write door (`PATCH /workspace/file`),
 * zero private API.
 *
 * The mount owns the frame (ADR-436); this app owns only the text and the
 * save. `onDone(saved)` hands the frame back to the default app — the mount
 * refetches on `saved` so Preview shows the new head.
 *
 * The 409 is a product surface, not an edge case (ADR-570 D5): the commons is
 * multi-principal, and a connector may revise the same file mid-edit. The
 * conflict banner names WHO moved the head and offers two explicit exits —
 * never a hidden merge (ADR-406 D2).
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import { AlertTriangle, Loader2 } from 'lucide-react';
import { api, APIError } from '@/lib/api/client';
import { formatAuthorLabel } from '@/lib/workspace/attribution';
import { cn } from '@/lib/utils';
import type { ViewerAppProps } from './index';

interface ConflictState {
  /** Who moved the head past us (authored_by, formatted for display). */
  actor: string;
  /** The head that superseded ours — Save-anyway CAS-chains off it. */
  currentHeadId: string | null;
}

export const MarkdownEditor = ({ file, compact, onDone }: ViewerAppProps) => {
  const loaded = file.content ?? '';
  const [text, setText] = useState(loaded);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [conflict, setConflict] = useState<ConflictState | null>(null);
  // The CAS base: the head this content was loaded with (ADR-406 D2). Null on
  // a pre-ADR-209 file → the save is unconditional, matching the house rule.
  const baseHead = useRef<string | null>(file.head_version_id ?? null);
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);

  const dirty = text !== loaded && !saving;

  useEffect(() => {
    textareaRef.current?.focus();
  }, []);

  const save = useCallback(
    async (expectedHead: string | null = baseHead.current) => {
      if (saving) return;
      setSaving(true);
      setError(null);
      try {
        await api.workspace.editFile(
          file.path,
          text,
          undefined,
          'Edited in the editor',
          expectedHead,
        );
        // ADR-570 D7: a successful save returns to Preview; the mount
        // refetches so the viewer renders the new head.
        onDone?.(true);
      } catch (err) {
        if (err instanceof APIError && err.status === 409) {
          const detail = (err.data as {
            detail?: { current_head?: { id?: string; authored_by?: string } };
          } | null)?.detail;
          const head = detail?.current_head;
          setConflict({
            actor: formatAuthorLabel(head?.authored_by ?? '') || 'Someone else',
            currentHeadId: head?.id ?? null,
          });
        } else {
          setError(err instanceof Error ? err.message : 'Save failed');
        }
      } finally {
        setSaving(false);
      }
    },
    [file.path, text, saving, onDone],
  );

  const onKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 's') {
        e.preventDefault();
        void save();
      }
    },
    [save],
  );

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between gap-3">
        <span className="text-xs text-muted-foreground">
          {dirty ? 'Unsaved changes' : 'Editing — every save is a signed revision'}
        </span>
        <div className="flex items-center gap-2 shrink-0">
          <button
            onClick={() => onDone?.(false)}
            disabled={saving}
            className="rounded-md border border-border px-2.5 py-1.5 text-xs text-muted-foreground hover:bg-muted/40 hover:text-foreground disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            onClick={() => void save()}
            disabled={saving || !dirty}
            className="inline-flex items-center gap-1.5 rounded-md border border-border bg-foreground px-2.5 py-1.5 text-xs text-background hover:opacity-90 disabled:opacity-50"
            title="Save (⌘S)"
          >
            {saving && <Loader2 className="h-3 w-3 animate-spin" />}
            Save
          </button>
        </div>
      </div>

      {conflict && (
        <div className="rounded-lg border border-amber-500/40 bg-amber-500/10 p-3 text-xs">
          <div className="flex items-start gap-2">
            <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-amber-600" />
            <div className="space-y-2">
              <p>
                <span className="font-medium">{conflict.actor}</span> revised this
                file while you were editing. Your text is still here — nothing was
                lost, and nothing merges silently.
              </p>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => onDone?.(true)}
                  className="rounded-md border border-border px-2 py-1 hover:bg-muted/40"
                >
                  Discard mine, show theirs
                </button>
                {conflict.currentHeadId && (
                  <button
                    onClick={() => void save(conflict.currentHeadId)}
                    className="rounded-md border border-border px-2 py-1 hover:bg-muted/40"
                  >
                    Save mine over theirs
                  </button>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {error && <p className="text-xs text-destructive">{error}</p>}

      <textarea
        ref={textareaRef}
        value={text}
        onChange={(e) => {
          setText(e.target.value);
          setConflict(null);
        }}
        onKeyDown={onKeyDown}
        className={cn(
          'w-full resize-y rounded-lg border border-border bg-muted/10 p-4 font-mono text-sm leading-relaxed outline-none focus:border-foreground/30',
          compact ? 'min-h-[280px]' : 'min-h-[560px]',
        )}
        spellCheck
      />
    </div>
  );
};
