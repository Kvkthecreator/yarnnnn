/**
 * The Handler Set — ADR-514 D2 (the LaunchServices cut).
 *
 * LaunchServices has three layers: UTI (what type is this) → the handler set
 * (who can open it, ordered) → the default binding (which one wins). yarnnn had
 * all three, but the middle one was degenerate: every type resolved to exactly
 * ONE app, and the set was split across two tables —
 *
 *   - `apps.tsx::resolveApps`            in-frame RENDERERS (text, markdown, web…)
 *   - `index.ts::resolveSurfaceApplication`  SURFACE-owning apps (Studio, Images, Radar)
 *
 * LaunchServices does not distinguish "opens in a pane" from "opens in a
 * window"; how a handler presents itself is the handler's business, not the
 * registry's. This module is the merge: ONE ordered set per file, `[0]` is the
 * default, and the Finder grammar follows — `Open` fires the default, `Open
 * With ›` lists the rest.
 *
 * ── THE SET WAS NEVER ACTUALLY A SINGLETON ────────────────────────────────
 *
 * `.html` has had two handlers since ADR-451 shipped: Studio (the authoring
 * surface) and the web viewer (the Quick Look render). The second one lived in
 * an if/else fallthrough in `files/page.tsx::openPath` rather than a registry
 * row, so ADR-451's "defer the picker until a second app claims the format"
 * condition was met and invisible at the same time. Making the set real is what
 * lights Open With up — no new app required.
 *
 * ── DELIVERY, NOT INTENT (D2.3) ───────────────────────────────────────────
 *
 * A row declares HOW the file reaches it, which is a mechanical property
 * LaunchServices itself encodes (open-document vs the service verbs sharing one
 * registry). It is NOT a taxonomy of what the app "means" toward the file — an
 * earlier draft tried that (edit/reason/observe) and was rejected as un-OS-like.
 *
 *   document   the handler takes CUSTODY and opens the file as its subject.
 *              Single-subject by nature: five files in Studio = five documents.
 *   reference  the handler receives the file as CITED MATERIAL. Naturally
 *              plural, and the only delivery a FOLDER can have — nothing opens
 *              a directory as a subject except the Finder itself.
 *
 * That axis is what makes Open With answerable for multi-selections and folders
 * at all, and it is why Chat needs no new receiving contract: `reference`
 * delivery IS the ADR-512 D6 bind that already shipped.
 */

import {
  resolveViewerApplication,
  resolveSurfaceApplication,
  resolveDeclarationApplication,
  type SurfaceApplication,
} from './index';
import { resolveApps, APPS } from './apps';

/** How a file is delivered to a handler (D2.3). Closed at two values. */
export type HandlerDelivery = 'document' | 'reference';

/** What the caller is opening — one file, several, or a folder. */
export interface HandlerSubject {
  paths: string[];
  isFolder: boolean;
  contentType?: string;
  /** The artifact's declared `data-template` when the caller has it (ADR-459). */
  kind?: string | null;
}

export interface Handler {
  /** Stable id — what a default-override stores. */
  id: string;
  /** Operator-readable, as it appears in Open With ("Studio", "Chat"). */
  label: string;
  delivery: HandlerDelivery;
  /**
   * How this handler opens. `surface` navigates the shell to an app that owns a
   * whole surface; `inline` mounts a renderer in the current frame (the Quick
   * Look analog). Presentation is the handler's business — both are peers here.
   */
  open: { via: 'surface'; surface: string; param: string } | { via: 'inline' };
  /** True iff this handler can take a multi-file selection in one open. */
  acceptsMultiple: boolean;
}

/** The in-frame renderer, as a handler row. Always last-resort, never surface. */
function inlineHandler(path: string, contentType?: string): Handler | null {
  const [appId] = resolveApps(path, contentType);
  const app = APPS[appId];
  if (!app) return null;
  const kind = resolveViewerApplication(path, contentType);
  return {
    id: app.id,
    // "Quick Look" is the honest name for preview-in-place; the kind
    // disambiguates when several inline handlers ever coexist.
    label: kind === 'download' ? 'Download' : 'Preview',
    delivery: 'document',
    open: { via: 'inline' },
    acceptsMultiple: false,
  };
}

function surfaceHandler(app: SurfaceApplication): Handler {
  return {
    id: `${app.surface}.app`,
    label: app.label,
    delivery: 'document',
    open: { via: 'surface', surface: app.surface, param: app.param },
    acceptsMultiple: false,
  };
}

/**
 * Chat — the `reference` handler (D2.3).
 *
 * Chat is a real app the operator picks to open something with; what differs is
 * that the file arrives as a CITATION, not as chat's subject. Because a
 * reference is naturally plural, this is the one handler that accepts a
 * multi-selection — and the only one a folder can have.
 */
const CHAT_HANDLER: Handler = {
  id: 'chat.app',
  label: 'Chat',
  delivery: 'reference',
  open: { via: 'surface', surface: 'chat', param: 'cite' },
  acceptsMultiple: true,
};

/**
 * The ordered handler set for a subject. `[0]` is the default.
 *
 * Order is the registry rank: the surface-owning app (the authoring claim)
 * outranks the inline preview, and `reference` handlers come last — they are
 * alternatives to opening, not the way a document is opened. Per-file and
 * per-type overrides re-rank this in `applyDefaultOverride`.
 */
export function resolveHandlers(subject: HandlerSubject): Handler[] {
  const { paths, isFolder, contentType, kind } = subject;

  // A folder has no `document` handler — nothing opens a directory as a
  // subject. It DOES have a reference handler, which is the first coherent
  // answer to what right-clicking a folder offers beyond navigation.
  if (isFolder) return [CHAT_HANDLER];

  // A multi-selection admits only handlers that accept it.
  if (paths.length > 1) return [CHAT_HANDLER].filter((h) => h.acceptsMultiple);

  const path = paths[0] ?? '';
  const handlers: Handler[] = [];

  // Declaration claims outrank format claims (ADR-486: `_radar.yaml` → Radar).
  const declared = resolveDeclarationApplication(path);
  if (declared) handlers.push(surfaceHandler(declared));

  const owning = resolveSurfaceApplication(path, contentType, kind);
  if (owning && !handlers.some((h) => h.id === `${owning.surface}.app`)) {
    handlers.push(surfaceHandler(owning));
  }

  // The inline renderer — the fallthrough that `openPath` used to hardcode as
  // an else-branch. Making it a ROW is what gives `.html` its second handler.
  const inline = inlineHandler(path, contentType);
  if (inline) handlers.push(inline);

  handlers.push(CHAT_HANDLER);
  return handlers;
}

/**
 * Re-rank a handler set by the operator's default override (D2.4).
 *
 * Resolution is most-specific-first: per-file → per-type → registry rank. An
 * unknown or stale handler id FALLS THROUGH to the next level rather than
 * winning — a bad override must never make a file unopenable, the same
 * terminal-fallback discipline ADR-309 applies to types.
 */
export function applyDefaultOverride(
  handlers: Handler[],
  override?: string | null,
): Handler[] {
  if (!override || handlers.length < 2) return handlers;
  const idx = handlers.findIndex((h) => h.id === override);
  if (idx <= 0) return handlers; // absent (stale) or already default → unchanged
  return [handlers[idx], ...handlers.slice(0, idx), ...handlers.slice(idx + 1)];
}

/** The default handler for a subject, override applied. */
export function resolveDefaultHandler(
  subject: HandlerSubject,
  override?: string | null,
): Handler | null {
  return applyDefaultOverride(resolveHandlers(subject), override)[0] ?? null;
}
