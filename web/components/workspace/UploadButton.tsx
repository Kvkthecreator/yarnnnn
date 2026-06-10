'use client';

/**
 * UploadButton — the operator 'add' verb on the Files surface (ADR-329).
 *
 * Upload is one of the two operator-facing file verbs (add · delete);
 * edit + index are system verbs. This is the single 'add a file'
 * affordance, homed on Files where uploads live and where "add a file"
 * is the natural operator thought. There is no parallel upload UI
 * (Singular Implementation) — Settings shows a count, not an uploader.
 *
 * Drops the file(s) through api.documents.upload → POST /api/documents/upload,
 * which extracts text → /workspace/uploads/{slug}.md via the Authored
 * Substrate (ADR-209, attributed operator) and auto-indexes (ADR-325 D6).
 * On success, calls onUploaded so the explorer re-fetches the tree.
 *
 * ADR-331 D5: multi-select + .zip. The operator can pick several files (or a
 * .zip of them) in one go; the batch is non-transactional — per-file results
 * surface, partial success is fine.
 */

import { useRef, useState } from 'react';
import { Upload, Loader2 } from 'lucide-react';
import { api } from '@/lib/api/client';

interface UploadButtonProps {
  /** Called after at least one successful upload so the surface can refresh. */
  onUploaded?: (workspacePath: string) => void;
}

// ADR-331 D5: .zip accepted as a transport envelope (expanded server-side).
const ACCEPT = '.pdf,.docx,.txt,.md,.zip';

export function UploadButton({ onUploaded }: UploadButtonProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const onPick = () => inputRef.current?.click();

  const onChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files ?? []);
    // Reset the input so the same file(s) can be re-picked after an error.
    e.target.value = '';
    if (files.length === 0) return;
    setBusy(true);
    setError(null);
    try {
      const res = await api.documents.upload(files);
      const firstOk = res.results.find((r) => r.success && r.workspace_path);
      if (firstOk?.workspace_path) onUploaded?.(firstOk.workspace_path);
      if (res.failed > 0) {
        // Surface per-file failures without hiding the partial success.
        const firstErr = res.results.find((r) => !r.success);
        const detail = firstErr ? `${firstErr.filename}: ${firstErr.error}` : 'some files failed';
        setError(
          res.succeeded > 0
            ? `${res.succeeded} added, ${res.failed} failed (${detail})`
            : detail,
        );
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed');
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="flex items-center gap-2">
      <input
        ref={inputRef}
        type="file"
        accept={ACCEPT}
        multiple
        onChange={onChange}
        className="hidden"
      />
      <button
        onClick={onPick}
        disabled={busy}
        title="Add files (PDF, DOCX, TXT, MD, or a .zip)"
        className="inline-flex items-center gap-1.5 rounded-md border border-border bg-background px-2.5 py-1.5 text-xs font-medium text-foreground hover:bg-muted transition-colors disabled:opacity-50"
      >
        {busy ? (
          <Loader2 className="w-3.5 h-3.5 animate-spin" />
        ) : (
          <Upload className="w-3.5 h-3.5" />
        )}
        {busy ? 'Adding…' : 'Add files'}
      </button>
      {error && <span className="text-[11px] text-destructive truncate max-w-[200px]" title={error}>{error}</span>}
    </div>
  );
}
