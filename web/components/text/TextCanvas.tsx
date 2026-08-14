'use client';

/**
 * TextCanvas — the Text app's canvas (ADR-571).
 *
 * The editor itself: plain monospace text, ⌘S, and nothing else. Textarea
 * grade by decision (ADR-456 D1) — never block-grade, no Studio machinery,
 * no AI in the loop (Editor sits in the lane beside it, not inside it).
 *
 * The save path is ADR-570's, carried whole from the retired inline app:
 * `PATCH /workspace/file` (prose class ∧ carve law ∧ principal gate),
 * CAS-guarded on the head the document was loaded with. The 409 is a
 * product surface, not an edge case — the commons is multi-principal, and a
 * connector may revise this same file mid-session, so the conflict names
 * WHO moved the head and offers two explicit exits. Never a hidden merge.
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import { AlertTriangle, ArrowLeft, Check, Loader2 } from 'lucide-react';
import { api, APIError } from '@/lib/api/client';
import { useFileLoad } from '@/components/workspace/useFileLoad';
import { formatAuthorLabel } from '@/lib/workspace/attribution';
import { cn } from '@/lib/utils';

interface ConflictState {
  /** Who moved the head past us (authored_by, formatted for display). */
  actor: string;
  /** The head that superseded ours — Save-anyway CAS-chains off it. */
  currentHeadId: string | null;
}

const WORKSPACE_PREFIX = '/workspace/';
const relPath = (p: string) => (p.startsWith(WORKSPACE_PREFIX) ? p.slice(WORKSPACE_PREFIX.length) : p);

export function TextCanvas({
  path,
  onClose,
  onSaved,
}: {
  path: string;
  onClose: () => void;
  onSaved?: () => void;
}) {
  const [reloadKey, setReloadKey] = useState(0);
  const { file, loading, notFound, error } = useFileLoad(path, { reloadKey });

  const [text, setText] = useState('');
  const [baseline, setBaseline] = useState('');
  const [saving, setSaving] = useState(false);
  const [savedAt, setSavedAt] = useState<number | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [conflict, setConflict] = useState<ConflictState | null>(null);
  /** The CAS base: the head this content was loaded with (ADR-406 D2). */
  const baseHead = useRef<string | null>(null);

  // Load → editor state. A reload after a save re-baselines both halves, so
  // the dirty check compares against what is actually on the head.
  useEffect(() => {
    if (!file) return;
    const content = file.content ?? '';
    setText(content);
    setBaseline(content);
    baseHead.current = file.head_version_id ?? null;
    setConflict(null);
  }, [file]);

  const dirty = text !== baseline;

  const save = useCallback(
    async (expectedHead: string | null = baseHead.current) => {
      if (saving) return;
      setSaving(true);
      setSaveError(null);
      try {
        const res = await api.workspace.editFile(
          path,
          text,
          undefined,
          'Edited in Text',
          expectedHead,
        );
        // The door returns the new head so the next save CAS-chains off it
        // without a refetch (the invisible-save shape).
        baseHead.current = (res as { head_version_id?: string }).head_version_id ?? null;
        setBaseline(text);
        setConflict(null);
        setSavedAt(Date.now());
        onSaved?.();
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
          setSaveError(err instanceof Error ? err.message : 'Save failed');
        }
      } finally {
        setSaving(false);
      }
    },
    [path, text, saving, onSaved],
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

  // The saved flash fades on its own; a lingering "Saved" over a dirty
  // document would be a lie.
  useEffect(() => {
    if (savedAt === null) return;
    const t = setTimeout(() => setSavedAt(null), 2200);
    return () => clearTimeout(t);
  }, [savedAt]);

  return (
    <main className="flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden">
      <header className="flex items-center gap-3 border-b border-border px-4 py-2">
        <button
          type="button"
          onClick={onClose}
          title="Back to documents"
          className="inline-flex items-center gap-1 rounded-md border border-border px-2 py-1 text-xs text-muted-foreground hover:bg-muted/40 hover:text-foreground"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
        </button>
        <div className="min-w-0 flex-1">
          <h1 className="truncate text-sm font-medium">{path.split('/').pop()}</h1>
          <p className="truncate text-xs text-muted-foreground">{relPath(path)}</p>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          <span className="text-xs text-muted-foreground">
            {saving
              ? 'Saving…'
              : dirty
                ? 'Unsaved changes'
                : savedAt
                  ? 'Saved'
                  : 'Every save is a signed revision'}
          </span>
          <button
            type="button"
            onClick={() => void save()}
            disabled={saving || !dirty}
            title="Save (⌘S)"
            className="inline-flex items-center gap-1.5 rounded-md border border-border bg-foreground px-2.5 py-1.5 text-xs text-background disabled:opacity-50"
          >
            {saving ? (
              <Loader2 className="h-3 w-3 animate-spin" />
            ) : savedAt && !dirty ? (
              <Check className="h-3 w-3" />
            ) : null}
            Save
          </button>
        </div>
      </header>

      {conflict && (
        <div className="border-b border-amber-500/40 bg-amber-500/10 px-4 py-2 text-xs">
          <div className="flex items-start gap-2">
            <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-amber-600" />
            <div className="space-y-2">
              <p>
                <span className="font-medium">{conflict.actor}</span> revised this
                document while you were editing. Your text is still here — nothing
                was lost, and nothing merges silently.
              </p>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => { setConflict(null); setReloadKey((n) => n + 1); }}
                  className="rounded-md border border-border px-2 py-1 hover:bg-muted/40"
                >
                  Discard mine, show theirs
                </button>
                {conflict.currentHeadId && (
                  <button
                    type="button"
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

      {saveError && (
        <p className="border-b border-destructive/30 bg-destructive/5 px-4 py-2 text-xs text-destructive">
          {saveError}
        </p>
      )}

      <div className="min-h-0 flex-1 overflow-auto p-4">
        {loading ? (
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <Loader2 className="h-3.5 w-3.5 animate-spin" /> Opening…
          </div>
        ) : notFound ? (
          <p className="text-sm text-muted-foreground">
            Nothing exists at <span className="font-mono text-xs">{relPath(path)}</span>.
            It may have been moved or never written.
          </p>
        ) : error ? (
          <p className="text-sm text-destructive">{error}</p>
        ) : (
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={onKeyDown}
            spellCheck
            className={cn(
              'h-full min-h-[520px] w-full resize-none rounded-lg border border-border bg-muted/10 p-4',
              'font-mono text-sm leading-relaxed outline-none focus:border-foreground/30',
            )}
          />
        )}
      </div>
    </main>
  );
}
