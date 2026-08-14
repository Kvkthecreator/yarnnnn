'use client';

/**
 * NameDocumentModal — Text's create dialog (ADR-571).
 *
 * The ONE create gesture, mirroring Docs' naming dialog: the member types
 * what the document IS and picks where it goes; the leaf is slugified from
 * the name (ADR-459 — the name is the member's, the encoding is ours).
 *
 * The write goes through the SAME member door every save uses (ADR-570 D4),
 * so creation and editing answer to one gate: no second write path, and a
 * placement the door would refuse fails HERE, visibly, rather than after.
 */

import { useEffect, useState } from 'react';
import { Loader2 } from 'lucide-react';
import { api } from '@/lib/api/client';
import { WorkspacePickerModal } from '@/components/workspace/WorkspacePicker';

const DEFAULT_FOLDER = 'Documents';

export function NameDocumentModal({
  open,
  onClose,
  onCreated,
  onError,
}: {
  open: boolean;
  onClose: () => void;
  onCreated: (path: string) => void;
  onError?: (message: string | null) => void;
}) {
  const [name, setName] = useState('');
  const [folder, setFolder] = useState(DEFAULT_FOLDER);
  const [pickingFolder, setPickingFolder] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    setName('');
    setFolder(DEFAULT_FOLDER);
    setError(null);
  }, [open]);

  if (!open) return null;

  const slug = name.trim().toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');

  const create = async () => {
    const typed = name.trim();
    if (!typed || busy) return;
    setBusy(true);
    setError(null);
    const path = `/workspace/${folder.replace(/^\/+|\/+$/g, '')}/${slug || 'untitled'}.md`;
    try {
      // The document is born with its own name as the H1 — the member typed
      // it once; retyping it into the body would be the ceremony Docs avoids.
      await api.workspace.editFile(path, `# ${typed}\n\n`, undefined, `create ${slug}.md`);
      onError?.(null);
      onCreated(path);
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'Could not create the document.';
      setError(msg);
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 p-4">
        <div className="w-full max-w-md rounded-lg border border-border bg-background p-5 shadow-lg">
          <h2 className="text-base font-semibold">New document</h2>
          <p className="mt-1 text-xs text-muted-foreground">
            Name it for what it is — the file takes a matching name.
          </p>

          <label className="mt-4 block text-xs font-medium text-muted-foreground">
            Name
          </label>
          <input
            autoFocus
            value={name}
            onChange={(e) => setName(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') void create();
              if (e.key === 'Escape') onClose();
            }}
            placeholder="Founder intro transcript"
            className="mt-1 w-full rounded-md border border-border bg-background px-3 py-2 text-sm outline-none focus:border-foreground/30"
          />

          <label className="mt-3 block text-xs font-medium text-muted-foreground">
            Where
          </label>
          <div className="mt-1 flex items-center gap-2">
            <span className="min-w-0 flex-1 truncate rounded-md border border-border bg-muted/20 px-3 py-2 font-mono text-xs">
              {folder}/{slug || 'untitled'}.md
            </span>
            <button
              type="button"
              onClick={() => setPickingFolder(true)}
              className="shrink-0 rounded-md border border-border px-2.5 py-2 text-xs text-muted-foreground hover:bg-muted/40 hover:text-foreground"
            >
              Change…
            </button>
          </div>

          {error && <p className="mt-3 text-xs text-destructive">{error}</p>}

          <div className="mt-5 flex justify-end gap-2">
            <button
              type="button"
              onClick={onClose}
              disabled={busy}
              className="rounded-md border border-border px-3 py-1.5 text-sm text-muted-foreground hover:bg-muted/40 disabled:opacity-50"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={() => void create()}
              disabled={busy || !name.trim()}
              className="inline-flex items-center gap-1.5 rounded-md bg-foreground px-3 py-1.5 text-sm text-background disabled:opacity-50"
            >
              {busy && <Loader2 className="h-3 w-3 animate-spin" />}
              Create
            </button>
          </div>
        </div>
      </div>

      <WorkspacePickerModal
        open={pickingFolder}
        mode="folder"
        title="Choose a folder"
        subtitle="Where this document lives"
        confirmLabel="Choose"
        emptyMessage="No folders yet."
        selectable={(node) => node.type === 'folder'}
        onClose={() => setPickingFolder(false)}
        onConfirm={(path) => {
          setFolder(path.replace(/^\/workspace\//, '').replace(/^\/+|\/+$/g, '') || DEFAULT_FOLDER);
          setPickingFolder(false);
        }}
      />
    </>
  );
}
