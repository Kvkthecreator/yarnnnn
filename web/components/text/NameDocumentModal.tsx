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
import { useTranslations } from 'next-intl';
import { Loader2 } from 'lucide-react';
import { api } from '@/lib/api/client';
import { WorkspacePickerModal } from '@/components/workspace/WorkspacePicker';
import { slugify, STUDIO_ARTIFACT_REGION } from '@/components/authoring/artifactNaming';
import { isSubmitKey } from '@/lib/shell/submit-key';

/** The default destination — the Documents home.
 *
 * ⚠️ The SUBSTRATE path (`operation/`), not the told-name. This was the literal
 * string 'Documents', which the picker never corrects because it only reports a
 * folder the member actually clicks — so an untouched default composed
 * `/workspace/Documents/<slug>.md` and created a PHANTOM ROOT beside the real
 * home. Two such files exist on production (`adr575-canvas-clickpass.md`,
 * `adr572-click-pass.md`), invisible to anything that walks `operation/`.
 *
 * `HOME_ALIASES` resolves told-names at `parse_file_reference`, but the
 * `PATCH /api/workspace/file` door this modal writes through does not run that
 * pass — so the told-name must never reach a composed path. The display stays
 * "Documents" via the picker's own `display_name`, exactly as the artifact
 * dialog does it (ADR-588). */
const DEFAULT_FOLDER = STUDIO_ARTIFACT_REGION.replace(/^\/workspace\//, '').replace(/\/+$/, '');

/** The operator-facing name of that home — display only, never a path. */
const DOCUMENTS_LABEL = 'Documents';

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
  const t = useTranslations('text.name');
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

  // The ONE slugifier (2026-09-21). This was a third, hand-rolled copy that
  // differed from the canon in a way ADR-469 had already fixed elsewhere: with
  // no NFKD fold, `Café notes` became `caf-notes` — the accented letter deleted
  // rather than folded to its base. `slugify` mirrors
  // `services/naming.py::path_slug` (fold, lowercase, 48-char cap) and is
  // already shared with the Studio's create door, so the two cannot drift.
  //
  // A name with no Latin characters still yields `untitled`, by design: the
  // path slug is an ASCII KEY, not the name. What the member typed is carried
  // verbatim into the H1 below, and the server disambiguates `untitled-2`,
  // `untitled-3`, … so a member working entirely in Korean gets distinct files
  // that each read back as the name they chose (naming.py::disambiguate).
  const slug = slugify(name.trim());

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
      const msg = e instanceof Error ? e.message : t('failed');
      setError(msg);
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 p-4">
        <div className="w-full max-w-md rounded-lg border border-border bg-background p-5 shadow-lg">
          <h2 className="text-base font-semibold">{t('heading')}</h2>
          <p className="mt-1 text-xs text-muted-foreground">
            {t('lede')}
          </p>

          <label className="mt-4 block text-xs font-medium text-muted-foreground">
            {t('nameLabel')}
          </label>
          <input
            autoFocus
            value={name}
            onChange={(e) => setName(e.target.value)}
            onKeyDown={(e) => {
              if (isSubmitKey(e, { allowShift: true })) void create();
              if (e.key === 'Escape') onClose();
            }}
            placeholder={t('namePlaceholder')}
            className="mt-1 w-full rounded-md border border-border bg-background px-3 py-2 text-sm outline-none focus:border-foreground/30"
          />

          <label className="mt-3 block text-xs font-medium text-muted-foreground">
            {t('whereLabel')}
          </label>
          <div className="mt-1 flex items-center gap-2">
            <span className="min-w-0 flex-1 truncate rounded-md border border-border bg-muted/20 px-3 py-2 font-mono text-xs">
              {folder === DEFAULT_FOLDER ? DOCUMENTS_LABEL : folder}/{slug || 'untitled'}.md
            </span>
            <button
              type="button"
              onClick={() => setPickingFolder(true)}
              className="shrink-0 rounded-md border border-border px-2.5 py-2 text-xs text-muted-foreground hover:bg-muted/40 hover:text-foreground"
            >
              {t('change')}
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
              {t('cancel')}
            </button>
            <button
              type="button"
              onClick={() => void create()}
              disabled={busy || !name.trim()}
              className="inline-flex items-center gap-1.5 rounded-md bg-foreground px-3 py-1.5 text-sm text-background disabled:opacity-50"
            >
              {busy && <Loader2 className="h-3 w-3 animate-spin" />}
              {t('create')}
            </button>
          </div>
        </div>
      </div>

      <WorkspacePickerModal
        open={pickingFolder}
        mode="folder"
        title={t('pickerTitle')}
        subtitle={t('pickerSubtitle')}
        confirmLabel={t('pickerConfirm')}
        emptyMessage={t('pickerEmpty')}
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
