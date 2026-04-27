/**
 * Compositor public API — ADR-225.
 *
 * Single import surface for the FE compositor module. Consumers use
 * useComposition() to fetch + cache; resolveMiddle() for match
 * resolution; selectors (getTab, getDetailMiddles, getActiveBundles)
 * for tree access.
 */

export { useComposition, getTab, getDetailMiddles, getActiveBundles } from './useComposition';
export { resolveMiddle } from './resolver';
export type { ResolutionContext } from './resolver';
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
  ComponentDecl,
  Binding,
} from './types';
