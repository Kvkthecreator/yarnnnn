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
 * Drops the file through api.documents.upload → POST /api/documents/upload,
 * which extracts text → /workspace/uploads/{slug}.md via the Authored
 * Substrate (ADR-209, attributed operator) and auto-indexes (ADR-325 D6).
 * On success, calls onUploaded so the explorer re-fetches the tree.
 */

import { useRef, useState } from 'react';
import { Upload, Loader2 } from 'lucide-react';
import { api } from '@/lib/api/client';

interface UploadButtonProps {
  /** Called after a successful upload so the surface can refresh its tree. */
  onUploaded?: (workspacePath: string) => void;
}

const ACCEPT = '.pdf,.docx,.txt,.md';

export function UploadButton({ onUploaded }: UploadButtonProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const onPick = () => inputRef.current?.click();

  const onChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    // Reset the input so the same file can be re-picked after an error.
    e.target.value = '';
    if (!file) return;
    setBusy(true);
    setError(null);
    try {
      const res = await api.documents.upload(file);
      onUploaded?.(res.workspace_path);
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
        onChange={onChange}
        className="hidden"
      />
      <button
        onClick={onPick}
        disabled={busy}
        title="Add a file (PDF, DOCX, TXT, MD)"
        className="inline-flex items-center gap-1.5 rounded-md border border-border bg-background px-2.5 py-1.5 text-xs font-medium text-foreground hover:bg-muted transition-colors disabled:opacity-50"
      >
        {busy ? (
          <Loader2 className="w-3.5 h-3.5 animate-spin" />
        ) : (
          <Upload className="w-3.5 h-3.5" />
        )}
        {busy ? 'Adding…' : 'Add file'}
      </button>
      {error && <span className="text-[11px] text-destructive truncate max-w-[160px]" title={error}>{error}</span>}
    </div>
  );
}
