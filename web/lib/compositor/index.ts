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
 * deleted, along with getProgramSections (its program-section reader). The
 * compositor now resolves only WorkDetail middle/chrome — no Home path remains.
 */

export { useComposition, getTab, getDetailMiddles, getActiveBundles } from './useComposition';
export { resolveMiddle, resolveChrome } from './resolver';
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
