'use client';

/**
 * NewStandingWorkModal — the door (ADR-658 D4), opened from a pre-shaped start
 * (D7) or from scratch.
 *
 * A member names a piece of standing work in their own words: where it lives
 * (a folder — new or picked with the ONE tree picker), which file it keeps
 * (one plain name, md · csv · json · txt), when it runs (a schedule in the
 * workspace's clock), where its updates come from (a connection they already
 * hold, or a web page), and what the file must stay true to (the
 * instructions — the load-bearing half, refused when blank).
 *
 * ⚠️ THE DOOR COMPOSES NOTHING ITSELF. It posts the fields; the server's ONE
 * composer writes the YAML, the ONE parser checks it, and a refusal comes back
 * BY NAME (`detail.problem` + `detail.message`) so the member reads which rule
 * refused, never "invalid". Designation stays explicit (ADR-569 D1): the
 * member names the file; nothing here infers one.
 *
 * The connector list is what the server DERIVED from reach (the starts) —
 * never a hand-typed catalogue. A connector with no capture binding is not
 * offered, because the kernel could not read it.
 */

import { useEffect, useState } from 'react';
import { createPortal } from 'react-dom';
import { useTranslations } from 'next-intl';
import { Loader2 } from 'lucide-react';
import {
  APIError,
  api,
  type StandingSource,
  type StandingStart,
  type StandingSummary,
} from '@/lib/api/client';
import { WorkspacePickerModal } from '@/components/workspace/WorkspacePicker';
import { StartMark } from '@/components/supervisor/StartMark';
import {
  AddSource,
  MAX_SOURCES_PROSE,
  SourceRow,
  isStructured,
  nextSourceId,
} from '@/components/supervisor/SourceList';
import { Z_CONFIRM_BACKDROP, Z_CONFIRM_DIALOG } from '@/lib/shell/z-tiers';
import { useStandingWords } from '@/components/standing/StandingRow';

const FORMATS = ['md', 'csv', 'json', 'txt'];

/** The schedules a member sets from the door — each one a cron the kernel
 *  reads in the workspace's clock. "Custom" takes any cron.
 *
 *  ADR-660 — the rows hold catalog KEYS: this table is evaluated at import,
 *  before any member's language is known. */
const PRESETS: Array<{ labelKey: string; cron: string }> = [
  { labelKey: 'preset.weekdays9', cron: '0 9 * * 1-5' },
  { labelKey: 'preset.daily9', cron: '0 9 * * *' },
  { labelKey: 'preset.monday9', cron: '0 9 * * 1' },
  { labelKey: 'preset.hourly', cron: '0 * * * *' },
];

function slugify(s: string): string {
  return s.trim().toLowerCase().replace(/[^a-z0-9/]+/g, '-').replace(/^-|-$/g, '').replace(/\/+/g, '/');
}

/** The refusal the SERVER named (`detail.message`) — served, so it rides as
 *  it came. `fallback` is the client's own last resort, worded by the caller. */
function refusalMessage(e: unknown, fallback: string): string {
  if (e instanceof APIError) {
    const detail = (e.data as { detail?: unknown } | undefined)?.detail;
    if (detail && typeof detail === 'object' && 'message' in detail) {
      const m = (detail as { message?: unknown }).message;
      if (typeof m === 'string' && m) return m;
    }
  }
  return e instanceof Error ? e.message : fallback;
}

export function NewStandingWorkModal({
  open, start, starts, timezone, onClose, onCreated,
}: {
  open: boolean;
  start: StandingStart | null;
  starts: StandingStart[];
  timezone?: string | null;
  onClose: () => void;
  onCreated: (created: StandingSummary) => void;
}) {
  const t = useTranslations('supervisor');
  const { describeSchedule } = useStandingWords();
  const [folder, setFolder] = useState('');
  const [target, setTarget] = useState('');
  const [preset, setPreset] = useState<string>(PRESETS[0].cron);
  const [customCron, setCustomCron] = useState('');
  // ⭐ SOURCES ARE A LIST (am.5). The kernel takes up to 12 for a prose file
  // and groups connector slices per platform, so one brief may read several
  // Slack channels, a Notion page and a web page. This door used to write a
  // ONE-element array from three mutually-exclusive tabs, which made the ADR's
  // own worked example — "a brief of my team's channelS" — unbuildable.
  const [sources, setSources] = useState<StandingSource[]>([]);
  // ADR-659 D4 — a workspace path. The folders are what the workspace already
  // HAS (`getRoots`, filesystem-literal): offered, never asked for from memory.
  const [folders, setFolders] = useState<Array<{ path: string; label: string }>>([]);
  const [contract, setContract] = useState('');
  const [pickingFolder, setPickingFolder] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Re-open lands on the chosen start (pre-filled) or a blank door.
  // The folders this workspace actually has — read when the door opens, and
  // independent of everything else on it: an unreadable tree leaves the field
  // typable, never a broken door.
  useEffect(() => {
    if (!open) return;
    let live = true;
    api.workspace
      .getRoots()
      .then((roots) => {
        if (!live) return;
        setFolders(
          roots
            .filter((r) => r.exists && r.name !== 'system' && r.name !== 'agents')
            .map((r) => ({ path: `${r.name}/`, label: r.display_name || r.name })),
        );
      })
      .catch(() => { if (live) setFolders([]); });
    return () => { live = false; };
  }, [open]);

  useEffect(() => {
    if (!open) return;
    setError(null);
    setBusy(false);
    const s = start;
    setFolder(s?.suggested_folder ?? '');
    setTarget(s?.suggested_target ?? 'brief.md');
    const cron = s?.suggested_schedule ?? PRESETS[0].cron;
    if (PRESETS.some((p) => p.cron === cron)) {
      setPreset(cron);
      setCustomCron('');
    } else {
      setPreset('custom');
      setCustomCron(cron);
    }
    // ⭐ A CONNECTOR START SEEDS EVERY SLICE THE MEMBER ALREADY CHOSE, not the
    // first one. `selectors` is what they picked at the connection's aperture
    // in Reach — "the channels I care about" — and seeding `selectors[0]` was
    // the silent narrowing: they chose four channels, Reach said four, and the
    // brief read one. A structured target still takes exactly one (the server
    // rule), so the seed is capped to the first there.
    if (s?.kind === 'connector' && s.connector) {
      const ext = (s.suggested_target ?? '').split('.').pop()?.toLowerCase() ?? '';
      const picked = isStructured(ext) ? s.selectors.slice(0, 1) : s.selectors.slice(0, MAX_SOURCES_PROSE);
      const seeded: StandingSource[] = [];
      for (const sel of picked) {
        seeded.push({ id: nextSourceId(sel, seeded), connector: s.connector, selector: sel });
      }
      setSources(seeded);
    } else {
      setSources([]);
    }
    setContract(s?.contract_seed ?? '');
  }, [open, start]);

  // ⚠️ ESCAPE CLOSES — the house idiom on ~20 modals (FindConnectorModal,
  // RenameModal, ShareDialog…), and this door shipped without it, so the one
  // modal a member meets FIRST was the one that trapped them. It does not
  // close while the picker is open on top: Escape belongs to the topmost
  // surface, or a member dismissing the picker loses the half-filled form
  // behind it.
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key !== 'Escape' || pickingFolder || busy) return;
      e.stopPropagation();
      onClose();
    };
    window.addEventListener('keydown', onKey, true);
    return () => window.removeEventListener('keydown', onKey, true);
  }, [open, pickingFolder, busy, onClose]);

  if (!open) return null;

  const schedule = preset === 'custom' ? customCron.trim() : preset;
  const ext = target.includes('.') ? target.split('.').pop()!.toLowerCase() : '';
  const formatOk = FORMATS.includes(ext);
  const folderSlug = slugify(folder);
  // The server's rule, mirrored (`_classify_sources`): a structured target
  // maps EXACTLY ONE source to the leaf; prose takes 1..12.
  const structured = isStructured(ext);
  const maxSources = structured ? 1 : MAX_SOURCES_PROSE;
  const sourceOk = sources.length >= 1 && sources.length <= maxSources;
  const canCreate = Boolean(folderSlug && target.trim() && formatOk && schedule && sourceOk && contract.trim()) && !busy;

  /** What is still missing, named in the order the fields appear — so a member
   *  following it always moves forward instead of being sent back up. Empty
   *  once the door can post. */
  const blocker = !folderSlug
    ? t('newWork.blockedFolder')
    : !target.trim()
      ? t('newWork.blockedTarget')
      : !formatOk
        ? t('newWork.blockedFormat')
        : !schedule
          ? t('newWork.blockedSchedule')
          : sources.length === 0
            ? t('newWork.blockedSource')
            : sources.length > maxSources
              ? t('newWork.blockedTooMany', { max: maxSources })
            : !contract.trim()
              ? t('newWork.blockedInstructions')
              : '';

  const create = async () => {
    if (!canCreate) return;
    setBusy(true);
    setError(null);
    try {
      const created = await api.standing.create({
        folder: folderSlug,
        target: target.trim(),
        schedule,
        contract: contract.trim(),
        sources: sources.map((x) => ({
          id: x.id,
          ...(x.connector ? { connector: x.connector, selector: x.selector ?? undefined } : {}),
          ...(x.path ? { path: x.path } : {}),
          ...(x.url ? { url: x.url } : {}),
        })),
      });
      onCreated(created);
    } catch (e) {
      setError(refusalMessage(e, t('newWork.couldNotSetUp')));
    } finally {
      setBusy(false);
    }
  };

  const whenLabel = timezone && timezone !== 'UTC'
    ? t('newWork.whenLabelWithZone', { timezone })
    : t('newWork.whenLabel');

  return createPortal(
    <>
      {/* The house modal shape (ADR-452 v2's `NewArtifactModal`): a portal to
          `document.body` on the shared z-tiers, so the dialog cannot be
          clipped or out-stacked by whatever pane it was opened from. A bare
          `z-50` inside the pane's own stacking context is how a door ends up
          UNDER the thing that opened it. */}
      <div
        className="fixed inset-0 bg-black/50 animate-in fade-in duration-150"
        style={{ zIndex: Z_CONFIRM_BACKDROP }}
        onClick={() => { if (!busy) onClose(); }}
      />
      <div
        className="pointer-events-none fixed inset-0 flex items-center justify-center p-4"
        style={{ zIndex: Z_CONFIRM_DIALOG }}
      >
        <div
          role="dialog"
          aria-modal="true"
          aria-label={t('newWork.title')}
          className="pointer-events-auto flex max-h-[90vh] w-full max-w-lg flex-col overflow-hidden rounded-xl border border-border bg-background shadow-xl animate-in fade-in zoom-in-95 duration-150"
        >
          {/* The chosen start is NAMED and WEARS ITS BRAND here — a member who
              picked "Slack" on the previous step must see that this form is
              the Slack one, or the two steps read as unrelated screens. */}
          <div className="flex items-start gap-3 border-b border-border px-5 py-4">
            {start ? <StartMark start={start} className="mt-0.5" /> : null}
            <div className="min-w-0">
              <h2 className="text-base font-semibold">{start ? start.title : t('newWork.title')}</h2>
              <p className="mt-1 text-xs text-muted-foreground">
                {t('newWork.subtitle')}
              </p>
            </div>
          </div>

          <div className="flex-1 space-y-4 overflow-y-auto px-5 py-4">
            <div>
              <label className="block text-xs font-medium text-muted-foreground">{t('newWork.whereLabel')}</label>
              <div className="mt-1 flex items-center gap-2">
                <input
                  value={folder}
                  onChange={(e) => setFolder(e.target.value)}
                  placeholder={t('newWork.folderPlaceholder')}
                  className="min-w-0 flex-1 rounded-md border border-border bg-background px-3 py-2 text-sm outline-none focus:border-foreground/30"
                />
                <button
                  type="button"
                  onClick={() => setPickingFolder(true)}
                  className="shrink-0 rounded-md border border-border px-2.5 py-2 text-xs text-muted-foreground hover:bg-muted/40 hover:text-foreground"
                >
                  {t('newWork.choose')}
                </button>
              </div>
              <p className="mt-1 text-[11px] text-muted-foreground">
                {t('newWork.whereHint')}
              </p>
            </div>

            <div>
              <label className="block text-xs font-medium text-muted-foreground">{t('newWork.targetLabel')}</label>
              <input
                value={target}
                onChange={(e) => setTarget(e.target.value)}
                placeholder={t('newWork.targetPlaceholder')}
                className="mt-1 w-full rounded-md border border-border bg-background px-3 py-2 text-sm outline-none focus:border-foreground/30"
              />
              <p className="mt-1 text-[11px] text-muted-foreground">
                {target && !formatOk
                  ? t('newWork.formatBad')
                  : t('newWork.targetHint', {
                      folder: folderSlug || t('newWork.ellipsis'),
                      target: target || t('newWork.ellipsis'),
                    })}
              </p>
            </div>

            <div>
              <label className="block text-xs font-medium text-muted-foreground">{whenLabel}</label>
              <select
                value={preset}
                onChange={(e) => setPreset(e.target.value)}
                className="mt-1 w-full rounded-md border border-border bg-background px-3 py-2 text-sm outline-none focus:border-foreground/30"
              >
                {PRESETS.map((p) => (
                  <option key={p.cron} value={p.cron}>{t(p.labelKey)}</option>
                ))}
                <option value="custom">{t('newWork.custom')}</option>
              </select>
              {preset === 'custom' && (
                <input
                  value={customCron}
                  onChange={(e) => setCustomCron(e.target.value)}
                  placeholder={t('newWork.cronPlaceholder')}
                  className="mt-2 w-full rounded-md border border-border bg-background px-3 py-2 font-mono text-sm outline-none focus:border-foreground/30"
                />
              )}
              {preset === 'custom' && customCron.trim() && (
                <p className="mt-1 text-[11px] text-muted-foreground">{describeSchedule(customCron)}</p>
              )}
            </div>

            <div>
              <div className="flex items-baseline justify-between gap-3">
                <label className="block text-xs font-medium text-muted-foreground">{t('newWork.sourceLabel')}</label>
                {!structured && sources.length > 0 && (
                  <span className="text-[11px] text-muted-foreground">
                    {t('newWork.sourceCount', { count: sources.length, max: MAX_SOURCES_PROSE })}
                  </span>
                )}
              </div>
              {sources.length > 0 && (
                <ul className="mt-1.5 space-y-1.5">
                  {sources.map((src) => (
                    <SourceRow
                      key={src.id}
                      source={src}
                      starts={starts}
                      onRemove={() => setSources((xs) => xs.filter((x) => x.id !== src.id))}
                    />
                  ))}
                </ul>
              )}
              <div className="mt-2">
                <AddSource
                  starts={starts}
                  existing={sources}
                  folders={folders}
                  disabled={sources.length >= maxSources}
                  onAdd={(x) => setSources((xs) => [...xs, x])}
                />
              </div>
              {/* A structured target maps exactly ONE source to the leaf — the
                  server's rule, said before a refusal rather than after. */}
              {structured && sources.length >= 1 && (
                <p className="mt-1.5 text-[11px] text-muted-foreground">{t('newWork.oneSourceOnly')}</p>
              )}
            </div>

            <div>
              <label className="block text-xs font-medium text-muted-foreground">{t('newWork.instructionsLabel')}</label>
              <textarea
                value={contract}
                onChange={(e) => setContract(e.target.value)}
                rows={5}
                placeholder={t('newWork.instructionsPlaceholder')}
                className="mt-1 w-full resize-y rounded-md border border-border bg-background px-3 py-2 text-sm outline-none focus:border-foreground/30"
              />
              <p className="mt-1 text-[11px] text-muted-foreground">
                {t('newWork.instructionsHint')}
              </p>
            </div>

            {error && <p className="text-xs text-destructive">{error}</p>}
          </div>

          {/* ⚠️ A DISABLED BUTTON MUST SAY WHY. Start greys out when any of six
              fields is unfilled, and the door said nothing — a member looking
              at a full-looking form and a dead button has no way to learn that
              a Slack channel was never chosen in Reach. This names the FIRST
              thing still missing, in the order the fields appear, so following
              it always makes progress. */}
          <div className="flex items-center justify-between gap-3 border-t border-border px-5 py-3">
            <p className="min-w-0 flex-1 text-[11px] text-muted-foreground">
              {busy ? '' : blocker}
            </p>
            <div className="flex shrink-0 items-center gap-2">
            <button
              type="button"
              onClick={onClose}
              disabled={busy}
              className="rounded-md border border-border px-3 py-1.5 text-sm text-muted-foreground hover:bg-muted/40 disabled:opacity-50"
            >
              {t('newWork.cancel')}
            </button>
            <button
              type="button"
              onClick={() => void create()}
              disabled={!canCreate}
              className="inline-flex items-center gap-1.5 rounded-md bg-foreground px-3 py-1.5 text-sm text-background disabled:opacity-50"
            >
              {busy && <Loader2 className="h-3 w-3 animate-spin" />}
              {t('newWork.start')}
            </button>
            </div>
          </div>
        </div>
      </div>

      <WorkspacePickerModal
        open={pickingFolder}
        // Opened from this dialog, so it must dim and outrank it — without
        // this the form stays at full contrast behind the picker and the two
        // read as one layer (driven 2026-09-21).
        nested
        mode="folder"
        title={t('newWork.pickerTitle')}
        subtitle={t('newWork.pickerSubtitle')}
        confirmLabel={t('newWork.pickerConfirm')}
        emptyMessage={t('newWork.pickerEmpty')}
        selectable={(node) => node.type === 'folder'}
        onClose={() => setPickingFolder(false)}
        onConfirm={(path) => {
          setFolder(path.replace(/^\/workspace\//, '').replace(/^\/+|\/+$/g, ''));
          setPickingFolder(false);
        }}
      />
    </>,
    document.body,
  );
}
