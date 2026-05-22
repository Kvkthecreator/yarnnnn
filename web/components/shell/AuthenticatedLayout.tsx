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
 * What this file owns after D11:
 *   - Auth check + loading state
 *   - Provider stack (BreadcrumbProvider · DeskProvider · NarrativeProvider
 *     · ShellChromeProvider)
 *   - The NarrativeContext.onSurfaceChange handoff machinery, because
 *     it couples auth-shell-level routing (router.push) with the
 *     legacy DeskSurface kinds (agent-list, document-viewer, etc.)
 *     and isn't a surface concern.
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

import { useEffect, useState, useCallback } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { createClient } from '@/lib/supabase/client';
import { DeskProvider, useDesk } from '@/contexts/DeskContext';
import { NarrativeProvider, useNarrative } from '@/contexts/NarrativeContext';
import { BreadcrumbProvider } from '@/contexts/BreadcrumbContext';
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
}

export default function AuthenticatedLayout({ children }: AuthenticatedLayoutProps) {
  const [userEmail, setUserEmail] = useState<string | undefined>();
  const [loading, setLoading] = useState(true);
  const router = useRouter();
  const supabase = createClient();

  useEffect(() => {
    const loginRedirect = () => {
      const next = `${window.location.pathname}${window.location.search}`;
      router.replace(`/auth/login?next=${encodeURIComponent(next)}`);
    };

    const checkAuth = async () => {
      const {
        data: { user },
      } = await supabase.auth.getUser();

      if (!user) {
        loginRedirect();
        return;
      }

      setUserEmail(user.email ?? undefined);
      setLoading(false);
    };

    checkAuth();

    // Listen for auth changes
    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((event, session) => {
      if (event === 'SIGNED_OUT' || !session) {
        loginRedirect();
      }
    });

    return () => subscription.unsubscribe();
  }, [router, supabase.auth]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <h1 className="text-2xl font-brand mb-2">yarnnn</h1>
          <p className="text-muted-foreground">Loading...</p>
        </div>
      </div>
    );
  }

  return (
    <BreadcrumbProvider>
      <DeskProvider>
        <SurfacePreferencesProvider>
          <ShellChromeProvider userEmail={userEmail}>
            <AuthenticatedLayoutInner>{children}</AuthenticatedLayoutInner>
          </ShellChromeProvider>
        </SurfacePreferencesProvider>
      </DeskProvider>
    </BreadcrumbProvider>
  );
}

// Inner component runs inside DeskProvider so it can dispatch surface
// changes; runs inside ShellChromeProvider so chrome surfaces (TopBar)
// can read userEmail + launcher state.
function AuthenticatedLayoutInner({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const { setSurface, setSurfaceWithHandoff } = useDesk();
  const { data: composition } = useComposition();
  const { foregroundSurface, foregrounded, closeSurface } =
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
  useEffect(() => {
    if (!composition.surfaces || composition.surfaces.length === 0) return;
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
  // machinery). Stays at shell level because it couples router.push with
  // the legacy DeskSurface kinds (agent-list, document-viewer, etc.).
  const handleSurfaceChange = useCallback(
    (newSurface: DeskSurface, handoffMessage?: string) => {
      switch (newSurface.type) {
        case 'agent-list':
          router.push('/agents');
          return;
        case 'agent-detail':
          router.push(`/agents?agent=${newSurface.agentId}`);
          return;
        case 'document-list':
          router.push('/context');
          return;
        case 'document-viewer':
          router.push(`/docs/${newSurface.documentId}`);
          return;
        case 'platform-list':
          router.push('/context');
          return;
        case 'platform-detail':
          router.push(`/context/${newSurface.platform}`);
          return;
        case 'context-browser':
          router.push('/context');
          return;
        case 'task-detail':
          router.push(`/agents`);
          return;
      }

      // For remaining surfaces, use surface system
      if (handoffMessage) {
        setSurfaceWithHandoff(newSurface, handoffMessage);
      } else {
        setSurface(newSurface);
      }
    },
    [setSurface, setSurfaceWithHandoff, router]
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
