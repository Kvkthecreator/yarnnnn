'use client';

/**
 * useFileLoad — the one file-load hook shared by every viewer mount (ADR-436 §6).
 *
 * Before this, `ContentViewer.FileView` and `chat-surface/ArtifactCard` each
 * hand-wrote their own `getFile` state machine with their own 404-vs-error
 * discrimination. This hook is the singular implementation: one fetch, one
 * loading/notFound/error shape, an optional parallel head-revision read.
 *
 * `notFound` (a 404) is an honest "no longer at this path" state — a stale
 * deep-link or a synthetic node for a typed-but-unwritten path — distinct from
 * a real load `error` (ADR-388 follow-up).
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import { api, APIError } from '@/lib/api/client';
import type { WorkspaceFile } from '@/types';

/** Head-revision authorship (ADR-209 Phase 4), surfaced on the file header. */
export interface HeadRevision {
  authored_by: string;
  created_at: string;
}

export interface FileLoadState {
  file: WorkspaceFile | null;
  loading: boolean;
  /** 404 — the file is not at this path (stale link / never written). */
  notFound: boolean;
  /** A real load failure (message for display). */
  error: string | null;
  /** The head revision, when `withRevision` is set. */
  headRevision: HeadRevision | null;
  /**
   * Re-read the head revision WITHOUT re-reading the file (ADR-575).
   *
   * `reloadKey` reloads both, which is right for a rename or a discard but
   * wrong after an autosave: re-running `getFile` re-fires the consumer's
   * `setText(content)` effect, and a keystroke landing during that refetch is
   * destroyed (the ADR-572 D12 stale-prop shape, which has already shipped
   * once in Text). Saving changes the revision, not the member's text — so the
   * refresh that follows a save must touch only the revision.
   */
  refreshRevision: () => void;
}

/**
 * Load a workspace file by path. Pass `withRevision` to also fetch the head
 * revision in parallel (the Files header wants it; the chat card does not).
 * `reloadKey` bumps to force a refetch.
 */
export function useFileLoad(
  path: string,
  opts?: { withRevision?: boolean; reloadKey?: number },
): FileLoadState {
  const withRevision = opts?.withRevision ?? false;
  const reloadKey = opts?.reloadKey ?? 0;

  const [file, setFile] = useState<WorkspaceFile | null>(null);
  const [loading, setLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [headRevision, setHeadRevision] = useState<HeadRevision | null>(null);

  /**
   * Fetch the head revision for a path. Shared by the mount effect and by
   * `refreshRevision`, so the two can never drift on what "the head" means.
   * `cancelledRef` guards a response landing after unmount or a path change.
   */
  const cancelledRef = useRef(false);
  const fetchHeadRevision = useCallback((forPath: string) => {
    api.workspace
      .listRevisions({ path: forPath }, 1)
      .then((res) => {
        const head = res.revisions[0];
        if (!cancelledRef.current && head) {
          setHeadRevision({ authored_by: head.authored_by, created_at: head.created_at });
        }
      })
      .catch(() => { /* informational — non-fatal */ });
  }, []);

  const refreshRevision = useCallback(() => {
    if (!path || !withRevision) return;
    fetchHeadRevision(path);
  }, [path, withRevision, fetchHeadRevision]);

  useEffect(() => {
    let cancelled = false;
    cancelledRef.current = false;

    // NO path = nothing to load — not a miss. Callers legitimately render this
    // hook before a file is chosen (the Studio landing has no artifact; the file
    // modal opens empty), and they pass '' for it. Fetching that asked the API
    // for `?path=` and took a 404 on every mount — console noise that looks like
    // a broken artifact, and a `notFound` that races the real load. Settle to
    // the idle state instead: no file, not loading, not found=false.
    if (!path) {
      setFile(null);
      setLoading(false);
      setError(null);
      setNotFound(false);
      setHeadRevision(null);
      return;
    }

    setLoading(true);
    setError(null);
    setNotFound(false);
    setHeadRevision(null);

    api.workspace
      .getFile(path)
      .then((data) => { if (!cancelled) setFile(data); })
      .catch((err) => {
        if (cancelled) return;
        if (err instanceof APIError && err.status === 404) {
          setNotFound(true);
        } else {
          setError(err?.message || 'Failed to load file');
        }
      })
      .finally(() => { if (!cancelled) setLoading(false); });

    if (withRevision) {
      // Non-blocking on the file render; absence falls back to updated_at.
      fetchHeadRevision(path);
    }

    return () => { cancelled = true; cancelledRef.current = true; };
  }, [path, reloadKey, withRevision, fetchHeadRevision]);

  return { file, loading, notFound, error, headRevision, refreshRevision };
}
