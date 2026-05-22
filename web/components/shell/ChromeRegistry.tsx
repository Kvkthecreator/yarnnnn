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
 * Post-D16 (2026-05-22) chrome set:
 *   top-bar     — merged dock-bar (D12: brand · launcher · Dock · user)
 *   launcher    — full surface-index overlay (D4 + D11)
 *   chat-drawer — FAB + slide-over drawer (D16, replaces chat-composer)
 *
 * D12 collapsed `dock` into top-bar's body.
 * D16 collapsed `chat-composer` (bottom-fixed strip) into chat-drawer
 * (FAB + floating-overlay summon).
 */

import type { ComponentType } from 'react';
import { TopBarSurface } from './chrome/TopBarSurface';
import { LauncherSurface } from './chrome/LauncherSurface';
import { ChatDrawerSurface } from './chrome/ChatDrawerSurface';

export type ChromeSurfaceSlug = 'top-bar' | 'launcher' | 'chat-drawer';

export const CHROME_SURFACE_REGISTRY: Record<ChromeSurfaceSlug, ComponentType> = {
  'top-bar': TopBarSurface,
  launcher: LauncherSurface,
  'chat-drawer': ChatDrawerSurface,
};

const CHROME_SLUG_SET = new Set<string>(Object.keys(CHROME_SURFACE_REGISTRY));

export function isChromeSurfaceSlug(s: string): s is ChromeSurfaceSlug {
  return CHROME_SLUG_SET.has(s);
}
