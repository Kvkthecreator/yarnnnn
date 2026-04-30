/**
 * Compositor public API — ADR-225, amended by ADR-228.
 *
 * Single import surface for the FE compositor module. Consumers use
 * useComposition() to fetch + cache; resolveMiddle() for match
 * resolution; selectors (getTab, getDetailMiddles, getActiveBundles)
 * for tree access.
 *
 * ADR-228: cockpit-side resolution (resolveCockpitPanes,
 * KERNEL_DEFAULT_COCKPIT_PANES) deleted — the cockpit renders four
 * faces directly via CockpitRenderer; no compositor-resolver step
 * stands between SURFACES.yaml and the cockpit faces.
 */

export { useComposition, getTab, getDetailMiddles, getActiveBundles } from './useComposition';
export { resolveMiddle, resolveChrome, getProgramSections } from './resolver';
export type { ResolutionContext } from './resolver';
export { KERNEL_DEFAULT_CHROME } from './kernel-defaults';
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
