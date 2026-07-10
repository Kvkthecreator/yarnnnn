'use client';

/**
 * Blob resolution + blob-state UI — shared by every blob-backed viewer app
 * (ADR-436). Extracted from `FileBody` when the monolith split into per-type
 * renderer apps: the signed-URL hook and the loading/error/missing states are
 * the common substrate the Image / Media / PDF apps all sit on.
 *
 * ADR-427 D4 forward pointer: `content_url` is scheduled for deletion as a
 * stored column — it becomes a per-request, per-principal, TTL'd MINTED
 * capability computed from `blob_sha`. `useSignedBlobUrl` is the SINGLE FE site
 * that consumes it, so the retirement lands here and nowhere else.
 */

import { useEffect, useState } from 'react';
import { FileQuestion, Loader2 } from 'lucide-react';
import { api } from '@/lib/api/client';

/**
 * Resolve a file's content_url to a directly-renderable URL (ADR-395).
 *
 * A raw upload's content_url is a relative `/api/documents/blob?storage_path=…`
 * reference that requires AUTH to resolve — a browser `<img>/<iframe>/<video>`
 * src can't send the Bearer header, so we resolve the signed URL here via an
 * authenticated fetch and hand the DIRECT (Supabase) signed URL to the element.
 * Absolute URLs pass through unchanged. Returns {url, loading, error}; url is
 * '' until resolved.
 */
export function useSignedBlobUrl(
  contentUrl: string | null | undefined,
): { url: string; loading: boolean; error: boolean } {
  const [state, setState] = useState<{ url: string; loading: boolean; error: boolean }>(
    { url: '', loading: false, error: false }
  );
  useEffect(() => {
    if (!contentUrl) { setState({ url: '', loading: false, error: false }); return; }
    if (/^(https?:|data:|blob:)/i.test(contentUrl)) {
      setState({ url: contentUrl, loading: false, error: false });
      return;
    }
    let cancelled = false;
    setState({ url: '', loading: true, error: false });
    api.documents
      .blobUrl(contentUrl)
      .then((r) => { if (!cancelled) setState({ url: r.url, loading: false, error: false }); })
      .catch(() => { if (!cancelled) setState({ url: '', loading: false, error: true }); });
    return () => { cancelled = true; };
  }, [contentUrl]);
  return state;
}

export function BlobLoading({ label }: { label: string }) {
  return (
    <div className="flex items-center justify-center gap-2 rounded-lg border border-border bg-muted/10 py-16 text-sm text-muted-foreground">
      <Loader2 className="h-4 w-4 animate-spin" />
      {label}
    </div>
  );
}

export function BlobError() {
  return (
    <div className="rounded-lg border border-dashed border-border bg-muted/10 p-6 text-center text-sm text-muted-foreground">
      <FileQuestion className="mx-auto mb-2 h-6 w-6 text-muted-foreground/50" />
      Couldn’t load this file. Try Download to open it in a native viewer.
    </div>
  );
}

/**
 * The type resolved to a blob-backed viewer but there is no blob.
 *
 * Today this is the honest state for a versioned `.mp4`: binary is still
 * Category-3 (`content_url` sidecar) and a `write_revision` of bytes has
 * nowhere to land until ADR-427 Phase 2. Saying so is better than painting an
 * empty player — and better than the pre-2026-07-09 behavior, which resolved
 * the same file to `text` and painted its bytes. The Media Player app owns this
 * state until Phase 2 lands (ADR-436 §3).
 */
export function BlobMissing({ kind }: { kind: string }) {
  return (
    <div className="rounded-lg border border-dashed border-border bg-muted/10 p-6 text-center text-sm text-muted-foreground">
      <FileQuestion className="mx-auto mb-2 h-6 w-6 text-muted-foreground/50" />
      This {kind} has no stored bytes yet.
    </div>
  );
}
