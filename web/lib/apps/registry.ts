/**
 * The app descriptor registry — ADR-636 D1 (2026-09-04).
 *
 * ONE row per app: the client mirror of the backend's `register_app`
 * (ADR-562 D1). Before this, an app was re-declared by hand in six places on
 * the frontend — the Dock default, the window registry, the slug union, the
 * type→app map, the authoring app row, and a served-index set — and none of
 * them was derived from, or gated against, the served roster. They agreed at
 * `7ed27fb`, and that agreement was held by memory: the checks that existed
 * over them were NEGATIVE ("APP_SURFACES no longer claims docs"), which
 * catches a forgotten DELETION and cannot, by construction, catch a forgotten
 * ADDITION.
 *
 * The rule this file enacts is the one the backend already states in
 * `api/services/apps/__init__.py`:
 *
 *     "The kernel never imports an app. Registration is the only direction."
 *
 * Adding an app = a row HERE, plus its window component and (if it authors)
 * its `AuthoringApp`. `api/test_adr636_app_declaration_parity.py` asserts this
 * table against `all_apps()` in BOTH directions, so a missing row is red
 * rather than a surface that silently renders someone else's default.
 *
 * ⚠️ WHAT MAY NOT LIVE HERE (ADR-636 D1, and the ADR-460 D3.a cliff behind it)
 * The resident, the engine, the stage, the launcher tier, the Dock pin. Every
 * one of those is the SERVER'S and arrives on the roster:
 *   - a client row naming a resident is ADR-562's deleted
 *     `web/lib/apps/authoring.ts` returning;
 *   - a client row naming a stage forks ADR-592's one derivation;
 *   - a client row naming ANY authority is the D3.a cliff arriving through a
 *     config file.
 * This table carries only what the client alone knows: what to render, and how
 * the member's object is shaped.
 *
 * ⚠️ ICONS ARE NOT HERE EITHER. A surface's mark resolves through
 * `resolveSurfaceIcon` off the served row's `icon_key` (ADR-297), so an app
 * has ONE look everywhere and a re-icon moves every rendering at once. The
 * drift this prevents is on the record: ADR-602 D4 repaired a Slides that wore
 * Palette on its landing and Presentation in the launcher.
 */

/** How the member's object is shaped — ADR-633 D2. */
export type ObjectModel = 'flow' | 'pages' | 'layers';

export interface AppDescriptor {
  /** The app identity. Keys the served roster join, the surface param
   *  namespace, and the backend's `register_app` slug — one spelling. */
  slug: string;
  /** Operator-readable app name ("Opens in Slides"). */
  label: string;
  /** ADR-633 D2 — the PROPERTY MODEL: what the member is composing, and
   *  therefore which left rail mounts and which noun the chrome says.
   *
   *  `flow`   — a continuous document (blogger). No page unit.
   *  `pages`  — a sequence of pages (slides). The rail is the sequence.
   *  `layers` — a stack on an artboard (images). The rail is the stack.
   *
   *  REQUIRED: no `?`, no default, no `?? 'pages'` at any read site. Adding one
   *  restores the fall-through this field deletes — images was never NAMED by
   *  the `layout === 'deck'` ternary, fell onto the document branch, and one
   *  object read "Slide" in the crumb and "Sections" in the rail (ADR-633 §1.1).
   *  A derivation has a default; a declaration does not. */
  objectModel: ObjectModel;
  /** The surface param that addresses this app's open artifact
   *  (`?slides.file=…`). */
  artifactParam: string;
  /** Does this app OWN artifact types — i.e. does a file route here?
   *
   *  True for every app today. The field exists for an app whose pane is
   *  not a document surface (the deleted strings app was one — its material
   *  was declarations, ADR-639 made it a kernel lane); a future such app
   *  declares false and is addressed by name, never by extension. */
  ownsArtifactTypes: boolean;
  /** Do this app's artifacts appear in the served `/studio/artifacts` index?
   *
   *  The HTML-authoring apps do. A prose app (ADR-571) has no row there and
   *  scopes by the type registry alone. */
  servesIndex: boolean;
  /** ADR-472 D3 — a raster artifact is born at a size, so creation asks for
   *  dimensions first. Not derivable from ownership, so it stays a property. */
  dimensionsFirst?: boolean;
}

/**
 * Every app the client renders, keyed by slug.
 *
 * ORDER IS NOT MEANING here — the Dock's order is `DEFAULT_KEPT_SURFACES`
 * (which IS the on-screen order) and the launcher's is the backend's
 * declaration order. This table is a lookup, so it reads alphabetically.
 */
export const APP_DESCRIPTORS: Record<string, AppDescriptor> = {
  // ADR-627 — the publish medium's pane. Prose for a reader OUTSIDE the
  // workspace; one continuous document, so no page rail (ADR-633 D2).
  blogger: {
    slug: 'blogger',
    label: 'Blogger',
    objectModel: 'flow',
    artifactParam: 'file',
    ownsArtifactTypes: true,
    servesIndex: true,
  },
  // ADR-472 — the raster app: a stack on an artboard, born at a size.
  images: {
    slug: 'images',
    label: 'Images',
    objectModel: 'layers',
    artifactParam: 'file',
    ownsArtifactTypes: true,
    servesIndex: true,
    dimensionsFirst: true,
  },
  // ADR-440 Studio → ADR-599 D4 the full evolve: the dedicated deck app. A
  // deck is a SEQUENCE of pages; the page is the unit, the rail is the
  // sequence, the noun is Slide.
  slides: {
    slug: 'slides',
    label: 'Slides',
    objectModel: 'pages',
    artifactParam: 'file',
    ownsArtifactTypes: true,
    servesIndex: true,
  },
  // ADR-639 — the strings descriptor is DELETED with the app (standing work is
  // a kernel lane; its roster is a Notifications pane). The parity gate
  // (test_adr636) reads this table against the backend's `all_apps()` in
  // both directions, so a row here for a lane with no app would be a phantom.
  // ADR-571 — the prose app (md · txt). Prose flows; no page unit.
  text: {
    slug: 'text',
    label: 'Text',
    objectModel: 'flow',
    artifactParam: 'file',
    ownsArtifactTypes: true,
    servesIndex: false,
  },
};

/** An app's descriptor, or undefined when nothing declares that slug. Pure.
 *
 *  Returns undefined rather than a fallback, matching `resident_for_app`'s
 *  posture (ADR-562): a missing registration is a programming error, and a
 *  plausible default hides the bug it should surface. */
export function resolveApp(slug?: string | null): AppDescriptor | undefined {
  if (!slug) return undefined;
  return APP_DESCRIPTORS[slug];
}

/** Every declared app slug. */
export function appSlugs(): string[] {
  return Object.keys(APP_DESCRIPTORS);
}

/** Does this app's artifact index exist server-side? Derived — ADR-636 D3. */
export function servesArtifactIndex(slug?: string | null): boolean {
  return resolveApp(slug)?.servesIndex ?? false;
}
