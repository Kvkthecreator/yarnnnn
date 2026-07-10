'use client';

/**
 * StudioSurface — the first authoring app (ADR-440).
 *
 * One surface ↔ one operator act: AUTHOR AN ARTIFACT — the first honest DP29
 * composition since ADR-435 deleted Home. Two states:
 *
 *  - No `studio.file` param → the START state: pick a template (Document ·
 *    Deck · Article), name it, place it (meaning-placed under operation/ —
 *    the Studio owns no namespace, D6), or open an existing artifact.
 *  - `studio.file` set → the WORKBENCH: a BOUND lane (left — full ADR-411
 *    machinery via LanePanel; its turns carry the authoring posture) + the
 *    live canvas (right — sandboxed projection) + the outline rail.
 *
 * Mutation is single-path (ADR-236): the lane writes, the canvas renders.
 * The lane's `onArtifactWrite` bumps `reloadKey` when the bound artifact
 * lands a write, so the member watches the document change as the lane works.
 */

import { useCallback, useEffect, useMemo, useState } from 'react';
import { ExternalLink, Loader2, Palette, Plus } from 'lucide-react';
import { api } from '@/lib/api/client';
import { useSurfaceParam } from '@/lib/shell/useSurfacePreferences';
import { useFileLoad } from '@/components/workspace/useFileLoad';
import { LanePanel } from '@/components/chat-surface/LanePanel';
import { SurfaceLink } from '@/components/shell/SurfaceLink';
import { StudioCanvas, type PointerEvent2 } from './StudioCanvas';
import { StudioInsertMenu } from './StudioInsertMenu';

interface LaneInfo {
  id: string;
  name: string;
  model: string;
  artifact_path?: string | null;
  status: string;
}

interface TemplateInfo {
  slug: string;
  label: string;
  description: string;
}

/** Strip the /workspace/ prefix for display + comparison. */
function relPath(p: string): string {
  return p.replace(/^\/workspace\//, '');
}

function baseName(p: string): string {
  const parts = p.split('/');
  return parts[parts.length - 1] || p;
}

/** The artifact's declared template (data-template root attr). */
function extractTemplate(html: string): string {
  const m = /data-template="([a-z-]+)"/.exec(html);
  return m?.[1] ?? 'document';
}

/** Starter prompts per template — clickable chips while the lane is empty.
 *  Plain words, no model-speak: they teach what the Studio DOES. */
const TEMPLATE_SUGGESTIONS: Record<string, string[]> = {
  document: [
    'Draft this document from these points: ',
    'Add a section on ',
    'Tighten the wording throughout — keep the structure',
  ],
  deck: [
    'Draft a 6-slide deck that argues: ',
    'Rewrite the title slide to lead with the strongest number',
    'Add a slide that shows the table from a workspace file',
  ],
  article: [
    'Draft this article from my rough notes: ',
    'Give it a sharper title and subtitle',
    'Add a closing section with a call to action',
  ],
};

/** Headings (h1/h2) in document order — the artifact's outline (rail). */
function extractOutline(html: string): Array<{ level: number; text: string }> {
  const out: Array<{ level: number; text: string }> = [];
  const re = /<h([12])[^>]*>([\s\S]*?)<\/h\1>/gi;
  let m: RegExpExecArray | null;
  while ((m = re.exec(html)) && out.length < 32) {
    const text = m[2].replace(/<[^>]+>/g, '').trim();
    if (text) out.push({ level: Number(m[1]), text });
  }
  return out;
}

function slugify(name: string): string {
  return name
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 48) || 'untitled';
}

export function StudioSurface() {
  const { get: getParam, set: setParam } = useSurfaceParam('studio');
  const artifactParam = getParam('file');
  const artifactPath = artifactParam
    ? artifactParam.startsWith('/')
      ? artifactParam
      : `/workspace/${artifactParam}`
    : null;

  // ── Lane environment (models + existing lanes) ─────────────────────────
  const [lanesEnabled, setLanesEnabled] = useState<boolean | null>(null);
  const [models, setModels] = useState<Array<{ id: string; label: string }>>([]);
  const [lanes, setLanes] = useState<LaneInfo[]>([]);
  const [laneError, setLaneError] = useState<string | null>(null);

  const refreshLanes = useCallback(async () => {
    try {
      const res = await api.lanes.list();
      setLanesEnabled(res.enabled);
      setModels(res.models);
      setLanes(res.lanes as LaneInfo[]);
    } catch {
      setLanesEnabled(false);
      setLaneError('Could not load lanes.');
    }
  }, []);

  useEffect(() => {
    void refreshLanes();
  }, [refreshLanes]);

  // ── The bound lane for the open artifact (find-or-create) ──────────────
  const boundLane = useMemo(() => {
    if (!artifactPath) return null;
    return (
      lanes.find(
        (l) =>
          l.status === 'active' &&
          l.artifact_path &&
          relPath(l.artifact_path.startsWith('/') ? l.artifact_path : `/workspace/${l.artifact_path}`) ===
            relPath(artifactPath),
      ) ?? null
    );
  }, [lanes, artifactPath]);

  const [creatingLane, setCreatingLane] = useState(false);
  useEffect(() => {
    if (!artifactPath || !lanesEnabled || boundLane || creatingLane || !models.length) return;
    setCreatingLane(true);
    api.lanes
      .create({
        name: baseName(artifactPath),
        model: models[0].id,
        artifact_path: artifactPath,
      })
      .then(() => refreshLanes())
      .catch(() => setLaneError('Could not create the authoring lane.'))
      .finally(() => setCreatingLane(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [artifactPath, lanesEnabled, boundLane, models.length]);

  // ── The artifact itself (the surface owns the load; canvas projects) ───
  const [reloadKey, setReloadKey] = useState(0);
  const { file, loading, notFound } = useFileLoad(artifactPath ?? '', { reloadKey });

  const onArtifactWrite = useCallback(
    (writtenPath: string) => {
      if (!artifactPath) return;
      if (relPath(writtenPath) === relPath(artifactPath)) {
        setReloadKey((k) => k + 1);
      }
    },
    [artifactPath],
  );

  // ── Composer seeding (v1.1): pointing + the insert menu ────────────────
  const [seed, setSeed] = useState<{ text: string; nonce: number } | null>(null);
  const seedComposer = useCallback(
    (text: string) => setSeed((s) => ({ text, nonce: (s?.nonce ?? 0) + 1 })),
    [],
  );
  const onPoint = useCallback(
    (p: PointerEvent2) => {
      seedComposer(
        p.dataRef
          ? `Pointing at the cited object "${p.dataRef}" — `
          : `Pointing at the ${p.tag}${p.text ? ` "${p.text}"` : ''} — `,
      );
    },
    [seedComposer],
  );

  const outline = useMemo(() => extractOutline(file?.content ?? ''), [file]);
  const template = useMemo(() => extractTemplate(file?.content ?? ''), [file]);
  const modelLabel = useMemo(
    () => models.find((m) => m.id === boundLane?.model)?.label ?? boundLane?.model ?? '',
    [models, boundLane],
  );

  // ── START STATE ─────────────────────────────────────────────────────────
  if (!artifactPath) {
    return (
      <StudioStart
        onOpen={(path) => setParam({ file: relPath(path) })}
      />
    );
  }

  // ── WORKBENCH ───────────────────────────────────────────────────────────
  return (
    <div className="flex h-full min-h-0 flex-col">
      {/* Header — the artifact's nameplate; frame belongs to the mount. */}
      <div className="flex items-center justify-between border-b border-border px-4 py-2">
        <div className="flex min-w-0 items-center gap-2">
          <Palette className="h-4 w-4 shrink-0 text-muted-foreground" />
          <span className="truncate text-sm font-medium">{baseName(artifactPath)}</span>
          <span className="truncate text-xs text-muted-foreground">{relPath(artifactPath)}</span>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          <SurfaceLink
            to="files"
            params={{ path: artifactPath }}
            className="inline-flex items-center gap-1 rounded-md border border-border px-2 py-1 text-[11px] text-muted-foreground hover:bg-muted/40 hover:text-foreground"
          >
            <ExternalLink className="h-3 w-3" />
            Open in Files
          </SurfaceLink>
          <button
            type="button"
            onClick={() => setParam({ file: null })}
            className="rounded-md border border-border px-2 py-1 text-[11px] text-muted-foreground hover:bg-muted/40 hover:text-foreground"
          >
            New / open…
          </button>
        </div>
      </div>

      <div className="flex min-h-0 flex-1">
        {/* Left — the bound lane (the mind; the single write path). */}
        <div className="flex w-[380px] shrink-0 flex-col border-r border-border">
          {lanesEnabled === false ? (
            <div className="flex flex-1 items-center justify-center p-6 text-center text-sm text-muted-foreground">
              Lanes are not enabled on this deployment — the Studio's authoring
              chat needs the model router. The canvas still renders the artifact.
            </div>
          ) : boundLane ? (
            <>
              <StudioInsertMenu onSeed={seedComposer} />
              <LanePanel
                key={boundLane.id}
                laneId={boundLane.id}
                laneName={boundLane.name}
                modelLabel={modelLabel}
                onArtifactWrite={onArtifactWrite}
                composerSeed={seed}
                emptyState={
                <div className="space-y-2 text-center text-xs text-muted-foreground">
                  <p className="text-sm font-medium text-foreground/80">
                    Tell it what to write.
                  </p>
                  <p>
                    Ask in plain words — every reply becomes an edit to{' '}
                    <span className="font-medium text-foreground/70">{baseName(artifactPath)}</span>,
                    and the page on the right updates as it works. It can also
                    pull in your workspace files — images, tables, notes — as
                    live references.
                  </p>
                </div>
              }
              suggestions={TEMPLATE_SUGGESTIONS[template] ?? TEMPLATE_SUGGESTIONS.document}
              />
            </>
          ) : (
            <div className="flex flex-1 items-center justify-center gap-2 text-sm text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" />
              {laneError ?? 'Preparing the authoring lane…'}
            </div>
          )}
        </div>

        {/* Right — the canvas (renders, never edits) + the outline rail. */}
        <div className="flex min-w-0 flex-1">
          <div className="flex min-w-0 flex-1 flex-col">
            {loading ? (
              <div className="flex flex-1 items-center justify-center text-muted-foreground">
                <Loader2 className="h-5 w-5 animate-spin" />
              </div>
            ) : notFound || !file ? (
              <div className="flex flex-1 items-center justify-center p-6 text-center text-sm text-muted-foreground">
                This artifact does not exist yet — ask the lane to create it at{' '}
                {relPath(artifactPath)}.
              </div>
            ) : (
              <StudioCanvas
                file={file}
                artifactPath={artifactPath}
                onPoint={onPoint}
              />
            )}
          </div>
          {outline.length > 1 && (
            <div className="w-52 shrink-0 overflow-y-auto border-l border-border p-3">
              <p className="mb-2 text-[10px] font-medium uppercase tracking-wide text-muted-foreground">
                Outline
              </p>
              <ul className="space-y-1">
                {outline.map((h, i) => (
                  <li
                    key={i}
                    className={`truncate text-xs ${h.level === 1 ? 'font-medium' : 'pl-3 text-muted-foreground'}`}
                    title={h.text}
                  >
                    {h.text}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ── The start state — template picker + meaning-placed creation ──────────

function StudioStart({ onOpen }: { onOpen: (path: string) => void }) {
  const [templates, setTemplates] = useState<TemplateInfo[]>([]);
  const [recents, setRecents] = useState<
    Array<{ path: string; updated_at: string | null; summary: string | null }>
  >([]);
  const [selected, setSelected] = useState<string>('document');
  const [name, setName] = useState('');
  const [pathEdited, setPathEdited] = useState(false);
  const [path, setPath] = useState('');
  const [existing, setExisting] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.studio
      .templates()
      .then((res) => setTemplates(res.templates))
      .catch(() => setError('Could not load templates.'));
    api.studio
      .artifacts()
      .then((res) => setRecents(res.artifacts))
      .catch(() => {
        /* recents are a convenience — creation still works without them */
      });
  }, []);

  // Meaning-placed default (D6): under operation/, named by the work — the
  // member edits freely; the Studio never invents an app-named root.
  useEffect(() => {
    if (pathEdited) return;
    const slug = slugify(name);
    setPath(name ? `operation/${slug}/${selected}.html` : '');
  }, [name, selected, pathEdited]);

  const create = async () => {
    if (!path || busy) return;
    setBusy(true);
    setError(null);
    try {
      const res = await api.studio.createArtifact(path, selected);
      onOpen(res.path);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Creation failed.');
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="flex h-full items-center justify-center overflow-y-auto p-8">
      <div className="w-full max-w-lg space-y-6">
        <div className="space-y-1 text-center">
          <Palette className="mx-auto h-8 w-8 text-muted-foreground" />
          <h1 className="text-lg font-semibold">Studio</h1>
          <p className="text-sm text-muted-foreground">
            Pick a shape, name it, then describe what you want in plain words.
            The Studio writes it as a real document in your workspace — you
            watch it take shape live, and it can pull in your files, images,
            and data as it goes.
          </p>
        </div>

        <div className="grid grid-cols-3 gap-2">
          {templates.map((t) => (
            <button
              key={t.slug}
              type="button"
              onClick={() => setSelected(t.slug)}
              className={`rounded-lg border p-3 text-left transition-colors ${
                selected === t.slug
                  ? 'border-foreground/60 bg-muted/40'
                  : 'border-border hover:bg-muted/20'
              }`}
            >
              <p className="text-sm font-medium">{t.label}</p>
              <p className="mt-1 text-[11px] leading-snug text-muted-foreground">
                {t.description}
              </p>
            </button>
          ))}
        </div>

        <div className="space-y-2">
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Name it (e.g. IR deck v3)"
            className="w-full rounded-md border border-border bg-transparent px-3 py-2 text-sm outline-none focus:border-foreground/40"
          />
          <input
            value={path}
            onChange={(e) => {
              setPathEdited(true);
              setPath(e.target.value);
            }}
            placeholder="operation/…/artifact.html (meaning-placed)"
            className="w-full rounded-md border border-border bg-transparent px-3 py-2 font-mono text-xs outline-none focus:border-foreground/40"
          />
          <button
            type="button"
            onClick={create}
            disabled={!path || busy}
            className="inline-flex w-full items-center justify-center gap-2 rounded-md bg-foreground px-3 py-2 text-sm font-medium text-background disabled:opacity-40"
          >
            {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
            Create
          </button>
        </div>

        {recents.length > 0 && (
          <div className="space-y-2 border-t border-border pt-4">
            <p className="text-[10px] font-medium uppercase tracking-wide text-muted-foreground">
              Continue where you left off
            </p>
            <ul className="space-y-1">
              {recents.slice(0, 6).map((r) => (
                <li key={r.path}>
                  <button
                    type="button"
                    onClick={() => onOpen(r.path)}
                    className="flex w-full items-center justify-between gap-3 rounded-md border border-border px-3 py-2 text-left transition-colors hover:bg-muted/30"
                  >
                    <span className="min-w-0">
                      <span className="block truncate text-sm">{baseName(r.path)}</span>
                      <span className="block truncate text-[11px] text-muted-foreground">
                        {relPath(r.path)}
                      </span>
                    </span>
                    {r.updated_at && (
                      <span className="shrink-0 text-[10px] text-muted-foreground">
                        {new Date(r.updated_at).toLocaleDateString()}
                      </span>
                    )}
                  </button>
                </li>
              ))}
            </ul>
          </div>
        )}

        <details className="border-t border-border pt-3">
          <summary className="cursor-pointer text-xs text-muted-foreground">
            Open by workspace path…
          </summary>
          <div className="mt-2 flex gap-2">
            <input
              value={existing}
              onChange={(e) => setExisting(e.target.value)}
              placeholder="operation/…/deck.html"
              className="flex-1 rounded-md border border-border bg-transparent px-3 py-2 font-mono text-xs outline-none focus:border-foreground/40"
            />
            <button
              type="button"
              onClick={() => existing.trim() && onOpen(existing.trim())}
              disabled={!existing.trim()}
              className="rounded-md border border-border px-3 py-2 text-sm disabled:opacity-40"
            >
              Open
            </button>
          </div>
        </details>

        {error && <p className="text-center text-xs text-red-500">{error}</p>}
      </div>
    </div>
  );
}
