/**
 * Type → Viewer Association — ADR-309 (the Applications register).
 *
 * This is the OS-native "which application opens this file type" layer —
 * macOS UTI + default-application binding; Unix MIME + xdg-open; the
 * thing ADR-222 named the "per-user customization layer" and marked
 * "Not yet built". ADR-309 makes it concrete.
 *
 * A userspace file has a *type* (derived from path + content-type). The
 * type binds to a viewer — the renderer that opens it. Every mount
 * dispatches through this single table; no mount re-implements type
 * detection. The Files surface (the Finder), the Recents view, the
 * Context surface, and the chat surface's artifact card all resolve here.
 *
 * ── THE THREE TIERS (the conformance fallback; ADR-245's L3/L2/L1) ─────
 *
 *   tier 1  path-exact  → a bespoke renderer for one known path. Today
 *                         this is the IDENTITY inference view, resolved by
 *                         `inferenceTarget()` inside `FileBody`, NOT here.
 *                         Named seam: when a path→component table becomes
 *                         warranted it belongs ABOVE this function, never
 *                         inside it. (`content-shapes/shapeForPath` is the
 *                         parser-side half of that tier and currently has
 *                         no consumer.)
 *   tier 2  type-exact  → this function's specific branches.
 *   tier 3  terminal    → `text` (the L1 raw view) for anything text-shaped,
 *                         `download` for anything else.
 *
 * The terminal is the escape hatch that makes an open type system safe: an
 * unknown type ALWAYS resolves to something. What it must never do is
 * resolve a 25 MB `.mp4` to `text` and paint the bytes — which is exactly
 * what the pre-2026-07-09 flat switch did (no video node, and `download`
 * was a hardcoded four-extension allowlist rather than a real terminal).
 *
 * ── THE TYPE IS DERIVED, NEVER TRUSTED (ADR-427 D5) ───────────────────
 *
 * `contentType` is a caller-supplied hint (`services/workspace.py:33`
 * defaults it to `text/markdown`). The path extension is the stronger
 * signal and is checked first. When ADR-427 D5 lands magic-byte sniffing
 * server-side, `contentType` becomes derived and this ordering can relax.
 * Until then: extension wins, MIME informs, and the terminal is COMPUTED
 * from text-ness rather than enumerated.
 *
 * Distinct from `web/lib/content-shapes/` (ADR-245 L2 parsers), which read
 * the *content* of specific governance files. That module answers "what
 * does this file mean"; this one answers "what opens it".
 */

import { APP_DESCRIPTORS } from '@/lib/apps/registry';

/**
 * The viewers a file type can bind to. Each value names the renderer that
 * `FileBody` mounts for that type.
 *
 *   - `markdown`  — prose renderer (governance docs, narrative reports)
 *   - `html`      — composed-artifact iframe (compose-pipeline output.html)
 *   - `image`     — image viewer (charts, favicons, generated assets)
 *   - `video`     — <video> player (ADR-420 lane-generated media)
 *   - `audio`     — <audio> player
 *   - `pdf`       — PDF viewer (exported reports)
 *   - `csv`       — tabular data preview
 *   - `text`      — plain-text raw view (yaml, json, txt, unknown text)
 *   - `download`  — the BINARY TERMINAL: no inline view; offer the bytes
 */
export type ViewerApplication =
  | 'markdown'
  | 'html'
  | 'image'
  | 'video'
  | 'audio'
  | 'pdf'
  | 'csv'
  | 'text'
  | 'download';

const IMAGE_EXTENSIONS = ['.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg', '.avif', '.bmp', '.ico'] as const;
const VIDEO_EXTENSIONS = ['.mp4', '.mov', '.webm', '.mkv', '.avi', '.m4v'] as const;
const AUDIO_EXTENSIONS = ['.mp3', '.wav', '.ogg', '.m4a', '.flac', '.aac'] as const;

/** Extensions whose bytes are not text, absent a content-type that says so. */
const BINARY_EXTENSIONS = [
  // office + archives
  '.xlsx', '.xls', '.pptx', '.ppt', '.docx', '.doc',
  '.zip', '.gz', '.tar', '.tgz', '.7z', '.rar',
  // fonts + binaries
  '.woff', '.woff2', '.ttf', '.otf', '.eot',
  '.wasm', '.so', '.dylib', '.dll', '.exe', '.bin',
  // design sources
  '.psd', '.ai', '.sketch', '.fig',
  // data
  '.parquet', '.db', '.sqlite',
] as const;

const endsWithAny = (p: string, exts: readonly string[]) => exts.some((e) => p.endsWith(e));

/**
 * Is this content-type text-shaped? `text/*` plus the structured-text
 * application types every text editor opens (including the `+json` /
 * `+xml` / `+yaml` structured-suffix convention, RFC 6839).
 */
function isTextualContentType(t: string): boolean {
  if (!t) return false;
  if (t.startsWith('text/')) return true;
  if (/^application\/(json|yaml|x-yaml|xml|javascript|ecmascript|toml|x-sh|x-ndjson)\b/.test(t)) return true;
  if (/\+(json|xml|yaml)\b/.test(t)) return true;
  return false;
}

/**
 * Kernel-default type → viewer association. The first matching rule wins.
 *
 * This is the single authoritative table. A new file type gets a new rule
 * here, not a new branch inside a viewer component.
 */
export function resolveViewerApplication(
  path: string,
  contentType?: string,
): ViewerApplication {
  const p = path.toLowerCase();
  const t = (contentType || '').toLowerCase();

  // ── tier 2: type-exact ──────────────────────────────────────────────
  if (p.endsWith('.md') || p.endsWith('.markdown')) return 'markdown';
  if (p.endsWith('.html') || p.endsWith('.htm') || t.includes('text/html')) return 'html';
  if (endsWithAny(p, IMAGE_EXTENSIONS) || t.startsWith('image/')) return 'image';
  if (endsWithAny(p, VIDEO_EXTENSIONS) || t.startsWith('video/')) return 'video';
  if (endsWithAny(p, AUDIO_EXTENSIONS) || t.startsWith('audio/')) return 'audio';
  if (p.endsWith('.pdf') || t.includes('application/pdf')) return 'pdf';
  if (p.endsWith('.csv') || p.endsWith('.tsv') || t.includes('text/csv')) return 'csv';

  // ── tier 3: the terminal, DERIVED from text-ness (never enumerated) ──
  //
  // A known-binary extension, or a content-type that is PRESENT and NOT
  // textual, terminates at `download`. Everything else is the L1 raw view,
  // which stays correct for `.yaml` / `.json` / `.log` / extension-less.
  if (endsWithAny(p, BINARY_EXTENSIONS)) return 'download';
  if (t && !isTextualContentType(t)) return 'download';
  return 'text';
}

/**
 * ADR-451 — the surface-owning app layer, ABOVE the viewer table.
 *
 * A row here claims a format for an app that owns a whole SURFACE: opening
 * such a file from the Finder (the Files surface) routes to the app —
 * `navigateToSurface(surface, {[param]: path})` — instead of rendering it
 * flat in the inline viewer (which remains the Quick Look analog for
 * everything unclaimed). One row in v1: the Studio owns its artifact format.
 *
 * The "Open with" picker stays deferred until a second installed app claims
 * the same format (ADR-436 — the resolver-is-an-ordered-list stance).
 */
export interface SurfaceApplication {
  /** The surface slug the app owns (navigateToSurface target). */
  surface: string;
  /** The window-namespaced param carrying the file path. */
  param: string;
  /** Operator-readable app name ("Opens in Studio"). */
  label: string;
}

/**
 * The type→app association (ADR-473 D2), learned at runtime from the served
 * layout vocabulary. The kernel owns the table; this is the FE's cache of it.
 *
 * Deliberately NOT a hardcoded map: a program-shipped document type must be
 * routable without a frontend deploy (ADR-222). Populated once by whoever
 * fetches the vocabulary; until then, `resolveSurfaceApplication` falls back to
 * the default app, which is exactly the pre-ADR-473 behavior.
 */
const KIND_TO_APP = new Map<string, string>();

/** The surfaces that can own an artifact type, by app slug (ADR-473 D2).
 *
 *  ADR-636 D3 — DERIVED from the app descriptor registry, not hand-kept. It
 *  was a hand map, gated only by NEGATIVE checks ("no longer claims docs"),
 *  which catch a forgotten deletion and never a forgotten addition; a new app
 *  that forgot this row routed its own artifacts to Slides.
 *
 *  ADR-599 — `docs` is DELETED with its app (was `stage: internal`, ADR-592).
 *  ADR-646 D5 — a legacy `document` artifact is therefore UNOWNED, and opens
 *  in the generic HTML viewer rather than in Slides. It used to fall back to
 *  the default app, which rendered it (the kernel CSS survives the type
 *  registry) but filed it under an app that never owned it. `article`/`page`/
 *  `web` are different: they alias FORWARD to `post` at the kind lift
 *  (`canonical_layout_slug`), so they are owned by Blogger and route there.
 *
 *  Only apps that OWN artifact types appear (every app today, since ADR-639
 *  deleted the declarations-only strings app).
 *
 *  Derived LAZILY, on first consult rather than at module init. Both readers
 *  call it at runtime, and a module-load-time derivation would make this
 *  module's correctness depend on another module having finished loading —
 *  a coupling that is invisible until something loads it in isolation
 *  (`test_adr571_text_app.py` executes this file with a stubbed `require`, and
 *  a top-level `Object.values(APP_DESCRIPTORS)` threw there before this was
 *  made lazy). Memoized, so the derivation runs once.
 */
let _appSurfaces: Record<string, SurfaceApplication> | null = null;

function appSurfaces(): Record<string, SurfaceApplication> {
  if (_appSurfaces) return _appSurfaces;
  _appSurfaces = Object.fromEntries(
    Object.values(APP_DESCRIPTORS || {})
      .filter((a) => a.ownsArtifactTypes)
      .map((a) => [a.slug, { surface: a.slug, param: a.artifactParam, label: a.label }]),
  );
  return _appSurfaces;
}

/** The prose class the Text app owns (ADR-571 D2 / ADR-570 D4's format class). */
const PROSE_EXT_RE = /\.(md|markdown|txt)$/i;

/** Publish the served association (call once with the vocabulary's layouts).
 *
 *  ADR-646 D5 — no client-side default. `DEFAULT_ARTIFACT_APP = 'slides'` used
 *  to live here and fill in for a row that arrived without an `app`; the
 *  server has ALWAYS sent one (`l.get("app") or DEFAULT_APP`, routes/studio.py),
 *  so it was a second home for a rule the kernel already owns — and the shape
 *  that let an unowned type quietly become a Slides artifact. A row without an
 *  app is now simply not registered, and `appForKind` returns null for it,
 *  which is ADR-473 D6's ruling. */
export function registerKindApps(rows: Array<{ slug: string; app?: string }>): void {
  for (const r of rows) {
    if (r.slug && r.app) KIND_TO_APP.set(r.slug, r.app);
  }
}

/**
 * Load the served association on demand (ADR-518 click-pass run-1, second
 * finding). `registerKindApps` used to run only from the authoring surfaces'
 * vocabulary fetches — so a session that went straight to Files consulted an
 * EMPTY map, and `appForKind` fell to the default app for every kind: a
 * document double-clicked in a fresh session routed to Studio. The
 * association must load wherever it is CONSULTED, not where authoring
 * surfaces happen to fetch. Idempotent one-shot (module promise); a failed
 * fetch clears it so the next consult retries. Dynamic import keeps the api
 * client out of this module's static graph.
 */
let KIND_APPS_LOADED: Promise<void> | null = null;

export function ensureKindApps(): Promise<void> {
  if (KIND_APPS_LOADED) return KIND_APPS_LOADED;
  KIND_APPS_LOADED = import('@/lib/api/client')
    .then(({ api }) => api.studio.vocabulary())
    .then((v) => {
      registerKindApps((v.layouts as Array<{ slug: string; app?: string }>) || []);
    })
    .catch(() => {
      KIND_APPS_LOADED = null; // retry on the next consult
    });
  return KIND_APPS_LOADED;
}

/** Which app owns a document type — null when nothing claims it (D6). */
export function appForKind(kind?: string | null): string | null {
  if (!kind) return null;
  return KIND_TO_APP.get(kind) ?? null;
}

/**
 * The per-path KIND cache (ADR-518 click-pass run-1 finding).
 *
 * A file's kind lives in its own bytes (`data-template`, ADR-473 D1), so any
 * caller that has not read the content cannot resolve the owning app — and
 * the context menu / Get Info are sync render paths that must not fetch per
 * row. Pre-ADR-518 the omission was invisible: the kind-less fallback
 * (DEFAULT_ARTIFACT_APP) matched every Studio-owned type. With a second
 * authoring app the menu showed "Studio (default)" for a document and never
 * listed Docs. Whoever reads content REMEMBERS the kind here; sync callers
 * consult it and pass what is known — the association itself stays served
 * (ADR-473 D3), this caches only the file's own declared type.
 */
const PATH_KIND = new Map<string, string>();

export function rememberKind(path: string, kind: string | null | undefined): void {
  if (path && kind) PATH_KIND.set(path, kind);
}

export function knownKind(path: string): string | undefined {
  return PATH_KIND.get(path);
}

/** Could this path be an app-claimed document at all? (ADR-473, widened by
 *  ADR-571 D2)
 *  A cheap path-only pre-check so the Finder reads content ONLY for files that
 *  might route to an app — never for an image or an arrival. Prose (`.md`)
 *  now qualifies: the Text app claims the class by EXTENSION, so no content
 *  read is needed for it, but it must pass this gate to reach the claim at
 *  all — `openPath` consults `resolveSurfaceApplication` only past here. */
/**
 * The SHAPE carves that are true for every principal (ADR-643 D4).
 *
 * ⚠️ This is deliberately the WEAK half of the access rule, and it is here
 * only because routing runs on a bare path — the decision rides a ROW, and
 * `resolveSurfaceApplication` is called during listing construction, before a
 * row's decision is in hand. The per-principal question is answered by the
 * server and read by the editor (`access.may_edit_as_prose`), which is what
 * renders a canvas read-only.
 *
 * ⭐⭐⭐ THE `system/` CARVE IS THE POINT. This function's comment used to claim
 * its exclusions "mirror the member write door exactly" while implementing two
 * of that door's THREE carves — so twelve mirrored `system/skills/…/SKILL.md`
 * files and three kernel prose files routed to an always-editable canvas that
 * 403'd every save. Adding the third carve is what makes the claim true.
 */
export function isShapeCarved(p: string): boolean {
  const rel = p.replace(/^\/+/, '').replace(/^workspace\//, '');
  if (rel.startsWith('system/')) return true;
  // ADR-422 D2 — raw intake is retained exactly as it arrived. The human
  // upload lane (ADR-395) is NOT carved: the operator owns what they uploaded.
  if (rel.startsWith('inbound/') && !rel.startsWith('inbound/uploads/')) return true;
  return false;
}

/**
 * May this path open in the Text editor AT ALL (ADR-643 D4)?
 *
 * The SHAPE half only — format class plus the carves true for everyone.
 * Whether THIS VIEWER may type is `access.may_edit_as_prose`, served per row.
 * Exported so no caller re-spells the rule: TextSurface's Recents filter had
 * its own copy, and it omitted the same `system/` carve the router did.
 */
export function isTextEditable(path: string): boolean {
  const leaf = (path.split('/').pop() || path).toLowerCase();
  return PROSE_EXT_RE.test(leaf) && !leaf.startsWith('_') && !isShapeCarved(path);
}

export function isArtifactCandidate(path: string, contentType?: string): boolean {
  const p = path.toLowerCase();
  const t = (contentType || '').toLowerCase();
  const isHtml = p.endsWith('.html') || p.endsWith('.htm') || t.includes('text/html');
  // ADR-643 D4 — the SAME carve set the write door composes, `system/`
  // included. (`isShapeCarved` covers the arrival check this line used to
  // spell out inline.)
  const leaf = p.split('/').pop() || p;
  const isProse = PROSE_EXT_RE.test(leaf) && !leaf.startsWith('_');
  return (isHtml || isProse) && !isShapeCarved(p);
}

/** The artifact's declared document type — its root `data-template` (ADR-459
 *  D1). Lifted from content, never stored; mirrors
 *  `services/authoring.py::extract_template`. */
export function extractTemplate(content: string): string | null {
  const m = /<html[^>]*\bdata-template="([^"]+)"/i.exec(content || '');
  return m ? m[1] : null;
}

/**
 * ADR-569 — the DECLARATION claim, ahead of the artifact (html) layer.
 *
 * A declaration file is not an authoring artifact — it is a standing app's
 * unit, and opening it from the Finder launches that app on its folder.
 * Path-only and cheap, so `openPath` consults it BEFORE the
 * isArtifactCandidate content-read gate. Every other yaml stays with the
 * inline raw view (Quick Look) — the claim is exactly one leaf name in
 * exactly one namespace, never "yaml opens an app".
 *
 * ADR-592 — the `_radar.yaml` claim is GONE with the Radar app. A leftover
 * hub declaration now falls through to the raw view, which is correct: it is
 * inert config for an app that no longer exists.
 */
export function resolveDeclarationApplication(path: string): SurfaceApplication | null {
  // ADR-639 — the `_string.yaml` claim is GONE with the Strings app (the radar
  // precedent above). A standing declaration ({folder}/_standing.yaml) opens
  // in the raw view like every other machine-config file: the roster of what
  // stands is the Notifications "Standing work" pane, and the declaration is
  // authored in conversation (the `declaring-standing-work` skill). No leaf
  // claims an app today; the resolver stays as the one door for the next one.
  void path;
  return null;
}

export function resolveSurfaceApplication(
  path: string,
  contentType?: string,
  /** The artifact's declared type (`data-template`, ADR-459) when the caller
   *  has it. Absent → the default app, preserving pre-ADR-473 behavior. */
  kind?: string | null,
): SurfaceApplication | null {
  const p = path.toLowerCase();
  const t = (contentType || '').toLowerCase();
  // An html artifact is claimed by an AUTHORING app — EXCEPT arrivals
  // (inbound/): a retained observation is a record to preview, not an
  // authoring canvas (ADR-451 D1).
  const isHtml = p.endsWith('.html') || p.endsWith('.htm') || t.includes('text/html');
  const carved = isShapeCarved(p);
  // ADR-571 D2 — the PROSE class is claimed by the Text app, the same way
  // .html is claimed by an authoring app. The two exclusions mirror the
  // member write door exactly (ADR-570 D4): an arrival is a retained
  // observation, and an `_`-prefixed leaf is machine-tended state, so
  // neither opens in an editor. Preview stays one Open With away.
  const leaf = p.split('/').pop() || p;
  if (PROSE_EXT_RE.test(leaf) && !carved && !leaf.startsWith('_')) {
    return appSurfaces().text;
  }
  if (!isHtml || carved) return null;
  // ADR-473 D2: the OWNING app comes from the artifact's declared type. The
  // ADR-451 hardcode (every html → Studio) is replaced, not supplemented —
  // it would send an IMAGES stage into Studio.
  // ADR-646 D5 — an UNOWNED type degrades to the generic viewer, never to an
  // app. This line read `appForKind(kind) ?? DEFAULT_ARTIFACT_APP`, which is
  // ADR-473 D6 stated and then contradicted three lines below its own comment:
  // "Absence of an owner is a fallback, not a failure" means the HTML viewer,
  // not whichever app happened to ship first. The default sent every untyped
  // `.html` to Slides — a bundle-shipped type, a hand-authored file, and every
  // compose-engine report (which emits no `data-template` at all).
  //
  // Returning null is the honest answer and the caller already handles it:
  // ArtifactCard falls to its in-chat modal, the Finder to the inline viewer.
  const app = appForKind(kind);
  return app ? appSurfaces()[app] ?? null : null;
}

/**
 * Is this file chat's own working material (prose-substrate), rather than a
 * thing chat MADE? — the ADR-443/454 asset-vs-dividend seam, answered once.
 *
 * The conversation renders its own material inline (reading a brief IS the
 * thinking-work) and CITES everything else as a tile. Only `.md` qualifies
 * today; the predicate exists so the card can ASK the question instead of
 * resolving the viewer kind and switching on it — the mount-side branch that
 * `test_lane_artifacts::test_the_file_body_is_the_only_kind_switch` forbids,
 * and rightly: a re-derived kind is how `.mp4`-renders-as-text comes back in
 * two places. Depth is a policy over the type; the type stays this table's.
 */
export function isConversationalSubstrate(
  path: string,
  contentType?: string,
): boolean {
  return resolveViewerApplication(path, contentType) === 'markdown';
}

/**
 * Does this viewer read the blob (`content_url`) rather than the `content`
 * text column? Mirrors the ADR-427 §8 read-side split: a binary revision's
 * text column is empty by construction.
 */
export function viewerNeedsBlob(kind: ViewerApplication): boolean {
  return kind === 'video' || kind === 'audio' || kind === 'pdf' || kind === 'download';
}

/** Operator-readable label for a viewer (the file-metadata strip). */
export function describeViewerApplication(
  path: string,
  contentType?: string,
): string {
  switch (resolveViewerApplication(path, contentType)) {
    case 'markdown':
      return 'Markdown';
    case 'html':
      return 'HTML report';
    case 'image':
      return 'Image';
    case 'video':
      return 'Video';
    case 'audio':
      return 'Audio';
    case 'pdf':
      return 'PDF';
    case 'csv':
      return 'CSV';
    case 'download':
      return 'Binary file';
    default:
      return 'Text';
  }
}
