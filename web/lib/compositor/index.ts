/**
 * Compositor public API — ADR-225, amended by ADR-228.
 *
 * Single import surface for the FE compositor module. Consumers use
 * useComposition() to fetch + cache; resolveMiddle() for match
 * resolution; selectors (getTab, getDetailMiddles, getActiveBundles)
 * for tree access.
 *
 * ADR-228/312: cockpit-side resolution (resolveCockpitPanes,
 * KERNEL_DEFAULT_COCKPIT_PANES) deleted. ADR-435: the Home surface itself was
 * deleted, along with getProgramSections (its program-section reader).
 * ADR-603 D5 (2026-08-24): WorkDetail middle/chrome resolution
 * (resolver.ts + kernel-defaults.ts) deleted with the Recurrence window —
 * its only tenant. What survives is the composition fetch + tree selectors
 * the shell reads (useComposition, surfaceTitle).
 */

export { useComposition, getTab, getDetailMiddles, getActiveBundles } from './useComposition';
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
