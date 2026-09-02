'use client';

/**
 * ChromeRegistry — ADR-297 D11 + D12 + D16.
 *
 * Maps each chrome-surface slug (declared in
 * api/services/kernel_surfaces.py with archetype ∈ {chrome, navigator,
 * input}) to its React component. The ShellCompositor reads this
 * registry to mount chrome surfaces into named layout regions.
 *
 * Distinct from KERNEL_SURFACE_REGISTRY (SurfaceRegistry.tsx) which
 * maps *content* surfaces — content surfaces are launcher-navigable,
 * dock-pinnable, and mount into `main` via SurfaceViewport. Chrome
 * surfaces are none of those; they mount into top / floating-overlay
 * regions and are not pickable from the launcher.
 *
 * Post-ADR-316 chrome set:
 *   top-bar     — merged dock-bar (D12: brand · launcher · Dock · user)
 *   launcher    — full surface-index overlay (D4 + D11), floating-overlay
 *   (the chat drawer — ADR-316 — retired with the steward, ADR-632)
 * D12 collapsed `dock` into top-bar's body.
 * main-rail (a flex sibling of main that reduces the surface area).
 */

import type { ComponentType } from 'react';
import { TopBarSurface } from './chrome/TopBarSurface';
import { LauncherSurface } from './chrome/LauncherSurface';

export type ChromeSurfaceSlug = 'top-bar' | 'launcher';

export const CHROME_SURFACE_REGISTRY: Record<ChromeSurfaceSlug, ComponentType> = {
  'top-bar': TopBarSurface,
  launcher: LauncherSurface,
};

const CHROME_SLUG_SET = new Set<string>(Object.keys(CHROME_SURFACE_REGISTRY));

export function isChromeSurfaceSlug(s: string): s is ChromeSurfaceSlug {
  return CHROME_SLUG_SET.has(s);
}
