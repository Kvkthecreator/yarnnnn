/**
 * Compositor public API — ADR-225.
 *
 * Single import surface for the FE compositor module. Consumers use
 * useComposition() to fetch + cache; resolveMiddle() for match
 * resolution; selectors (getTab, getDetailMiddles, getActiveBundles)
 * for tree access.
 */

export { useComposition, getTab, getDetailMiddles, getActiveBundles } from './useComposition';
export { resolveMiddle, resolveChrome, resolveCockpitPanes } from './resolver';
export type { ResolutionContext } from './resolver';
export { KERNEL_DEFAULT_CHROME, KERNEL_DEFAULT_COCKPIT_PANES } from './kernel-defaults';
export type {
  SurfacesResponse,
  BundleMetadata,
  CompositionTree,
  TabBlock,
  TabListBlock,
  TabDetailBlock,
  BandDecl,
  MiddleDecl,
  MiddleMatch,
  Archetype,
  ChromeDecl,
  ComponentDecl,
  Binding,
} from './types';
