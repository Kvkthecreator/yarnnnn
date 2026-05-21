'use client';

/**
 * ChromeRegistry — ADR-297 D11.
 *
 * Maps each chrome-surface slug (declared in
 * api/services/kernel_surfaces.py with archetype ∈ {chrome, navigator,
 * input}) to its React component. The ShellCompositor reads this
 * registry to mount chrome surfaces into named layout regions.
 *
 * Distinct from KERNEL_SURFACE_REGISTRY (SurfaceRegistry.tsx) which
 * maps *content* surfaces — content surfaces are launcher-navigable,
 * dock-pinnable, and mount into `main` via SurfaceViewport. Chrome
 * surfaces are none of those; they mount into top / bottom-floating /
 * bottom-fixed / floating-overlay regions and are not pickable from
 * the launcher.
 *
 * Per ADR-297 D11: chrome-vs-content is not a special case at the
 * architecture layer (both are surfaces; both come from the registry
 * that composition_resolver emits). The two registries here are a
 * pragmatic split — they differ only in WHICH JSX slot the compositor
 * mounts them into, not in WHAT they fundamentally are.
 */

import type { ComponentType } from 'react';
import { TopBarSurface } from './chrome/TopBarSurface';
import { DockSurface } from './chrome/DockSurface';
import { LauncherSurface } from './chrome/LauncherSurface';
import { ChatComposerSurface } from './chrome/ChatComposerSurface';

export type ChromeSurfaceSlug = 'top-bar' | 'dock' | 'launcher' | 'chat-composer';

export const CHROME_SURFACE_REGISTRY: Record<ChromeSurfaceSlug, ComponentType> = {
  'top-bar': TopBarSurface,
  dock: DockSurface,
  launcher: LauncherSurface,
  'chat-composer': ChatComposerSurface,
};

const CHROME_SLUG_SET = new Set<string>(Object.keys(CHROME_SURFACE_REGISTRY));

export function isChromeSurfaceSlug(s: string): s is ChromeSurfaceSlug {
  return CHROME_SLUG_SET.has(s);
}
