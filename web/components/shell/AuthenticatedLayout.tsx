'use client';

/**
 * AuthenticatedLayout — ADR-297 D11 (Universal Surface Application).
 *
 * Pre-D11 this file rendered the shell chrome as hardcoded JSX (a top
 * header, a Dock, a Launcher overlay, a SurfaceViewport). D11 dissolves
 * that chrome into a compositor-driven mount: every chrome element is
 * a registered surface, the compositor reads default_region from the
 * surface registry, and the shell becomes structural only.
 *
 * What this file owns after D11 (+ Phase 3 legacy-desk deletion):
 *   - Auth check + loading state
 *   - Provider stack (BreadcrumbProvider · SurfacePreferencesProvider
 *     · ShellChromeProvider). The legacy DeskProvider was deleted in
 *     ADR-297 Phase 3 — the window manager (SurfacePreferencesProvider)
 *     is the sole surface-state source of truth.
 *   - The NarrativeContext.onSurfaceChange handoff machinery, which maps
 *     TP-emitted DeskSurface kinds to navigateToSurface (window-opening).
 *   - Pathname → foreground surface tracking (D13) — when the URL
 *     deep-links to an atomic surface, the shell foregrounds it in the
 *     open-surfaces registry. Replaces the pre-D13 recordVisit/
 *     lastActive concept with the open-surfaces-registry foreground
 *     pointer.
 *   - The setup-confirm modal (still mounted at shell level for now).
 *
 * What ShellCompositor owns:
 *   - All chrome surface mounting (top bar, dock, launcher, future
 *     chat composer)
 *   - The main content region (SurfaceViewport + children fallback)
 */

import { useEffect, useCallback, useRef } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { createClient } from '@/lib/supabase/client';
import { NarrativeProvider, useNarrative } from '@/contexts/NarrativeContext';
import { BreadcrumbProvider } from '@/contexts/BreadcrumbContext';
import { FeedbackProvider } from '@/contexts/FeedbackContext';
import type { DeskSurface } from '@/types/desk';
import { ShellCompositor } from './ShellCompositor';
import { ShellChromeProvider } from './ShellChromeContext';
import { useComposition } from '@/lib/compositor/useComposition';
import {
  SurfacePreferencesProvider,
  useSurfacePreferences,
} from '@/lib/shell/useSurfacePreferences';
import { SetupConfirmModal } from '@/components/modals/SetupConfirmModal';

interface AuthenticatedLayoutProps {
  children: React.ReactNode;
  /**
   * Resolved server-side in app/(authenticated)/layout.tsx. The shell no
   * longer fetches the user client-side or blocks first paint on it —
   * middleware.ts is the gate. This prop just feeds the chrome (UserMenu).
   */
  userEmail?: string;
}

export default function AuthenticatedLayout({ children, userEmail }: AuthenticatedLayoutProps) {
  const router = useRouter();
  const supabase = createClient();

  // Live sign-out invalidation only — NOT an auth gate. Middleware already
  // refreshed + gated the session server-side before this component rendered;
  // re-checking with getUser() here only added a redundant round-trip behind a
  // full-screen spinner. We keep the listener so a sign-out in another tab (or
  // an expired session surfaced by onAuthStateChange) bounces to login live.
  useEffect(() => {
    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((event, session) => {
      if (event === 'SIGNED_OUT' || !session) {
        const next = `${window.location.pathname}${window.location.search}`;
        router.replace(`/auth/login?next=${encodeURIComponent(next)}`);
      }
    });

    return () => subscription.unsubscribe();
  }, [router, supabase.auth]);

  return (
    <FeedbackProvider>
      <BreadcrumbProvider>
        <SurfacePreferencesProvider>
          <ShellChromeProvider userEmail={userEmail}>
            <AuthenticatedLayoutInner>{children}</AuthenticatedLayoutInner>
          </ShellChromeProvider>
        </SurfacePreferencesProvider>
      </BreadcrumbProvider>
    </FeedbackProvider>
  );
}

// Inner component runs inside SurfacePreferencesProvider (the window
// manager — ADR-297 Phase 3 deleted the legacy DeskProvider) so it can
// foreground surfaces; runs inside ShellChromeProvider so chrome
// surfaces (TopBar) can read userEmail + launcher state.
function AuthenticatedLayoutInner({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const { data: composition } = useComposition();
  const { foregroundSurface, navigateToSurface, foregrounded, closeSurface } =
    useSurfacePreferences();

  // ADR-297 D13: when the URL deep-links to an atomic kernel surface,
  // foreground it in the open-surfaces registry (auto-open if not yet
  // open). Replaces the pre-D13 recordVisit/lastActive flow with the
  // foreground pointer in the multi-mount registry. Resolves the
  // active surface slug by matching the current pathname against the
  // surface registry's routes (longest-prefix wins).
  //
  // D18.2 (2026-05-22): the previously-paired "Effect B" that handled
  // URL-sync-on-close (foregrounded===null && open===[] → /desktop)
  // has been DELETED. URL sync now happens synchronously inside
  // `closeSurface` itself in useSurfacePreferences — when a foreground
  // close runs, the pathname is updated in the same React batch as the
  // registry mutation, so this effect's pathname-match below sees
  // either /desktop or the fallback surface's route on its next run
  // (no resurrection of the just-closed surface). Operator-observed
  // race fixed (KVK 2026-05-22 — couldn't close the topmost window).
  // Singular Implementation: one URL-sync path, owned by closeSurface.
  //
  // 2026-06-01 re-fire-loop fix (operator-observed: "on /feed, click a
  // Dock icon → the new window flashes to top, then Feed reclaims top").
  // ROOT CAUSE: `foregroundSurface` is a useCallback with `open` in its
  // deps, so its identity changes whenever the open-set changes. This
  // effect listed `foregroundSurface` as a dependency, so clicking a Dock
  // icon (which mutates `open`) re-ran this effect with the SAME pathname
  // (bare Dock-nav doesn't change the URL per D19.2). On /feed the
  // pathname still matched the Feed surface → foregroundSurface('feed')
  // fired → Feed reclaimed foreground + top z. The effect is meant for
  // GENUINE pathname transitions only (cold-load deep-link, real
  // navigation), not open-set churn. Guard with a last-synced-pathname
  // ref so a re-run triggered by callback-identity change (same pathname)
  // is a no-op. Same shape as the D18.3 re-fire guard.
  const lastSyncedPathname = useRef<string | null>(null);
  useEffect(() => {
    if (pathname === lastSyncedPathname.current) return; // no-op on churn
    if (!composition.surfaces || composition.surfaces.length === 0) return;
    lastSyncedPathname.current = pathname;
    const sorted = [...composition.surfaces].sort(
      (a, b) => b.route.length - a.route.length
    );
    const match = sorted.find(
      (s) => s.route && (pathname === s.route || pathname.startsWith(s.route + '/'))
    );
    if (match) foregroundSurface(match.slug);
  }, [pathname, composition.surfaces, foregroundSurface]);

  // D18 §4: ⌘W (macOS) / Ctrl+W (others) closes the foregrounded
  // window. macOS-standard 'close window' binding. Works regardless
  // of what's visible (e.g. when the Launcher overlay is open and
  // intercepting clicks). preventDefault avoids browser's tab-close.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const isCloseKey = (e.metaKey || e.ctrlKey) && e.key === 'w';
      if (!isCloseKey) return;
      if (!foregrounded) return; // nothing to close
      e.preventDefault();
      closeSurface(foregrounded);
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [foregrounded, closeSurface]);

  // Handle surface change from TP tool results (NarrativeContext handoff
  // machinery — when the agent says "I opened Cadence for you", it emits
  // a DeskSurface here).
  //
  // ADR-297 D19.5 (navigation enactment): the legacy DeskSurface kinds
  // map to atomic kernel surfaces via navigateToSurface — window-opening,
  // not router.push route-replacement. The task-detail → 'recurrence' slug
  // corrects the prior wrong mapping (it pushed to /agents, a relic from
  // before /work dissolved into the Recurrence surface per ADR-297 D1;
  // surface renamed Cadence → Recurrence 2026-06-03).
  const handleSurfaceChange = useCallback(
    (newSurface: DeskSurface, handoffMessage?: string) => {
      switch (newSurface.type) {
        case 'agent-list':
          navigateToSurface('agents');
          return;
        case 'agent-detail':
          navigateToSurface('agents', { agent: newSurface.agentId });
          return;
        case 'task-detail':
          navigateToSurface('recurrence', { task: newSurface.taskSlug });
          return;
        case 'document-list':
        case 'platform-list':
        case 'context-browser':
          navigateToSurface('files');
          return;
        case 'platform-detail':
          navigateToSurface('files', { platform: newSurface.platform });
          return;
        case 'document-viewer':
          // /docs/{id} is an operator-external public page (D19.4), not a
          // kernel surface — stays a route push (transport, not nav).
          router.push(`/docs/${newSurface.documentId}`);
          return;
        case 'atomic':
          // TP handed off an atomic surface directly — open it.
          navigateToSurface(newSurface.slug, newSurface.params);
          return;
      }
      // idle / unhandled kinds: no-op. ADR-297 Phase 3 deleted the legacy
      // DeskState setSurface fallback — its handoff-message display sink
      // was never read by SurfaceViewport (which renders from the window
      // manager), so the fallback was dead. handoffMessage is dropped;
      // the navigation itself is the live effect.
    },
    [navigateToSurface, router]
  );

  return (
    <NarrativeProvider onSurfaceChange={handleSurfaceChange}>
      <ShellCompositor>{children}</ShellCompositor>

      {/* Setup Confirmation Modal - rendered inside NarrativeProvider */}
      <SetupConfirmModalWrapper />
    </NarrativeProvider>
  );
}

// Separate component to access NarrativeContext inside NarrativeProvider
function SetupConfirmModalWrapper() {
  const { setupConfirmModal, closeSetupConfirmModal } = useNarrative();

  return (
    <SetupConfirmModal
      open={setupConfirmModal.open}
      data={setupConfirmModal.data}
      onClose={closeSetupConfirmModal}
    />
  );
}
