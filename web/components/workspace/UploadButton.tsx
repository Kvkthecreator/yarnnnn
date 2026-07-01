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
 * 2026-07-01 (operator-observed KVK): the bare inline button opened the OS
 * file picker directly and never told the operator WHERE the files land. It is
 * now a MODAL (matches the GetInfoModal / SetupConfirmModal shell — the project
 * has no shared Dialog primitive) that states the destination up front: every
 * upload lands in the Uploads/ root (/workspace/uploads/), the operator's raw
 * source-material lane (ADR-320 topology, the human case of the ADR-376 intake
 * lane). The destination is fixed — Uploads/ is the single canonical home for
 * operator-contributed files; the modal makes that legible instead of silent.
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

import { useEffect, useRef, useState } from 'react';
import { Upload, Loader2, X, ArrowDownToLine, FileText } from 'lucide-react';
import { api } from '@/lib/api/client';

interface UploadButtonProps {
  /**
   * Called after at least one successful upload so the surface can refresh AND
   * navigate to the new file. May be async (the modal awaits it before closing,
   * keeping the "Adding…" state up through the tree refresh + selection).
   */
  onUploaded?: (workspacePath: string) => void | Promise<void>;
}

// ADR-331 D5: .zip accepted as a transport envelope (expanded server-side).
const ACCEPT = '.pdf,.docx,.txt,.md,.zip';

export function UploadButton({ onUploaded }: UploadButtonProps) {
  const [open, setOpen] = useState(false);

  return (
    <>
      <button
        onClick={() => setOpen(true)}
        title="Add files (PDF, DOCX, TXT, MD, or a .zip)"
        className="inline-flex items-center gap-1.5 rounded-md border border-border bg-background px-2.5 py-1.5 text-xs font-medium text-foreground hover:bg-muted transition-colors"
      >
        <Upload className="w-3.5 h-3.5" />
        Add files
      </button>
      {open && (
        <UploadModal
          onClose={() => setOpen(false)}
          onUploaded={onUploaded}
        />
      )}
    </>
  );
}

function UploadModal({
  onClose,
  onUploaded,
}: {
  onClose: () => void;
  onUploaded?: (workspacePath: string) => void | Promise<void>;
}) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [picked, setPicked] = useState<File[]>([]);
  const [dragOver, setDragOver] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && !busy) onClose();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [busy, onClose]);

  const addFiles = (files: File[]) => {
    if (files.length === 0) return;
    setError(null);
    setNotice(null);
    // Append (dedupe by name+size) so a second browse/drop adds to the batch.
    setPicked((prev) => {
      const seen = new Set(prev.map((f) => `${f.name}:${f.size}`));
      return [...prev, ...files.filter((f) => !seen.has(`${f.name}:${f.size}`))];
    });
  };

  const onBrowseChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    addFiles(Array.from(e.target.files ?? []));
    e.target.value = ''; // allow re-picking the same file after removal
  };

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    addFiles(Array.from(e.dataTransfer.files ?? []));
  };

  const removeAt = (idx: number) =>
    setPicked((prev) => prev.filter((_, i) => i !== idx));

  const handleUpload = async () => {
    if (picked.length === 0 || busy) return;
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      const res = await api.documents.upload(picked);
      const firstOk = res.results.find((r) => r.success && r.workspace_path);
      if (res.failed > 0) {
        const firstErr = res.results.find((r) => !r.success);
        const detail = firstErr ? `${firstErr.filename}: ${firstErr.error}` : 'some files failed';
        if (res.succeeded > 0) {
          // Partial success — keep the modal open, report both sides. Still let
          // the surface refresh + jump to the first file that DID land.
          if (firstOk?.workspace_path) await onUploaded?.(firstOk.workspace_path);
          setNotice(`${res.succeeded} added to Uploads/`);
          setError(`${res.failed} failed (${detail})`);
          setPicked([]);
        } else {
          setError(detail);
        }
      } else {
        // Full success — hand off to the surface (refresh tree + select the new
        // file under Uploads/), THEN close. onUploaded may be async; awaiting it
        // keeps the "Adding…" state up through processing so the modal doesn't
        // vanish onto a stale-looking tree.
        if (firstOk?.workspace_path) await onUploaded?.(firstOk.workspace_path);
        onClose();
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed');
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/50" onClick={() => !busy && onClose()} />
      <div className="relative z-10 mx-4 w-full max-w-md overflow-hidden rounded-lg border border-border bg-background shadow-lg">
        <div className="flex items-center justify-between border-b border-border px-4 py-3">
          <h2 className="text-sm font-semibold">Add files</h2>
          <button
            type="button"
            onClick={() => !busy && onClose()}
            disabled={busy}
            className="rounded p-1 text-muted-foreground hover:bg-muted hover:text-foreground disabled:opacity-50"
            aria-label="Close"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="space-y-3 p-4">
          {/* Destination — stated up front. Uploads/ is the fixed home for all
              operator-contributed files (ADR-320 topology). */}
          <div className="flex items-start gap-2 rounded-md border border-border bg-muted/30 px-3 py-2 text-xs">
            <ArrowDownToLine className="mt-0.5 h-4 w-4 shrink-0 text-emerald-600" />
            <div className="min-w-0">
              <p className="font-medium text-foreground">
                Lands in <span className="font-mono">Uploads/</span>
              </p>
              <p className="text-muted-foreground">
                Your raw source material. Files are indexed so agents can read
                them; nothing is published anywhere.
              </p>
            </div>
          </div>

          {/* Drop zone / browse */}
          <input
            ref={inputRef}
            type="file"
            accept={ACCEPT}
            multiple
            onChange={onBrowseChange}
            className="hidden"
          />
          <button
            type="button"
            onClick={() => inputRef.current?.click()}
            onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
            onDragLeave={() => setDragOver(false)}
            onDrop={onDrop}
            className={`flex w-full flex-col items-center justify-center gap-1.5 rounded-md border-2 border-dashed px-4 py-6 text-center transition-colors ${
              dragOver
                ? 'border-primary bg-primary/5'
                : 'border-border hover:border-muted-foreground/40 hover:bg-muted/30'
            }`}
          >
            <Upload className="h-5 w-5 text-muted-foreground" />
            <span className="text-sm text-foreground">
              Drop files here or <span className="font-medium underline">browse</span>
            </span>
            <span className="text-[11px] text-muted-foreground">
              PDF · DOCX · TXT · MD · ZIP
            </span>
          </button>

          {/* Selected files */}
          {picked.length > 0 && (
            <ul className="max-h-40 space-y-1 overflow-y-auto">
              {picked.map((f, idx) => (
                <li
                  key={`${f.name}:${f.size}:${idx}`}
                  className="flex items-center gap-2 rounded-md border border-border px-2 py-1.5 text-xs"
                >
                  <FileText className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
                  <span className="min-w-0 flex-1 truncate text-foreground">{f.name}</span>
                  {!busy && (
                    <button
                      type="button"
                      onClick={() => removeAt(idx)}
                      className="rounded p-0.5 text-muted-foreground hover:bg-muted hover:text-foreground"
                      aria-label={`Remove ${f.name}`}
                    >
                      <X className="h-3 w-3" />
                    </button>
                  )}
                </li>
              ))}
            </ul>
          )}

          {notice && <p className="text-[11px] text-emerald-600">{notice}</p>}
          {error && <p className="text-[11px] text-destructive">{error}</p>}
        </div>

        <div className="flex items-center justify-end gap-2 border-t border-border px-4 py-3">
          <button
            type="button"
            onClick={() => !busy && onClose()}
            disabled={busy}
            className="rounded-md px-3 py-1.5 text-xs font-medium text-muted-foreground hover:bg-muted disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={handleUpload}
            disabled={busy || picked.length === 0}
            className="inline-flex items-center gap-1.5 rounded-md bg-primary px-3 py-1.5 text-xs font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
          >
            {busy ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <ArrowDownToLine className="h-3.5 w-3.5" />}
            {busy
              ? 'Adding…'
              : picked.length > 0
                ? `Add ${picked.length} to Uploads/`
                : 'Add to Uploads/'}
          </button>
        </div>
      </div>
    </div>
  );
}
