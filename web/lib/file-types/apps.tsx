'use client';

/**
 * The App Registry — ADR-436.
 *
 * The first-party half of yarnnn's LaunchServices layer. `resolveViewerApplication`
 * (in `./index`) answers "what TYPE is this file"; this table answers "what APP
 * renders that type". FileBody dispatches through `resolveApps` + `APPS`.
 *
 * ── CODE-SEEDED, SHAPE-OPEN ───────────────────────────────────────────────
 *
 * The registry is a code-seeded table: the 7 kernel apps are rows, the row
 * SHAPE admits a third party's app, but only yarnnn adds rows (a stranger can't
 * write our code). "Open" here = the shape is ready; adding rows stays
 * demand-gated (the App(principal) ADR, deferred — app-seam §8 / ADR-380 §5).
 *
 * ── THE ONE-FILE RATCHET (app-layer §12; NOT flipped here) ────────────────
 *
 * `AppId` is an opaque string (not re-narrowed to a union), so the flip to a
 * third-party-writable registry is a type change + a seed swap confined to THIS
 * file + `./index`. The CI ratchet ("can a third party replace a viewer with no
 * kernel change?") runs red until an App(principal) ADR flips it — correctly,
 * per ESSENCE v15 positioning.
 *
 * ── THE APP CONTRACT ──────────────────────────────────────────────────────
 * An app is a frame-agnostic RENDERER (`ViewerApp` — `components/workspace/
 * viewers`). It owns types + draws content; it never owns its frame (the mount
 * does) and never edits (mutation → chat, ADR-236).
 */

import type { ViewerApp } from '@/components/workspace/viewers';
import {
  TextViewer,
  MarkdownViewer,
  WebViewer,
  ImageViewer,
  MediaPlayer,
  PdfViewer,
  TableViewer,
  DownloadTerminal,
  isIdentityPath,
} from '@/components/workspace/viewers';
import { resolveViewerApplication, type ViewerApplication } from './index';

/**
 * An opaque app id. Deliberately a plain string, NOT a re-narrowed union: the
 * registry's shape must admit a third party's id without a kernel type edit
 * (the one-file ratchet — see header). Today only the 7 kernel ids exist.
 */
export type AppId = string;

interface AppRegistration {
  id: AppId;
  /** The `ViewerApplication` kinds this app renders. */
  ownsTypes: ViewerApplication[];
  /** The frame-agnostic renderer component. */
  renderer: ViewerApp;
  /** True if the app reads the blob (`content_url`) not the text column. */
  needsBlob: boolean;
}

/**
 * The seeded kernel apps. Seven renderers + the download terminal. A third
 * party's app would be an additional row of the exact same shape.
 */
export const APPS: Record<AppId, AppRegistration> = {
  'text.viewer': { id: 'text.viewer', ownsTypes: ['text'], renderer: TextViewer, needsBlob: false },
  'markdown.viewer': { id: 'markdown.viewer', ownsTypes: ['markdown'], renderer: MarkdownViewer, needsBlob: false },
  'web.viewer': { id: 'web.viewer', ownsTypes: ['html'], renderer: WebViewer, needsBlob: false },
  'image.viewer': { id: 'image.viewer', ownsTypes: ['image'], renderer: ImageViewer, needsBlob: false },
  'media.player': { id: 'media.player', ownsTypes: ['video', 'audio'], renderer: MediaPlayer, needsBlob: true },
  'pdf.viewer': { id: 'pdf.viewer', ownsTypes: ['pdf'], renderer: PdfViewer, needsBlob: true },
  'table.viewer': { id: 'table.viewer', ownsTypes: ['csv'], renderer: TableViewer, needsBlob: false },
  // The download terminal (not a viewer app — the resolver's binary terminal).
  'download.terminal': { id: 'download.terminal', ownsTypes: ['download'], renderer: DownloadTerminal, needsBlob: true },
};

/**
 * type → the app ids that own it. Built once from `APPS`. First-registered
 * wins ordering (the default), so a future second app for a type appends as an
 * alternative rather than displacing the kernel default.
 */
const APPS_BY_TYPE: Record<string, AppId[]> = (() => {
  const map: Record<string, AppId[]> = {};
  for (const app of Object.values(APPS)) {
    for (const t of app.ownsTypes) {
      (map[t] ??= []).push(app.id);
    }
  }
  return map;
})();

/**
 * Resolve a file to the ordered list of app ids that can open it (ADR-436 §4).
 *
 * The default is first; alternatives follow. Today every type has exactly ONE
 * app, so this returns a singleton and the caller mounts `apps[0]` —
 * byte-identical to the pre-split single-return resolver. When a second app
 * ever claims a type, the "Open With" picker lights up (render only when
 * `length > 1`) with NO kernel change — the app-layer §11 falsification
 * boundary.
 *
 * Tier-1 (path-exact) is handled INSIDE the resolved app (the Markdown app owns
 * the IDENTITY case, `isIdentityPath`), not by a branch here — the tier stays a
 * table concern, never an inline `if` in a mount (ADR-436 §4).
 */
export function resolveApps(path: string, contentType?: string): AppId[] {
  const kind = resolveViewerApplication(path, contentType);
  return APPS_BY_TYPE[kind] ?? ['download.terminal'];
}

/** The app that renders a file (the default — first of `resolveApps`). */
export function resolveApp(path: string, contentType?: string): AppRegistration {
  const [id] = resolveApps(path, contentType);
  return APPS[id] ?? APPS['download.terminal'];
}

export { isIdentityPath };
